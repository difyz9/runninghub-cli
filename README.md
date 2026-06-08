# RunningHub CLI

Command-line and agent-facing tools for RunningHub workflows and AI Apps.

`runninghub-cli` is a thin CLI built on top of [`runninghub-sdk`](https://pypi.org/project/runninghub-sdk/). It is designed for humans, scripts, and agents such as Hermes. Every command returns stable JSON on stdout.

## Install

```bash
pip install runninghub-cli
```

For local development:

```bash
pip install -e .
```

## Auth

Set your RunningHub API key:

```bash
export RUNNINGHUB_API_KEY=your_api_key
```

Or pass it explicitly:

```bash
runninghub doctor --api-key your_api_key
```

You can also load a `.env` file:

```bash
runninghub doctor --env-file ./backend/.env
```

## Commands

```bash
runninghub doctor
runninghub detect <workflow_or_webapp_id>
runninghub inspect <id> --type workflow
runninghub inspect <id> --type webapp
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub wait-download <id> <task_id>
runninghub run <id> --type webapp --node-overrides overrides.json
```

`runhub` is also installed as a short alias.

## Node Overrides

Node overrides use the standard RunningHub SDK format:

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A cinematic coffee shop scene"}
]
```

You can pass overrides as an inline JSON string or as a file path.

## Agent Contract

All commands write JSON to stdout:

```json
{
  "ok": true,
  "data": {}
}
```

Failures also return JSON and exit non-zero:

```json
{
  "ok": false,
  "error_type": "ValidationError",
  "error": "..."
}
```

Recommended agent flow:

1. `runninghub doctor`
2. `runninghub detect <id>`
3. `runninghub inspect <id> --type <type>`
4. Build `node_overrides`
5. `runninghub submit` or `runninghub run`
6. If the task fails, inspect `error_type`, `error`, and `failed_reason`, then retry with a minimal payload change.

