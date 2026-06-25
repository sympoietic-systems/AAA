# Research Export / Import

Transfer research tasks from one AAA server to another via JSON.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/research/tasks/{id}/export/json` | Export a single task |
| GET | `/api/research/export/all` | Export all tasks |
| POST | `/api/research/import` | Import task(s) |

All endpoints require Bearer token auth (same as all `/api` routes).

## Export All Tasks

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/research/export/all > research-all.json
```

Filter by status:
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/research/export/all?status=completed" > research.json
```

## Export Single Task

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/research/tasks/<TASK_ID>/export/json > research.json
```

## Import to Another Server

Supports both single-task and bulk (export all) payloads. The import generates fresh UUIDs
for all records to avoid ID collisions.

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @research.json \
  http://other-server:8000/api/research/import
```

Works with output from both `export/all` and single-task export.

## Import Behavior

- **New UUIDs**: Every record gets a fresh UUID — never conflicts with existing data
- **Internal references remapped**: `task_id`, `branch_id`, `plan_id`, `step_id` all point to new IDs
- **External references nullified**: `conversation_id`, `message_id`, `memory_node_id` are set to null (they may not exist on target)
- **Always inserts**: Each import creates net-new records; existing data is never overwritten

## Full Workflow

```bash
# On dev server — export all
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/research/export/all > backup.json

# On prod server — import
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @backup.json \
  https://prod.example.com/api/research/import
```

## Response Format

**Import response:**
```json
{
  "imported": true,
  "count": 3,
  "results": [
    {
      "imported": true,
      "new_task_id": "550e8400-e29b-...",
      "stats": {
        "task": "inserted",
        "branches": 4,
        "assets": 12,
        "plan": 1,
        "steps": 7,
        "step_results": 35,
        "meta_log_entries": 42,
        "notes": 4
      },
      "warnings": []
    }
  ]
}
```
