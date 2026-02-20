# Branch & Commit Tools

## Branches

### create_branch
Create a new branch.

```json
{"tool": "create_branch", "arguments": {
  "project_id": "string (required)",
  "branch": "string (required, new branch name)",
  "ref": "string (optional, source branch/commit)"
}}
```

### get_branch_diffs
Get diffs between two branches or commits.

```json
{"tool": "get_branch_diffs", "arguments": {
  "project_id": "string (required)",
  "from": "string (required, base branch/SHA)",
  "to": "string (required, target branch/SHA)",
  "straight": false,
  "excluded_file_patterns": ["^vendor/", "\\.spec\\.ts$"]
}}
```

## Commits

### list_commits
List repository commits with filtering.

```json
{"tool": "list_commits", "arguments": {
  "project_id": "string (required)",
  "ref_name": "string (branch/tag)",
  "since": "YYYY-MM-DDTHH:MM:SSZ",
  "until": "YYYY-MM-DDTHH:MM:SSZ",
  "path": "string (file path filter)",
  "author": "string",
  "with_stats": true,
  "page": 1,
  "per_page": 20
}}
```

### get_commit
Get details of a specific commit.

```json
{"tool": "get_commit", "arguments": {
  "project_id": "string (required)",
  "sha": "string (required, commit hash or branch/tag)",
  "stats": true
}}
```

### get_commit_diff
Get diffs of a specific commit.

```json
{"tool": "get_commit_diff", "arguments": {
  "project_id": "string (required)",
  "sha": "string (required)",
  "full_diff": false
}}
```
