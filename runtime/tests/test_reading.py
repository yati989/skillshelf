import json
import tempfile
import unittest
import fcntl
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from knowledge_base.models import DocumentBlock, StructuredDocument
from knowledge_base.reading import ReadingError, ReadingWorkspace


class ReadingWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = (Path(self.temporary.name) / "workspace").resolve()
        self.workspace = ReadingWorkspace(self.root)
        self.source = Path(self.temporary.name) / "book.md"
        self.source.write_text(
            "# Mind\n\nConsciousness is a question about subjective experience.\n\n"
            "## Language\n\nLanguage can express a thought without settling its truth.\n\n"
            "# Art\n\nA story can sustain several interpretations.\n", encoding="utf-8")

    def ingest(self):
        return self.workspace.ingest(self.source, "Mind and Art", source_id="mind-art")

    def citation(self, resource=None):
        resource = resource or self.ingest()
        return {"source_id": resource["source_id"], "source_hash": resource["current_hash"],
                "block_id": "b00002", "quote": "subjective experience"}

    def note(self, **overrides):
        value = {"kind": "wiki", "id": "consciousness", "title": "Consciousness",
                 "body": "An unresolved question about experience.", "citations": [self.citation()]}
        value.update(overrides)
        return value

    def test_end_to_end_reload_and_source_preservation(self):
        before = self.source.read_bytes()
        resource = self.ingest()
        version = resource["versions"][resource["current_hash"]]
        self.assertEqual(version["status"], "ready")
        self.assertEqual((self.root / version["original_path"]).read_bytes(), before)
        self.assertEqual(self.source.read_bytes(), before)
        hit = self.workspace.search("subjective experience", "mind-art")[0]
        self.assertEqual(hit["source_hash"], resource["current_hash"])
        self.assertIn("b00002", hit["block_ids"])
        saved = self.workspace.save_note(self.note())
        reloaded = ReadingWorkspace(self.root)
        self.assertEqual(reloaded.resources()[0]["current_hash"], resource["current_hash"])
        self.assertIn("subjective experience", reloaded.read("mind-art", "Mind")["blocks"][1]["text"])
        self.assertEqual(saved["revision"], 1)
        self.assertIn(resource["current_hash"], Path(saved["path"]).read_text())
        self.assertEqual(len(reloaded.search("consciousness")), 1)

    def test_init_and_duplicate_ingest_are_idempotent_and_preserve_tutor(self):
        legacy = self.root / "learner-profile/profile.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"facts":[{"fact":"Original preference"}]}')
        tutor = self.root / "subjects/old/track.json"
        tutor.parent.mkdir(parents=True)
        tutor.write_text('{"phase":"assessing"}')
        self.workspace.initialize()
        (self.root / "INDEX.md").write_text("Handwritten index\n")
        self.workspace.initialize()
        self.assertEqual((self.root / "INDEX.md").read_text(), "Handwritten index\n")
        self.assertIn("Original preference", legacy.read_text())
        self.assertIn("assessing", tutor.read_text())
        self.assertEqual(self.workspace.context()["legacy_profile"], str(legacy))
        first = self.ingest()
        with patch.object(self.workspace.processor, "process", side_effect=AssertionError("Reprocessed")):
            second = self.ingest()
        self.assertTrue(second["unchanged"])
        self.assertEqual(first["versions"], second["versions"])
        self.assertFalse((self.root / "history").exists())

    def test_citation_errors_do_not_modify_notes_or_initialize_workspace(self):
        before = set(self.root.rglob("*"))
        with self.assertRaises(ReadingError):
            self.workspace.save_note({"kind": "wiki", "id": "missing", "title": "Missing",
                                      "body": "Unverifiable", "citations": [{"source_id": "unknown",
                                      "source_hash": "a" * 64, "block_id": "b00001"}]})
        self.assertEqual(before, set(self.root.rglob("*")))
        self.ingest()
        valid = self.note()
        for field, value in [("source_hash", "f" * 64), ("block_id", "absent"), ("quote", "invented words")]:
            payload = dict(valid, citations=[dict(valid["citations"][0], **{field: value})])
            with self.assertRaises(ReadingError):
                self.workspace.save_note(payload)
        self.assertFalse((self.root / "wiki/consciousness.md").exists())

    def test_note_corrections_keep_revisions_and_reject_conflicts(self):
        first = self.workspace.save_note(self.note())
        with self.assertRaisesRegex(ReadingError, "Revision conflict"):
            self.workspace.save_note(self.note(body="Lost update"))
        corrected = self.workspace.save_note(self.note(body="A corrected interpretation.", expected_revision=1))
        self.assertEqual(corrected["revision"], 2)
        snapshot = self.root / "records/reading-revisions/wiki/consciousness/000001.md"
        self.assertIn("unresolved", snapshot.read_text())
        self.assertIn("corrected", Path(first["path"]).read_text())
        with self.assertRaisesRegex(ReadingError, "Revision conflict"):
            self.workspace.save_note(self.note(expected_revision=1))
        Path(first["path"]).write_text("Manual correction\n")
        with self.assertRaisesRegex(ReadingError, "manually modified"):
            self.workspace.save_note(self.note(expected_revision=2))
        self.assertEqual(Path(first["path"]).read_text(), "Manual correction\n")
        context = self.workspace.context()["wiki_notes"][0]
        self.assertTrue(context["modified"])
        self.assertEqual(context["revision"], 2)
        with self.assertRaisesRegex(ReadingError, "Content conflict"):
            self.workspace.save_note(self.note(expected_revision=2, expected_content_hash="f" * 64))
        third = self.workspace.save_note(self.note(body="Manual correction plus a new connection.",
            expected_revision=2, expected_content_hash=context["current_content_hash"]))
        self.assertEqual(third["revision"], 3)
        manual = self.root / "records/reading-revisions/wiki/consciousness" / (
            "manual-" + context["current_content_hash"] + ".md")
        self.assertEqual(manual.read_text(), "Manual correction\n")
        self.assertFalse(self.workspace.context()["wiki_notes"][0]["modified"])

    def test_old_citations_remain_resolvable_after_refresh(self):
        old = self.ingest()
        original_citation = self.citation(old)
        self.source.write_text("# New edition\n\nA revised account of experience.\n")
        new = self.ingest()
        self.assertNotEqual(old["current_hash"], new["current_hash"])
        self.assertEqual(len(new["versions"]), 2)
        saved = self.workspace.save_note(self.note(citations=[original_citation]))
        self.assertEqual(saved["citations"][0]["source_hash"], old["current_hash"])
        self.assertIn("Consciousness", self.workspace.document("mind-art", old["current_hash"]).blocks[1].text)

    def tutor_document(self, warnings=None, blocks=None):
        document = StructuredDocument("tutor-book", "Existing Book", "markdown", "b" * 64, {},
            blocks if blocks is not None else [DocumentBlock("b00001", "paragraph",
                    "A reusable explanation of memory.", "lines:1-1")], warnings or [])
        path = self.root / "subjects/topic/sources/structured/tutor-book.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document.to_dict()))
        return path

    def test_concurrent_source_versions_remain_resolvable(self):
        original = self.ingest()
        paths = []
        for number in [2, 3]:
            path = Path(self.temporary.name) / ("edition{0}.md".format(number))
            path.write_text("# Edition {0}\n\nA changed account of experience.\n".format(number))
            paths.append(path)
        first_processing = threading.Event()
        second_lock_attempted = threading.Event()
        state = threading.local()
        process = self.workspace.processor.process
        flock = fcntl.flock

        def observed_lock(fd, operation):
            if getattr(state, "role", None) == "second":
                second_lock_attempted.set()
            return flock(fd, operation)

        def controlled_process(*args, **kwargs):
            if state.role == "first":
                first_processing.set()
                self.assertTrue(second_lock_attempted.wait(5), "Second importer never attempted its lock")
            return process(*args, **kwargs)

        def ingest_version(role, path):
            state.role = role
            if role == "second":
                self.assertTrue(first_processing.wait(5), "First importer never began acquisition")
            return self.workspace.ingest(path, "Mind and Art", source_id="mind-art")

        with patch("knowledge_base.reading.fcntl.flock", side_effect=observed_lock), \
                patch.object(self.workspace.processor, "process", side_effect=controlled_process), \
                ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(ingest_version, "first", paths[0])
            second = executor.submit(ingest_version, "second", paths[1])
            results = [original, first.result(timeout=10), second.result(timeout=10)]
        reloaded = ReadingWorkspace(self.root)
        self.assertEqual(len(reloaded.resources()[0]["versions"]), 3)
        for resource in results:
            self.assertEqual(reloaded.document("mind-art", resource["current_hash"]).source_hash,
                             resource["current_hash"])

    def test_reuse_keeps_original_tutor_document_and_copies_no_original(self):
        path = self.tutor_document()
        before = path.read_bytes()
        resource = self.workspace.reuse(path)
        version = resource["versions"][resource["current_hash"]]
        self.assertIsNone(version["original_path"])
        self.assertEqual(version["reused_from"], str(path.relative_to(self.root)))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list((self.root / "library/originals").iterdir()), [])
        path.write_text("changed tutor state")
        self.assertIn("memory", self.workspace.document("tutor-book").blocks[0].text)

    def test_quality_review_and_empty_extraction(self):
        resource = self.workspace.reuse(self.tutor_document(warnings=["Needs page inspection"]))
        version = resource["versions"][resource["current_hash"]]
        self.assertEqual(version["status"], "review_required")
        self.assertEqual(self.workspace.search("memory"), [])
        self.assertIn("Needs page inspection", self.workspace.read("tutor-book")["warnings"])
        with self.assertRaises(ReadingError):
            self.workspace.review("tutor-book", " ")
        reviewed = self.workspace.review("tutor-book", "Compared the extracted passage with the original")
        self.assertEqual(reviewed["versions"][reviewed["current_hash"]]["status"], "ready")
        self.assertTrue(self.workspace.search("memory"))
        empty = Path(self.temporary.name) / "empty.txt"
        empty.write_text("")
        self.workspace.ingest(empty, "Empty")
        with self.assertRaisesRegex(ReadingError, "Failed or empty"):
            self.workspace.review("empty", "Accept anyway")

    def test_truncated_read_reports_scope_and_exact_locations(self):
        self.ingest()
        bounded = self.workspace.read("mind-art", section="Mind", max_chars=20)
        self.assertTrue(bounded["truncated"])
        self.assertEqual(bounded["scope"], "Mind")
        self.assertEqual(sum(len(block["text"]) for block in bounded["blocks"]), 20)
        self.assertTrue(bounded["blocks"][-1]["truncated"])
        self.assertTrue(all(block["location"].startswith("lines:") for block in bounded["blocks"]))
        with self.assertRaisesRegex(ReadingError, "No exact section"):
            self.workspace.read("mind-art", "Missing chapter")

    def test_review_records_captured_version_when_an_import_intervenes(self):
        path = self.tutor_document(warnings=["Inspect this extraction"])
        first = self.workspace.reuse(path)
        changed = json.loads(path.read_text())
        changed['source_hash'] = 'c' * 64
        path.write_text(json.dumps(changed))
        source_lock = self.workspace._source_lock
        intervened = False

        @contextmanager
        def interleaved_lock(source_id):
            nonlocal intervened
            if not intervened:
                intervened = True
                self.workspace.reuse(path)
            with source_lock(source_id):
                yield

        with patch.object(self.workspace, '_source_lock', interleaved_lock):
            result = self.workspace.review('tutor-book', 'Checked the original extraction')
        self.assertEqual(result['reviewed_hash'], first['current_hash'])
        self.assertEqual(result['current_hash'], 'c' * 64)
        self.assertEqual(result['versions'][first['current_hash']]['status'], 'ready')
        self.assertEqual(result['versions']['c' * 64]['status'], 'review_required')
        event = json.loads((self.root / 'records/reading-log.jsonl').read_text().splitlines()[-1])
        self.assertEqual(event['action'], 'review')
        self.assertEqual(event['reviewed_hash'], first['current_hash'])

    def test_context_is_read_only_before_initialization(self):
        self.assertFalse(self.workspace.context()["initialized"])
        self.assertEqual(self.workspace.context()["self_notes"], [])
        self.assertFalse(self.root.exists())

    def test_index_failure_reports_that_resource_was_saved(self):
        with patch.object(self.workspace, "reindex", side_effect=ReadingError("Existing source is damaged")):
            resource = self.ingest()
        self.assertIn("Resource saved", resource["index_warning"])
        self.assertEqual(self.workspace.document("mind-art").source_hash, resource["current_hash"])
        self.assertTrue(self.workspace.search("mind", "mind-art"))

    def test_navigation_log_and_concurrent_note_updates(self):
        self.workspace.save_note(self.note())
        def update(body):
            try:
                return self.workspace.save_note(self.note(body=body, expected_revision=1))["revision"]
            except ReadingError:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(update, ["First interpretation", "Second interpretation"]))
        self.assertCountEqual(results, [2, "conflict"])
        navigation = (self.root / "indexes/reading-index.md").read_text()
        self.assertIn("../wiki/consciousness.md", navigation)
        self.assertIn("Mind and Art", navigation)
        events = [json.loads(line) for line in (self.root / "records/reading-log.jsonl").read_text().splitlines()]
        self.assertEqual([event["action"] for event in events], ["ingest", "save_note", "save_note"])

    def test_personal_attribution_and_related_notes(self):
        historical = {"kind": "self", "id": "timeline", "title": "Interest history",
                      "body": "An episode of literary exploration.", "attribution": "historical_observation",
                      "basis": "Summary of an earlier discussion of the activity export."}
        self.workspace.save_note(historical)
        with self.assertRaises(ReadingError):
            self.workspace.save_note(dict(historical, id="belief", category="worldview"))
        saved = self.workspace.save_note(dict(historical, id="current", category="preferences",
            attribution="user_statement", body="I prefer conversational reading.",
            basis="The user explicitly requested this reading style.", links=["self/timeline.md"]))
        self.assertIn("../self/timeline.md", Path(saved["path"]).read_text())
        self.assertFalse((self.root / "learner-profile/profile.json").exists())

    def test_traversal_symlinks_and_modified_extraction_are_rejected(self):
        for value in ["../escape", "/tmp/escape", "has/slash", "..", "UPPERCASE"]:
            with self.assertRaises(ReadingError):
                self.workspace.ingest(self.source, "Title", source_id=value)
        with self.assertRaises(ReadingError):
            self.workspace.reuse(self.source)
        self.workspace.initialize()
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text("Outside")
        (self.root / "self/escape.md").symlink_to(outside)
        with self.assertRaises(ReadingError):
            self.workspace.save_note({"kind": "wiki", "id": "unsafe", "title": "Unsafe",
                                      "body": "Unsafe", "links": ["self/escape.md"]})
        resource = self.ingest()
        path = self.root / resource["versions"][resource["current_hash"]]["structured_path"]
        path.write_text("{}")
        with self.assertRaisesRegex(ReadingError, "modified"):
            self.workspace.search("mind")


if __name__ == "__main__":
    unittest.main()
