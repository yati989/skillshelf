"""Filesystem persistence with atomic JSON and text writes."""

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("A name must contain at least one letter or number")
    return slug


class WorkspaceStore:
    """Owns the durable layout for subjects, tracks, and learner state."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()

    def subject_path(self, subject_id: str) -> Path:
        return self.root / "subjects" / slugify(subject_id)

    def track_path(self, subject_id: str, track_id: str) -> Path:
        return self.subject_path(subject_id) / "tracks" / slugify(track_id)

    def initialize_subject(
        self, subject_name: str, learning_intent: str, track_name: str
    ) -> Dict[str, Any]:
        subject_id = slugify(subject_name)
        track_id = slugify(track_name)
        subject = self.subject_path(subject_id)
        directories: Iterable[Path] = (
            subject / "sources" / "originals",
            subject / "sources" / "structured",
            subject / "sources" / "markdown",
            subject / "sources" / "quality",
            subject / "indexes" / "structural",
            subject / "indexes" / "retrieval",
            subject / "knowledge-book",
            subject / "tracks" / track_id / "assessments",
            subject / "tracks" / track_id / "course-plans",
            subject / "tracks" / track_id / "memory-proposals",
            subject / "tracks" / track_id / "final-exams",
        )
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        state_path = subject / "subject.json"
        if state_path.exists():
            raise FileExistsError("Subject already exists: {0}".format(subject_id))

        now = utc_now()
        state = {
            "subject_id": subject_id,
            "subject_name": subject_name,
            "active_track_id": track_id,
            "phase": "source_research",
            "created_at": now,
            "updated_at": now,
        }
        self.write_json(state_path, state)
        self.write_json(
            subject / "sources" / "manifest.json",
            {"corpus_approved": False, "approved_at": None, "sources": []},
        )
        self.write_json(subject / "indexes" / "concepts.json", {"mappings": []})
        self.write_json(
            self.track_path(subject_id, track_id) / "track.json",
            {
                "track_id": track_id,
                "track_name": track_name,
                "learning_intent": learning_intent,
                "workflow_phase": "source_research",
                "created_at": now,
            },
        )
        self.write_json(
            self.track_path(subject_id, track_id) / "progress.json",
            {"concepts": {}, "updated_at": now},
        )
        self.write_text(
            subject / "knowledge-book" / "README.md",
            "# {0} Knowledge Book\n\nCompleted concept chapters appear here.\n".format(
                subject_name
            ),
        )
        return state

    def read_json(self, path: Path) -> Dict[str, Any]:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def write_json(self, path: Path, value: Dict[str, Any]) -> None:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        self.write_text(path, text)

    def write_text(self, path: Path, value: str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".{0}.".format(path.name), text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, str(path))
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
