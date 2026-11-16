import json
import tempfile
import unittest
from pathlib import Path

from knowledge_base.models import ProgressStatus, SourceCandidate, WorkflowPhase
from knowledge_base.orchestrator import SubjectWorkflow, WorkflowError


class SubjectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "workspace"
        self.personal_context_root = Path(self.temporary.name) / "personal-context"
        self.source_path = Path(self.temporary.name) / "networking.md"
        self.source_path.write_text(
            "# Transport\n\nTCP provides reliable ordered delivery.\n\n"
            "# Application\n\nHTTP carries application messages over a transport.\n",
            encoding="utf-8",
        )
        self.workflow = SubjectWorkflow.create(
            self.root,
            "Computer Networking",
            "Understand how loading a website works",
            "Website Loading",
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
            reason="Provides a coherent protocol overview",
            coverage=["TCP", "HTTP"],
            author="Fixture Author",
            reputation_basis="Controlled foundational fixture",
            access_strategy="Local learner-provided file",
            preferred_artifact="Exact local Markdown fixture",
            access_status="local",
            license_status="test fixture",
            inspection_status="inspected",
        )

    def grounding(self):
        return {
            "grounding_note": "The source supplies the protocol mechanism and boundary.",
            "sources": [
                {
                    "kind": "course",
                    "source_id": "networking-notes",
                    "location": "lines:3-7",
                }
            ],
        }

    def prepare_sources(self):
        self.workflow.propose_sources([self.candidate()])
        self.workflow.decide_source("networking-notes", True, "Approved for pilot")
        self.workflow.approve_corpus()
        self.workflow.process_sources()

    def approve_course(self):
        self.workflow.propose_course(
            {
                "outcome": "Explain a browser request",
                "assumed_prerequisites": ["basic Python"],
                "concepts": ["TCP", "HTTP"],
                "lesson_order": ["TCP", "HTTP"],
                "deferred": ["congestion control details"],
            }
        )
        self.workflow.approve_course()

    def test_independent_lesson_packets_and_checkpoints(self):
        self.prepare_sources()
        self.approve_course()
        first = self.workflow.begin_lesson(["TCP"])
        second = self.workflow.begin_lesson(["HTTP"])
        with self.assertRaises(WorkflowError):
            self.workflow.complete_lesson("Done", {"HTTP": "HTTP chapter"}, {})
        second_packet = self.workflow.complete_lesson("Done", {"HTTP": "HTTP chapter"}, {}, lesson_id=second)
        self.assertIn(first, self.workflow.state["open_lessons"])
        first_packet = self.workflow.complete_lesson("Done", {"TCP": "TCP chapter"}, {}, lesson_id=first)
        with self.assertRaises(WorkflowError):
            self.workflow.add_assessment_question("Ambiguous", ["TCP"], ["transfer"], "rubric")
        for aid, concept in ((first_packet, "TCP"), (second_packet, "HTTP")):
            self.workflow.add_assessment_question(
                "Explain", [concept], ["transfer"], "rubric",
                self.grounding(), assessment_id=aid
            )
            if concept == "TCP":
                self.workflow.add_assessment_question(
                    "Transfer", [concept], ["transfer"], "rubric",
                    self.grounding(), assessment_id=aid
                )
            self.workflow.freeze_assessment(aid, {"concepts": {concept: ["q001"]}})
        self.workflow.checkpoint_assessment(first_packet, {"question_id": "q001", "selected_probe": "Prepared probe"})
        self.workflow.checkpoint_assessment(first_packet, {"question_id": "q002", "selected_probe": None})
        with self.assertRaises(WorkflowError):
            self.workflow.checkpoint_assessment(first_packet, {"question_id": "q001", "selected_probe": "Different probe"})
        self.workflow.checkpoint_assessment(first_packet, {"question_id": "q001", "selected_probe": "Prepared probe"})
        self.workflow.select_assessment(second_packet)
        self.workflow.record_assessment_result("q001", "HTTP response", None, 1, 1, "Good", assessment_id=second_packet)
        first_record = self.workflow.store.read_json(self.workflow._assessment_path(first_packet))
        self.assertIsNone(first_record["questions"][0]["result"])
        self.assertEqual(first_record["checkpoint"]["selected_probe"], "Prepared probe")
        with self.assertRaises(WorkflowError):
            self.workflow.add_assessment_question("Extra", ["HTTP"], ["transfer"], "rubric", assessment_id=second_packet)
        with self.assertRaises(WorkflowError):
            self.workflow.record_assessment_result("q001", "overwrite", None, 0, 1, "No", assessment_id=second_packet)
        self.workflow.finalize_assessment({"HTTP": {"status": "demonstrated", "evidence": "Novel answer", "score": 1, "out_of": 1, "independent_evidence": True}}, assessment_id=second_packet)
        self.workflow.select_assessment(first_packet)
        self.assertEqual(self.workflow.store.read_json(self.workflow._assessment_path(first_packet))["checkpoint"]["selected_probe"], "Prepared probe")

    def test_legacy_course_threshold_is_preserved(self):
        self.prepare_sources()
        self.approve_course()
        path = self.workflow.store.track_path(self.workflow.subject_id, self.workflow.track_id) / "course-plan.json"
        plan = self.workflow.store.read_json(path)
        plan["pass_standard"] = {"overall": "At least 50% of all available points.", "per_required_concept": "At least 50% of allocated points."}
        self.workflow.store.write_json(path, plan)
        self.assertEqual(self.workflow._pass_standard(), {"overall_percent": 50.0, "required_concept_percent": 50.0})

    def test_complete_external_workflow(self):
        self.assertEqual(self.workflow.phase, WorkflowPhase.SOURCE_RESEARCH)
        self.workflow.propose_sources([self.candidate()])
        with self.assertRaises(WorkflowError):
            self.workflow.approve_corpus()

        self.workflow.decide_source("networking-notes", True, "Approved for pilot")
        self.workflow.approve_corpus()
        self.workflow.process_sources()
        markdown_view = (
            self.root
            / "subjects"
            / "computer-networking"
            / "sources"
            / "markdown"
            / "networking-notes"
        )
        self.assertTrue((markdown_view / "index.md").exists())
        self.assertTrue((markdown_view / "001-transport.md").exists())
        matches = self.workflow.search("reliable delivery")
        self.assertEqual(matches[0]["source_id"], "networking-notes")
        self.assertIn("lines:", matches[0]["location"])

        self.approve_course()
        lesson_id = self.workflow.begin_lesson(["TCP", "HTTP"])
        with self.assertRaises(WorkflowError):
            self.workflow.complete_lesson("okay", {"TCP": "Draft"}, {})
        self.assertFalse(
            (self.root / "subjects" / "computer-networking" / "knowledge-book" / "tcp.md").exists()
        )

        assessment_id = self.workflow.complete_lesson(
            "Done.",
            {
                "TCP": "TCP adds ordered, reliable delivery above an unreliable packet layer.",
                "HTTP": "HTTP defines application messages and relies on a transport.",
            },
            {
                "TCP": [
                    {
                        "source_id": "networking-notes",
                        "location": "lines:3-3",
                        "excerpt": "TCP provides reliable ordered delivery.",
                    }
                ],
                "HTTP": [
                    {
                        "source_id": "networking-notes",
                        "location": "lines:7-7",
                        "excerpt": "HTTP carries application messages over a transport.",
                    }
                ],
            },
            [
                {
                    "key": "teaching.analogy.python-protocols",
                    "fact": "Python protocol analogies were helpful",
                    "confidence": "high",
                    "evidence": "Learner used the analogy to explain TCP and HTTP boundaries.",
                }
            ],
        )
        self.assertEqual(self.workflow.phase, WorkflowPhase.ASSESSMENT_PENDING)
        tcp_chapter = (
            self.root / "subjects" / "computer-networking" / "knowledge-book" / "tcp.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Source evidence", tcp_chapter)
        self.assertIn("networking-notes", tcp_chapter)

        tcp_question = self.workflow.add_assessment_question(
            "What changes if packets arrive out of order?",
            ["TCP"],
            ["prediction", "mechanism"],
            "Explain sequence handling and application-visible ordering.",
            self.grounding(),
        )
        http_question = self.workflow.add_assessment_question(
            "Design a request that exposes the boundary between HTTP and TCP.",
            ["HTTP", "TCP"],
            ["construction", "boundary"],
            "Separate application semantics from transport behavior.",
            self.grounding(),
        )
        self.workflow.record_assessment_result(
            tcp_question,
            "TCP uses sequence information to reconstruct ordered bytes.",
            None,
            8,
            10,
            "Correct mechanism; retransmission detail was omitted.",
        )
        self.workflow.record_assessment_result(
            http_question,
            None,
            {"path": "exercise/client.py", "sha256": "fixture-hash"},
            7,
            10,
            "The protocol boundary is visible, with one missing failure case.",
            assistance="One hint about message framing",
        )
        self.workflow.finalize_assessment(
            {
                "TCP": {
                    "status": ProgressStatus.DEMONSTRATED.value,
                    "evidence": "Predicted reordering behavior independently.",
                },
                "HTTP": {
                    "status": ProgressStatus.DEVELOPING.value,
                    "evidence": "Constructed a valid example with one hint.",
                },
            }
        )
        self.assertEqual(self.workflow.phase, WorkflowPhase.TRACK_READY)

        assessment_path = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / "website-loading"
            / "assessments"
            / (assessment_id + ".json")
        )
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        self.assertEqual(assessment["status"], "completed")
        self.assertEqual(len(assessment["questions"]), 2)
        self.assertEqual(assessment["questions"][0]["result"]["score"], 8)
        self.assertEqual(assessment["questions"][1]["result"]["artifact"]["path"], "exercise/client.py")

        self.workflow.approve_memory_proposal(
            lesson_id,
            [
                {
                    "key": "teaching.analogy.python-protocols",
                    "fact": "Python protocol analogies are effective",
                    "confidence": "high",
                    "evidence": "Learner independently transferred the analogy during assessment.",
                }
            ],
        )
        profile = json.loads(
            (self.personal_context_root / "profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual(profile["schema_version"], 3)
        self.assertEqual(len(profile["facts"]), 1)
        self.assertEqual(
            profile["facts"][0]["key"], "teaching-analogy-python-protocols"
        )
        self.assertEqual(profile["facts"][0]["source"]["subject_id"], "computer-networking")
        history = list((self.personal_context_root / "history").glob("*.json"))
        self.assertEqual(len(history), 1)

    def test_global_personal_profile_updates_a_key_across_workspaces(self):
        first_lesson = "lesson-first"
        first_proposal = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / "website-loading"
            / "memory-proposals"
            / (first_lesson + ".json")
        )
        self.workflow.store.write_json(
            first_proposal,
            {
                "lesson_id": first_lesson,
                "status": "pending",
                "proposals": [],
                "created_at": "fixture",
            },
        )
        self.workflow.approve_memory_proposal(
            first_lesson,
            [
                {
                    "key": "assessment.depth",
                    "fact": "Prefers transfer questions over direct recall",
                    "confidence": "medium",
                    "evidence": "Rejected a recall-only assessment.",
                }
            ],
        )

        second_workspace = Path(self.temporary.name) / "other-workspace"
        statistics = SubjectWorkflow.create(
            second_workspace,
            "Statistics",
            "Understand statistical reasoning",
            "Foundations",
            self.personal_context_root,
        )
        second_lesson = "lesson-second"
        second_proposal = (
            second_workspace
            / "subjects"
            / "statistics"
            / "tracks"
            / "foundations"
            / "memory-proposals"
            / (second_lesson + ".json")
        )
        statistics.store.write_json(
            second_proposal,
            {
                "lesson_id": second_lesson,
                "status": "pending",
                "proposals": [],
                "created_at": "fixture",
            },
        )
        statistics.approve_memory_proposal(
            second_lesson,
            [
                {
                    "key": "assessment.depth",
                    "fact": "Requires novel, integrated transfer problems rather than recall",
                    "confidence": "high",
                    "evidence": "Repeated the preference while defining the final exam.",
                }
            ],
        )

        profile = json.loads(
            (self.personal_context_root / "profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(profile["facts"]), 1)
        self.assertEqual(profile["facts"][0]["key"], "assessment-depth")
        self.assertEqual(
            profile["facts"][0]["fact"],
            "Requires novel, integrated transfer problems rather than recall",
        )
        self.assertEqual(profile["facts"][0]["source"]["subject_id"], "statistics")
        history = sorted((self.personal_context_root / "history").glob("*.json"))
        self.assertEqual(len(history), 2)
        history_changes = [
            json.loads(path.read_text(encoding="utf-8"))["changes"][0]
            for path in history
        ]
        last_change = next(
            change for change in history_changes if change["action"] == "updated"
        )
        self.assertEqual(last_change["action"], "updated")
        self.assertEqual(
            last_change["before"]["fact"],
            "Prefers transfer questions over direct recall",
        )

    def test_processing_is_blocked_before_corpus_approval(self):
        self.workflow.propose_sources([self.candidate()])
        self.workflow.decide_source("networking-notes", True, "Good source")
        with self.assertRaises(WorkflowError):
            self.workflow.process_sources()

    def test_source_proposal_requires_quality_first_research_record(self):
        incomplete = SourceCandidate(
            source_id="convenient-download",
            title="Convenient Download",
            uri=str(self.source_path),
            source_type="markdown",
            role="foundational",
            reason="Easy to access",
            coverage=["TCP"],
        )
        with self.assertRaisesRegex(ValueError, "quality-first research fields"):
            self.workflow.propose_sources([incomplete])

    def test_research_revision_preserves_accepted_sources(self):
        accepted = self.candidate()
        rejected = SourceCandidate(
            source_id="weak-notes",
            title="Weak Notes",
            uri=str(self.source_path),
            source_type="markdown",
            role="complementary",
            reason="Candidate",
            coverage=["HTTP"],
            reputation_basis="Controlled complementary fixture",
            access_strategy="Local learner-provided file",
            preferred_artifact="Exact local Markdown fixture",
        )
        self.workflow.propose_sources([accepted, rejected])
        self.workflow.decide_source("networking-notes", True, "Keep")
        self.workflow.decide_source("weak-notes", False, "Replace")
        replacement = SourceCandidate(
            source_id="better-notes",
            title="Better Notes",
            uri=str(self.source_path),
            source_type="markdown",
            role="complementary",
            reason="Clearer treatment",
            coverage=["HTTP"],
            reputation_basis="Controlled replacement fixture",
            access_strategy="Local learner-provided file",
            preferred_artifact="Exact local Markdown fixture",
        )
        self.workflow.propose_sources([replacement])
        manifest = self.workflow.source_manifest()
        statuses = {item["source_id"]: item["status"] for item in manifest["sources"]}
        self.assertEqual(statuses["networking-notes"], "approved")
        self.assertEqual(statuses["weak-notes"], "rejected")
        self.assertEqual(statuses["better-notes"], "proposed")
        self.workflow.decide_source("better-notes", True, "Use replacement")
        self.workflow.approve_corpus()

    def test_assessment_result_cannot_be_overwritten(self):
        self.prepare_sources()
        self.approve_course()
        self.workflow.begin_lesson(["TCP"])
        self.workflow.complete_lesson(
            "done",
            {"TCP": "A complete TCP explanation."},
            {"TCP": [{"source_id": "networking-notes", "location": "lines:3-3"}]},
        )
        question_id = self.workflow.add_assessment_question(
            "Predict a retransmission outcome.", ["TCP"], ["prediction"],
            "Correct causal chain.", self.grounding()
        )
        self.workflow.record_assessment_result(
            question_id, "First answer", None, 5, 10, "Partial"
        )
        with self.assertRaises(WorkflowError):
            self.workflow.record_assessment_result(
                question_id, "Replacement answer", None, 10, 10, "Overwrite"
            )

    def test_assessment_question_requires_and_preserves_real_source_grounding(self):
        self.prepare_sources()
        self.approve_course()
        self.workflow.begin_lesson(["TCP"])
        assessment_id = self.workflow.complete_lesson(
            "done",
            {"TCP": "A complete TCP explanation."},
            {"TCP": [{"source_id": "networking-notes", "location": "lines:3-3"}]},
        )
        with self.assertRaisesRegex(WorkflowError, "source-grounding note"):
            self.workflow.add_assessment_question(
                "Unsupported question.", ["TCP"], ["transfer"], "rubric"
            )

        external = {
            "grounding_note": "The external standard supplies the failure constraint.",
            "sources": [
                {
                    "kind": "external",
                    "title": "Example Networking Standard",
                    "uri": "https://example.org/networking-standard",
                    "location": "section 4",
                    "retrieved_at": "2026-10-26",
                    "publisher": "Example Standards Body",
                }
            ],
        }
        question_id = self.workflow.add_assessment_question(
            "Diagnose the failure.", ["TCP"], ["diagnosis"], "rubric", external
        )
        assessment = self.workflow.store.read_json(
            self.workflow._assessment_path(assessment_id)
        )
        stored = next(q for q in assessment["questions"] if q["question_id"] == question_id)
        self.assertEqual(stored["source_grounding"]["sources"][0]["kind"], "external")

    def test_multiple_tracks_share_subject_workspace_but_keep_separate_plans(self):
        self.prepare_sources()
        first_track = self.workflow.track_id
        second_track = self.workflow.create_track(
            "Build Networked App", "Build and debug a small networked application"
        )
        self.assertEqual(second_track, "build-networked-app")
        self.workflow.propose_course(
            {
                "outcome": "Build a networked application",
                "assumed_prerequisites": ["Python"],
                "concepts": ["TCP"],
                "lesson_order": ["TCP"],
                "deferred": ["HTTP"],
            }
        )
        second_plan = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / second_track
            / "course-plan.json"
        )
        self.assertTrue(second_plan.exists())
        self.workflow.activate_track(first_track)
        self.assertEqual(self.workflow.track_id, "website-loading")
        first_plan = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / first_track
            / "course-plan.json"
        )
        self.assertFalse(first_plan.exists())

    def test_reassessment_is_append_only_and_retention_requires_later_evidence(self):
        self.prepare_sources()
        self.approve_course()
        self.workflow.begin_lesson(["TCP"])
        first_assessment = self.workflow.complete_lesson(
            "done",
            {"TCP": "TCP provides an ordered reliable byte stream."},
            {"TCP": [{"source_id": "networking-notes", "location": "lines:3-3"}]},
        )
        question = self.workflow.add_assessment_question(
            "Explain packet reordering.", ["TCP"], ["mechanism"],
            "Explain ordering.", self.grounding()
        )
        self.workflow.record_assessment_result(
            question, "Sequence information restores order.", None, 9, 10, "Sound."
        )
        with self.assertRaises(WorkflowError):
            self.workflow.finalize_assessment(
                {"TCP": {"status": ProgressStatus.RETAINED.value, "evidence": "Immediate answer"}}
            )
        self.workflow.finalize_assessment(
            {"TCP": {"status": ProgressStatus.DEMONSTRATED.value, "evidence": "Independent mechanism"}}
        )

        second_assessment = self.workflow.start_reassessment(
            ["TCP"], "Later retention check", retention_revisit=True
        )
        second_question = self.workflow.add_assessment_question(
            "Transfer ordering to a new protocol.", ["TCP"], ["transfer"],
            "Correct transfer.", self.grounding()
        )
        self.workflow.record_assessment_result(
            second_question, "Use sequence positions and buffering.", None, 9, 10, "Transferred."
        )
        self.workflow.finalize_assessment(
            {"TCP": {"status": ProgressStatus.RETAINED.value, "evidence": "Later transfer"}}
        )

        assessments_dir = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / "website-loading"
            / "assessments"
        )
        first = json.loads((assessments_dir / (first_assessment + ".json")).read_text())
        second = json.loads((assessments_dir / (second_assessment + ".json")).read_text())
        self.assertEqual(first["attempt"], 1)
        self.assertEqual(second["attempt"], 2)
        self.assertEqual(second["questions"][0]["attempt"], 2)
        self.assertEqual(first["questions"][0]["result"]["answer"], "Sequence information restores order.")

    def test_course_revisions_require_reason_and_preserve_each_version(self):
        self.prepare_sources()
        self.approve_course()
        self.workflow.begin_lesson(["TCP"])
        self.workflow.complete_lesson(
            "done",
            {"TCP": "TCP provides reliable delivery."},
            {"TCP": [{"source_id": "networking-notes", "location": "lines:3-3"}]},
        )
        question = self.workflow.add_assessment_question(
            "Explain reliability.", ["TCP"], ["mechanism"],
            "Correct mechanism.", self.grounding()
        )
        self.workflow.record_assessment_result(
            question, "Acknowledgments and retransmission.", None, 8, 10, "Good."
        )
        self.workflow.finalize_assessment(
            {"TCP": {"status": ProgressStatus.DEMONSTRATED.value, "evidence": "Mechanism"}}
        )
        revised = {
            "outcome": "Debug a browser request",
            "assumed_prerequisites": ["basic Python"],
            "concepts": ["TCP", "HTTP"],
            "lesson_order": ["HTTP", "TCP"],
            "deferred": ["congestion control details"],
        }
        with self.assertRaises(ValueError):
            self.workflow.propose_course(revised)
        revised["revision_reason"] = "Assessment showed application framing matters first"
        self.workflow.propose_course(revised)
        versions = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / "website-loading"
            / "course-plans"
        )
        self.assertTrue((versions / "v001.json").exists())
        self.assertTrue((versions / "v002.json").exists())

    def test_nonperfect_assessment_can_pass_and_demonstrate_concepts(self):
        self.prepare_sources()
        self.approve_course()
        self.workflow.begin_lesson(["TCP", "HTTP"])
        assessment_id = self.workflow.complete_lesson(
            "done",
            {"TCP": "Reliable transport.", "HTTP": "Application messages."},
            {
                "TCP": [{"source_id": "networking-notes", "location": "lines:3-3"}],
                "HTTP": [{"source_id": "networking-notes", "location": "lines:7-7"}],
            },
        )
        question = self.workflow.add_assessment_question(
            "Trace and diagnose one request.",
            ["TCP", "HTTP"],
            ["transfer", "diagnosis"],
            {"maximum_score": 100},
            self.grounding(),
        )
        self.workflow.record_assessment_result(
            question, "Partly correct trace with omissions.", None, 33, 100, "Passes at cutoff."
        )
        self.workflow.finalize_assessment(
            {
                "TCP": {
                    "status": "developing",
                    "evidence": "Independent novel trace with a minor omission.",
                    "score": 33,
                    "out_of": 100,
                    "independent_evidence": True,
                    "critical_gap": False,
                },
                "HTTP": {
                    "status": "developing",
                    "evidence": "Independent diagnosis with a noncritical error.",
                    "score": 33,
                    "out_of": 100,
                    "independent_evidence": True,
                    "critical_gap": False,
                },
            }
        )

        assessment_path = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / "website-loading"
            / "assessments"
            / (assessment_id + ".json")
        )
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        self.assertEqual(assessment["outcome"], "passed")
        self.assertEqual(assessment["summary"]["percent"], 33.0)
        self.assertEqual(assessment["judgments"]["TCP"]["status"], "demonstrated")
        self.assertEqual(assessment["judgments"]["HTTP"]["status"], "demonstrated")

    def test_cumulative_final_exam_is_distinct_and_append_only(self):
        self.prepare_sources()
        self.approve_course()
        self.workflow.begin_lesson(["TCP", "HTTP"])
        self.workflow.complete_lesson(
            "done",
            {"TCP": "Reliable transport.", "HTTP": "Application messages."},
            {
                "TCP": [{"source_id": "networking-notes", "location": "lines:3-3"}],
                "HTTP": [{"source_id": "networking-notes", "location": "lines:7-7"}],
            },
        )
        lesson_question = self.workflow.add_assessment_question(
            "Trace one request.", ["TCP", "HTTP"], ["transfer"],
            {"maximum_score": 1}, self.grounding()
        )
        self.workflow.record_assessment_result(
            lesson_question, "HTTP uses TCP.", None, 1, 1, "Correct."
        )
        self.workflow.finalize_assessment(
            {
                "TCP": {"status": "demonstrated", "evidence": "Independent trace."},
                "HTTP": {"status": "demonstrated", "evidence": "Independent trace."},
            }
        )

        exam_id = self.workflow.start_final_exam(
            {"coverage": {"request-case": ["TCP", "HTTP"]}}
        )
        self.assertEqual(self.workflow.phase, WorkflowPhase.FINAL_EXAM_PENDING)
        question_id = self.workflow.add_final_exam_question(
            "Diagnose a novel failure.",
            ["TCP", "HTTP"],
            ["diagnosis", "transfer"],
            {"maximum_score": 2},
            self.grounding(),
        )
        self.workflow.record_final_exam_result(
            question_id, "Separate transport from application behavior.", None, 2, 2, "Correct."
        )
        with self.assertRaises(WorkflowError):
            self.workflow.record_final_exam_result(
                question_id, "Overwrite.", None, 2, 2, "Not allowed."
            )
        self.workflow.finalize_final_exam(
            {
                "TCP": {"status": "demonstrated", "evidence": "Cumulative diagnosis."},
                "HTTP": {"status": "demonstrated", "evidence": "Cumulative diagnosis."},
            }
        )
        exam_path = (
            self.root
            / "subjects"
            / "computer-networking"
            / "tracks"
            / "website-loading"
            / "final-exams"
            / (exam_id + ".json")
        )
        exam = json.loads(exam_path.read_text(encoding="utf-8"))
        self.assertEqual(exam["kind"], "cumulative_final_exam")
        self.assertEqual(exam["status"], "completed")
        self.assertEqual(exam["outcome"], "passed")
        self.assertEqual(self.workflow.phase, WorkflowPhase.TRACK_READY)


    def test_new_grounded_packet_attempt_preserves_frozen_lesson_checkpoint(self):
        self.prepare_sources()
        self.approve_course()
        lesson_id = self.workflow.begin_lesson(["TCP", "HTTP"])
        original_id = self.workflow.complete_lesson(
            "Done",
            {"TCP": "Reliable transport.", "HTTP": "Application messages."},
            {},
            lesson_id=lesson_id,
        )
        self.workflow.add_assessment_question(
            "Original packet question.", ["TCP"], ["transfer"], "original rubric",
            self.grounding(), assessment_id=original_id
        )
        self.workflow.freeze_assessment(original_id, {"concepts": {"TCP": ["q001"], "HTTP": ["q001"]}})
        self.workflow.checkpoint_assessment(
            original_id, {"question_id": "q001", "selected_probe": None}
        )
        original_path = self.workflow._assessment_path(original_id)
        original_before = json.loads(original_path.read_text(encoding="utf-8"))

        revised_id = self.workflow.start_assessment_attempt(
            lesson_id, "Generate a source-grounded packet under the current assessment rules."
        )
        self.assertNotEqual(revised_id, original_id)
        revised_question = self.workflow.add_assessment_question(
            "A source-grounded transfer question.",
            ["TCP", "HTTP"],
            ["diagnosis", "transfer"],
            json.dumps({
                "max_score": 2,
                "concept_points": {"TCP": 1, "HTTP": 1},
                "eligible_probes": [
                    {"prompt": "Prepared probe A", "expected_evidence": "Evidence A"},
                    {"prompt": "Prepared probe B", "expected_evidence": "Evidence B"},
                ],
            }),
            self.grounding(),
            assessment_id=revised_id,
        )
        self.workflow.freeze_assessment(
            revised_id,
            {"concepts": {"TCP": [revised_question], "HTTP": [revised_question]}},
        )

        original_after = json.loads(original_path.read_text(encoding="utf-8"))
        revised = self.workflow.store.read_json(self.workflow._assessment_path(revised_id))
        self.assertEqual(original_after, original_before)
        self.assertEqual(revised["lesson_id"], lesson_id)
        self.assertEqual(revised["attempt"], 2)
        self.assertEqual(revised["supersedes_assessment_id"], original_id)
        self.assertTrue(revised["packet_frozen_at"])
        stored_grounding = revised["questions"][0]["source_grounding"]
        self.assertEqual(stored_grounding["grounding_note"], self.grounding()["grounding_note"])
        self.assertEqual(stored_grounding["sources"][0]["source_id"], "networking-notes")
        self.assertTrue(stored_grounding["sources"][0]["source_hash"])
        self.assertEqual(self.workflow.state["active_assessment_id"], revised_id)


if __name__ == "__main__":
    unittest.main()
