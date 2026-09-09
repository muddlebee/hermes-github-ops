"""Native Hermes plugin entry point for generic GitHub operations.

The plugin deliberately delegates authentication to the VPS user's `gh` CLI. It does
not read, write, or distribute GitHub credentials.
"""

from pathlib import Path
import subprocess


def _gh_status(_: str) -> str:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"], text=True, capture_output=True, check=False
        )
    except FileNotFoundError:
        return "GitHub CLI is missing. Install gh, then run `gh auth login` on this host."

    output = (result.stderr or result.stdout).strip()
    if result.returncode == 0:
        return "GitHub CLI authentication is ready.\n" + output
    return "GitHub CLI is not authenticated. Run `gh auth login` on this host.\n" + output


def _help(_: str) -> str:
    return (
        "Load `hermes-github-ops:issue-triage` for the generic issue-triage workflow. "
        "Choose a project profile to supply repository, policy, allowed labels, and "
        "checkout path. GitHub access always goes through the authenticated gh CLI."
    )


def register(ctx):
    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)

    ctx.register_command(
        "github-ops-status",
        handler=_gh_status,
        description="Verify the gh CLI authentication used by GitHub Ops",
    )
    ctx.register_command(
        "github-ops-help",
        handler=_help,
        description="Explain the GitHub Ops workflow",
    )

