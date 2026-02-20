# Label Tools

### list_labels
List labels for a project.

```json
{"tool": "list_labels", "arguments": {
  "project_id": "string (required)",
  "with_counts": true,
  "include_ancestor_groups": true,
  "search": "string"
}}
```

### get_label
Get a single label.

```json
{"tool": "get_label", "arguments": {
  "project_id": "string (required)",
  "label_id": "string (required, ID or title)"
}}
```

### create_label
Create a new label.

```json
{"tool": "create_label", "arguments": {
  "project_id": "string (required)",
  "name": "string (required)",
  "color": "#FF0000 (required, 6-digit hex with #)",
  "description": "string",
  "priority": 1
}}
```

### update_label
Update an existing label.

```json
{"tool": "update_label", "arguments": {
  "project_id": "string (required)",
  "label_id": "string (required, ID or title)",
  "new_name": "string",
  "color": "#00FF00",
  "description": "string",
  "priority": 2
}}
```

### delete_label
Delete a label.

```json
{"tool": "delete_label", "arguments": {
  "project_id": "string (required)",
  "label_id": "string (required, ID or title)"
}}
```
