from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from .codex import run_codex
from .config import load_config
from .github import GitHubCliError, apply_issue_actions, list_open_issues
from .report import load_and_validate_report
from .state import StateStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-github-ops")
    parser.add_argument("--profile", required=True, help="Path to a project profile TOML")
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="Emit unseen/newly-updated issues as JSON Lines")
    scan.add_argument("--bootstrap", action="store_true", help="Record current issues without triaging them")
    scan.add_argument("--limit", type=int, default=100)

    apply = commands.add_parser("apply", help="Validate a report, add approved labels/comment, and acknowledge the issue")
    apply.add_argument("--issue", type=int, required=True)
    apply.add_argument("--report", type=Path, required=True)

    codex = commands.add_parser("run-codex", help="Run a read-only Codex triage worker for one issue request")
    codex.add_argument("--issue-file", type=Path, required=True)
    codex.add_argument("--report", type=Path, required=True)
    codex.add_argument("--schema", type=Path, default=Path("schemas/triage-report.schema.json"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    config = load_config(args.profile)
    try:
        if args.command == "scan":
            issues = list_open_issues(config.repo, args.limit)
            store = StateStore(config.database_path)
            try:
                candidates = store.scan(config.repo, issues, args.bootstrap, config.retry_after_seconds)
            finally:
                store.close()
            for issue in candidates:
                print(json.dumps(issue, separators=(",", ":")))
            return

        if args.command == "apply":
            report = load_and_validate_report(args.report, config)
            comment = report.comment if config.comment_on_issue else None
            apply_issue_actions(config.repo, args.issue, report.labels, comment)
            store = StateStore(config.database_path)
            try:
                store.complete(config.repo, args.issue)
            finally:
                store.close()
            return

        if args.command == "run-codex":
            run_codex(config, args.issue_file.resolve(), args.report.resolve(), args.schema.resolve())
            return
    except (GitHubCliError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
