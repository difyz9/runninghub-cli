---
name: runninghub-cli
description: Use the runninghub CLI to inspect, submit, wait for, download, and debug RunningHub workflows or AI Apps.
---

# RunningHub CLI Agent Workflow

Use `runninghub` when the user asks to integrate, debug, submit, inspect, or validate a RunningHub workflow or AI App.

## First Check

```bash
runninghub doctor
```

Stop and report the environment issue if `ok` is false.

## Detect Type

```bash
runninghub detect <id>
```

Use the returned `type` for later commands:

- `workflow`
- `webapp`

## Inspect

```bash
runninghub inspect <id> --type workflow
runninghub inspect <id> --type webapp
```

Use the returned nodes and fields to build `node_overrides`.

## Submit And Debug

For a quick end-to-end validation:

```bash
runninghub run <id> --type webapp --node-overrides overrides.json
```

For long tasks, submit first:

```bash
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub wait-download <id> <task_id>
```

## Payload Rules

`node_overrides` must use RunningHub SDK format:

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A test prompt"}
]
```

Prefer writing long JSON to a temporary file and passing its path with `--node-overrides`.

## Failure Handling

All commands return JSON on stdout. On failure, parse:

- `error_type`
- `error`
- `code`
- `task_id`
- `failed_reason`

If a field is invalid, re-run `runninghub inspect` and choose a valid `fieldName`. If a task fails after submission, change only the minimum necessary payload field and retry.

