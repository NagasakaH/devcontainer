# Milestone Tools

> Requires `USE_MILESTONE=true` or toolset `milestones` enabled.

### list_milestones
List milestones.

```json
{"tool": "list_milestones", "arguments": {
  "project_id": "string (required)",
  "state": "active | closed",
  "title": "string",
  "search": "string",
  "include_ancestors": true,
  "page": 1,
  "per_page": 20
}}
```

### get_milestone
Get a specific milestone.

```json
{"tool": "get_milestone", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)"
}}
```

### create_milestone
Create a new milestone.

```json
{"tool": "create_milestone", "arguments": {
  "project_id": "string (required)",
  "title": "string (required)",
  "description": "string",
  "due_date": "YYYY-MM-DD",
  "start_date": "YYYY-MM-DD"
}}
```

### edit_milestone
Edit a milestone.

```json
{"tool": "edit_milestone", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)",
  "title": "string",
  "description": "string",
  "due_date": "YYYY-MM-DD",
  "start_date": "YYYY-MM-DD",
  "state_event": "close | activate"
}}
```

### delete_milestone
Delete a milestone.

```json
{"tool": "delete_milestone", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)"
}}
```

### get_milestone_issue
Get issues associated with a milestone.

```json
{"tool": "get_milestone_issue", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)"
}}
```

### get_milestone_merge_requests
Get MRs associated with a milestone.

```json
{"tool": "get_milestone_merge_requests", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)",
  "page": 1,
  "per_page": 20
}}
```

### promote_milestone
Promote a project milestone to group milestone.

```json
{"tool": "promote_milestone", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)"
}}
```

### get_milestone_burndown_events
Get burndown events for a milestone.

```json
{"tool": "get_milestone_burndown_events", "arguments": {
  "project_id": "string (required)",
  "milestone_id": "string (required)",
  "page": 1,
  "per_page": 20
}}
```
