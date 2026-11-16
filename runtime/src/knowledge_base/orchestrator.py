"""High-level subject-learning workflow and its approval gates."""

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import ProgressStatus, SourceCandidate, SourceStatus, StructuredDocument, WorkflowPhase
from .personal_context import PersonalContextStore
from .quality import QualityEvaluator
from .rendering import split_markdown
from .retrieval import EmbeddingProvider, HybridRetriever, LexicalIndex, VectorIndex
from .sources import SourceProcessingError, SourceProcessor
from .storage import WorkspaceStore, slugify, utc_now


class WorkflowError(RuntimeError):
    pass


DONE_PATTERN = re.compile(r"^\s*done[.!]?\s*$", re.IGNORECASE)
DEFAULT_PASS_STANDARD = {
    "overall_percent": 33.0,
    "required_concept_percent": 33.0,
}


class SubjectWorkflow:
    """The single behavioral seam used by the skill and end-to-end tests."""

    def __init__(
        self,
        root: Path,
        subject_id: str,
        personal_context_root: Optional[Path] = None,
    ):
        self.store = WorkspaceStore(root)
        self.personal_context = PersonalContextStore(personal_context_root)
        self.subject_id = slugify(subject_id)
        self.subject_dir = self.store.subject_path(self.subject_id)
        if not (self.subject_dir / "subject.json").exists():
            raise FileNotFoundError("Unknown subject: {0}".format(self.subject_id))

    @classmethod
    def create(
        cls,
        root: Path,
        subject_name: str,
        learning_intent: str,
        track_name: str,
        personal_context_root: Optional[Path] = None,
    ) -> "SubjectWorkflow":
        store = WorkspaceStore(root)
        state = store.initialize_subject(subject_name, learning_intent, track_name)
        return cls(root, state["subject_id"], personal_context_root)

    @property
    def state(self) -> Dict[str, Any]:
        return self.store.read_json(self.subject_dir / "subject.json")

    @property
    def phase(self) -> WorkflowPhase:
        return WorkflowPhase(self.state["phase"])

    @property
    def track_id(self) -> str:
        return self.state["active_track_id"]

    def _set_phase(self, phase: WorkflowPhase, **updates: Any) -> None:
        state = self.state
        state["phase"] = phase.value
        state["updated_at"] = utc_now()
        state.update(updates)
        self.store.write_json(self.subject_dir / "subject.json", state)
        if phase in {
            WorkflowPhase.SOURCES_READY,
            WorkflowPhase.COURSE_REVIEW,
            WorkflowPhase.COURSE_APPROVED,
            WorkflowPhase.EXPLORING,
            WorkflowPhase.ASSESSMENT_PENDING,
            WorkflowPhase.ASSESSING,
            WorkflowPhase.TRACK_READY,
            WorkflowPhase.FINAL_EXAM_PENDING,
            WorkflowPhase.FINAL_EXAMINING,
        }:
            track_path = self.store.track_path(self.subject_id, self.track_id) / "track.json"
            if track_path.exists():
                track = self.store.read_json(track_path)
                track["workflow_phase"] = phase.value
                track["updated_at"] = utc_now()
                self.store.write_json(track_path, track)

    def _require_phase(self, *phases: WorkflowPhase) -> None:
        if self.phase not in phases:
            expected = ", ".join(phase.value for phase in phases)
            raise WorkflowError(
                "Operation requires phase {0}; current phase is {1}".format(
                    expected, self.phase.value
                )
            )

    def _pass_standard(self) -> Dict[str, float]:
        standard = dict(DEFAULT_PASS_STANDARD)
        course_path = self.store.track_path(self.subject_id, self.track_id) / "course-plan.json"
        if course_path.exists():
            configured = self.store.read_json(course_path).get("pass_standard", {})
            for old_key, key in (("overall", "overall_percent"),
                                 ("per_required_concept", "required_concept_percent")):
                if key not in configured and isinstance(configured.get(old_key), str):
                    match = re.search(r"(\d+(?:\.\d+)?)\s*%", configured[old_key])
                    if match:
                        standard[key] = float(match.group(1))
            for key in standard:
                if key in configured:
                    standard[key] = float(configured[key])
        if any(value < 0 or value > 100 for value in standard.values()):
            raise WorkflowError("Pass-standard percentages must fall between 0 and 100")
        return standard

    def _assessment_summary(
        self,
        questions: List[Dict[str, Any]],
        judgments: Dict[str, Dict[str, Any]],
        pass_standard: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        standard = pass_standard or self._pass_standard()
        total_score = sum(float(question["result"]["score"]) for question in questions)
        total_out_of = sum(float(question["result"]["out_of"]) for question in questions)
        overall_percent = 100.0 * total_score / total_out_of
        blocking = []
        concepts = {}
        passing_statuses = {
            ProgressStatus.DEMONSTRATED.value,
            ProgressStatus.RETAINED.value,
        }

        for concept, judgment in judgments.items():
            required = judgment.get("required", True)
            score = judgment.get("score")
            out_of = judgment.get("out_of")
            percent = None
            if score is not None or out_of is not None:
                if score is None or out_of is None or float(out_of) <= 0:
                    raise ValueError("Concept score and positive out_of must be provided together")
                if float(score) < 0 or float(score) > float(out_of):
                    raise ValueError("Concept score must fall between zero and out_of")
                percent = 100.0 * float(score) / float(out_of)

            independent = judgment.get("independent_evidence")
            critical_gap = bool(judgment.get("critical_gap", False))
            has_structured_evidence = percent is not None and independent is not None
            clears_floor = (
                has_structured_evidence
                and percent >= standard["required_concept_percent"]
                and bool(independent)
                and not critical_gap
            )
            if has_structured_evidence:
                if clears_floor and judgment["status"] != ProgressStatus.RETAINED.value:
                    judgment["status"] = ProgressStatus.DEMONSTRATED.value
                elif not clears_floor and judgment["status"] in passing_statuses:
                    judgment["status"] = ProgressStatus.DEVELOPING.value

            reasons = []
            if required:
                if judgment["status"] not in passing_statuses:
                    reasons.append("concept is not demonstrated")
                if percent is not None and percent < standard["required_concept_percent"]:
                    reasons.append("concept score is below the pass floor")
                if independent is False:
                    reasons.append("evidence is assisted-only")
                if critical_gap:
                    reasons.append("critical misconception remains")
            if reasons:
                blocking.append({"concept": concept, "reasons": reasons})
            concepts[concept] = {
                "score": score,
                "out_of": out_of,
                "percent": percent,
                "required": required,
                "independent_evidence": independent,
                "critical_gap": critical_gap,
                "status": judgment["status"],
            }

        passed = overall_percent >= standard["overall_percent"] and not blocking
        return {
            "outcome": "passed" if passed else "not_yet_passed",
            "score": total_score,
            "out_of": total_out_of,
            "percent": overall_percent,
            "pass_standard": standard,
            "concepts": concepts,
            "blocking_concepts": blocking,
        }

    def _manifest_path(self) -> Path:
        return self.subject_dir / "sources" / "manifest.json"

    def source_manifest(self) -> Dict[str, Any]:
        return self.store.read_json(self._manifest_path())

    @staticmethod
    def _record_source_status(
        item: Dict[str, Any], status: SourceStatus, reason: Optional[str] = None
    ) -> None:
        item["status"] = status.value
        event = {"status": status.value, "at": utc_now()}
        if reason:
            event["reason"] = reason
        item.setdefault("status_history", []).append(event)

    def propose_sources(self, candidates: Iterable[SourceCandidate]) -> None:
        self._require_phase(WorkflowPhase.SOURCE_RESEARCH, WorkflowPhase.SOURCE_REVIEW)
        revising = self.phase == WorkflowPhase.SOURCE_REVIEW
        proposed = list(candidates)
        if not proposed:
            raise ValueError("At least one source candidate is required")
        identifiers = [candidate.source_id for candidate in proposed]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Source identifiers must be unique")
        for candidate in proposed:
            missing = [
                name
                for name in ("reputation_basis", "access_strategy", "preferred_artifact")
                if not getattr(candidate, name)
            ]
            if missing:
                raise ValueError(
                    "Source {0} is missing quality-first research fields: {1}".format(
                        candidate.source_id, ", ".join(missing)
                    )
                )
        for candidate in proposed:
            candidate.status = SourceStatus.PROPOSED
        existing_records = self.source_manifest().get("sources", []) if revising else []
        existing_by_id = {item["source_id"]: item for item in existing_records}
        records = [item for item in existing_records if item["source_id"] not in identifiers]
        for candidate in proposed:
            record = candidate.to_dict()
            existing = existing_by_id.get(candidate.source_id)
            if (
                existing
                and existing.get("status") == SourceStatus.APPROVED.value
                and existing.get("uri") == candidate.uri
                and existing.get("title") == candidate.title
            ):
                records.append(existing)
                continue
            if existing:
                record["status_history"] = list(existing.get("status_history", []))
                if existing.get("versions"):
                    record["versions"] = list(existing["versions"])
            self._record_source_status(record, SourceStatus.PROPOSED)
            records.append(record)
        self.store.write_json(
            self._manifest_path(),
            {
                "corpus_approved": False,
                "approved_at": None,
                "sources": records,
            },
        )
        self._set_phase(WorkflowPhase.SOURCE_REVIEW)

    def decide_source(self, source_id: str, approved: bool, reason: str) -> None:
        self._require_phase(WorkflowPhase.SOURCE_REVIEW)
        manifest = self.source_manifest()
        source = next(
            (item for item in manifest["sources"] if item["source_id"] == source_id), None
        )
        if source is None:
            raise KeyError("Unknown source: {0}".format(source_id))
        self._record_source_status(
            source,
            SourceStatus.APPROVED if approved else SourceStatus.REJECTED,
            reason,
        )
        source["decision_reason"] = reason
        self.store.write_json(self._manifest_path(), manifest)

    def approve_corpus(self) -> None:
        self._require_phase(WorkflowPhase.SOURCE_REVIEW)
        manifest = self.source_manifest()
        approved = [
            item for item in manifest["sources"] if item["status"] == SourceStatus.APPROVED.value
        ]
        undecided = [
            item for item in manifest["sources"] if item["status"] == SourceStatus.PROPOSED.value
        ]
        if undecided:
            raise WorkflowError("Every proposed source needs an individual decision")
        if not approved:
            raise WorkflowError("The corpus must contain at least one approved source")
        manifest["corpus_approved"] = True
        manifest["approved_at"] = utc_now()
        self.store.write_json(self._manifest_path(), manifest)
        self._set_phase(WorkflowPhase.CORPUS_APPROVED)

    def process_sources(self, processor: Optional[SourceProcessor] = None) -> None:
        self._require_phase(
            WorkflowPhase.CORPUS_APPROVED, WorkflowPhase.SOURCE_QUALITY_REVIEW
        )
        manifest = self.source_manifest()
        if not manifest.get("corpus_approved"):
            raise WorkflowError("Corpus-level approval is required before processing")
        processor = processor or SourceProcessor()
        quality_evaluator = QualityEvaluator()
        originals = self.subject_dir / "sources" / "originals"
        documents: List[StructuredDocument] = []
        errors: List[str] = []
        for item in manifest["sources"]:
            if item["status"] in {
                SourceStatus.PROCESSED.value,
                SourceStatus.READY.value,
            }:
                structured_path = (
                    self.subject_dir
                    / "sources"
                    / "structured"
                    / (item["source_id"] + ".json")
                )
                if structured_path.exists():
                    documents.append(
                        StructuredDocument.from_dict(self.store.read_json(structured_path))
                    )
                    continue
            if item["status"] not in {
                SourceStatus.APPROVED.value,
                SourceStatus.FAILED.value,
                SourceStatus.REVIEW_REQUIRED.value,
            }:
                continue
            source = SourceCandidate.from_dict(item)
            try:
                acquired_path, document, markdown = processor.process(source, originals)
                self._record_source_status(item, SourceStatus.ACQUIRED)
                previous_hash = item.get("source_hash")
                item["acquired_path"] = str(acquired_path.relative_to(self.subject_dir))
                item["source_hash"] = document.source_hash
                item["warnings"] = document.warnings
                versions = item.setdefault("versions", [])
                if not any(version["source_hash"] == document.source_hash for version in versions):
                    versions.append(
                        {
                            "source_hash": document.source_hash,
                            "acquired_path": item["acquired_path"],
                            "processed_at": utc_now(),
                        }
                    )
                self.store.write_json(
                    self.subject_dir / "sources" / "structured" / (source.source_id + ".json"),
                    document.to_dict(),
                )
                self.store.write_json(
                    self.subject_dir
                    / "sources"
                    / "structured"
                    / (source.source_id + "-" + document.source_hash[:12] + ".json"),
                    document.to_dict(),
                )
                self.store.write_text(
                    self.subject_dir / "sources" / "markdown" / (source.source_id + ".md"),
                    markdown,
                )
                self.store.write_text(
                    self.subject_dir
                    / "sources"
                    / "markdown"
                    / (source.source_id + "-" + document.source_hash[:12] + ".md"),
                    markdown,
                )
                split_views = split_markdown(document)
                current_view = (
                    self.subject_dir / "sources" / "markdown" / source.source_id
                )
                versioned_view = (
                    self.subject_dir
                    / "sources"
                    / "markdown"
                    / (source.source_id + "-" + document.source_hash[:12])
                )
                for relative, content in split_views.items():
                    self.store.write_text(current_view / relative, content)
                    self.store.write_text(versioned_view / relative, content)
                expected_views = set(split_views)
                for view in (current_view, versioned_view):
                    for stale in view.glob("*.md"):
                        if stale.name not in expected_views:
                            stale.unlink()
                self.store.write_json(
                    self.subject_dir / "indexes" / "structural" / (source.source_id + ".json"),
                    {
                        "source_id": source.source_id,
                        "source_hash": document.source_hash,
                        "locations": [
                            {
                                "block_id": block.block_id,
                                "kind": block.kind,
                                "section": block.section,
                                "heading_path": block.heading_path,
                                "page": block.page,
                                "page_end": block.page_end,
                                "location": block.location,
                                "confidence": block.confidence,
                            }
                            for block in document.blocks
                        ],
                        "warnings": document.warnings,
                    },
                )
                quality = quality_evaluator.evaluate(document)
                self._record_source_status(item, SourceStatus.PROCESSED)
                self.store.write_json(
                    self.subject_dir / "sources" / "quality" / (source.source_id + ".json"),
                    quality,
                )
                if quality["status"] == "failed":
                    self._record_source_status(item, SourceStatus.FAILED, "No usable content")
                    errors.append("{0}: no usable content extracted".format(source.source_id))
                elif quality["status"] == "review_required":
                    self._record_source_status(item, SourceStatus.REVIEW_REQUIRED)
                else:
                    self._record_source_status(item, SourceStatus.READY)
                if previous_hash and previous_hash != document.source_hash:
                    self._invalidate_source_dependencies(
                        source.source_id, previous_hash, document.source_hash
                    )
                documents.append(document)
            except (OSError, UnicodeError, SourceProcessingError) as error:
                self._record_source_status(item, SourceStatus.FAILED, str(error))
                item["processing_error"] = str(error)
                errors.append("{0}: {1}".format(source.source_id, error))
        self.store.write_json(self._manifest_path(), manifest)
        if errors:
            raise WorkflowError("Source processing failed: {0}".format("; ".join(errors)))
        if not documents:
            raise WorkflowError("No approved sources were processed")
        if any(
            item["status"] == SourceStatus.REVIEW_REQUIRED.value
            for item in manifest["sources"]
        ):
            self._set_phase(WorkflowPhase.SOURCE_QUALITY_REVIEW)
        else:
            self._rebuild_lexical_index()
            self._set_phase(WorkflowPhase.SOURCES_READY)

    def approve_source_quality(self, source_id: str, reason: str) -> None:
        self._require_phase(WorkflowPhase.SOURCE_QUALITY_REVIEW)
        manifest = self.source_manifest()
        source = next(
            (item for item in manifest["sources"] if item["source_id"] == source_id), None
        )
        if source is None:
            raise KeyError("Unknown source: {0}".format(source_id))
        if source["status"] != SourceStatus.REVIEW_REQUIRED.value:
            raise WorkflowError("Source is not awaiting quality review")
        report_path = self.subject_dir / "sources" / "quality" / (source_id + ".json")
        report = self.store.read_json(report_path)
        report["review"] = {"decision": "approved", "reason": reason, "at": utc_now()}
        report["status"] = "approved_after_review"
        self.store.write_json(report_path, report)
        self._record_source_status(source, SourceStatus.READY, reason)
        source["quality_decision_reason"] = reason
        self.store.write_json(self._manifest_path(), manifest)
        if not any(
            item["status"] == SourceStatus.REVIEW_REQUIRED.value
            for item in manifest["sources"]
        ):
            self._rebuild_lexical_index()
            self._set_phase(WorkflowPhase.SOURCES_READY)

    def propose_source_refresh(
        self,
        source_id: str,
        new_uri: str,
        edition_or_date: Optional[str],
        reason: str,
    ) -> None:
        self._require_phase(WorkflowPhase.SOURCES_READY, WorkflowPhase.TRACK_READY)
        manifest = self.source_manifest()
        source = next(
            (item for item in manifest["sources"] if item["source_id"] == source_id), None
        )
        if source is None:
            raise KeyError("Unknown source: {0}".format(source_id))
        source["uri"] = new_uri
        source["edition_or_date"] = edition_or_date
        source["refresh_reason"] = reason
        source["decision_reason"] = None
        self._record_source_status(source, SourceStatus.PROPOSED, reason)
        manifest["corpus_approved"] = False
        manifest["approved_at"] = None
        self.store.write_json(self._manifest_path(), manifest)
        self._set_phase(WorkflowPhase.SOURCE_REVIEW)

    def _rebuild_lexical_index(self) -> None:
        documents: List[StructuredDocument] = []
        for item in self.source_manifest()["sources"]:
            if item["status"] != SourceStatus.READY.value:
                continue
            path = self.subject_dir / "sources" / "structured" / (item["source_id"] + ".json")
            documents.append(StructuredDocument.from_dict(self.store.read_json(path)))
        if not documents:
            raise WorkflowError("No quality-approved sources are ready for retrieval")
        self.store.write_json(
            self.subject_dir / "indexes" / "retrieval" / "lexical.json",
            LexicalIndex.build(documents),
        )

    def _invalidate_source_dependencies(
        self, source_id: str, old_hash: str, new_hash: str
    ) -> None:
        concept_path = self.subject_dir / "indexes" / "concepts.json"
        concepts = self.store.read_json(concept_path)
        changed = False
        for mapping in concepts.get("mappings", []):
            if any(reference.get("source_id") == source_id for reference in mapping.get("references", [])):
                mapping["needs_review"] = True
                mapping.setdefault("audit", []).append(
                    {
                        "event": "source_version_changed",
                        "source_id": source_id,
                        "old_hash": old_hash,
                        "new_hash": new_hash,
                        "at": utc_now(),
                    }
                )
                changed = True
        if changed:
            self.store.write_json(concept_path, concepts)
        for metadata_path in (self.subject_dir / "knowledge-book").glob("*.json"):
            metadata = self.store.read_json(metadata_path)
            if any(
                citation.get("source_id") == source_id
                for citation in metadata.get("citations", [])
            ):
                metadata["needs_review"] = True
                metadata.setdefault("history", []).append(
                    {
                        "event": "source_version_changed",
                        "source_id": source_id,
                        "old_hash": old_hash,
                        "new_hash": new_hash,
                        "at": utc_now(),
                    }
                )
                self.store.write_json(metadata_path, metadata)

    def create_track(self, track_name: str, learning_intent: str) -> str:
        self._require_phase(WorkflowPhase.SOURCES_READY, WorkflowPhase.TRACK_READY)
        track_id = slugify(track_name)
        track_dir = self.store.track_path(self.subject_id, track_id)
        if track_dir.exists():
            raise FileExistsError("Track already exists: {0}".format(track_id))
        (track_dir / "assessments").mkdir(parents=True, exist_ok=True)
        (track_dir / "course-plans").mkdir(parents=True, exist_ok=True)
        (track_dir / "memory-proposals").mkdir(parents=True, exist_ok=True)
        now = utc_now()
        self.store.write_json(
            track_dir / "track.json",
            {
                "track_id": track_id,
                "track_name": track_name,
                "learning_intent": learning_intent,
                "workflow_phase": WorkflowPhase.SOURCES_READY.value,
                "created_at": now,
                "updated_at": now,
            },
        )
        self.store.write_json(
            track_dir / "progress.json", {"concepts": {}, "updated_at": now}
        )
        state = self.state
        state["active_track_id"] = track_id
        self.store.write_json(self.subject_dir / "subject.json", state)
        self._set_phase(WorkflowPhase.SOURCES_READY)
        return track_id

    def activate_track(self, track_id: str) -> None:
        if self.phase in {
            WorkflowPhase.EXPLORING,
            WorkflowPhase.ASSESSMENT_PENDING,
            WorkflowPhase.ASSESSING,
        }:
            raise WorkflowError("Cannot switch tracks during an active lesson or assessment")
        track_id = slugify(track_id)
        track_path = self.store.track_path(self.subject_id, track_id) / "track.json"
        if not track_path.exists():
            raise FileNotFoundError("Unknown track: {0}".format(track_id))
        track = self.store.read_json(track_path)
        state = self.state
        state["active_track_id"] = track_id
        state["phase"] = track.get("workflow_phase", WorkflowPhase.SOURCES_READY.value)
        state["updated_at"] = utc_now()
        state.pop("active_lesson", None)
        state.pop("active_assessment_id", None)
        self.store.write_json(self.subject_dir / "subject.json", state)

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        index_path = self.subject_dir / "indexes" / "retrieval" / "lexical.json"
        if not index_path.exists():
            raise WorkflowError("Retrieval index is not ready")
        return LexicalIndex.search(self.store.read_json(index_path), query, limit)

    def build_vector_index(self, provider: EmbeddingProvider) -> None:
        self._require_phase(
            WorkflowPhase.SOURCES_READY,
            WorkflowPhase.COURSE_REVIEW,
            WorkflowPhase.COURSE_APPROVED,
            WorkflowPhase.TRACK_READY,
        )
        documents: List[StructuredDocument] = []
        for item in self.source_manifest()["sources"]:
            if item["status"] != SourceStatus.READY.value:
                continue
            path = self.subject_dir / "sources" / "structured" / (item["source_id"] + ".json")
            documents.append(StructuredDocument.from_dict(self.store.read_json(path)))
        index = VectorIndex.build(documents, provider)
        self.store.write_json(
            self.subject_dir / "indexes" / "retrieval" / "vector.json", index
        )

    def hybrid_search(
        self,
        query: str,
        provider: EmbeddingProvider,
        limit: int = 5,
        lexical_weight: float = 0.55,
    ) -> List[Dict[str, Any]]:
        retrieval_dir = self.subject_dir / "indexes" / "retrieval"
        vector_path = retrieval_dir / "vector.json"
        if not vector_path.exists():
            raise WorkflowError("Vector index is not ready")
        return HybridRetriever.search(
            self.store.read_json(retrieval_dir / "lexical.json"),
            self.store.read_json(vector_path),
            query,
            provider,
            limit,
            lexical_weight,
        )

    def propose_course(self, plan: Dict[str, Any]) -> None:
        self._require_phase(WorkflowPhase.SOURCES_READY, WorkflowPhase.TRACK_READY)
        required = {"outcome", "assumed_prerequisites", "concepts", "lesson_order", "deferred"}
        missing = required.difference(plan)
        if missing:
            raise ValueError("Course plan is missing: {0}".format(", ".join(sorted(missing))))
        payload = dict(plan)
        payload.update({"status": "proposed", "version": 1, "updated_at": utc_now()})
        course_path = self.store.track_path(self.subject_id, self.track_id) / "course-plan.json"
        if course_path.exists():
            previous = self.store.read_json(course_path)
            if not plan.get("revision_reason"):
                raise ValueError("A revised course plan requires revision_reason")
            payload["version"] = previous.get("version", 0) + 1
        self.store.write_json(course_path, payload)
        self.store.write_json(
            self.store.track_path(self.subject_id, self.track_id)
            / "course-plans"
            / "v{0:03d}.json".format(payload["version"]),
            payload,
        )
        self._set_phase(WorkflowPhase.COURSE_REVIEW)

    def approve_course(self) -> None:
        self._require_phase(WorkflowPhase.COURSE_REVIEW)
        course_path = self.store.track_path(self.subject_id, self.track_id) / "course-plan.json"
        plan = self.store.read_json(course_path)
        plan["status"] = "approved"
        plan["approved_at"] = utc_now()
        self.store.write_json(course_path, plan)
        self.store.write_json(
            self.store.track_path(self.subject_id, self.track_id)
            / "course-plans"
            / "v{0:03d}.json".format(plan["version"]),
            plan,
        )
        self._set_phase(WorkflowPhase.COURSE_APPROVED)

    def begin_lesson(self, concepts: List[str]) -> str:
        self._require_phase(WorkflowPhase.COURSE_APPROVED, WorkflowPhase.TRACK_READY,
                            WorkflowPhase.EXPLORING, WorkflowPhase.ASSESSMENT_PENDING,
                            WorkflowPhase.ASSESSING)
        if not concepts:
            raise ValueError("A lesson must target at least one concept")
        lesson_id = "lesson-" + uuid.uuid4().hex[:12]
        lessons = self._open_lessons()
        lesson = {"lesson_id": lesson_id, "concepts": concepts, "started_at": utc_now()}
        lessons[lesson_id] = lesson
        self._set_phase(
            WorkflowPhase.EXPLORING,
            active_lesson=lesson, open_lessons=lessons,
        )
        return lesson_id

    def _open_lessons(self) -> Dict[str, Any]:
        lessons = dict(self.state.get("open_lessons", {}))
        legacy = self.state.get("active_lesson")
        if legacy:
            lessons.setdefault(legacy["lesson_id"], legacy)
        return lessons

    def complete_lesson(
        self,
        signal: str,
        chapters: Dict[str, str],
        citations: Dict[str, List[Dict[str, str]]],
        memory_proposals: Optional[List[Dict[str, str]]] = None,
        lesson_id: Optional[str] = None,
    ) -> str:
        self._require_phase(WorkflowPhase.EXPLORING, WorkflowPhase.ASSESSMENT_PENDING,
                            WorkflowPhase.ASSESSING)
        if not DONE_PATTERN.match(signal):
            raise WorkflowError("An explicit standalone Done signal is required")
        lessons = self._open_lessons()
        if lesson_id is None:
            if len(lessons) != 1:
                raise WorkflowError("Specify lesson_id when multiple lessons are open")
            lesson_id = next(iter(lessons))
        if lesson_id not in lessons:
            raise WorkflowError("Unknown or already completed lesson: " + lesson_id)
        active = lessons[lesson_id]
        expected = {item.lower() for item in active.get("concepts", [])}
        supplied = {item.lower() for item in chapters}
        if not supplied or not supplied.issubset(expected):
            raise WorkflowError("Chapters must correspond to the active lesson concepts")
        self._validate_citations(citations)
        for concept, body in chapters.items():
            if not body.strip():
                raise ValueError("Chapter content cannot be empty")
            self._write_chapter(concept, body, citations.get(concept, []), active["lesson_id"])
        self._refresh_book_index()

        assessment_id = "assessment-" + uuid.uuid4().hex[:12]
        assessment = {
            "assessment_id": assessment_id,
            "lesson_id": active["lesson_id"],
            "concepts": list(chapters),
            "status": "pending",
            "attempt": 1,
            "kind": "lesson_completion",
            "questions": [],
            "created_at": utc_now(),
        }
        self.store.write_json(self._assessment_path(assessment_id), assessment)
        proposal = {
            "lesson_id": active["lesson_id"],
            "status": "pending",
            "proposals": memory_proposals or [],
            "created_at": utc_now(),
        }
        self.store.write_json(
            self.store.track_path(self.subject_id, self.track_id)
            / "memory-proposals"
            / (active["lesson_id"] + ".json"),
            proposal,
        )
        state = self.state
        state.pop("active_lesson", None)
        lessons.pop(lesson_id)
        state["open_lessons"] = lessons
        if lessons:
            state["active_lesson"] = next(reversed(lessons.values()))
        self.store.write_json(self.subject_dir / "subject.json", state)
        self._set_phase(
            WorkflowPhase.ASSESSMENT_PENDING, active_assessment_id=assessment_id
        )
        return assessment_id

    def start_assessment_attempt(self, lesson_id: str, reason: str) -> str:
        """Append a new packet attempt for a completed lesson without changing its earlier packet."""
        if not reason.strip():
            raise ValueError("A reason is required for a new assessment attempt")
        self._require_phase(
            WorkflowPhase.ASSESSMENT_PENDING,
            WorkflowPhase.ASSESSING,
            WorkflowPhase.TRACK_READY,
        )
        directory = self.store.track_path(self.subject_id, self.track_id) / "assessments"
        prior = [
            self.store.read_json(path)
            for path in directory.glob("*.json")
            if self.store.read_json(path).get("lesson_id") == lesson_id
            and self.store.read_json(path).get("kind") == "lesson_completion"
        ]
        if not prior:
            raise WorkflowError("No completed lesson assessment exists for: " + lesson_id)
        previous = max(prior, key=lambda item: (int(item.get("attempt", 1)), item.get("created_at", "")))
        attempt = max(int(item.get("attempt", 1)) for item in prior) + 1
        assessment_id = "assessment-" + uuid.uuid4().hex[:12]
        self.store.write_json(
            self._assessment_path(assessment_id),
            {
                "assessment_id": assessment_id,
                "lesson_id": lesson_id,
                "concepts": list(previous["concepts"]),
                "status": "pending",
                "attempt": attempt,
                "kind": "lesson_completion",
                "supersedes_assessment_id": previous["assessment_id"],
                "revision_reason": reason.strip(),
                "questions": [],
                "created_at": utc_now(),
            },
        )
        self._set_phase(WorkflowPhase.ASSESSMENT_PENDING, active_assessment_id=assessment_id)
        return assessment_id

    def _resolve_assessment(self, assessment_id: Optional[str] = None) -> Dict[str, Any]:
        directory = self.store.track_path(self.subject_id, self.track_id) / "assessments"
        if assessment_id is not None and not re.fullmatch(r"assessment-[a-f0-9]{12}", assessment_id):
            raise WorkflowError("Invalid assessment ID")
        if assessment_id is None:
            open_records = [self.store.read_json(path) for path in directory.glob("*.json")]
            open_records = [item for item in open_records if item["status"] in {"pending", "in_progress"}]
            if len(open_records) != 1:
                raise WorkflowError("Specify assessment_id when there is not exactly one open assessment")
            assessment = open_records[0]
        else:
            assessment = self.store.read_json(self._assessment_path(assessment_id))
        if assessment["status"] not in {"pending", "in_progress"}:
            raise WorkflowError("Assessment is already completed")
        return assessment

    def select_assessment(self, assessment_id: str) -> None:
        assessment = self._resolve_assessment(assessment_id)
        self._set_phase(WorkflowPhase.ASSESSING if assessment["status"] == "in_progress"
                        else WorkflowPhase.ASSESSMENT_PENDING,
                        active_assessment_id=assessment_id)

    def freeze_assessment(self, assessment_id: str, blueprint: Dict[str, Any]) -> None:
        assessment = self._resolve_assessment(assessment_id)
        if assessment.get("packet_frozen_at") or any(q["result"] is not None for q in assessment["questions"]):
            raise WorkflowError("Assessment packet is immutable after freezing or a result")
        if not assessment["questions"] or set(blueprint.get("concepts", {})) != set(assessment["concepts"]):
            raise WorkflowError("A frozen packet requires questions and complete concept coverage")
        standard = self._pass_standard()
        configured_standard = blueprint.get("pass_standard", {})
        for key in standard:
            if key in configured_standard:
                value = float(configured_standard[key])
                if value < 0 or value > 100:
                    raise WorkflowError("Pass-standard percentages must fall between 0 and 100")
                standard[key] = value
        if configured_standard:
            standard.update(configured_standard)
        assessment.update(blueprint=blueprint, pass_standard=standard,
                          packet_frozen_at=utc_now(),
                          checkpoint={"question_id": assessment["questions"][0]["question_id"],
                                      "selected_probe": None})
        self.store.write_json(self._assessment_path(assessment_id), assessment)

    def checkpoint_assessment(self, assessment_id: str, checkpoint: Dict[str, Any]) -> None:
        assessment = self._resolve_assessment(assessment_id)
        question = next((q for q in assessment["questions"] if q["question_id"] == checkpoint.get("question_id")), None)
        if question is None or question["result"] is not None:
            raise WorkflowError("Checkpoint must identify an unanswered question")
        selections = assessment.setdefault("probe_selections", {})
        selected = selections.get(checkpoint["question_id"])
        if selected is not None:
            if checkpoint.get("selected_probe") != selected:
                raise WorkflowError("A selected probe cannot be replaced")
        if checkpoint.get("selected_probe") is not None:
            try:
                rubric = json.loads(question["rubric"])
            except (ValueError, TypeError):
                rubric = {}
            eligible = [probe["prompt"] for probe in rubric.get("eligible_probes", [])]
            if eligible and checkpoint["selected_probe"] not in eligible:
                raise WorkflowError("Probe must be one of the prepared eligible probes")
            selections[checkpoint["question_id"]] = checkpoint["selected_probe"]
        assessment["checkpoint"] = checkpoint
        self.store.write_json(self._assessment_path(assessment_id), assessment)

    def _validate_citations(self, citations: Dict[str, List[Dict[str, str]]]) -> None:
        processed = {
            item["source_id"]: item.get("source_hash")
            for item in self.source_manifest()["sources"]
            if item["status"] == SourceStatus.READY.value
        }
        course_sources = self._approved_course_source_hashes()
        for items in citations.values():
            for citation in items:
                source_id = citation.get("source_id")
                if not source_id:
                    raise WorkflowError("Citation does not reference a processed source")
                if not citation.get("location"):
                    raise WorkflowError("Citation requires a stable source location")
                if source_id in processed:
                    expected_hash = processed[source_id]
                    if citation.get("source_hash") and expected_hash and citation["source_hash"] != expected_hash:
                        raise WorkflowError("Citation source hash does not match the processed source")
                    citation.setdefault("source_hash", expected_hash)
                    continue

                allowed_hashes = course_sources.get(source_id, set())
                if not allowed_hashes:
                    raise WorkflowError("Citation does not reference a processed source")
                source_hash = citation.get("source_hash")
                if source_hash is None and len(allowed_hashes) == 1:
                    citation["source_hash"] = next(iter(allowed_hashes))
                elif source_hash not in allowed_hashes:
                    raise WorkflowError(
                        "Course citation requires a source hash from its approved processed version"
                    )

    def _validate_question_grounding(self, grounding: Optional[Dict[str, Any]]) -> None:
        if not grounding or not str(grounding.get("grounding_note", "")).strip():
            raise WorkflowError("Assessment questions require a source-grounding note")
        sources = grounding.get("sources")
        if not isinstance(sources, list) or not sources:
            raise WorkflowError("Assessment questions require at least one real source")

        course_sources = []
        for source in sources:
            kind = source.get("kind")
            if kind == "course":
                course_sources.append(source)
                continue
            if kind != "external":
                raise WorkflowError("Question source kind must be course or external")
            if not str(source.get("title", "")).strip():
                raise WorkflowError("External assessment sources require a title")
            if not source.get("uri") and not source.get("artifact"):
                raise WorkflowError("External assessment sources require a URI or artifact path")
            if not str(source.get("location", "")).strip():
                raise WorkflowError("Assessment sources require a stable location")
            if not str(source.get("retrieved_at", "")).strip():
                raise WorkflowError("External assessment sources require a retrieval date")
            if source.get("artifact") and not source.get("content_hash"):
                raise WorkflowError("Downloaded assessment sources require a content hash")

        if course_sources:
            self._validate_citations({"assessment_question": course_sources})

    def _approved_course_source_hashes(self) -> Dict[str, set]:
        """Return exact source versions from approved, ready course-local corpora."""
        course_root = self.store.track_path(self.subject_id, self.track_id) / "courses"
        approved: Dict[str, set] = {}
        if not course_root.is_dir():
            return approved

        for plan_path in sorted(course_root.glob("*/course-plan-v*.json")):
            course_dir = plan_path.parent
            try:
                document = self.store.read_json(plan_path)
                plan = document.get("G2", document)
                version = str(plan.get("version", ""))
                if plan.get("status") != "course_approved":
                    continue
                gate = plan.get("preparation_gate", {})
                if not gate.get("sources_ready"):
                    continue
                plan_approval_path = plan_path.with_name(plan_path.stem + "-approval.json")
                source_approval_path = course_dir / gate.get(
                    "source_decisions_record", "source-approval-v1.json"
                )
                quality_path = course_dir / gate.get(
                    "quality_review", "evidence/quality-review-v1.json"
                )
                plan_approval = self.store.read_json(plan_approval_path)
                source_approval = self.store.read_json(source_approval_path)
                quality = self.store.read_json(quality_path)
                if str(plan_approval.get("plan_version", "")) != version:
                    continue
                if "approve" not in str(plan_approval.get("learner_response", "")).lower():
                    continue
                if "approve" not in str(source_approval.get("learner_response", "")).lower():
                    continue
                if not str(quality.get("status", "")).startswith("selected_core_ready"):
                    continue

                lessons = plan.get("lessons", {})
                digest_cache: Dict[Path, str] = {}
                for lesson in lessons.values() if isinstance(lessons, dict) else lessons:
                    for part in lesson.get("lesson_parts", []):
                        for passage in part.get("source_passages", []):
                            source_id = passage.get("source_id")
                            source_hash = passage.get("source_hash")
                            artifact = passage.get("artifact")
                            retrieval = passage.get("retrieval_file")
                            if not source_id or not source_hash or not artifact or not retrieval:
                                continue
                            artifact_path = Path(artifact)
                            retrieval_path = Path(retrieval)
                            if (
                                artifact_path.is_absolute()
                                or ".." in artifact_path.parts
                                or artifact_path.parts[:2] != ("evidence", "originals")
                                or retrieval_path.is_absolute()
                                or ".." in retrieval_path.parts
                                or retrieval_path.parts[:2] != ("evidence", "processed")
                            ):
                                continue
                            original = course_dir / artifact_path
                            derivative = course_dir / retrieval_path
                            if not original.is_file() or not derivative.is_file():
                                continue
                            if original not in digest_cache:
                                digest_cache[original] = hashlib.sha256(original.read_bytes()).hexdigest()
                            digest = digest_cache[original]
                            if digest == source_hash:
                                approved.setdefault(source_id, set()).add(source_hash)
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        return approved

    def _write_chapter(
        self, concept: str, body: str, citations: List[Dict[str, str]], lesson_id: str
    ) -> None:
        chapter_id = slugify(concept)
        chapter_path = self.subject_dir / "knowledge-book" / (chapter_id + ".md")
        evidence = []
        for citation in citations:
            evidence.append(
                "- `{0}` at `{1}`{2}".format(
                    citation["source_id"],
                    citation["location"],
                    ": " + citation["excerpt"].strip() if citation.get("excerpt") else "",
                )
            )
        rendered = "# {0}\n\n{1}\n\n## Source evidence\n\n{2}\n".format(
            concept.strip(), body.strip(), "\n".join(evidence) if evidence else "No source claims recorded."
        )
        self.store.write_text(chapter_path, rendered)
        metadata_path = self.subject_dir / "knowledge-book" / (chapter_id + ".json")
        previous = self.store.read_json(metadata_path) if metadata_path.exists() else {"history": []}
        previous["concept"] = concept
        previous["current_lesson_id"] = lesson_id
        previous["citations"] = citations
        previous.setdefault("history", []).append(
            {"lesson_id": lesson_id, "updated_at": utc_now()}
        )
        self.store.write_json(metadata_path, previous)

    def _refresh_book_index(self) -> None:
        book = self.subject_dir / "knowledge-book"
        subject_name = self.state["subject_name"]
        entries = []
        for path in sorted(book.glob("*.md")):
            if path.name == "README.md":
                continue
            title = path.stem.replace("-", " ").title()
            entries.append("- [{0}]({1})".format(title, path.name))
        self.store.write_text(
            book / "README.md",
            "# {0} Knowledge Book\n\n{1}\n".format(
                subject_name, "\n".join(entries) if entries else "No completed chapters yet."
            ),
        )

    def _assessment_path(self, assessment_id: str) -> Path:
        return (
            self.store.track_path(self.subject_id, self.track_id)
            / "assessments"
            / (assessment_id + ".json")
        )

    def _final_exam_path(self, exam_id: str) -> Path:
        return (
            self.store.track_path(self.subject_id, self.track_id)
            / "final-exams"
            / (exam_id + ".json")
        )

    def start_final_exam(self, blueprint: Dict[str, Any]) -> str:
        self._require_phase(WorkflowPhase.TRACK_READY)
        directory = self.store.track_path(self.subject_id, self.track_id) / "assessments"
        if self._open_lessons() or any(self.store.read_json(path)["status"] != "completed"
                                       for path in directory.glob("*.json")):
            raise WorkflowError("Complete all open lessons and assessments before the final exam")
        course_path = self.store.track_path(self.subject_id, self.track_id) / "course-plan.json"
        if not course_path.exists():
            raise WorkflowError("A final exam requires an approved course plan")
        course = self.store.read_json(course_path)
        if course.get("status") != "approved":
            raise WorkflowError("A final exam requires an approved course plan")
        concepts = list(course.get("concepts", []))
        progress_path = self.store.track_path(self.subject_id, self.track_id) / "progress.json"
        progress = self.store.read_json(progress_path)
        missing = set(concepts).difference(progress.get("concepts", {}))
        if missing:
            raise WorkflowError(
                "Every course concept needs lesson-assessment evidence before the final exam: {0}".format(
                    ", ".join(sorted(missing))
                )
            )
        assessments_dir = self.store.track_path(self.subject_id, self.track_id) / "assessments"
        incomplete = [
            path.name
            for path in assessments_dir.glob("*.json")
            if self.store.read_json(path).get("status") != "completed"
        ]
        if incomplete:
            raise WorkflowError("All lesson assessments must be completed before the final exam")
        if not blueprint or not blueprint.get("coverage"):
            raise ValueError("A final exam requires a non-empty coverage blueprint")
        exam_id = "final-exam-" + uuid.uuid4().hex[:12]
        self.store.write_json(
            self._final_exam_path(exam_id),
            {
                "exam_id": exam_id,
                "kind": "cumulative_final_exam",
                "track_id": self.track_id,
                "course_plan_version": course.get("version"),
                "concepts": concepts,
                "blueprint": blueprint,
                "status": "pending",
                "attempt": 1,
                "questions": [],
                "created_at": utc_now(),
            },
        )
        self._set_phase(WorkflowPhase.FINAL_EXAM_PENDING, active_final_exam_id=exam_id)
        return exam_id

    def add_final_exam_question(
        self,
        prompt: str,
        concepts: List[str],
        dimensions: List[str],
        rubric: Dict[str, Any],
        source_grounding: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._require_phase(WorkflowPhase.FINAL_EXAM_PENDING, WorkflowPhase.FINAL_EXAMINING)
        exam_id = self.state["active_final_exam_id"]
        exam = self.store.read_json(self._final_exam_path(exam_id))
        unknown = set(concepts).difference(exam["concepts"])
        if unknown:
            raise WorkflowError("Question references concepts outside the approved course")
        self._validate_question_grounding(source_grounding)
        question_id = "q{0:03d}".format(len(exam["questions"]) + 1)
        exam["questions"].append(
            {
                "question_id": question_id,
                "prompt": prompt,
                "concepts": concepts,
                "dimensions": dimensions,
                "rubric": rubric,
                "source_grounding": source_grounding,
                "attempt": exam.get("attempt", 1),
                "result": None,
            }
        )
        exam["status"] = "in_progress"
        self.store.write_json(self._final_exam_path(exam_id), exam)
        self._set_phase(WorkflowPhase.FINAL_EXAMINING)
        return question_id

    def record_final_exam_result(
        self,
        question_id: str,
        answer: Optional[str],
        artifact: Optional[Dict[str, str]],
        score: float,
        out_of: float,
        feedback: str,
        assistance: Optional[str] = None,
    ) -> None:
        self._require_phase(WorkflowPhase.FINAL_EXAMINING)
        if answer is None and artifact is None:
            raise ValueError("An answer or artifact reference is required")
        if out_of <= 0 or score < 0 or score > out_of:
            raise ValueError("Score must fall between zero and out_of")
        exam = self.store.read_json(self._final_exam_path(self.state["active_final_exam_id"]))
        question = next(
            (item for item in exam["questions"] if item["question_id"] == question_id), None
        )
        if question is None:
            raise KeyError("Unknown final-exam question: {0}".format(question_id))
        if question["result"] is not None:
            raise WorkflowError("Final-exam results are append-only and cannot be overwritten")
        question["result"] = {
            "answer": answer,
            "artifact": artifact,
            "score": score,
            "out_of": out_of,
            "feedback": feedback,
            "assistance": assistance,
            "recorded_at": utc_now(),
        }
        self.store.write_json(self._final_exam_path(exam["exam_id"]), exam)

    def finalize_final_exam(self, judgments: Dict[str, Dict[str, Any]]) -> None:
        self._require_phase(WorkflowPhase.FINAL_EXAMINING)
        exam_id = self.state["active_final_exam_id"]
        exam = self.store.read_json(self._final_exam_path(exam_id))
        if not exam["questions"] or any(question["result"] is None for question in exam["questions"]):
            raise WorkflowError("Every final-exam question needs a recorded result")
        if set(judgments) != set(exam["concepts"]):
            raise WorkflowError("A final-exam judgment is required for every course concept")
        allowed = {status.value for status in ProgressStatus}
        for concept, judgment in judgments.items():
            if judgment.get("status") not in allowed:
                raise ValueError("Invalid progress status for {0}".format(concept))
            if not judgment.get("evidence"):
                raise ValueError("Final-exam judgments require evidence")
        summary = self._assessment_summary(exam["questions"], judgments)
        exam["status"] = "completed"
        exam["judgments"] = judgments
        exam["summary"] = summary
        exam["outcome"] = summary["outcome"]
        exam["completed_at"] = utc_now()
        self.store.write_json(self._final_exam_path(exam_id), exam)

        progress_path = self.store.track_path(self.subject_id, self.track_id) / "progress.json"
        progress = self.store.read_json(progress_path)
        for concept, judgment in judgments.items():
            entry = progress["concepts"].setdefault(concept, {"history": []})
            entry["status"] = judgment["status"]
            entry["history"].append(
                {
                    "final_exam_id": exam_id,
                    "kind": "cumulative_final_exam",
                    "status": judgment["status"],
                    "evidence": judgment["evidence"],
                    "pass_evidence": summary["concepts"][concept],
                    "at": utc_now(),
                }
            )
        progress["updated_at"] = utc_now()
        self.store.write_json(progress_path, progress)
        state = self.state
        state.pop("active_final_exam_id", None)
        self.store.write_json(self.subject_dir / "subject.json", state)
        self._set_phase(WorkflowPhase.TRACK_READY)

    def add_assessment_question(
        self,
        prompt: str,
        concepts: List[str],
        dimensions: List[str],
        rubric: str,
        source_grounding: Optional[Dict[str, Any]] = None,
        assessment_id: Optional[str] = None,
    ) -> str:
        assessment = self._resolve_assessment(assessment_id)
        assessment_id = assessment["assessment_id"]
        if assessment.get("packet_frozen_at") or any(q["result"] is not None for q in assessment["questions"]):
            raise WorkflowError("Assessment packet is immutable after freezing or a result")
        unknown = set(concepts).difference(assessment["concepts"])
        if unknown:
            raise WorkflowError("Question references concepts outside the lesson")
        self._validate_question_grounding(source_grounding)
        question_id = "q{0:03d}".format(len(assessment["questions"]) + 1)
        assessment["questions"].append(
            {
                "question_id": question_id,
                "prompt": prompt,
                "concepts": concepts,
                "dimensions": dimensions,
                "rubric": rubric,
                "source_grounding": source_grounding,
                "attempt": assessment.get("attempt", 1),
                "result": None,
            }
        )
        assessment["status"] = "in_progress"
        self.store.write_json(self._assessment_path(assessment_id), assessment)
        if self.state.get("active_assessment_id") == assessment_id:
            self._set_phase(WorkflowPhase.ASSESSING)
        return question_id

    def record_assessment_result(
        self,
        question_id: str,
        answer: Optional[str],
        artifact: Optional[Dict[str, str]],
        score: float,
        out_of: float,
        feedback: str,
        assistance: Optional[str] = None,
        assessment_id: Optional[str] = None,
    ) -> None:
        if answer is None and artifact is None:
            raise ValueError("An answer or artifact reference is required")
        if out_of <= 0 or score < 0 or score > out_of:
            raise ValueError("Score must fall between zero and out_of")
        assessment = self._resolve_assessment(assessment_id)
        assessment_id = assessment["assessment_id"]
        question = next(
            (item for item in assessment["questions"] if item["question_id"] == question_id), None
        )
        if question is None:
            raise KeyError("Unknown assessment question: {0}".format(question_id))
        if question["result"] is not None:
            raise WorkflowError("Assessment results are append-only and cannot be overwritten")
        question["result"] = {
            "answer": answer,
            "artifact": artifact,
            "score": score,
            "out_of": out_of,
            "feedback": feedback,
            "assistance": assistance,
            "recorded_at": utc_now(),
        }
        if assessment.get("packet_frozen_at"):
            question["result"]["delivery_checkpoint"] = assessment.get("checkpoint")
            remaining = [q for q in assessment["questions"] if q["result"] is None]
            assessment["checkpoint"] = {
                "question_id": remaining[0]["question_id"] if remaining else None,
                "selected_probe": None,
            }
        self.store.write_json(self._assessment_path(assessment_id), assessment)

    def finalize_assessment(self, judgments: Dict[str, Dict[str, Any]], assessment_id: Optional[str] = None) -> None:
        assessment = self._resolve_assessment(assessment_id)
        assessment_id = assessment["assessment_id"]
        if not assessment["questions"] or any(
            question["result"] is None for question in assessment["questions"]
        ):
            raise WorkflowError("Every assessment question needs a recorded result")
        if set(judgments) != set(assessment["concepts"]):
            raise WorkflowError("A progress judgment is required for every assessed concept")
        allowed = {status.value for status in ProgressStatus}
        progress_path = self.store.track_path(self.subject_id, self.track_id) / "progress.json"
        progress = self.store.read_json(progress_path)
        for concept, judgment in judgments.items():
            if judgment.get("status") not in allowed:
                raise ValueError("Invalid progress status for {0}".format(concept))
            if not judgment.get("evidence"):
                raise ValueError("Progress judgments require evidence")
            if judgment.get("status") == ProgressStatus.RETAINED.value:
                prior = progress.get("concepts", {}).get(concept, {}).get("status")
                if not assessment.get("retention_revisit") or prior not in {
                    ProgressStatus.DEMONSTRATED.value,
                    ProgressStatus.RETAINED.value,
                }:
                    raise WorkflowError(
                        "Retained requires a later reassessment after demonstrated understanding"
                    )

        summary = self._assessment_summary(assessment["questions"], judgments, assessment.get("pass_standard"))
        assessment["status"] = "completed"
        assessment["judgments"] = judgments
        assessment["summary"] = summary
        assessment["outcome"] = summary["outcome"]
        assessment["completed_at"] = utc_now()
        self.store.write_json(self._assessment_path(assessment_id), assessment)

        for concept, judgment in judgments.items():
            entry = progress["concepts"].setdefault(concept, {"history": []})
            entry["status"] = judgment["status"]
            entry["history"].append(
                {
                    "assessment_id": assessment_id,
                    "status": judgment["status"],
                    "evidence": judgment["evidence"],
                    "pass_evidence": summary["concepts"][concept],
                    "at": utc_now(),
                }
            )
        progress["updated_at"] = utc_now()
        self.store.write_json(progress_path, progress)
        state = self.state
        if state.get("active_assessment_id") == assessment_id:
            state.pop("active_assessment_id", None)
        self.store.write_json(self.subject_dir / "subject.json", state)
        if state.get("active_assessment_id") is None:
            directory = self.store.track_path(self.subject_id, self.track_id) / "assessments"
            remaining = [self.store.read_json(path) for path in sorted(directory.glob("*.json"))]
            remaining = [item for item in remaining if item.get("status") in {"pending", "in_progress"}]
            if self._open_lessons():
                self._set_phase(WorkflowPhase.EXPLORING)
            elif remaining:
                self.select_assessment(remaining[0]["assessment_id"])
            else:
                self._set_phase(WorkflowPhase.TRACK_READY)

    def start_reassessment(
        self, concepts: List[str], reason: str, retention_revisit: bool = False
    ) -> str:
        self._require_phase(WorkflowPhase.TRACK_READY)
        if not concepts:
            raise ValueError("A reassessment must target at least one concept")
        progress_path = self.store.track_path(self.subject_id, self.track_id) / "progress.json"
        progress = self.store.read_json(progress_path)
        unknown = set(concepts).difference(progress.get("concepts", {}))
        if unknown:
            raise WorkflowError("Cannot reassess concepts without prior progress evidence")
        assessments_dir = self.store.track_path(self.subject_id, self.track_id) / "assessments"
        prior = [self.store.read_json(path) for path in assessments_dir.glob("*.json")]
        attempt = 1 + max(
            (
                item.get("attempt", 1)
                for item in prior
                if set(item.get("concepts", [])) == set(concepts)
            ),
            default=0,
        )
        assessment_id = "assessment-" + uuid.uuid4().hex[:12]
        self.store.write_json(
            self._assessment_path(assessment_id),
            {
                "assessment_id": assessment_id,
                "lesson_id": None,
                "concepts": concepts,
                "status": "pending",
                "attempt": attempt,
                "kind": "retention" if retention_revisit else "remediation",
                "retention_revisit": retention_revisit,
                "reason": reason,
                "questions": [],
                "created_at": utc_now(),
            },
        )
        self._set_phase(
            WorkflowPhase.ASSESSMENT_PENDING, active_assessment_id=assessment_id
        )
        return assessment_id

    def approve_memory_proposal(
        self, lesson_id: str, approved_facts: List[Dict[str, str]]
    ) -> None:
        proposal_path = (
            self.store.track_path(self.subject_id, self.track_id)
            / "memory-proposals"
            / (lesson_id + ".json")
        )
        proposal = self.store.read_json(proposal_path)
        if proposal.get("status") != "pending":
            raise WorkflowError("Memory proposal has already been decided")
        result = self.personal_context.apply_approved_facts(
            approved_facts,
            {
                "workflow": "tutor-source-grounded",
                "workspace_root": str(self.store.root),
                "subject_id": self.subject_id,
                "track_id": self.track_id,
                "unit_id": lesson_id,
            },
        )
        proposal["status"] = "approved"
        proposal["approved_facts"] = approved_facts
        proposal["approved_at"] = utc_now()
        proposal["global_profile"] = result
        self.store.write_json(proposal_path, proposal)

    def reject_memory_proposal(self, lesson_id: str, reason: str) -> None:
        proposal_path = (
            self.store.track_path(self.subject_id, self.track_id)
            / "memory-proposals"
            / (lesson_id + ".json")
        )
        proposal = self.store.read_json(proposal_path)
        if proposal.get("status") != "pending":
            raise WorkflowError("Memory proposal has already been decided")
        proposal["status"] = "rejected"
        proposal["rejection_reason"] = reason
        proposal["decided_at"] = utc_now()
        self.store.write_json(proposal_path, proposal)
