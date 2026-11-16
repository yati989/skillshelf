"""A conversational reading library, independent of the tutor's course gates.

Originals and versioned extractions are evidence. Markdown notes are the readable
record; sidecars supply citation validation and optimistic revision checks.
"""

import hashlib
import fcntl
import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SourceCandidate, StructuredDocument
from .personal_context import PersonalContextStore
from .quality import QualityEvaluator
from .rendering import split_markdown
from .retrieval import LexicalIndex
from .sources import SourceProcessor, sha256_file
from .storage import WorkspaceStore, slugify, utc_now


class ReadingError(ValueError):
    """A request cannot safely update or retrieve the reading workspace."""


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,99}", value):
        raise ReadingError("IDs must contain lowercase letters, numbers, hyphens or underscores")
    return value


def _hash(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ReadingError("A complete lowercase SHA-256 source hash is required")
    return value


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReadingError("{0} must be nonempty text".format(name))
    return value


class ReadingWorkspace:
    def __init__(self, root: Path):
        self.store = WorkspaceStore(root)
        self.root = self.store.root
        self.processor = SourceProcessor()

    def _path(self, relative: str) -> Path:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ReadingError("Workspace paths must be relative without parent traversal")
        resolved = (self.root / candidate).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as error:
            raise ReadingError("Workspace path escapes the root") from error
        return resolved

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root))

    @contextmanager
    def _source_lock(self, source_id):
        # Serialize duplicate detection, acquisition and catalog updates for a
        # source. Different versions must never overwrite each other's catalog.
        lock = self._path("records/reading-locks/source-{0}.lock".format(_identifier(source_id)))
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield

    def initialize(self) -> Dict[str, Any]:
        directories = ["library/catalog", "library/originals", "library/extracted",
                       "wiki", "sessions", "self", "indexes", "records/reading-notes",
                       "records/reading-revisions", "records/reading-locks"]
        paths = [self._path(item) for item in directories]
        index = self._path("INDEX.md")
        conventions = self._path("conventions.md")
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        defaults = {
            index: "# Knowledge workspace\n\n- [Reading index](indexes/reading-index.md)\n"
                   "- [Library](library/catalog/)\n- [Wiki](wiki/)\n"
                   "- [Personal evidence](self/)\n- [Sessions](sessions/)\n\n"
                   "The approved personal profile lives in the user-level personal-context workspace.\n",
            conventions: "# Reading conventions\n\nSources, interpretations, and personal statements "
                         "remain distinct. Source citations identify an immutable version and block.\n\n"
                         "Historical activity is represented only by evidence summaries in self/. "
                         "These notes are not a competing current profile. Do not import activity "
                         "exports or create a history database.\n\n"
                         "Reading has no compulsory assessments or mastery claims. Current user "
                         "corrections supersede older personal interpretations. Read and update "
                         "approved durable facts only through the global personal-context interface.\n",
        }
        for path, content in defaults.items():
            if not path.exists():
                self.store.write_text(path, content)
        return {"root": str(self.root), "directories": directories}

    def resources(self) -> List[Dict[str, Any]]:
        directory = self._path("library/catalog")
        return [self.store.read_json(self._path(self._relative(item)))
                for item in sorted(directory.glob("*.json"))]

    def _resource(self, source_id: str) -> Dict[str, Any]:
        path = self._path("library/catalog/{0}.json".format(_identifier(source_id)))
        if not path.is_file():
            raise ReadingError("Unknown source: {0}".format(source_id))
        return self.store.read_json(path)

    def _version(self, source_id: str, source_hash: Optional[str] = None):
        resource = self._resource(source_id)
        source_hash = _hash(source_hash or resource["current_hash"])
        if source_hash not in resource["versions"]:
            raise ReadingError("Unknown source version: {0}".format(source_hash))
        return resource, source_hash, resource["versions"][source_hash]

    def document(self, source_id: str, source_hash: Optional[str] = None) -> StructuredDocument:
        _, version_hash, version = self._version(source_id, source_hash)
        path = self._path(version["structured_path"])
        if sha256_file(path) != version["structured_sha256"]:
            raise ReadingError("Stored extraction was modified; restore it before using its citations")
        document = StructuredDocument.from_dict(self.store.read_json(path))
        if document.source_id != source_id or document.source_hash != version_hash:
            raise ReadingError("Stored extraction identity does not match its catalog")
        return document

    def ingest(self, path: Path, title: str, source_id: Optional[str] = None,
               author: Optional[str] = None) -> Dict[str, Any]:
        title = _required_text(title, "title")
        source_id = _identifier(source_id or slugify(title))
        source_path = Path(path).expanduser().resolve()
        types = {".pdf": "pdf", ".md": "markdown", ".markdown": "markdown",
                 ".txt": "text", ".html": "html", ".htm": "html",
                 ".vtt": "transcript", ".srt": "transcript"}
        if not source_path.is_file() or source_path.suffix.lower() not in types:
            raise ReadingError("Provide a local PDF, Markdown, text, HTML, VTT or SRT file")
        content_hash = sha256_file(source_path)
        with self._source_lock(source_id):
            return self._ingest_source(source_path, title, source_id, author,
                                       types[source_path.suffix.lower()], content_hash)

    def _ingest_source(self, source_path, title, source_id, author, source_type, content_hash):
        catalog_path = self._path("library/catalog/{0}.json".format(source_id))
        if catalog_path.exists():
            existing = self._resource(source_id)
            if content_hash in existing["versions"]:
                self.document(source_id, content_hash)
                return dict(existing, unchanged=True, matched_hash=content_hash)
        source = SourceCandidate(source_id=source_id, title=title, uri=str(source_path),
                                 source_type=source_type, role="reading",
                                 reason="User supplied local reading material", coverage=[], author=author)
        originals = self._path("library/originals/{0}/{1}".format(source_id, content_hash))
        # Validate the complete destination before the processor writes its file.
        self._path(self._relative(originals) + "/{0}-{1}{2}".format(
            source_id, content_hash[:12], source_path.suffix.lower()))
        self.initialize()
        acquired, document, markdown = self.processor.process(source, originals)
        if document.source_hash != content_hash or sha256_file(acquired) != content_hash:
            raise ReadingError("Source changed during acquisition; repeat ingestion")
        return self._register(document, markdown, author, acquired, None)

    def reuse(self, structured_path: Path) -> Dict[str, Any]:
        path = Path(structured_path).expanduser().resolve()
        try:
            path.relative_to(self._path("subjects"))
        except ValueError as error:
            raise ReadingError("Reuse requires a structured document inside this workspace's subjects") from error
        if not path.is_file() or path.suffix != ".json":
            raise ReadingError("Reuse requires an existing structured JSON document")
        document = StructuredDocument.from_dict(self.store.read_json(path))
        _identifier(document.source_id)
        _hash(document.source_hash)
        with self._source_lock(document.source_id):
            return self._reuse_document(document, path)

    def _reuse_document(self, document, path):
        catalog = self._path("library/catalog/{0}.json".format(document.source_id))
        if catalog.exists():
            existing = self._resource(document.source_id)
            if document.source_hash in existing["versions"]:
                self.document(document.source_id, document.source_hash)
                return dict(existing, unchanged=True, matched_hash=document.source_hash)
        markdown = "\n\n".join(block.text for block in document.blocks) + "\n"
        self.initialize()
        return self._register(document, markdown, document.metadata.get("author"), None, path)

    def _register(self, document, markdown, author, original, reused_from):
        source_id, content_hash = _identifier(document.source_id), _hash(document.source_hash)
        block_ids = [block.block_id for block in document.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ReadingError("Extraction contains ambiguous duplicate block IDs")
        directory = self._path("library/extracted/{0}/{1}".format(source_id, content_hash))
        structured = self._path(self._relative(directory) + "/document.json")
        full_markdown = self._path(self._relative(directory) + "/full.md")
        quality_path = self._path(self._relative(directory) + "/quality.json")
        chapter_paths = {self._path(self._relative(directory) + "/chapters/" + name): body
                         for name, body in split_markdown(document).items()}
        quality = QualityEvaluator().evaluate(document)
        if not any(block.text.strip() for block in document.blocks):
            quality["status"] = "failed"
        catalog = self._path("library/catalog/{0}.json".format(source_id))
        resource = self.store.read_json(catalog) if catalog.exists() else {
            "source_id": source_id, "created_at": utc_now(), "versions": {},
            "engagement": "encountered",
        }
        self.store.write_json(structured, document.to_dict())
        self.store.write_text(full_markdown, markdown)
        self.store.write_json(quality_path, quality)
        for chapter_path, body in chapter_paths.items():
            self.store.write_text(chapter_path, body)
        version = {"structured_path": self._relative(structured),
                   "structured_sha256": sha256_file(structured),
                   "markdown_path": self._relative(full_markdown),
                   "original_path": self._relative(original) if original else None,
                   "reused_from": self._relative(reused_from) if reused_from else None,
                   "quality": quality,
                   "status": "ready" if quality["status"] == "passed" else quality["status"],
                   "registered_at": utc_now()}
        resource["versions"][content_hash] = version
        resource.update(title=document.title, author=author, current_hash=content_hash, updated_at=utc_now())
        self.store.write_json(catalog, resource)
        return self._complete(resource, "reuse" if reused_from else "ingest")

    def _record(self, action, value):
        event = {"at": utc_now(), "action": action}
        event.update({key: value[key] for key in ["source_id", "current_hash", "reviewed_hash", "kind", "id", "revision"]
                      if key in value})
        path = self._path("records/reading-log.jsonl")
        lock = self._path("records/reading-locks/log.lock")
        with lock.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            previous = path.read_text(encoding="utf-8") if path.exists() else ""
            self.store.write_text(path, previous + json.dumps(event, sort_keys=True) + "\n")

    def _complete(self, value, action):
        try:
            self._record(action, value)
        except (ValueError, OSError) as error:
            value = dict(value, log_warning="Saved, but change logging failed: {0}".format(error))
        return self._update_index(value)

    def _update_index(self, resource):
        try:
            self.reindex()
        except (ValueError, OSError, KeyError) as error:
            return dict(resource, index_warning="Resource saved; search index rebuild failed: {0}".format(error))
        return resource

    def _ready_documents(self, source_id=None):
        resources = [self._resource(source_id)] if source_id else self.resources()
        return [self.document(item["source_id"]) for item in resources
                if item["versions"][item["current_hash"]]["status"] == "ready"]

    def reindex(self) -> Dict[str, Any]:
        lines = ["# Reading index", "", "## Sources", ""]
        for resource in self.resources():
            version = resource["versions"][resource["current_hash"]]
            lines.append("- [{0}](../{1}) — {2}; `{3}`".format(
                resource["title"], version["markdown_path"], version["status"], resource["source_id"]))
        for directory in ["wiki", "self", "sessions"]:
            lines.extend(["", "## " + directory.capitalize(), ""])
            for path in sorted(self._path(directory).glob("*.md")):
                lines.append("- [{0}](../{1}/{2})".format(path.stem, directory, path.name))
        self.store.write_text(self._path("indexes/reading-index.md"), "\n".join(lines) + "\n")
        index = LexicalIndex.build(self._ready_documents())
        self.store.write_json(self._path("indexes/reading-search.json"), index)
        return {"chunk_count": index["chunk_count"]}

    def search(self, query: str, source_id: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
            raise ReadingError("limit must be between 1 and 50")
        # Rebuild cheaply in memory: current source integrity and readiness are checked.
        return LexicalIndex.search(LexicalIndex.build(self._ready_documents(source_id)), query, limit)

    def read(self, source_id: str, section: Optional[str] = None, max_chars: int = 16000,
             source_hash: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 1 <= max_chars <= 200000:
            raise ReadingError("max_chars must be between 1 and 200000")
        document = self.document(source_id, source_hash)
        _, _, version = self._version(source_id, document.source_hash)
        selected = document.blocks
        if section:
            key = section.casefold().strip()
            selected = [block for block in selected if key in {
                block.block_id.casefold(), (block.section or "").casefold(),
                " > ".join(block.heading_path).casefold(),
                *[heading.casefold() for heading in block.heading_path]}]
            if not selected:
                raise ReadingError("No exact section, heading path or block ID matches: {0}".format(section))
        remaining, returned = max_chars, []
        for block in selected:
            if remaining <= 0:
                break
            value = block.to_dict()
            value["text"] = block.text[:remaining]
            value["truncated"] = len(value["text"]) < len(block.text)
            remaining -= len(value["text"])
            returned.append(value)
        truncated = len(returned) < len(selected) or any(block["truncated"] for block in returned)
        warnings = list(document.warnings)
        if version["status"] != "ready":
            warnings.append("Extraction status is {0}; inspect before relying on it".format(version["status"]))
        if truncated:
            warnings.append("Output is truncated; this is not the complete requested text")
        return {"source_id": source_id, "source_hash": document.source_hash, "title": document.title,
                "status": version["status"], "scope": section or "extracted text",
                "blocks": returned, "total_matching_blocks": len(selected),
                "returned_blocks": len(returned), "truncated": truncated, "warnings": warnings}

    def review(self, source_id: str, reason: str) -> Dict[str, Any]:
        reason = _required_text(reason, "inspection reason")
        # Capture the inspected version before waiting; a concurrent new import
        # must not silently receive an older version's extraction approval.
        _, version_hash, _ = self._version(source_id)
        with self._source_lock(source_id):
            return self._review_version(source_id, version_hash, reason)

    def _review_version(self, source_id, version_hash, reason):
        resource, version_hash, version = self._version(source_id, version_hash)
        document = self.document(source_id, version_hash)
        if version["quality"]["status"] == "failed" or not any(b.text.strip() for b in document.blocks):
            raise ReadingError("Failed or empty extraction cannot be accepted; repair and ingest again")
        if version["status"] == "ready":
            return dict(resource, reviewed_hash=version_hash)
        version["quality"]["review"] = {"accepted": True, "reason": reason, "reviewed_at": utc_now()}
        version["status"] = "ready"
        self.store.write_json(self._path("library/catalog/{0}.json".format(source_id)), resource)
        self.store.write_json(self._path("library/extracted/{0}/{1}/quality.json".format(source_id, version_hash)), version["quality"])
        return self._complete(dict(resource, reviewed_hash=version_hash), "review")

    def context(self) -> Dict[str, Any]:
        def notes(directory, kind):
            results = []
            for item in sorted(self._path(directory).glob("*.md")):
                path = self._path("{0}/{1}".format(directory, item.name))
                metadata_path = self._path("records/reading-notes/{0}/{1}.json".format(kind, item.stem))
                metadata = self.store.read_json(metadata_path) if metadata_path.exists() else {}
                current_hash = sha256_file(path)
                results.append({"path": str(path), "metadata_path": str(metadata_path),
                                "revision": metadata.get("revision"),
                                "attribution": metadata.get("attribution"),
                                "current_content_hash": current_hash,
                                "modified": bool(metadata) and current_hash != metadata["content_sha256"],
                                "tracked": bool(metadata)})
            return results
        personal_context = PersonalContextStore()
        return {"root": str(self.root),
                "initialized": all(self._path(path).is_dir() for path in
                                   ["library/catalog", "library/extracted", "wiki", "sessions", "self"]),
                "index": str(self._path("INDEX.md")),
                "conventions": str(self._path("conventions.md")),
                "self_notes": notes("self", "self"),
                "wiki_notes": notes("wiki", "wiki"),
                "session_notes": notes("sessions", "session"),
                "global_profile": str(personal_context.profile_path),
                "legacy_profile": str(self._path("learner-profile/profile.json"))
                if self._path("learner-profile/profile.json").exists() else None,
                "profile_policy": "Use the global personal-context interface for approved current facts; self notes are evidence only."}

    def save_note(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        kind = payload.get("kind")
        if kind not in {"wiki", "session", "self"}:
            raise ReadingError("kind must be wiki, session or self")
        note_id = _identifier(payload.get("id"))
        title = _required_text(payload.get("title"), "title")
        body = _required_text(payload.get("body"), "body")
        attribution = payload.get("attribution")
        category = payload.get("category")
        if kind == "self":
            if attribution not in {"user_statement", "historical_observation", "assistant_inference"}:
                raise ReadingError("Self notes require explicit attribution")
            if category in {"worldview", "background", "preferences"} and attribution != "user_statement":
                raise ReadingError("Worldview, background and preferences require a user statement")
            _required_text(payload.get("basis"), "self note basis")
        citations = []
        for citation in payload.get("citations", []):
            source_id = _identifier(citation.get("source_id"))
            version_hash = _hash(citation.get("source_hash"))
            document = self.document(source_id, version_hash)
            block = next((block for block in document.blocks if block.block_id == citation.get("block_id")), None)
            if block is None:
                raise ReadingError("Citation refers to an unknown block")
            if "quote" in citation:
                quote = _required_text(citation["quote"], "quote")
                if " ".join(quote.split()) not in " ".join(block.text.split()):
                    raise ReadingError("Quoted text is absent from the cited block")
            citations.append(dict(citation, location=block.location, title=document.title))
        links = payload.get("links", [])
        for link in links:
            path = self._path(link)
            if not Path(link).parts or Path(link).parts[0] not in {"wiki", "self", "sessions"} or path.suffix != ".md" or not path.is_file():
                raise ReadingError("Links must reference existing wiki, self or sessions Markdown notes")
        # Validation above precedes creation of any workspace files. The lock
        # spans the revision check and every note write, including reconciliation.
        self.initialize()
        lock_path = self._path("records/reading-locks/{0}-{1}.lock".format(kind, note_id))
        with lock_path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            return self._write_note(payload, citations)

    def _write_note(self, payload, citations):
        kind, note_id = payload["kind"], payload["id"]
        title, body = payload["title"], payload["body"]
        attribution, category = payload.get("attribution"), payload.get("category")
        links = payload.get("links", [])
        directory = "sessions" if kind == "session" else kind
        current = self._path("{0}/{1}.md".format(directory, note_id))
        metadata_path = self._path("records/reading-notes/{0}/{1}.json".format(kind, note_id))
        previous = self.store.read_json(metadata_path) if metadata_path.exists() else None
        manual_content = None
        current_hash = sha256_file(current) if current.is_file() else None
        expected_hash = payload.get("expected_content_hash")
        if expected_hash is not None and expected_hash != current_hash:
            raise ReadingError("Content conflict: expected_content_hash does not match the current Markdown")
        if previous:
            if payload.get("expected_revision") != previous["revision"]:
                raise ReadingError("Revision conflict: supply expected_revision from the current note metadata")
            if current_hash != previous["content_sha256"]:
                if not current_hash or expected_hash != current_hash:
                    raise ReadingError("Note was manually modified; read it and supply expected_content_hash to reconcile")
                manual_content = current.read_bytes().decode("utf-8")
        elif current.exists():
            raise ReadingError("Untracked note already exists; do not overwrite manual content")
        elif payload.get("expected_revision") is not None:
            raise ReadingError("Revision conflict: this note has no previous revision")
        revision = previous["revision"] + 1 if previous else 1
        revision_dir = self._path("records/reading-revisions/{0}/{1}".format(kind, note_id))
        revision_md = self._path(self._relative(revision_dir) + "/{0:06d}.md".format(revision))
        revision_json = self._path(self._relative(revision_dir) + "/{0:06d}.json".format(revision))
        manual_path = self._path(self._relative(revision_dir) + "/manual-{0}.md".format(current_hash))
        if revision_md.exists() or revision_json.exists():
            raise ReadingError("Revision snapshot already exists; inspect the interrupted write before retrying")
        parts = ["# " + title, body]
        if attribution:
            parts.append("Attribution: " + attribution)
        if payload.get("basis"):
            parts.append("Basis: " + payload["basis"])
        if citations:
            parts.append("## Sources\n\n" + "\n".join(
                "- {title}: {source_id}@{source_hash}, {block_id} ({location})".format(**item)
                for item in citations))
        if links:
            parts.append("## Related notes\n\n" + "\n".join(
                "- [{0}](../{0})".format(link) for link in links))
        content = "\n\n".join(parts).rstrip() + "\n"
        metadata = {"id": note_id, "kind": kind, "title": title, "revision": revision,
                    "attribution": attribution, "category": category, "basis": payload.get("basis"),
                    "citations": citations, "links": links, "updated_at": utc_now(),
                    "created_at": previous["created_at"] if previous else utc_now(),
                    "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "reconciled_content_hash": current_hash if manual_content is not None else None,
                    "path": self._relative(current)}
        # All request and conflict validation precedes the first write.
        self.initialize()
        if manual_content is not None and not manual_path.exists():
            self.store.write_text(manual_path, manual_content)
        self.store.write_text(revision_md, content)
        self.store.write_json(revision_json, metadata)
        self.store.write_text(current, content)
        self.store.write_json(metadata_path, metadata)
        return self._complete(dict(metadata, path=str(current), metadata_path=str(metadata_path)), "save_note")
