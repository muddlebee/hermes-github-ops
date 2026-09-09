from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest

from hermes_github_ops.state import StateStore


def issue(number: int, updated_at: str):
    return {"number": number, "updatedAt": updated_at, "title": "Example"}


class StateStoreTests(unittest.TestCase):
    def test_bootstrap_suppresses_existing_backlog(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.sqlite3")
            try:
                first = issue(12, "2026-09-09T10:00:00Z")
                self.assertEqual(
                    store.scan("owner/repo", [first], bootstrap=True, retry_after_seconds=900),
                    [],
                )
                self.assertEqual(
                    store.scan("owner/repo", [first], bootstrap=False, retry_after_seconds=900),
                    [],
                )
                changed = issue(12, "2026-09-09T11:00:00Z")
                self.assertEqual(
                    store.scan("owner/repo", [changed], bootstrap=False, retry_after_seconds=900),
                    [changed],
                )
            finally:
                store.close()

    def test_new_issue_is_emitted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.sqlite3")
            try:
                fresh = issue(13, datetime.now(UTC).isoformat())
                self.assertEqual(
                    store.scan("owner/repo", [fresh], bootstrap=False, retry_after_seconds=900),
                    [fresh],
                )
            finally:
                store.close()
