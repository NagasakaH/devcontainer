# Issue Tools

## CRUD

### create_issue
Create a new issue.

```json
{"tool": "create_issue", "arguments": {
  "project_id": "string (required)",
  "title": "string (required)",
  "description": "string",
  "assignee_ids": [1, 2],
  "labels": ["bug"],
  "milestone_id": "string",
  "issue_type": "issue | incident | test_case | task"
}}
```

### get_issue
Get details of a specific issue.

```json
{"tool": "get_issue", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)"
}}
```

### update_issue
Update an issue.

```json
{"tool": "update_issue", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "title": "string",
  "description": "string",
  "assignee_ids": [1],
  "labels": ["ready"],
  "milestone_id": "string",
  "state_event": "close | reopen",
  "due_date": "YYYY-MM-DD",
  "weight": 5,
  "confidential": false
}}
```

### delete_issue
Delete an issue.

```json
{"tool": "delete_issue", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)"
}}
```

## List

### list_issues
List issues (default: created by current user, use `scope: "all"` for all).

```json
{"tool": "list_issues", "arguments": {
  "project_id": "string (optional)",
  "state": "opened | closed | all",
  "scope": "created_by_me | assigned_to_me | all",
  "labels": ["bug"],
  "milestone": "v1.0",
  "search": "keyword",
  "assignee_username": ["user1"],
  "created_after": "ISO 8601",
  "page": 1,
  "per_page": 20
}}
```

### my_issues
List issues assigned to the authenticated user.

```json
{"tool": "my_issues", "arguments": {
  "project_id": "string (optional)",
  "state": "opened | closed | all",
  "labels": ["label"],
  "search": "keyword",
  "page": 1,
  "per_page": 20
}}
```

## Notes

### create_issue_note
Add a note to an existing issue thread.

```json
{"tool": "create_issue_note", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "body": "string (required)"
}}
```

### update_issue_note
Modify an existing issue note.

```json
{"tool": "update_issue_note", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "note_id": "string (required)",
  "body": "string (required)"
}}
```

## Discussions

### list_issue_discussions
List discussions for an issue.

```json
{"tool": "list_issue_discussions", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "page": 1,
  "per_page": 20
}}
```

## Issue Links

### list_issue_links
List all links for an issue.

```json
{"tool": "list_issue_links", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)"
}}
```

### get_issue_link
Get a specific issue link.

```json
{"tool": "get_issue_link", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "issue_link_id": "string (required)"
}}
```

### create_issue_link
Create a link between two issues.

```json
{"tool": "create_issue_link", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "target_project_id": "string (required)",
  "target_issue_iid": "string (required)",
  "link_type": "relates_to | blocks | is_blocked_by"
}}
```

### delete_issue_link
Delete an issue link.

```json
{"tool": "delete_issue_link", "arguments": {
  "project_id": "string (required)",
  "issue_iid": "string (required)",
  "issue_link_id": "string (required)"
}}
```
