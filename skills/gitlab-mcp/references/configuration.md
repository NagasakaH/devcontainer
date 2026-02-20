# Configuration

## Environment Variables

### Authentication

| Variable | Description | Required |
|----------|-------------|----------|
| `GITLAB_TOKEN` | GitLab Personal Access Token (skill reads this) | Yes |
| `GITLAB_API_URL` | GitLab API URL (default: `https://gitlab.com/api/v4`) | No |
| `GITLAB_PROJECT_ID` | Default project ID | No |

### Optional Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `GITLAB_READ_ONLY_MODE` | Restrict to read-only operations | `false` |
| `GITLAB_ALLOWED_PROJECT_IDS` | Comma-separated list of allowed project IDs | (none) |
| `USE_GITLAB_WIKI` | Enable wiki tools | `false` |
| `USE_MILESTONE` | Enable milestone tools | `false` |
| `USE_PIPELINE` | Enable pipeline tools | `false` |
| `GITLAB_TOOLSETS` | Comma-separated toolset IDs or `"all"` | default set |
| `GITLAB_TOOLS` | Additional individual tool names (additive) | (none) |

### Available Toolsets

| Toolset | Default | Tool Count |
|---------|---------|------------|
| `merge_requests` | ✅ | 31 |
| `issues` | ✅ | 14 |
| `repositories` | ✅ | 7 |
| `branches` | ✅ | 4 |
| `projects` | ✅ | 8 |
| `labels` | ✅ | 5 |
| `releases` | ✅ | 7 |
| `users` | ✅ | 5 |
| `pipelines` | ❌ | 12 |
| `milestones` | ❌ | 9 |
| `wiki` | ❌ | 5 |

To modify `mcp-config.json` for additional toolsets, add env vars:

```json
{
  "env": {
    "GITLAB_PERSONAL_ACCESS_TOKEN": "${GITLAB_TOKEN}",
    "GITLAB_API_URL": "https://gitlab.com/api/v4",
    "USE_PIPELINE": "true",
    "USE_MILESTONE": "true",
    "USE_GITLAB_WIKI": "true"
  }
}
```

### Pagination

All list operations support pagination:
- `page`: Page number (default: 1)
- `per_page`: Items per page (max: 100, default: 20)
