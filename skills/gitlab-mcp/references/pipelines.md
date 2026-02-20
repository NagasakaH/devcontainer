# Pipeline Tools

> Requires `USE_PIPELINE=true` or toolset `pipelines` enabled.

### list_pipelines
List pipelines with filtering.

```json
{"tool": "list_pipelines", "arguments": {
  "project_id": "string (required)",
  "scope": "running | pending | finished | branches | tags",
  "status": "created | pending | running | success | failed | canceled | skipped | manual",
  "ref": "string (branch/tag)",
  "sha": "string",
  "order_by": "id | status | ref | updated_at | user_id",
  "sort": "asc | desc",
  "page": 1,
  "per_page": 20
}}
```

### get_pipeline
Get details of a specific pipeline.

```json
{"tool": "get_pipeline", "arguments": {
  "project_id": "string (required)",
  "pipeline_id": "string (required)"
}}
```

### create_pipeline
Create a new pipeline for a branch or tag.

```json
{"tool": "create_pipeline", "arguments": {
  "project_id": "string (required)",
  "ref": "string (required, branch/tag)",
  "variables": [
    {"key": "VAR_NAME", "value": "value"}
  ]
}}
```

### retry_pipeline
Retry a failed or canceled pipeline.

```json
{"tool": "retry_pipeline", "arguments": {
  "project_id": "string (required)",
  "pipeline_id": "string (required)"
}}
```

### cancel_pipeline
Cancel a running pipeline.

```json
{"tool": "cancel_pipeline", "arguments": {
  "project_id": "string (required)",
  "pipeline_id": "string (required)"
}}
```

## Pipeline Jobs

### list_pipeline_jobs
List all jobs in a pipeline.

```json
{"tool": "list_pipeline_jobs", "arguments": {
  "project_id": "string (required)",
  "pipeline_id": "string (required)",
  "scope": "created | pending | running | failed | success | canceled | skipped | manual",
  "page": 1,
  "per_page": 20
}}
```

### list_pipeline_trigger_jobs
List trigger jobs (bridges) that trigger downstream pipelines.

```json
{"tool": "list_pipeline_trigger_jobs", "arguments": {
  "project_id": "string (required)",
  "pipeline_id": "string (required)",
  "scope": "string",
  "page": 1,
  "per_page": 20
}}
```

### get_pipeline_job
Get details of a specific job.

```json
{"tool": "get_pipeline_job", "arguments": {
  "project_id": "string (required)",
  "job_id": "string (required)"
}}
```

### get_pipeline_job_output
Get job output/trace with optional pagination.

```json
{"tool": "get_pipeline_job_output", "arguments": {
  "project_id": "string (required)",
  "job_id": "string (required)",
  "limit": 1000,
  "offset": 0
}}
```

### play_pipeline_job
Run a manual pipeline job.

```json
{"tool": "play_pipeline_job", "arguments": {
  "project_id": "string (required)",
  "job_id": "string (required)"
}}
```

### retry_pipeline_job
Retry a failed/canceled job.

```json
{"tool": "retry_pipeline_job", "arguments": {
  "project_id": "string (required)",
  "job_id": "string (required)"
}}
```

### cancel_pipeline_job
Cancel a running job.

```json
{"tool": "cancel_pipeline_job", "arguments": {
  "project_id": "string (required)",
  "job_id": "string (required)"
}}
```
