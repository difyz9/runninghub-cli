# RunningHub CLI

Command-line and agent-facing tools for RunningHub workflows and AI Apps.

`runninghub-cli` is a thin CLI built on top of [`runninghub-sdk`](https://pypi.org/project/runninghub-sdk/). It is designed for humans, scripts, and agents such as Hermes. Every command returns stable JSON on stdout.

## Distribution Model

`runninghub-cli` is intentionally **GitHub-first** for now. The stable public dependency is `runninghub-sdk` on PyPI; this CLI is a fast-moving agent workflow tool that Hermes can clone, inspect, and update directly.

Keep `pyproject.toml` because it provides local editable installation and command entry points. Publishing this package to PyPI can wait until the command contract is stable.

## Install From Git

```bash
git clone https://github.com/difyz9/runninghub-cli.git
cd runninghub-cli
./scripts/bootstrap.sh
```

If your API key is in another `.env` file, bootstrap and verify in one go:

```bash
./scripts/bootstrap.sh --doctor-env /absolute/path/to/.env
```

Manual install:

```bash
git clone https://github.com/difyz9/runninghub-cli.git
cd runninghub-cli
pip install "runninghub-sdk>=1.1.5" "typer>=0.9.0"
pip install -e .
```

No package publication is required. After editable install, both commands are available:

```bash
runninghub --help
runhub --help
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
runninghub doctor --env-file /path/to/.env
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

## Without Installing The CLI

For one-off use, Hermes can run from a clone without installing the entry point:

```bash
pip install "runninghub-sdk>=1.1.5" "typer>=0.9.0"
PYTHONPATH=src python -m runninghub_cli.main doctor
```

Editable install is still preferred because it gives Hermes stable `runninghub` and `runhub` commands.

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
