# Hermes GitHub Ops

A generic, multi-repository Hermes plugin for GitHub operations. `gh` is the sole
GitHub transport, while Hermes owns skills, schedules, alerts, and future capability
expansion. The first shipped capability is conservative issue triage; PR review, CI
investigation, release watch, and work queues can be added without changing the core.

It is not a general autonomous coding bot. It never closes issues, assigns people,
edits code, opens PRs, or accepts model-generated shell commands.

## Architecture

```text
GitHub event/poller → project profile → Hermes/Codex worker → validated action plan → gh writer
```

The model produces a report; the Python controller owns all side effects. This keeps
prompt injection in issue text from becoming arbitrary GitHub commands.

## Prerequisites

- Python 3.11+
- [GitHub CLI](https://cli.github.com/) authenticated with **your** account on the
  Hermes VPS:

  ```bash
  gh auth login
  gh auth status
  ```

- A clean checkout of the target repository on the VPS.
- Hermes Agent for scheduling/notifications. The bundled `github-auth` and
  `github-issues` skills own GitHub access; the optional `watchers` skill handles
  polling/deduplication.
- Codex CLI only if you use the `run-codex` worker. The harness itself does not store
  or read an OpenAI credential.

## Install as a Hermes plugin

After publishing this repository, install it on the VPS:

```bash
hermes plugins install muddlebee/hermes-github-ops --no-enable
hermes plugins enable hermes-github-ops
hermes plugins doctor ~/.hermes/plugins/hermes-github-ops --ci
```

Authenticate `gh` once on the same Linux account that runs Hermes, then verify it in
any Hermes chat with `/github-ops-status`. The plugin never stores or reads a GitHub
token.

## Project profiles

Each repository has a profile; the core has no OpenSRE-specific policy or label names.
Copy `profiles/example.toml` to `profiles/<project>.toml` and set repository, checkout,
policy, write mode, and the label allow-list. Store runtime SQLite state under
`${HERMES_HOME}/plugin-data/hermes-github-ops/`, not inside the plugin install tree.

## Controller quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .

cp profiles/example.toml profiles/my-project.toml
# Edit project.repository, checkout_path, database_path and allowed labels.

# Establish a baseline so the current backlog is not re-triaged.
hermes-github-ops --profile profiles/my-project.toml scan --bootstrap

# Future scans emit only new or updated issues as JSON Lines.
hermes-github-ops --profile profiles/my-project.toml scan
```

Run the dependency-free checks with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

For every emitted issue, write it to an `issue.json`, run your model worker, then use
the constrained writer:

```bash
hermes-github-ops --profile profiles/my-project.toml run-codex \
  --issue-file issue.json --report report.json

hermes-github-ops --profile profiles/my-project.toml apply \
  --issue 123 --report report.json
```

`apply` fails closed if the report does not have the exact expected fields or requests
a label outside `labels.allowed`.

## Hermes scheduling

Install Hermes' optional watcher skill:

```bash
hermes skills install official/devops/watchers
```

Start with a five-minute cron job. The job should:

1. call `hermes-github-ops scan`;
2. send each emitted issue to the `hermes-github-ops:issue-triage` skill;
3. write the report to disk;
4. call `apply` only when its report validates;
5. notify you for `P1`, `P2`, `duplicate`, and `security_report_needed` results.

Keep the first week human-reviewed: use triage-prefixed priority labels and do not
enable automatic closure or assignment.

## Credential boundary

The VPS authenticates GitHub once with `gh auth login`; Hermes and this controller use
that account through normal `gh` commands. The project contains no GitHub token.

On a public repository, keep the Codex worker read-only and use an automation-safe
authentication method rather than copying a personal ChatGPT/Codex account token into
the service.
