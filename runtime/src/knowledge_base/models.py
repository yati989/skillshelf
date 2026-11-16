"""Durable domain values for subject-learning workspaces."""

from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceStatus(str, Enum):
    DISCOVERED = "discovered"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACQUIRED = "acquired"
    PROCESSED = "processed"
    REVIEW_REQUIRED = "review_required"
    READY = "ready"
    FAILED = "failed"


class WorkflowPhase(str, Enum):
    SOURCE_RESEARCH = "source_research"
    SOURCE_REVIEW = "source_review"
    CORPUS_APPROVED = "corpus_approved"
    SOURCE_QUALITY_REVIEW = "source_quality_review"
    SOURCES_READY = "sources_ready"
    COURSE_REVIEW = "course_review"
    COURSE_APPROVED = "course_approved"
    EXPLORING = "exploring"
    ASSESSMENT_PENDING = "assessment_pending"
    ASSESSING = "assessing"
    TRACK_READY = "track_ready"
    FINAL_EXAM_PENDING = "final_exam_pending"
    FINAL_EXAMINING = "final_examining"


class ConceptMappingStatus(str, Enum):
    GENERATED = "generated"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProgressStatus(str, Enum):
    EXPOSED = "exposed"
    DEVELOPING = "developing"
    DEMONSTRATED = "demonstrated"
    RETAINED = "retained"


@dataclass
class SourceCandidate:
    source_id: str
    title: str
    uri: str
    source_type: str
    role: str
    reason: str
    coverage: List[str]
    author: Optional[str] = None
    edition_or_date: Optional[str] = None
    authority: Optional[str] = None
    recency: Optional[str] = None
    difficulty: Optional[str] = None
    overlap: Optional[str] = None
    reputation_basis: Optional[str] = None
    access_strategy: Optional[str] = None
    preferred_artifact: Optional[str] = None
    access_status: str = "unknown"
    license_status: str = "unknown"
    inspection_status: str = "discovered"
    status: SourceStatus = SourceStatus.PROPOSED
    decision_reason: Optional[str] = None
    processing_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceCandidate":
        allowed = {item.name for item in fields(cls)}
        values = {key: value for key, value in data.items() if key in allowed}
        values["status"] = SourceStatus(values.get("status", SourceStatus.PROPOSED.value))
        return cls(**values)


@dataclass
class DocumentBlock:
    block_id: str
    kind: str
    text: str
    location: str
    section: Optional[str] = None
    page: Optional[int] = None
    page_end: Optional[int] = None
    heading_path: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentBlock":
        allowed = {item.name for item in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class StructuredDocument:
    source_id: str
    title: str
    source_type: str
    source_hash: str
    metadata: Dict[str, Any]
    blocks: List[DocumentBlock] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "source_type": self.source_type,
            "source_hash": self.source_hash,
            "metadata": self.metadata,
            "blocks": [block.to_dict() for block in self.blocks],
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredDocument":
        return cls(
            source_id=data["source_id"],
            title=data["title"],
            source_type=data["source_type"],
            source_hash=data["source_hash"],
            metadata=data.get("metadata", {}),
            blocks=[DocumentBlock.from_dict(item) for item in data.get("blocks", [])],
            warnings=data.get("warnings", []),
        )
