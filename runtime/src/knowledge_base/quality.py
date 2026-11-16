"""Observable conversion-quality checks and review routing."""

from statistics import mean
from typing import Any, Dict, List

from .models import StructuredDocument


class QualityEvaluator:
    """Classifies conversions without pretending heuristics prove fidelity."""

    def evaluate(self, document: StructuredDocument) -> Dict[str, Any]:
        confidences = [block.confidence for block in document.blocks]
        pages = sorted({block.page for block in document.blocks if block.page is not None})
        low_confidence = [value for value in confidences if value < 0.8]
        hierarchical = [block for block in document.blocks if block.heading_path]
        checks: List[Dict[str, Any]] = []

        checks.append(
            {
                "name": "content_extracted",
                "passed": bool(document.blocks),
                "detail": "{0} blocks extracted".format(len(document.blocks)),
                "severity": "critical",
            }
        )
        if document.source_type == "pdf":
            page_count = document.metadata.get("page_count") or document.metadata.get("pages")
            try:
                expected_pages = int(page_count) if page_count is not None else None
            except (TypeError, ValueError):
                expected_pages = None
            checks.append(
                {
                    "name": "page_coverage",
                    "passed": expected_pages is None or len(pages) >= expected_pages * 0.95,
                    "detail": "{0} pages represented{1}".format(
                        len(pages),
                        " of {0}".format(expected_pages) if expected_pages is not None else "",
                    ),
                    "severity": "review",
                }
            )
            outline_count = int(document.metadata.get("outline_entry_count") or 0)
            checks.append(
                {
                    "name": "outline_hierarchy",
                    "passed": outline_count == 0 or len(hierarchical) / max(1, len(document.blocks)) >= 0.8,
                    "detail": "{0} outline entries; {1} of {2} blocks carry hierarchy".format(
                        outline_count, len(hierarchical), len(document.blocks)
                    ),
                    "severity": "review",
                }
            )
        checks.append(
            {
                "name": "extractor_warnings",
                "passed": not document.warnings,
                "detail": "; ".join(document.warnings) if document.warnings else "No warnings",
                "severity": "review",
            }
        )
        checks.append(
            {
                "name": "confidence_distribution",
                "passed": not confidences or len(low_confidence) / len(confidences) <= 0.25,
                "detail": "{0} of {1} blocks below 0.8 confidence".format(
                    len(low_confidence), len(confidences)
                ),
                "severity": "review",
            }
        )

        if any(not item["passed"] and item["severity"] == "critical" for item in checks):
            status = "failed"
        elif any(not item["passed"] for item in checks):
            status = "review_required"
        else:
            status = "passed"
        return {
            "source_id": document.source_id,
            "source_hash": document.source_hash,
            "status": status,
            "metrics": {
                "block_count": len(document.blocks),
                "page_count_observed": len(pages),
                "mean_confidence": round(mean(confidences), 4) if confidences else 0.0,
                "low_confidence_block_count": len(low_confidence),
                "hierarchical_block_count": len(hierarchical),
            },
            "checks": checks,
            "review": None,
        }
