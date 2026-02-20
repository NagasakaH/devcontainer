# User & Event Tools

## Users

### get_users
Get user details by usernames.

```json
{"tool": "get_users", "arguments": {
  "usernames": ["user1", "user2"]
}}
```

## Events

### list_events
List events for the authenticated user.

```json
{"tool": "list_events", "arguments": {
  "action": "created | updated | closed | reopened | pushed | commented | merged | joined | left | destroyed | expired",
  "target_type": "Issue | MergeRequest | Milestone",
  "before": "YYYY-MM-DD",
  "after": "YYYY-MM-DD",
  "sort": "asc | desc",
  "page": 1,
  "per_page": 20
}}
```

### get_project_events
List events for a specific project.

```json
{"tool": "get_project_events", "arguments": {
  "project_id": "string (required)",
  "action": "created | updated | closed | reopened | pushed | commented | merged | joined | left | destroyed | expired",
  "target_type": "Issue | MergeRequest | Milestone",
  "before": "YYYY-MM-DD",
  "after": "YYYY-MM-DD",
  "sort": "asc | desc",
  "page": 1,
  "per_page": 20
}}
```

## Uploads

### upload_markdown
Upload a file for use in markdown content.

```json
{"tool": "upload_markdown", "arguments": {
  "project_id": "string (required)",
  "file_path": "string (required, local path)"
}}
```

### download_attachment
Download an uploaded file by secret and filename. Images are returned as base64.

```json
{"tool": "download_attachment", "arguments": {
  "project_id": "string (required)",
  "secret": "string (required, 32-char secret)",
  "filename": "string (required)",
  "local_path": "string (optional, save path)"
}}
```

## GraphQL

### execute_graphql
Execute a GitLab GraphQL query. Not in any toolset — must be explicitly enabled via `GITLAB_TOOLS=execute_graphql`.

```json
{"tool": "execute_graphql", "arguments": {
  "query": "string (required, GraphQL query)",
  "variables": {}
}}
```
