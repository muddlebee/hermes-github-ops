from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .config import Config


VERDICTS = {
    "confirmed_bug", "possible_bug", "needs_info", "duplicate",
    "expected_behavior", "out_of_scope", "security_report_needed",
}
CONFIDENCE = {"high", "medium", "low"}
PRIORITIES = {"P1", "P2", "P3", "P4", None}
REQUIRED_FIELDS = {
    "verdict", "confidence", "priority_recommendation", "evidence",
    "missing_information", "duplicate_candidates", "suggested_labels", "comment",
}


@dataclass(frozen=True)
class ValidatedReport:
    labels: list[str]
    comment: str | None


def load_and_validate_report(path: str | Path, config: Config) -> ValidatedReport:
    with Path(path).open(encoding="utf-8") as handle:
        report: dict[str, Any] = json.load(handle)

    if set(report) != REQUIRED_FIELDS:
        raise ValueError("report does not match the exact expected field set")
    verdict = report["verdict"]
    priority = report["priority_recommendation"]
    if verdict not in VERDICTS or report["confidence"] not in CONFIDENCE:
        raise ValueError("report contains an invalid verdict or confidence")
    if priority not in PRIORITIES:
        raise ValueError("report contains an invalid priority recommendation")
    if not all(isinstance(report[key], list) for key in ("evidence", "missing_information", "duplicate_candidates", "suggested_labels")):
        raise ValueError("report list fields must be arrays")
    if not isinstance(report["comment"], str) or len(report["comment"]) > 2400:
        raise ValueError("report.comment must be a string of at most 2400 characters")

    labels = [config.verdict_labels[verdict]]
    if priority is not None:
        labels.append(config.priority_labels[priority])
    labels.extend(report["suggested_labels"])
    if not all(isinstance(label, str) and label in config.allowed_labels for label in labels):
        raise ValueError("report requested a label outside the configured allow-list")

    # Never surface model-generated details for a possible security report.
    comment = None if verdict == "security_report_needed" else report["comment"].strip() or None
    return ValidatedReport(labels=sorted(set(labels)), comment=comment)
