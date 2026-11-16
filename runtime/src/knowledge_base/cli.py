"""Command-line entrypoint for deterministic workspace operations."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SourceCandidate
from .orchestrator import SubjectWorkflow


def _load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kb-tutor")
    parser.add_argument("--root", default=".", help="Knowledge-base workspace root")
    parser.add_argument(
        "--personal-context-root",
        type=Path,
        help="Override the user-level personal-context root",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialize = subparsers.add_parser("init")
    initialize.add_argument("--subject", required=True)
    initialize.add_argument("--intent", required=True)
    initialize.add_argument("--track", required=True)

    for name in ("status", "approve-corpus", "process-sources", "approve-course"):
        command = subparsers.add_parser(name)
        command.add_argument("--subject", required=True)

    propose_sources = subparsers.add_parser("propose-sources")
    propose_sources.add_argument("--subject", required=True)
    propose_sources.add_argument("--file", required=True)

    decide_source = subparsers.add_parser("decide-source")
    decide_source.add_argument("--subject", required=True)
    decide_source.add_argument("--source-id", required=True)
    decide_source.add_argument("--decision", choices=("approve", "reject"), required=True)
    decide_source.add_argument("--reason", required=True)

    propose_course = subparsers.add_parser("propose-course")
    propose_course.add_argument("--subject", required=True)
    propose_course.add_argument("--file", required=True)

    search = subparsers.add_parser("search")
    search.add_argument("--subject", required=True)
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)

    begin_lesson = subparsers.add_parser("begin-lesson")
    begin_lesson.add_argument("--subject", required=True)
    begin_lesson.add_argument("--concept", action="append", required=True)

    complete_lesson = subparsers.add_parser("complete-lesson")
    complete_lesson.add_argument("--subject", required=True)
    complete_lesson.add_argument("--signal", required=True)
    complete_lesson.add_argument("--chapters", required=True)
    complete_lesson.add_argument("--citations", required=True)
    complete_lesson.add_argument("--memory-proposals")
    complete_lesson.add_argument("--lesson-id")

    new_attempt = subparsers.add_parser("new-assessment-attempt")
    new_attempt.add_argument("--subject", required=True)
    new_attempt.add_argument("--lesson-id", required=True)
    new_attempt.add_argument("--reason", required=True)

    add_question = subparsers.add_parser("add-question")
    add_question.add_argument("--subject", required=True)
    add_question.add_argument("--file", required=True)

    record_result = subparsers.add_parser("record-result")
    record_result.add_argument("--subject", required=True)
    record_result.add_argument("--question-id", required=True)
    record_result.add_argument("--file", required=True)

    finalize = subparsers.add_parser("finalize-assessment")
    finalize.add_argument("--subject", required=True)
    finalize.add_argument("--judgments", required=True)
    for command in (add_question, record_result, finalize):
        command.add_argument("--assessment-id")

    select_assessment = subparsers.add_parser("select-assessment")
    select_assessment.add_argument("--subject", required=True)
    select_assessment.add_argument("--assessment-id", required=True)
    for name in ("freeze-assessment", "checkpoint-assessment"):
        command = subparsers.add_parser(name)
        command.add_argument("--subject", required=True)
        command.add_argument("--assessment-id", required=True)
        command.add_argument("--file", required=True)

    start_final = subparsers.add_parser("start-final-exam")
    start_final.add_argument("--subject", required=True)
    start_final.add_argument("--blueprint", required=True)

    add_final_question = subparsers.add_parser("add-final-exam-question")
    add_final_question.add_argument("--subject", required=True)
    add_final_question.add_argument("--file", required=True)

    record_final_result = subparsers.add_parser("record-final-exam-result")
    record_final_result.add_argument("--subject", required=True)
    record_final_result.add_argument("--question-id", required=True)
    record_final_result.add_argument("--file", required=True)

    finalize_final = subparsers.add_parser("finalize-final-exam")
    finalize_final.add_argument("--subject", required=True)
    finalize_final.add_argument("--judgments", required=True)

    approve_memory = subparsers.add_parser("approve-memory")
    approve_memory.add_argument("--subject", required=True)
    approve_memory.add_argument("--lesson-id", required=True)
    approve_memory.add_argument("--facts", required=True)

    reject_memory = subparsers.add_parser("reject-memory")
    reject_memory.add_argument("--subject", required=True)
    reject_memory.add_argument("--lesson-id", required=True)
    reject_memory.add_argument("--reason", required=True)

    reassess = subparsers.add_parser("start-reassessment")
    reassess.add_argument("--subject", required=True)
    reassess.add_argument("--concept", action="append", required=True)
    reassess.add_argument("--reason", required=True)
    reassess.add_argument("--retention", action="store_true")

    create_track = subparsers.add_parser("create-track")
    create_track.add_argument("--subject", required=True)
    create_track.add_argument("--track", required=True)
    create_track.add_argument("--intent", required=True)

    activate_track = subparsers.add_parser("activate-track")
    activate_track.add_argument("--subject", required=True)
    activate_track.add_argument("--track", required=True)

    approve_quality = subparsers.add_parser("approve-source-quality")
    approve_quality.add_argument("--subject", required=True)
    approve_quality.add_argument("--source-id", required=True)
    approve_quality.add_argument("--reason", required=True)

    refresh_source = subparsers.add_parser("refresh-source")
    refresh_source.add_argument("--subject", required=True)
    refresh_source.add_argument("--source-id", required=True)
    refresh_source.add_argument("--uri", required=True)
    refresh_source.add_argument("--edition-or-date")
    refresh_source.add_argument("--reason", required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if args.command == "init":
        workflow = SubjectWorkflow.create(
            root,
            args.subject,
            args.intent,
            args.track,
            args.personal_context_root,
        )
        result: Any = workflow.state
    else:
        workflow = SubjectWorkflow(root, args.subject, args.personal_context_root)
        if args.command == "status":
            result = workflow.state
        elif args.command == "propose-sources":
            payload = _load_json(args.file)
            workflow.propose_sources(SourceCandidate.from_dict(item) for item in payload)
            result = workflow.source_manifest()
        elif args.command == "decide-source":
            workflow.decide_source(
                args.source_id, args.decision == "approve", args.reason
            )
            result = workflow.source_manifest()
        elif args.command == "approve-corpus":
            workflow.approve_corpus()
            result = workflow.state
        elif args.command == "process-sources":
            workflow.process_sources()
            result = workflow.state
        elif args.command == "propose-course":
            workflow.propose_course(_load_json(args.file))
            result = workflow.state
        elif args.command == "approve-course":
            workflow.approve_course()
            result = workflow.state
        elif args.command == "search":
            result = workflow.search(args.query, args.limit)
        elif args.command == "begin-lesson":
            result = {"lesson_id": workflow.begin_lesson(args.concept), "state": workflow.state}
        elif args.command == "complete-lesson":
            memory = _load_json(args.memory_proposals) if args.memory_proposals else []
            result = {
                "assessment_id": workflow.complete_lesson(
                    args.signal,
                    _load_json(args.chapters),
                    _load_json(args.citations),
                    memory,
                    lesson_id=args.lesson_id,
                ),
                "state": workflow.state,
            }
        elif args.command == "new-assessment-attempt":
            result = {
                "assessment_id": workflow.start_assessment_attempt(args.lesson_id, args.reason),
                "state": workflow.state,
            }
        elif args.command == "add-question":
            question = _load_json(args.file)
            result = {
                "question_id": workflow.add_assessment_question(
                    question["prompt"],
                    question["concepts"],
                    question["dimensions"],
                    question["rubric"],
                    question["source_grounding"],
                    assessment_id=args.assessment_id,
                ),
                "state": workflow.state,
            }
        elif args.command == "record-result":
            payload = _load_json(args.file)
            workflow.record_assessment_result(
                args.question_id,
                payload.get("answer"),
                payload.get("artifact"),
                payload["score"],
                payload["out_of"],
                payload["feedback"],
                payload.get("assistance"),
                assessment_id=args.assessment_id,
            )
            result = workflow.state
        elif args.command == "finalize-assessment":
            workflow.finalize_assessment(_load_json(args.judgments), assessment_id=args.assessment_id)
            result = workflow.state
        elif args.command == "select-assessment":
            workflow.select_assessment(args.assessment_id)
            result = workflow.state
        elif args.command == "freeze-assessment":
            workflow.freeze_assessment(args.assessment_id, _load_json(args.file))
            result = workflow.state
        elif args.command == "checkpoint-assessment":
            workflow.checkpoint_assessment(args.assessment_id, _load_json(args.file))
            result = workflow.state
        elif args.command == "start-final-exam":
            result = {
                "exam_id": workflow.start_final_exam(_load_json(args.blueprint)),
                "state": workflow.state,
            }
        elif args.command == "add-final-exam-question":
            question = _load_json(args.file)
            result = {
                "question_id": workflow.add_final_exam_question(
                    question["prompt"],
                    question["concepts"],
                    question["dimensions"],
                    question["rubric"],
                    question["source_grounding"],
                ),
                "state": workflow.state,
            }
        elif args.command == "record-final-exam-result":
            payload = _load_json(args.file)
            workflow.record_final_exam_result(
                args.question_id,
                payload.get("answer"),
                payload.get("artifact"),
                payload["score"],
                payload["out_of"],
                payload["feedback"],
                payload.get("assistance"),
            )
            result = workflow.state
        elif args.command == "finalize-final-exam":
            workflow.finalize_final_exam(_load_json(args.judgments))
            result = workflow.state
        elif args.command == "approve-memory":
            facts = _load_json(args.facts)
            workflow.approve_memory_proposal(args.lesson_id, facts)
            result = workflow.state
        elif args.command == "reject-memory":
            workflow.reject_memory_proposal(args.lesson_id, args.reason)
            result = workflow.state
        elif args.command == "start-reassessment":
            result = {
                "assessment_id": workflow.start_reassessment(
                    args.concept, args.reason, args.retention
                ),
                "state": workflow.state,
            }
        elif args.command == "create-track":
            result = {
                "track_id": workflow.create_track(args.track, args.intent),
                "state": workflow.state,
            }
        elif args.command == "activate-track":
            workflow.activate_track(args.track)
            result = workflow.state
        elif args.command == "approve-source-quality":
            workflow.approve_source_quality(args.source_id, args.reason)
            result = workflow.state
        elif args.command == "refresh-source":
            workflow.propose_source_refresh(
                args.source_id, args.uri, args.edition_or_date, args.reason
            )
            result = workflow.source_manifest()
        else:
            raise AssertionError("Unhandled command")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0
