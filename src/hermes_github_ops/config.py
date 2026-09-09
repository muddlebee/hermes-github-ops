from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Config:
    project_name: str
    repo: str
    checkout_path: Path
    database_path: Path
    policy_path: Path
    comment_on_issue: bool
    retry_after_seconds: int
    allowed_labels: frozenset[str]
    verdict_labels: dict[str, str]
    priority_labels: dict[str, str]


def load_config(path: str | Path) -> Config:
    path = Path(path).resolve()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    project = raw["project"]
    repo = project["repository"]
    if repo.count("/") != 1:
        raise ValueError("project.repository must be owner/repository")

    base = path.parent

    def resolve(value: str) -> Path:
        candidate = Path(os.path.expandvars(os.path.expanduser(value)))
        return candidate if candidate.is_absolute() else (base / candidate).resolve()

    labels = raw["labels"]
    allowed = frozenset(labels["allowed"])
    verdict_labels = dict(labels["verdict"])
    priority_labels = dict(labels["priority"])
    configured_labels = set(verdict_labels.values()) | set(priority_labels.values())
    if not configured_labels.issubset(allowed):
        raise ValueError("labels.allowed must include every verdict and priority label")

    triage = raw["issue_triage"]
    return Config(
        project_name=project["name"],
        repo=repo,
        checkout_path=resolve(project["checkout_path"]),
        database_path=resolve(raw["state"]["database_path"]),
        policy_path=resolve(triage["policy_path"]),
        comment_on_issue=bool(triage.get("comment_on_issue", True)),
        retry_after_seconds=int(triage.get("retry_after_seconds", 900)),
        allowed_labels=allowed,
        verdict_labels=verdict_labels,
        priority_labels=priority_labels,
    )
