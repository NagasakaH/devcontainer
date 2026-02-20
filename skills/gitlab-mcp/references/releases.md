# Release Tools

### list_releases
List all releases for a project.

```json
{"tool": "list_releases", "arguments": {
  "project_id": "string (required)",
  "order_by": "released_at | created_at",
  "sort": "asc | desc",
  "page": 1,
  "per_page": 20
}}
```

### get_release
Get a release by tag name.

```json
{"tool": "get_release", "arguments": {
  "project_id": "string (required)",
  "tag_name": "string (required)"
}}
```

### create_release
Create a new release.

```json
{"tool": "create_release", "arguments": {
  "project_id": "string (required)",
  "tag_name": "string (required)",
  "name": "string",
  "description": "string (release notes, markdown)",
  "ref": "string (branch/commit for new tag)",
  "milestones": ["v1.0"],
  "released_at": "ISO 8601 datetime",
  "assets": {
    "links": [
      {
        "name": "string",
        "url": "string",
        "filepath": "string (optional)",
        "link_type": "other | runbook | image | package"
      }
    ]
  }
}}
```

### update_release
Update an existing release.

```json
{"tool": "update_release", "arguments": {
  "project_id": "string (required)",
  "tag_name": "string (required)",
  "name": "string",
  "description": "string",
  "milestones": ["v1.1"],
  "released_at": "ISO 8601 datetime"
}}
```

### delete_release
Delete a release (tag is not deleted).

```json
{"tool": "delete_release", "arguments": {
  "project_id": "string (required)",
  "tag_name": "string (required)"
}}
```

### create_release_evidence
Create release evidence (Premium/Ultimate only).

```json
{"tool": "create_release_evidence", "arguments": {
  "project_id": "string (required)",
  "tag_name": "string (required)"
}}
```

### download_release_asset
Download a release asset file.

```json
{"tool": "download_release_asset", "arguments": {
  "project_id": "string (required)",
  "tag_name": "string (required)",
  "asset_path": "string (required, direct asset path)"
}}
```
