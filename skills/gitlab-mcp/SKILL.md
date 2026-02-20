---
name: gitlab-mcp
description: GitLab API access via MCP server (@zereight/mcp-gitlab). Use when interacting with GitLab projects, merge requests, issues, pipelines, branches, labels, milestones, wiki pages, releases, or users. Supports all standard GitLab operations including CRUD for issues/MRs, code review with diff comments, pipeline management, and repository operations. Requires GITLAB_TOKEN environment variable (or prompts user for token).
---

# GitLab MCP Skill

Access GitLab API through the `@zereight/mcp-gitlab` MCP server.

## Authentication

Read GITLAB_TOKEN from environment. If not set, prompt the user for their GitLab Personal Access Token.

```bash
# Check token availability
echo $GITLAB_TOKEN
```

## Usage

Execute tools via the executor script:

```bash
# Call a tool
python3 "$SKILL_DIR/scripts/executor.py" --call '{"tool": "tool_name", "arguments": {...}}'

# List available tools
python3 "$SKILL_DIR/scripts/executor.py" --list

# Describe a specific tool's parameters
python3 "$SKILL_DIR/scripts/executor.py" --describe tool_name
```

Replace `$SKILL_DIR` with the actual discovered path of this skill directory.

## Tool Categories

Select the appropriate reference for detailed tool documentation:

| Category | Tools | Reference |
|----------|-------|-----------|
| Merge Requests | merge, approve, diffs, threads, notes, draft notes | [references/merge-requests.md](references/merge-requests.md) |
| Issues | CRUD, notes, links, discussions | [references/issues.md](references/issues.md) |
| Repositories | search, create, file contents, push, fork, tree | [references/repositories.md](references/repositories.md) |
| Branches & Commits | create branch, diffs, commits | [references/branches.md](references/branches.md) |
| Projects & Namespaces | project info, members, groups, iterations | [references/projects.md](references/projects.md) |
| Labels | CRUD | [references/labels.md](references/labels.md) |
| Pipelines | list, create, retry, cancel, jobs | [references/pipelines.md](references/pipelines.md) |
| Milestones | CRUD, burndown, associated issues/MRs | [references/milestones.md](references/milestones.md) |
| Wiki | CRUD | [references/wiki.md](references/wiki.md) |
| Releases | CRUD, evidence, asset download | [references/releases.md](references/releases.md) |
| Users & Events | user info, events, uploads, attachments | [references/users.md](references/users.md) |
| Configuration | environment variables, setup options | [references/configuration.md](references/configuration.md) |
