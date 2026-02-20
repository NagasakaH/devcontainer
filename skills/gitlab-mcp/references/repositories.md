# Repository Tools

### search_repositories
Search for GitLab projects.

```json
{"tool": "search_repositories", "arguments": {
  "search": "string (required)",
  "page": 1,
  "per_page": 20
}}
```

### create_repository
Create a new GitLab project.

```json
{"tool": "create_repository", "arguments": {
  "name": "string (required)",
  "description": "string",
  "visibility": "private | internal | public",
  "initialize_with_readme": true
}}
```

### get_file_contents
Get file or directory contents.

```json
{"tool": "get_file_contents", "arguments": {
  "project_id": "string (required)",
  "file_path": "string (required)",
  "ref": "branch/tag/commit (optional)"
}}
```

### create_or_update_file
Create or update a single file.

```json
{"tool": "create_or_update_file", "arguments": {
  "project_id": "string (required)",
  "file_path": "string (required)",
  "content": "string (required)",
  "commit_message": "string (required)",
  "branch": "string (required)",
  "previous_path": "string (for rename)"
}}
```

### push_files
Push multiple files in a single commit.

```json
{"tool": "push_files", "arguments": {
  "project_id": "string (required)",
  "branch": "string (required)",
  "commit_message": "string (required)",
  "files": [
    {"file_path": "path/to/file", "content": "file content"}
  ]
}}
```

### fork_repository
Fork a project.

```json
{"tool": "fork_repository", "arguments": {
  "project_id": "string (required)",
  "namespace": "string (optional, full path)"
}}
```

### get_repository_tree
List files and directories in a project.

```json
{"tool": "get_repository_tree", "arguments": {
  "project_id": "string (required)",
  "path": "string (optional, subdirectory)",
  "ref": "string (branch/tag)",
  "recursive": true,
  "page": 1,
  "per_page": 20
}}
```
