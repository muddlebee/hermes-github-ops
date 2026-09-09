from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Iterable


class GitHubCliError(RuntimeError):
    pass


def _run_gh(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["gh", *args], text=True, capture_output=True, check=True
        )
    except FileNotFoundError as exc:
        raise GitHubCliError("gh is required; install it and run `gh auth login`.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or "unknown gh failure"
        raise GitHubCliError(message) from exc
    return result.stdout


def list_open_issues(repo: str, limit: int = 100) -> list[dict[str, Any]]:
    fields = "number,title,body,updatedAt,labels,url,author"
    output = _run_gh([
        "issue", "list", "--repo", repo, "--state", "open", "--limit", str(limit),
        "--json", fields,
    ])
    data = json.loads(output)
    if not isinstance(data, list):
        raise GitHubCliError("gh returned a non-list issue payload")
    return data


def apply_issue_actions(
    repo: str, issue_number: int, labels: Iterable[str], comment: str | None
) -> None:
    label_args: list[str] = []
    for label in labels:
        label_args.extend(["--add-label", label])
    if label_args:
        _run_gh(["issue", "edit", str(issue_number), "--repo", repo, *label_args])

    if comment:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(comment)
            comment_path = Path(handle.name)
        try:
            _run_gh([
                "issue", "comment", str(issue_number), "--repo", repo,
                "--body-file", str(comment_path),
            ])
        finally:
            comment_path.unlink(missing_ok=True)

