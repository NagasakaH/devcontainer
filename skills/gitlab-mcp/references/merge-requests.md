# Merge Request Tools

## Tools

### merge_merge_request
Merge a merge request.

```json
{"tool": "merge_merge_request", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string",
  "auto_merge": false,
  "merge_commit_message": "string",
  "should_remove_source_branch": false,
  "squash": false,
  "squash_commit_message": "string"
}}
```

### approve_merge_request
Approve a merge request.

```json
{"tool": "approve_merge_request", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "sha": "string (optional, HEAD of MR for safety check)"
}}
```

### unapprove_merge_request
Unapprove a previously approved merge request.

```json
{"tool": "unapprove_merge_request", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)"
}}
```

### get_merge_request_approval_state
Get approval state including rules and who has approved.

```json
{"tool": "get_merge_request_approval_state", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)"
}}
```

### create_merge_request
Create a new merge request.

```json
{"tool": "create_merge_request", "arguments": {
  "project_id": "string (required)",
  "title": "string (required)",
  "source_branch": "string (required)",
  "target_branch": "string (required)",
  "description": "string",
  "assignee_ids": [1, 2],
  "reviewer_ids": [3],
  "labels": ["bug", "urgent"],
  "draft": false,
  "remove_source_branch": true,
  "squash": false
}}
```

### get_merge_request
Get details (use `merge_request_iid` or `source_branch`).

```json
{"tool": "get_merge_request", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string",
  "source_branch": "string"
}}
```

### update_merge_request
Update MR fields (use `merge_request_iid` or `source_branch`).

```json
{"tool": "update_merge_request", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string",
  "title": "string",
  "description": "string",
  "target_branch": "string",
  "assignee_ids": [1],
  "reviewer_ids": [2],
  "labels": ["ready"],
  "state_event": "close | reopen",
  "draft": false,
  "squash": true
}}
```

### list_merge_requests
List MRs globally or per project.

```json
{"tool": "list_merge_requests", "arguments": {
  "project_id": "string (optional)",
  "state": "opened | closed | locked | merged | all",
  "scope": "created_by_me | assigned_to_me | all",
  "labels": ["label1"],
  "search": "string",
  "order_by": "created_at | updated_at",
  "sort": "asc | desc",
  "page": 1,
  "per_page": 20
}}
```

### get_merge_request_diffs
Get changes/diffs of a MR.

```json
{"tool": "get_merge_request_diffs", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string",
  "source_branch": "string"
}}
```

### list_merge_request_diffs
List MR diffs with pagination.

```json
{"tool": "list_merge_request_diffs", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string",
  "source_branch": "string",
  "page": 1,
  "per_page": 20
}}
```

### list_merge_request_versions
List all versions of a merge request.

```json
{"tool": "list_merge_request_versions", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)"
}}
```

### get_merge_request_version
Get a specific version of a merge request.

```json
{"tool": "get_merge_request_version", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "version_id": "string (required)"
}}
```

## Threads & Discussions

### create_merge_request_thread
Create a new thread on a MR (supports diff position for code review).

```json
{"tool": "create_merge_request_thread", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "body": "string (required)",
  "position": {
    "base_sha": "string (from diff_refs.base_sha)",
    "head_sha": "string (from diff_refs.head_sha)",
    "start_sha": "string (from diff_refs.start_sha)",
    "position_type": "text | image | file",
    "new_path": "path/to/file",
    "old_path": "path/to/file",
    "new_line": 10,
    "old_line": null
  }
}}
```

### resolve_merge_request_thread
Resolve/unresolve a thread.

```json
{"tool": "resolve_merge_request_thread", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "discussion_id": "string (required)",
  "resolved": true
}}
```

### mr_discussions
List discussion items for a MR.

```json
{"tool": "mr_discussions", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "page": 1,
  "per_page": 20
}}
```

### create_merge_request_discussion_note
Add a reply to an existing discussion thread.

```json
{"tool": "create_merge_request_discussion_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "discussion_id": "string (required)",
  "body": "string (required)"
}}
```

### update_merge_request_discussion_note
Update a discussion note.

```json
{"tool": "update_merge_request_discussion_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "discussion_id": "string (required)",
  "note_id": "string (required)",
  "body": "string (required)"
}}
```

### delete_merge_request_discussion_note
Delete a discussion note.

```json
{"tool": "delete_merge_request_discussion_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "discussion_id": "string (required)",
  "note_id": "string (required)"
}}
```

## Notes (non-discussion)

### create_note
Create a note (comment) on an issue or MR.

```json
{"tool": "create_note", "arguments": {
  "project_id": "string (required)",
  "noteable_type": "issue | merge_request",
  "noteable_iid": "string (required)",
  "body": "string (required)"
}}
```

### create_merge_request_note
Add a note to a MR.

```json
{"tool": "create_merge_request_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "body": "string (required)"
}}
```

### get_merge_request_note / get_merge_request_notes
Get single or list notes for a MR.

```json
{"tool": "get_merge_request_notes", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "page": 1,
  "per_page": 20
}}
```

### update_merge_request_note
Modify an existing MR note.

```json
{"tool": "update_merge_request_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "note_id": "string (required)",
  "body": "string (required)"
}}
```

### delete_merge_request_note
Delete a MR note.

```json
{"tool": "delete_merge_request_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "note_id": "string (required)"
}}
```

## Draft Notes

### create_draft_note
Create a draft note for a MR.

```json
{"tool": "create_draft_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "body": "string (required)",
  "in_reply_to_discussion_id": "string",
  "position": { "...position object..." },
  "resolve_discussion": false
}}
```

### list_draft_notes / get_draft_note
List or get draft notes.

```json
{"tool": "list_draft_notes", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)"
}}
```

### update_draft_note
Update an existing draft note.

```json
{"tool": "update_draft_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "draft_note_id": "string (required)",
  "body": "string"
}}
```

### delete_draft_note
Delete a draft note.

```json
{"tool": "delete_draft_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "draft_note_id": "string (required)"
}}
```

### publish_draft_note
Publish a single draft note.

```json
{"tool": "publish_draft_note", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)",
  "draft_note_id": "string (required)"
}}
```

### bulk_publish_draft_notes
Publish all draft notes for a MR.

```json
{"tool": "bulk_publish_draft_notes", "arguments": {
  "project_id": "string (required)",
  "merge_request_iid": "string (required)"
}}
```
