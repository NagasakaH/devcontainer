# Project & Namespace Tools

## Projects

### get_project
Get details of a specific project.

```json
{"tool": "get_project", "arguments": {
  "project_id": "string (required)"
}}
```

### list_projects
List accessible projects.

```json
{"tool": "list_projects", "arguments": {
  "search": "string",
  "search_namespaces": true,
  "owned": true,
  "membership": true,
  "visibility": "public | internal | private",
  "order_by": "name | created_at | updated_at | last_activity_at",
  "sort": "asc | desc",
  "page": 1,
  "per_page": 20
}}
```

### list_project_members
List members of a project.

```json
{"tool": "list_project_members", "arguments": {
  "project_id": "string (required)",
  "query": "string (search name/username)",
  "include_inheritance": true,
  "page": 1,
  "per_page": 20
}}
```

### list_group_projects
List projects in a GitLab group.

```json
{"tool": "list_group_projects", "arguments": {
  "group_id": "string (required)",
  "include_subgroups": true,
  "search": "string",
  "order_by": "name | created_at | updated_at",
  "sort": "asc | desc",
  "visibility": "public | internal | private",
  "page": 1,
  "per_page": 20
}}
```

### list_group_iterations
List group iterations.

```json
{"tool": "list_group_iterations", "arguments": {
  "group_id": "string (required)",
  "state": "opened | upcoming | current | closed | all",
  "search": "string",
  "include_ancestors": true,
  "page": 1,
  "per_page": 20
}}
```

## Namespaces

### list_namespaces
List all available namespaces.

```json
{"tool": "list_namespaces", "arguments": {
  "search": "string",
  "owned": true,
  "page": 1,
  "per_page": 20
}}
```

### get_namespace
Get namespace details.

```json
{"tool": "get_namespace", "arguments": {
  "namespace_id": "string (required, ID or full path)"
}}
```

### verify_namespace
Verify if a namespace path exists.

```json
{"tool": "verify_namespace", "arguments": {
  "path": "string (required)"
}}
```
