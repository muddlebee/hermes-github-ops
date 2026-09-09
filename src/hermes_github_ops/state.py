from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Any, Iterable


@dataclass(frozen=True)
class PendingIssue:
    number: int
    updated_at: str


class StateStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS issue_state (
              repo TEXT NOT NULL,
              number INTEGER NOT NULL,
              updated_at TEXT NOT NULL,
              status TEXT NOT NULL,
              last_attempt_at TEXT,
              PRIMARY KEY (repo, number)
            )
            """
        )

    def close(self) -> None:
        self.connection.close()

    def scan(
        self,
        repo: str,
        issues: Iterable[dict[str, Any]],
        bootstrap: bool,
        retry_after_seconds: int,
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        retry_before = (now - timedelta(seconds=retry_after_seconds)).isoformat()
        candidates: list[dict[str, Any]] = []

        for issue in issues:
            number = int(issue["number"])
            updated_at = str(issue["updatedAt"])
            row = self.connection.execute(
                "SELECT updated_at, status, last_attempt_at FROM issue_state WHERE repo = ? AND number = ?",
                (repo, number),
            ).fetchone()

            if row is None:
                status = "completed" if bootstrap else "pending"
                self.connection.execute(
                    "INSERT INTO issue_state(repo, number, updated_at, status) VALUES (?, ?, ?, ?)",
                    (repo, number, updated_at, status),
                )
                if not bootstrap:
                    candidates.append(issue)
                continue

            previous_updated_at, status, last_attempt_at = row
            changed = previous_updated_at != updated_at
            retryable = status == "pending" and (
                last_attempt_at is None or last_attempt_at < retry_before
            )
            if changed:
                self.connection.execute(
                    "UPDATE issue_state SET updated_at = ?, status = 'pending', last_attempt_at = NULL "
                    "WHERE repo = ? AND number = ?",
                    (updated_at, repo, number),
                )
                candidates.append(issue)
            elif retryable:
                candidates.append(issue)

        for issue in candidates:
            self.connection.execute(
                "UPDATE issue_state SET last_attempt_at = ? WHERE repo = ? AND number = ?",
                (now.isoformat(), repo, int(issue["number"])),
            )
        self.connection.commit()
        return candidates

    def complete(self, repo: str, issue_number: int) -> None:
        self.connection.execute(
            "UPDATE issue_state SET status = 'completed' WHERE repo = ? AND number = ?",
            (repo, issue_number),
        )
        self.connection.commit()

