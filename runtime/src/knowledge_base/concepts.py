"""Lifecycle operations for revisable concept mappings."""

from typing import Any, Dict, List, Optional

from .models import ConceptMappingStatus
from .storage import WorkspaceStore, utc_now


class ConceptMap:
    def __init__(self, store: WorkspaceStore, subject_id: str):
        self.store = store
        self.path = store.subject_path(subject_id) / "indexes" / "concepts.json"

    def list(self) -> List[Dict[str, Any]]:
        return self.store.read_json(self.path).get("mappings", [])

    def propose(
        self,
        concept: str,
        aliases: List[str],
        references: List[Dict[str, str]],
        confidence: float,
        rationale: Optional[str] = None,
    ) -> Dict[str, Any]:
        mappings = self.list()
        canonical = concept.strip()
        existing = next(
            (item for item in mappings if item["concept"].lower() == canonical.lower()), None
        )
        if existing and existing["status"] == ConceptMappingStatus.REJECTED.value:
            raise ValueError("Rejected mapping requires new evidence before reproposal")
        mapping = {
            "concept": canonical,
            "aliases": sorted(set(aliases)),
            "references": references,
            "confidence": confidence,
            "rationale": rationale,
            "status": ConceptMappingStatus.GENERATED.value,
            "updated_at": utc_now(),
            "audit": [],
        }
        if existing:
            mapping["audit"] = existing.get("audit", [])
            mappings[mappings.index(existing)] = mapping
        else:
            mappings.append(mapping)
        self.store.write_json(self.path, {"mappings": mappings})
        return mapping

    def set_status(
        self, concept: str, status: ConceptMappingStatus, reason: str
    ) -> Dict[str, Any]:
        mappings = self.list()
        mapping = next(
            (item for item in mappings if item["concept"].lower() == concept.lower()), None
        )
        if mapping is None:
            raise KeyError("Unknown concept mapping: {0}".format(concept))
        previous = mapping["status"]
        mapping["status"] = status.value
        mapping["updated_at"] = utc_now()
        mapping.setdefault("audit", []).append(
            {"from": previous, "to": status.value, "reason": reason, "at": utc_now()}
        )
        self.store.write_json(self.path, {"mappings": mappings})
        return mapping
