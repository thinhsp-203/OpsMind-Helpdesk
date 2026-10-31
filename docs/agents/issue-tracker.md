# Issue tracker: GitHub

Repository: `thinhsp-203/OpsMind-Helpdesk`.

Issues and new specifications requested for publication live in GitHub Issues. Use the connected GitHub tools when available; otherwise use authenticated `gh` with an explicit `--repo thinhsp-203/OpsMind-Helpdesk`. Verify the repository before writing. Never file this project's issues in the skills author's repository.

## Workflow

- Search existing open and closed issues before creating work to avoid duplicates.
- Read the issue body, labels, comments, and dependencies before implementation.
- When a skill says to publish to the issue tracker, create a GitHub issue in this repository. When it says to fetch a ticket, read the referenced issue.
- Include the problem, scope, acceptance criteria, verification plan, and source specification in each implementation issue.
- Prefer native sub-issues and blocking dependencies when supported. Otherwise use `Part of #<parent>` and `Blocked by: #<number>` in the body, plus a task list in the parent. A ticket is startable only when all blockers are closed.
- Use numeric database IDs, not issue numbers or node IDs, for GitHub dependency APIs that require `issue_id`.
- Add verification evidence and limitations before closing completed work. Post any completion explanation separately before closing, so it is preserved even if the issue was already closed.
- For CLI multiline bodies, write a temporary UTF-8 file and pass `--body-file`; preserve actual newlines.

## Existing local tickets

The eight files in `.scratch/assistant-spec/issues/` are historical records. Preserve them. GitHub Issues is the tracker for new work; do not automatically recreate historical tickets or mark externally gated work complete. If migration is requested, search for duplicates and record the resulting issue links.

## Pull requests as a triage surface

**PRs as a request surface: no.**

GitHub shares issue and PR numbers; resolve the object type before acting on a bare reference.

