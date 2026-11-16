import tempfile
import unittest
from pathlib import Path

from knowledge_base.models import DocumentBlock, SourceCandidate, StructuredDocument
from knowledge_base.pdf_processing import (
    ExtractedPage,
    OutlineEntry,
    PDFExtraction,
    PDFIngestor,
)
from knowledge_base.rendering import split_markdown
from knowledge_base.retrieval import LexicalIndex, build_retrieval_chunks
from knowledge_base.sources import PDFAdapter


class FixtureBackend:
    backend_id = "fixture-primary"

    def extract(self, path):
        return PDFExtraction(
            backend_id=self.backend_id,
            pages=[
                ExtractedPage(1, "# Foundations\n\nNetworks move packets between hosts."),
                ExtractedPage(2, "## Forwarding\n\nA forwarding table selects an output link."),
                ExtractedPage(3, "# Transport\n\nTCP exposes a reliable byte stream."),
            ],
            outline=[
                OutlineEntry(1, "Foundations", 1),
                OutlineEntry(2, "Forwarding", 2),
                OutlineEntry(1, "Transport", 3),
            ],
            metadata={"page_count": 3},
        )


class RecordingFallback:
    provider_id = "fixture-layout"

    def __init__(self):
        self.pages = []

    def extract_page(self, pdf_path, page_number):
        self.pages.append(page_number)
        return "Recovered diagram labels and explanatory prose."


class DifficultPageBackend:
    backend_id = "fixture-difficult"

    def extract(self, path):
        return PDFExtraction(
            backend_id=self.backend_id,
            pages=[
                ExtractedPage(1, "A complete page with enough readable networking content."),
                ExtractedPage(2, "?", 0.2, ["Very little text extracted"]),
            ],
            metadata={"page_count": 2},
        )


def candidate(path):
    return SourceCandidate(
        source_id="networking-book",
        title="Networking Book",
        uri=str(path),
        source_type="pdf",
        role="foundational",
        reason="Fixture",
        coverage=["routing", "transport"],
    )


class HierarchicalPDFTests(unittest.TestCase):
    def test_outline_drives_hierarchy_and_split_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.pdf"
            path.write_bytes(b"fixture")
            document, _ = PDFAdapter(
                ingestor=PDFIngestor(primary=FixtureBackend())
            ).convert(candidate(path), path)

            forwarding = next(block for block in document.blocks if "output link" in block.text)
            self.assertEqual(forwarding.heading_path, ["Foundations", "Forwarding"])
            self.assertEqual(forwarding.section, "Forwarding")
            self.assertEqual(document.metadata["outline_entry_count"], 3)

            artifacts = split_markdown(document)
            self.assertIn("001-foundations.md", artifacts)
            self.assertIn("002-transport.md", artifacts)
            self.assertIn("[Foundations](001-foundations.md)", artifacts["index.md"])
            self.assertIn("<!-- page:2 -->", artifacts["001-foundations.md"])

    def test_only_rejected_pages_are_sent_to_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.pdf"
            path.write_bytes(b"fixture")
            fallback = RecordingFallback()
            document, _ = PDFAdapter(
                ingestor=PDFIngestor(
                    primary=DifficultPageBackend(), page_fallback=fallback
                )
            ).convert(candidate(path), path)

            self.assertEqual(fallback.pages, [2])
            self.assertEqual(document.metadata["fallback_pages"], [2])
            self.assertTrue(any(block.page == 2 for block in document.blocks))


class RetrievalChunkTests(unittest.TestCase):
    def test_nested_headings_stay_with_their_first_substantive_paragraph(self):
        document = StructuredDocument(
            "guide",
            "Guide",
            "web",
            "a" * 64,
            {},
            [
                DocumentBlock(
                    "b1", "heading", "HTTP", "html-block:1",
                    section="HTTP", heading_path=["HTTP"]
                ),
                DocumentBlock(
                    "b2", "heading", "Requests", "html-block:2",
                    section="Requests", heading_path=["HTTP", "Requests"]
                ),
                DocumentBlock(
                    "b3", "paragraph", "A request carries a method and target.",
                    "html-block:3", section="Requests",
                    heading_path=["HTTP", "Requests"]
                ),
            ],
        )
        chunks = build_retrieval_chunks([document])
        self.assertEqual(len(chunks), 1)
        self.assertIn("method and target", chunks[0]["text"])
        self.assertEqual(chunks[0]["heading_path"], ["HTTP", "Requests"])

    def test_chunks_respect_sections_and_neighbor_context_budget(self):
        document = StructuredDocument(
            source_id="book",
            title="Book",
            source_type="pdf",
            source_hash="a" * 64,
            metadata={},
            blocks=[
                DocumentBlock(
                    "b1", "paragraph", "routing forwarding table", "page:1",
                    section="Routing", page=1, heading_path=["Network", "Routing"]
                ),
                DocumentBlock(
                    "b2", "paragraph", "longest prefix match", "page:2",
                    section="Routing", page=2, heading_path=["Network", "Routing"]
                ),
                DocumentBlock(
                    "b3", "paragraph", "reliable transport stream", "page:3",
                    section="Transport", page=3, heading_path=["Transport"]
                ),
            ],
        )
        chunks = build_retrieval_chunks([document], maximum_tokens=20)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["heading_path"], ["Network", "Routing"])
        self.assertEqual(chunks[0]["location"], "pages:1-2")

        index = LexicalIndex.build([document])
        result = LexicalIndex.search(
            index, "prefix routing", limit=1, context_token_budget=7
        )[0]
        self.assertLessEqual(result["context_token_count"], 7)
        self.assertEqual(result["context_chunk_ids"], [result["chunk_id"]])

    def test_context_does_not_cross_chapters_or_expand_without_limit(self):
        blocks = []
        for number in range(1, 8):
            blocks.append(
                DocumentBlock(
                    "b{0}".format(number),
                    "paragraph",
                    "routing detail{0}{1}".format(
                        number, " needle" if number == 4 else ""
                    ),
                    "page:{0}".format(number),
                    section="Section {0}".format(number),
                    page=number,
                    heading_path=["Routing", "Section {0}".format(number)],
                )
            )
        blocks.append(
            DocumentBlock(
                "b8", "paragraph", "transport boundary", "page:8",
                section="Transport", page=8, heading_path=["Transport"]
            )
        )
        document = StructuredDocument(
            "book", "Book", "pdf", "a" * 64, {}, blocks
        )
        index = LexicalIndex.build([document])
        result = LexicalIndex.search(index, "needle", limit=1)[0]
        self.assertEqual(len(result["context_chunk_ids"]), 3)
        context_chunks = {
            chunk["chunk_id"]: chunk for chunk in index["chunks"]
        }
        self.assertTrue(
            all(
                context_chunks[chunk_id]["heading_path"][0] == "Routing"
                for chunk_id in result["context_chunk_ids"]
            )
        )
        transport = LexicalIndex.search(index, "transport boundary", limit=1)[0]
        self.assertEqual(transport["context_chunk_ids"], [transport["chunk_id"]])


if __name__ == "__main__":
    unittest.main()
