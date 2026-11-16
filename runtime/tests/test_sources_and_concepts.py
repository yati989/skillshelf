import subprocess
import tempfile
import unittest
from pathlib import Path

from knowledge_base.concepts import ConceptMap
from knowledge_base.models import ConceptMappingStatus, SourceCandidate
from knowledge_base.orchestrator import SubjectWorkflow
from knowledge_base.sources import HTMLAdapter, PDFAdapter, RepositoryAdapter, SourceProcessor


class FakeOCR:
    provider_id = "fixture-ocr"

    def extract_page(self, pdf_path, page_number):
        return "Scanned routing diagram explanation." if page_number == 2 else ""


class SourceAdapterTests(unittest.TestCase):
    def test_bibliographic_source_roles_route_to_transport_adapters(self):
        processor = SourceProcessor()
        self.assertIsInstance(processor.adapters["web-book"], HTMLAdapter)
        self.assertIsInstance(processor.adapters["standard"], HTMLAdapter)
        self.assertIsInstance(processor.adapters["paper"], PDFAdapter)

    def test_html_adapter_preserves_headings_and_readable_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "article.html"
            path.write_text(
                "<html><body><h1>Routing</h1><p>Routers forward packets.</p>"
                "<ul><li>Inspect destination</li></ul></body></html>",
                encoding="utf-8",
            )
            source = SourceCandidate(
                source_id="routing-article",
                title="Routing Article",
                uri=str(path),
                source_type="web",
                role="complementary",
                reason="Fixture",
                coverage=["routing"],
            )
            document, markdown = HTMLAdapter().convert(source, path)
            self.assertEqual(document.blocks[0].kind, "heading")
            self.assertEqual(document.blocks[1].heading_path, ["Routing"])
            self.assertIn("# Routing", markdown)
            self.assertIn("Routers forward packets", markdown)

    def test_pdf_adapter_records_pages_and_warnings_with_controlled_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.pdf"
            path.write_bytes(b"%PDF-1.4 fixture")

            def runner(command):
                if command[0] == "pdfinfo":
                    return subprocess.CompletedProcess(command, 0, "Pages: 2\nTitle: Fixture\n", "")
                return subprocess.CompletedProcess(
                    command, 0, "Transport Layer\n\nReliable delivery.\f\f", ""
                )

            source = SourceCandidate(
                source_id="networking-pdf",
                title="Networking PDF",
                uri=str(path),
                source_type="pdf",
                role="foundational",
                reason="Fixture",
                coverage=["transport"],
            )
            document, markdown = PDFAdapter(runner=runner).convert(source, path)
            self.assertEqual(document.metadata["page_count_extracted"], "2")
            self.assertEqual(document.blocks[0].page, 1)
            self.assertIn("No text extracted from page 2", document.warnings)
            self.assertIn("<!-- source-page: 1 -->", markdown)

    def test_pdf_adapter_uses_optional_ocr_fallback_for_textless_page(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.pdf"
            path.write_bytes(b"%PDF-1.4 fixture")

            def runner(command):
                if command[0] == "pdfinfo":
                    return subprocess.CompletedProcess(command, 0, "Pages: 2\n", "")
                return subprocess.CompletedProcess(command, 0, "Text page.\f\f", "")

            source = SourceCandidate(
                source_id="scanned-pdf",
                title="Scanned PDF",
                uri=str(path),
                source_type="pdf",
                role="specialist",
                reason="Fixture",
                coverage=["routing"],
            )
            document, markdown = PDFAdapter(
                runner=runner, ocr_provider=FakeOCR()
            ).convert(source, path)
            self.assertTrue(any(block.page == 2 for block in document.blocks))
            self.assertIn("required OCR", " ".join(document.warnings))
            self.assertEqual(document.metadata["ocr_provider"], "fixture-ocr")
            self.assertIn("Scanned routing diagram", markdown)

    def test_repository_adapter_preserves_file_and_line_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "book"
            repository.mkdir()
            (repository / "transport.rst").write_text(
                "Transport\n=========\n\nTCP provides a byte stream.\n", encoding="utf-8"
            )
            (repository / "application.md").write_text(
                "# HTTP\n\nHTTP defines messages.\n", encoding="utf-8"
            )
            source = SourceCandidate(
                source_id="open-book",
                title="Open Book",
                uri=str(repository),
                source_type="repository",
                role="foundational",
                reason="Fixture",
                coverage=["TCP", "HTTP"],
            )
            acquired, document, markdown = SourceProcessor().process(
                source, root / "originals"
            )
            self.assertTrue(acquired.is_dir())
            self.assertEqual(document.metadata["readable_file_count"], 2)
            self.assertTrue(
                any(block.location.startswith("file:transport.rst:lines:") for block in document.blocks)
            )
            self.assertIn("<!-- source-file: application.md -->", markdown)

    def test_repository_adapter_extracts_static_html_chapters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "web-book"
            repository.mkdir()
            (repository / "chapter.html").write_text(
                "<h1>Latency</h1><p>Latency constrains request completion.</p>",
                encoding="utf-8",
            )
            source = SourceCandidate(
                source_id="web-book",
                title="Web Book",
                uri=str(repository),
                source_type="repository",
                role="specialist",
                reason="Fixture",
                coverage=["latency"],
            )
            document, markdown = RepositoryAdapter().convert(source, repository)
            self.assertEqual(document.metadata["readable_file_count"], 1)
            self.assertTrue(
                any(block.location == "file:chapter.html:html-block:2" for block in document.blocks)
            )
            self.assertIn("# Latency", markdown)

    def test_html_adapter_preserves_nested_heading_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "guide.html"
            path.write_text(
                "<h1>HTTP</h1><h2>Requests</h2><p>A request has a method.</p>",
                encoding="utf-8",
            )
            source = SourceCandidate(
                source_id="http-guide",
                title="HTTP Guide",
                uri=str(path),
                source_type="web",
                role="specialist",
                reason="Fixture",
                coverage=["HTTP"],
            )
            document, _ = HTMLAdapter().convert(source, path)
            self.assertEqual(document.blocks[-1].heading_path, ["HTTP", "Requests"])


class ConceptMapTests(unittest.TestCase):
    def test_rejected_mapping_requires_new_evidence_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            workflow = SubjectWorkflow.create(
                root,
                "Networking",
                "Learn routing",
                "Routing",
                Path(directory) / "personal-context",
            )
            concepts = ConceptMap(workflow.store, workflow.subject_id)
            concepts.propose(
                "Routing",
                ["packet forwarding"],
                [{"source_id": "fixture", "location": "section:1"}],
                0.6,
            )
            rejected = concepts.set_status(
                "Routing", ConceptMappingStatus.REJECTED, "Conflated routing with forwarding"
            )
            self.assertEqual(rejected["status"], "rejected")
            self.assertEqual(len(rejected["audit"]), 1)
            with self.assertRaises(ValueError):
                concepts.propose(
                    "Routing",
                    ["forwarding"],
                    [{"source_id": "fixture", "location": "section:2"}],
                    0.7,
                )


if __name__ == "__main__":
    unittest.main()
