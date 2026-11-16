"""One approval-gated personal profile shared across workspaces and skills."""

import fcntl
import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .storage import WorkspaceStore, slugify, utc_now


SCHEMA_VERSION = 3
SENSITIVITY_LEVELS = {"normal", "restricted"}
ATTRIBUTIONS = {
    "user_statement",
    "historical_observation",
    "assistant_inference",
    "approved_migration",
}


class PersonalContextError(ValueError):
    """A personal-context operation would violate the profile contract."""


def default_personal_context_root() -> Path:
    configured = os.environ.get("PERSONAL_CONTEXT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex" / "personal-context").resolve()


def _identifier(value: Any, label: str = "identifier") -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]{0,119}", value
    ):
        raise PersonalContextError(
            "{0} must contain lowercase letters, numbers, hyphens, or underscores".format(
                label
            )
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonalContextError("{0} must be nonempty text".format(label))
    return value.strip()


def _source(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise PersonalContextError("source must be an object")
    result = dict(value)
    result["workflow"] = _text(result.get("workflow"), "source.workflow")
    return result


class PersonalContextStore:
    """Deep module for approved facts, proposals, decisions, and history."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or default_personal_context_root()).expanduser().resolve()
        self.store = WorkspaceStore(self.root)

    @property
    def profile_path(self) -> Path:
        return self.root / "profile.json"

    @property
    def markdown_path(self) -> Path:
        return self.root / "profile.md"

    def _write_markdown(self, profile: Dict[str, Any]) -> None:
        # Older profiles have no approved narrative. Preserve their existing view.
        if "narrative" not in profile and self.markdown_path.exists():
            return
        narrative = profile.get("narrative")
        rendered = (narrative["markdown"] + "\n") if narrative else (
            "# Personal profile\n\nNo narrative has been approved yet.\n"
        )
        if not self.markdown_path.exists() or self.markdown_path.read_text(encoding="utf-8") != rendered:
            self.store.write_text(self.markdown_path, rendered)

    def export_markdown(self) -> Dict[str, Any]:
        """Export only approved narrative wording; never generate prose from facts."""
        with self._lock():
            profile = self._profile()
            self._write_markdown(profile)
            return {
                "profile": str(self.profile_path),
                "markdown": str(self.markdown_path),
                "facts_count": len(profile["facts"]),
            }

    def proposal_path(self, proposal_id: str) -> Path:
        return self.root / "proposals" / ("{0}.json".format(_identifier(proposal_id)))

    @contextmanager
    def _lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".profile.lock"
        with lock.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield

    def initialize(self) -> Dict[str, Any]:
        for directory in (self.root, self.root / "history", self.root / "proposals"):
            directory.mkdir(parents=True, exist_ok=True)
        if not self.profile_path.exists():
            self.store.write_json(
                self.profile_path,
                {"schema_version": SCHEMA_VERSION, "facts": [], "updated_at": utc_now()},
            )
        profile = self._profile()
        self._write_markdown(profile)
        return {
            "root": str(self.root),
            "profile": str(self.profile_path),
            "markdown": str(self.markdown_path),
            "schema_version": profile["schema_version"],
            "facts_count": len(profile["facts"]),
        }

    def _profile(self) -> Dict[str, Any]:
        if not self.profile_path.exists():
            self.initialize()
        profile = self.store.read_json(self.profile_path)
        if profile.get("schema_version") != SCHEMA_VERSION:
            raise PersonalContextError(
                "Unsupported personal-context schema; migrate it before use"
            )
        facts = profile.get("facts")
        if not isinstance(facts, list):
            raise PersonalContextError("profile facts must be an array")
        return profile

    def index(
        self, category: Optional[str] = None, scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for fact in self._profile()["facts"]:
            if category and fact.get("category") != category:
                continue
            if scope and scope not in fact.get("scopes", []):
                continue
            results.append(
                {
                    "key": fact["key"],
                    "category": fact.get("category", "general"),
                    "scopes": fact.get("scopes", ["global"]),
                    "sensitivity": fact.get("sensitivity", "normal"),
                    "updated_at": fact.get("updated_at"),
                }
            )
        narrative = self._profile().get("narrative")
        if narrative and (not category or category == "narrative") and (not scope or scope == "global"):
            results.append({"key": "profile-narrative", "category": "narrative", "scopes": ["global"],
                            "sensitivity": narrative["sensitivity"], "updated_at": narrative["updated_at"]})
        return sorted(results, key=lambda item: item["key"])

    def get(self, key: str) -> Dict[str, Any]:
        normalized = _identifier(slugify(key), "key")
        if normalized == "profile-narrative" and self._profile().get("narrative"):
            return dict(self._profile()["narrative"], key=normalized)
        for fact in self._profile()["facts"]:
            if fact["key"] == normalized:
                return fact
        raise PersonalContextError("Unknown personal-context key: {0}".format(normalized))

    def _normalize_change(
        self, change: Dict[str, Any], existing: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not isinstance(change, dict):
            raise PersonalContextError("Each proposed change must be an object")
        action = change.get("action")
        if action in {"replace-narrative", "delete-narrative"}:
            if change.get("key") != "profile-narrative":
                raise PersonalContextError("Narrative changes must use key profile-narrative")
            result = {"action": action, "key": "profile-narrative"}
            result["evidence"] = _text(change.get("evidence"), "narrative evidence")
            if action == "replace-narrative":
                result["markdown"] = _text(change.get("markdown"), "narrative markdown")
                sensitivity = change.get("sensitivity", "normal")
                if sensitivity not in SENSITIVITY_LEVELS:
                    raise PersonalContextError("sensitivity must be normal or restricted")
                result["sensitivity"] = sensitivity
            return result
        if action not in {"add", "update", "delete"}:
            raise PersonalContextError("action must be add, update, or delete")
        key = _identifier(slugify(_text(change.get("key"), "change.key")), "key")
        if key == "profile-narrative":
            raise PersonalContextError("Use a narrative action for profile-narrative")
        if action == "add" and key in existing:
            raise PersonalContextError("Add targets an existing key: {0}".format(key))
        if action in {"update", "delete"} and key not in existing:
            raise PersonalContextError(
                "{0} targets a missing key: {1}".format(action.title(), key)
            )
        result: Dict[str, Any] = {"action": action, "key": key}
        if action == "delete":
            result["reason"] = _text(change.get("reason"), "delete reason")
            return result

        result["fact"] = _text(change.get("fact"), "fact")
        result["category"] = _identifier(
            slugify(change.get("category", "general")), "category"
        )
        raw_scopes = change.get("scopes", ["global"])
        if not isinstance(raw_scopes, list) or not raw_scopes:
            raise PersonalContextError("scopes must be a nonempty array")
        result["scopes"] = sorted(
            {_identifier(slugify(item), "scope") for item in raw_scopes}
        )
        sensitivity = change.get("sensitivity", "normal")
        if sensitivity not in SENSITIVITY_LEVELS:
            raise PersonalContextError("sensitivity must be normal or restricted")
        result["sensitivity"] = sensitivity
        attribution = change.get("attribution", "user_statement")
        if attribution not in ATTRIBUTIONS:
            raise PersonalContextError("Unsupported attribution")
        result["attribution"] = attribution
        result["confidence"] = _text(change.get("confidence"), "confidence")
        result["evidence"] = _text(change.get("evidence"), "evidence")
        if change.get("origin") is not None:
            if not isinstance(change["origin"], dict):
                raise PersonalContextError("origin must be an object")
            result["origin"] = dict(change["origin"])
        return result

    def propose(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise PersonalContextError("Proposal payload must be an object")
        source = _source(payload.get("source"))
        changes = payload.get("changes")
        if not isinstance(changes, list) or not changes:
            raise PersonalContextError("A proposal needs at least one change")
        with self._lock():
            self.initialize()
            existing = {fact["key"]: fact for fact in self._profile()["facts"]}
            normalized = [self._normalize_change(item, existing) for item in changes]
            keys = [item["key"] for item in normalized]
            if len(keys) != len(set(keys)):
                raise PersonalContextError("A proposal may mention each key only once")
            proposal_id = "proposal-{0}".format(uuid.uuid4().hex[:12])
            proposal = {
                "proposal_id": proposal_id,
                "status": "pending",
                "source": source,
                "changes": [dict(item, decision="pending") for item in normalized],
                "created_at": utc_now(),
            }
            self.store.write_json(self.proposal_path(proposal_id), proposal)
            return proposal

    def record_no_change(self, source: Dict[str, Any], reason: str) -> Dict[str, Any]:
        with self._lock():
            self.initialize()
            proposal_id = "review-{0}".format(uuid.uuid4().hex[:12])
            record = {
                "proposal_id": proposal_id,
                "status": "no_change",
                "source": _source(source),
                "changes": [],
                "reason": _text(reason, "reason"),
                "created_at": utc_now(),
                "decided_at": utc_now(),
            }
            self.store.write_json(self.proposal_path(proposal_id), record)
            return record

    def _write_history(self, source: Dict[str, Any], changes: List[Dict[str, Any]]) -> str:
        now = utc_now()
        name = "{0}-{1}.json".format(
            now.replace(":", "-").replace("+", "-"), uuid.uuid4().hex[:8]
        )
        self.store.write_json(
            self.root / "history" / name,
            {"approved_at": now, "source": source, "changes": changes},
        )
        return str(self.root / "history" / name)

    def _apply_changes(
        self,
        profile: Dict[str, Any],
        changes: Iterable[Dict[str, Any]],
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        now = utc_now()
        current = {fact["key"]: fact for fact in profile["facts"]}
        applied = []
        for change in changes:
            key = change["key"]
            if change["action"] in {"replace-narrative", "delete-narrative"}:
                before = profile.get("narrative")
                after = None
                if change["action"] == "replace-narrative":
                    after = {field: change[field] for field in ("markdown", "evidence", "sensitivity")}
                    after.update({"approved_at": now, "updated_at": now, "source": source})
                profile["narrative"] = after
                applied.append({"action": change["action"], "key": key, "before": before, "after": after})
                continue
            before = current.get(key)
            if change["action"] == "delete":
                if before is None:
                    raise PersonalContextError("Cannot delete missing key: {0}".format(key))
                del current[key]
                after = None
            else:
                if change["action"] == "add" and before is not None:
                    raise PersonalContextError("Cannot add existing key: {0}".format(key))
                if change["action"] == "update" and before is None:
                    raise PersonalContextError("Cannot update missing key: {0}".format(key))
                after = {
                    key_: value
                    for key_, value in change.items()
                    if key_ not in {"action", "decision", "decided_at"}
                }
                after.update(
                    {
                        "key": key,
                        "created_at": before.get("created_at", now) if before else now,
                        "updated_at": now,
                        "approved_at": now,
                        "source": source,
                    }
                )
                current[key] = after
            applied.append(
                {
                    "action": "deleted" if after is None else ("updated" if before else "added"),
                    "key": key,
                    "before": before,
                    "after": after,
                }
            )
        profile["facts"] = [current[key] for key in sorted(current)]
        profile["schema_version"] = SCHEMA_VERSION
        profile["updated_at"] = now
        return applied

    def approve(
        self, proposal_id: str, keys: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        with self._lock():
            self.initialize()
            path = self.proposal_path(proposal_id)
            proposal = self.store.read_json(path)
            pending = {
                item["key"]: item
                for item in proposal.get("changes", [])
                if item.get("decision") == "pending"
            }
            selected = sorted({_identifier(slugify(item), "key") for item in keys}) if keys else sorted(pending)
            if not selected or any(key not in pending for key in selected):
                raise PersonalContextError("Approval must target pending proposal keys")
            profile = self._profile()
            applied = self._apply_changes(
                profile, [pending[key] for key in selected], proposal["source"]
            )
            now = utc_now()
            for item in proposal["changes"]:
                if item["key"] in selected:
                    item["decision"] = "approved"
                    item["decided_at"] = now
            proposal["status"] = (
                "pending"
                if any(item["decision"] == "pending" for item in proposal["changes"])
                else "resolved"
            )
            proposal["updated_at"] = now
            self.store.write_json(self.profile_path, profile)
            self.store.write_json(path, proposal)
            history = self._write_history(proposal["source"], applied)
            self._write_markdown(profile)
            return {"proposal": proposal, "applied": applied, "history": history}

    def reject(
        self, proposal_id: str, reason: str, keys: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        with self._lock():
            self.initialize()
            path = self.proposal_path(proposal_id)
            proposal = self.store.read_json(path)
            pending = {
                item["key"]: item
                for item in proposal.get("changes", [])
                if item.get("decision") == "pending"
            }
            selected = sorted({_identifier(slugify(item), "key") for item in keys}) if keys else sorted(pending)
            if not selected or any(key not in pending for key in selected):
                raise PersonalContextError("Rejection must target pending proposal keys")
            now = utc_now()
            for item in proposal["changes"]:
                if item["key"] in selected:
                    item["decision"] = "rejected"
                    item["decision_reason"] = _text(reason, "reason")
                    item["decided_at"] = now
            proposal["status"] = (
                "pending"
                if any(item["decision"] == "pending" for item in proposal["changes"])
                else "resolved"
            )
            proposal["updated_at"] = now
            self.store.write_json(path, proposal)
            return proposal

    def apply_approved_facts(
        self, facts: List[Dict[str, Any]], source: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compatibility seam for workflows that already record approval elsewhere."""
        if not isinstance(facts, list):
            raise PersonalContextError("approved facts must be an array")
        with self._lock():
            self.initialize()
            profile = self._profile()
            existing = {fact["key"]: fact for fact in profile["facts"]}
            normalized = []
            for fact in facts:
                item = dict(fact)
                key = _identifier(slugify(_text(item.get("key") or item.get("fact"), "fact key")), "key")
                item.update(
                    {
                        "key": key,
                        "action": "update" if key in existing else "add",
                        "category": item.get("category", "learning"),
                        "scopes": item.get("scopes", ["global", "learning"]),
                        "sensitivity": item.get("sensitivity", "normal"),
                        "attribution": item.get("attribution", "user_statement"),
                        "origin": item.get("origin")
                        or {
                            key_: item[key_]
                            for key_ in (
                                "source_subject",
                                "source_lesson",
                                "approved_at",
                                "created_at",
                                "updated_at",
                            )
                            if item.get(key_) is not None
                        },
                    }
                )
                normalized.append(self._normalize_change(item, existing))
            keys = [item["key"] for item in normalized]
            if len(keys) != len(set(keys)):
                raise PersonalContextError("Approved facts may mention each key only once")
            applied = self._apply_changes(profile, normalized, _source(source))
            self.store.write_json(self.profile_path, profile)
            history = self._write_history(_source(source), applied) if applied else None
            self._write_markdown(profile)
            return {"applied": applied, "history": history, "profile": str(self.profile_path)}
