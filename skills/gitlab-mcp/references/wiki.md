# Wiki Tools

> Requires `USE_GITLAB_WIKI=true` or toolset `wiki` enabled.

### list_wiki_pages
List wiki pages.

```json
{"tool": "list_wiki_pages", "arguments": {
  "project_id": "string (required)",
  "with_content": true,
  "page": 1,
  "per_page": 20
}}
```

### get_wiki_page
Get a specific wiki page.

```json
{"tool": "get_wiki_page", "arguments": {
  "project_id": "string (required)",
  "slug": "string (required, URL-encoded slug)"
}}
```

### create_wiki_page
Create a new wiki page.

```json
{"tool": "create_wiki_page", "arguments": {
  "project_id": "string (required)",
  "title": "string (required)",
  "content": "string (required)",
  "format": "markdown | rdoc"
}}
```

### update_wiki_page
Update a wiki page.

```json
{"tool": "update_wiki_page", "arguments": {
  "project_id": "string (required)",
  "slug": "string (required)",
  "title": "string",
  "content": "string",
  "format": "markdown | rdoc"
}}
```

### delete_wiki_page
Delete a wiki page.

```json
{"tool": "delete_wiki_page", "arguments": {
  "project_id": "string (required)",
  "slug": "string (required)"
}}
```
