from pathlib import Path
import json
import unittest

from hermes_github_ops.config import load_config
from hermes_github_ops.report import load_and_validate_report


def write_config(tmp_path: Path) -> Path:
    config = tmp_path / "config.toml"
    config.write_text(
        """
[project]
name = "example"
repository = "owner/repo"
checkout_path = "checkout"
[state]
database_path = "state.sqlite3"
[issue_triage]
policy_path = "policy.md"
[labels]
allowed = ["triage:confirmed", "triage:priority-p2", "area:scheduler"]
[labels.verdict]
confirmed_bug = "triage:confirmed"
[labels.priority]
P2 = "triage:priority-p2"
"""
    )
    return config


def report_payload(**overrides):
    payload = {
        "verdict": "confirmed_bug",
        "confidence": "high",
        "priority_recommendation": "P2",
        "evidence": ["tests/example.py"],
        "missing_information": [],
        "duplicate_candidates": [],
        "suggested_labels": ["area:scheduler"],
        "comment": "Thanks — this looks reproducible.",
    }
    payload.update(overrides)
    return payload


class ReportValidationTests(unittest.TestCase):
    def test_only_allow_listed_labels_are_returned(self):
        with self.subTest("valid report"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as directory:
                tmp_path = Path(directory)
                config = load_config(write_config(tmp_path))
                report_path = tmp_path / "report.json"
                report_path.write_text(json.dumps(report_payload()))

                report = load_and_validate_report(report_path, config)

                self.assertEqual(
                    report.labels,
                    ["area:scheduler", "triage:confirmed", "triage:priority-p2"],
                )

    def test_unknown_suggested_label_is_rejected(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            config = load_config(write_config(tmp_path))
            report_path = tmp_path / "report.json"
            report_path.write_text(json.dumps(report_payload(suggested_labels=["area:unknown"])))

            with self.assertRaisesRegex(ValueError, "allow-list"):
                load_and_validate_report(report_path, config)
