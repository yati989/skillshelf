import json
import tempfile
import unittest
from pathlib import Path

from knowledge_base.concepts import ConceptMap
from knowledge_base.models import DocumentBlock, SourceCandidate, StructuredDocument, WorkflowPhase
from knowledge_base.orchestrator import SubjectWorkflow, WorkflowError


class WarningProcessor:
    def __init__(self, subject_dir):
        self.subject_dir = subject_dir

    def process(self, source, originals_dir):
        acquired = originals_dir / "warning-source.txt"
        acquired.write_text("Recovered content", encoding="utf-8")
        document = StructuredDocument(
            source_id=source.source_id,
            title=source.title,
            source_type=source.source_type,
            source_hash="a" * 64,
            metadata={"filename": acquired.name},
            blocks=[
                DocumentBlock(
                    block_id="b00001",
                    kind="paragraph",
                    text="Recovered transport content",
                    location="lines:1-1",
                    confidence=0.7,
                )
            ],
            warnings=["Fixture requires human review"],
        )
        return acquired, document, "Recovered transport content\n"


class AliasEmbeddingProvider:
    model_id = "fixture-alias-v1"

    def embed(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    float("reliable" in lowered or "dependable" in lowered),
                    float("http" in lowered or "web" in lowered),
                    0.1,
                ]
            )
        return vectors


class QualityRetrievalAndVersionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "workspace"
        self.personal_context_root = Path(self.temporary.name) / "personal-context"
        self.source_path = Path(self.temporary.name) / "networking.md"
        self.source_path.write_text(
            "# Transport\n\nTCP provides reliable ordered delivery.\n\n"
            "# Application\n\nHTTP carries web messages.\n",
            encoding="utf-8",
        )
        self.workflow = SubjectWorkflow.create(
            self.root,
            "Networking",
            "Understand browser loading",
            "Browser Loading",
            self.personal_context_root,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def candidate(self):
        return SourceCandidate(
            source_id="networking-notes",
            title="Networking Notes",
            uri=str(self.source_path),
            source_type="markdown",
            role="foundational",
            reason="Coherent fixture",
            coverage=["TCP", "HTTP"],
            reputation_basis="Controlled foundational fixture",
            access_strategy="Local learner-provided file",
            preferred_artifact="Exact local Markdown fixture",
            inspection_status="inspected",
        )

    def approve(self):
        self.workflow.propose_sources([self.candidate()])
        self.workflow.decide_source("networking-notes", True, "Approved")
        self.workflow.approve_corpus()

    def test_quality_review_blocks_retrieval_until_human_approval(self):
        self.approve()
        self.workflow.process_sources(WarningProcessor(self.workflow.subject_dir))
        self.assertEqual(self.workflow.phase, WorkflowPhase.SOURCE_QUALITY_REVIEW)
        with self.assertRaises(WorkflowError):
            self.workflow.search("transport")
        self.workflow.approve_source_quality("networking-notes", "Readable in manual check")
        self.assertEqual(self.workflow.phase, WorkflowPhase.SOURCES_READY)
        self.assertEqual(self.workflow.search("transport")[0]["source_id"], "networking-notes")

    def test_review_required_source_can_be_reprocessed_after_parser_improvement(self):
        self.approve()
        self.workflow.process_sources(WarningProcessor(self.workflow.subject_dir))
        self.assertEqual(self.workflow.phase, WorkflowPhase.SOURCE_QUALITY_REVIEW)

        self.workflow.process_sources()

        self.assertEqual(self.workflow.phase, WorkflowPhase.SOURCES_READY)
        self.assertEqual(
            self.workflow.source_manifest()["sources"][0]["status"], "ready"
        )

    def test_hybrid_retrieval_finds_an_alias_and_keeps_provenance(self):
        self.approve()
        self.workflow.process_sources()
        provider = AliasEmbeddingProvider()
        self.workflow.build_vector_index(provider)
        matches = self.workflow.hybrid_search(
            "dependable byte stream", provider, lexical_weight=0.1
        )
        self.assertEqual(matches[0]["source_id"], "networking-notes")
        self.assertIn("lines:", matches[0]["location"])
        self.assertGreater(matches[0]["semantic_score"], 0.5)

    def test_refresh_preserves_versions_and_invalidates_dependencies(self):
        self.approve()
        self.workflow.process_sources()
        first_hash = self.workflow.source_manifest()["sources"][0]["source_hash"]
        stale_markdown = (
            self.workflow.subject_dir
            / "sources"
            / "markdown"
            / "networking-notes"
            / "obsolete.md"
        )
        stale_markdown.write_text("obsolete derivative", encoding="utf-8")
        ConceptMap(self.workflow.store, self.workflow.subject_id).propose(
            "TCP",
            ["reliable stream"],
            [{"source_id": "networking-notes", "location": "lines:3-3"}],
            0.9,
        )
        metadata_path = self.workflow.subject_dir / "knowledge-book" / "tcp.json"
        self.workflow.store.write_json(
            metadata_path,
            {
                "concept": "TCP",
                "citations": [
                    {
                        "source_id": "networking-notes",
                        "source_hash": first_hash,
                        "location": "lines:3-3",
                    }
                ],
                "history": [],
            },
        )

        self.source_path.write_text(
            "# Transport\n\nTCP is a reliable ordered byte stream with retransmission.\n",
            encoding="utf-8",
        )
        self.workflow.propose_source_refresh(
            "networking-notes", str(self.source_path), "fixture-v2", "Adds retransmission"
        )
        self.workflow.decide_source("networking-notes", True, "Approve refreshed source")
        self.workflow.approve_corpus()
        self.workflow.process_sources()
        self.assertFalse(stale_markdown.exists())

        manifest = self.workflow.source_manifest()["sources"][0]
        self.assertEqual(len(manifest["versions"]), 2)
        self.assertNotEqual(first_hash, manifest["source_hash"])
        versioned = list((self.workflow.subject_dir / "sources" / "structured").glob(
            "networking-notes-*.json"
        ))
        self.assertEqual(len(versioned), 2)
        concepts = json.loads(
            (self.workflow.subject_dir / "indexes" / "concepts.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(concepts["mappings"][0]["needs_review"])
        self.assertTrue(json.loads(metadata_path.read_text(encoding="utf-8"))["needs_review"])


if __name__ == "__main__":
    unittest.main()
