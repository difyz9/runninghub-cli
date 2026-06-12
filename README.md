# RunningHub CLI

Command-line and agent-facing tools for RunningHub workflows and AI Apps.

`runninghub-cli` is a thin CLI built on top of [`runninghub-sdk`](https://pypi.org/project/runninghub-sdk/). It is designed for humans, scripts, and agents such as Hermes. Every command returns stable JSON on stdout.

## Features

- ✅ **Submit, poll, download** — end-to-end workflow/webapp execution
- ✅ **Auto-upload media** — `@upload:` prefix in fieldValue uploads files automatically
- ✅ **Task debugging** — detailed failure analysis with `task-detail`
- ✅ **Marketplace discovery** — search, inspect, auto-test portal templates & AI Apps (`discover` subcommand)
- ✅ **Hermes Skill export** — auto-generate `SKILL.md` from tested workflows (`discover export`)
- ✅ **Agent-friendly JSON** — all commands return structured JSON on stdout
- ✅ **Self-update** — git tag-based update mechanism

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

---

## Command Reference

### Core Commands

| Command | Purpose |
|---------|---------|
| `runninghub doctor` | Check SDK, API key, and queue access. |
| `runninghub detect <id>` | Detect whether an ID is a workflow or webapp/AI App. |
| `runninghub inspect <id> --type <type>` | Inspect node and field structure. |
| `runninghub submit` | Submit a task and return immediately with task_id. |
| `runninghub status <task_id>` | Query task status. |
| `runninghub wait-download` | Wait for completion and download outputs. |
| `runninghub run` | Submit, wait, and download in one command. |
| `runninghub task-detail <task_id>` | Fetch status, outputs, and webhook detail for failure analysis. |
| `runninghub upload <file> --kind <kind>` | Upload image, video, audio, or general file inputs. |
| `runninghub self-update` | Update this editable Git checkout to a tagged release. |

### Discover Commands (Marketplace + Auto-test + Export)

| Command | Purpose |
|---------|---------|
| `runninghub discover search` | Search the RunningHub marketplace for workflows and AI Apps. |
| `runninghub discover inspect <id>` | Deep-inspect a marketplace workflow or AI App structure. |
| `runninghub discover test <id>` | Auto-test: detect type → build inputs → submit → wait → verify. |
| `runninghub discover export <id>` | Test and export as a Hermes Agent `SKILL.md` file. |

---

## Quickstart: Core Workflow

```bash
runninghub doctor
runninghub detect <workflow_or_webapp_id>
runninghub inspect <id> --type workflow
runninghub inspect <id> --type webapp
```

Create an `overrides.json` file after inspecting the node IDs and field names:

```json
[
  {"nodeId":"43","fieldName":"text","fieldValue":"A cinematic coffee shop scene"}
]
```

For local media inputs, put `@upload:` directly in `fieldValue`. The CLI uploads the file before submission and replaces it with the RunningHub `fileName`:

```json
[
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:./model.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"@upload:./dance.mp4"}
]
```

Run everything in one step:

```bash
runninghub run <id> --type webapp --node-overrides overrides.json
```

For encrypted AI Apps/webapps, keep the password out of files and pass it through a private environment variable:

```bash
export APP_ACCESS_PASSWORD='<app_password>'
runninghub run <id> --type webapp --access-password "$APP_ACCESS_PASSWORD" --node-overrides overrides.json
```

Or run long tasks step by step:

```bash
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub task-detail <task_id>
runninghub wait-download <id> <task_id>
```

If a workflow or webapp fails, inspect the JSON error first. `run` and `wait-download` include `task_id`, `failed_reason`, and best-effort `task_detail` when the SDK exposes it. If you only have a task ID, run:

```bash
runninghub task-detail <task_id>
```

Use the returned status, outputs, webhook callback data, and detail errors to adjust only the smallest necessary part of `overrides.json`, then retry.

Useful maintenance commands:

```bash
runninghub upload ./input.png --kind image
runninghub upload ./input.mp4 --kind video
runninghub self-update --dry-run
runninghub self-update
```

---

## Discover: Marketplace, Auto-test & Export

The `discover` command group lets you browse the RunningHub marketplace, automatically test workflows, and export them as Hermes Agent skills — all without leaving the terminal.

### 1. Search the Marketplace

Search portal templates (workflows) and AI Apps by keyword:

```bash
# Search workflows
runninghub discover search --keyword "LTX" --type workflow --size 10

# Search AI Apps
runninghub discover search --keyword "视频" --type webapp --size 10

# Search both
runninghub discover search --keyword "换脸" --type both --size 5
```

Optional filters:
- `--sort RECOMMEND|NEWEST|POPULAR` — sort order (default: RECOMMEND)
- `--page 2` — pagination
- `--size 30` — results per page

Response includes: name, description, tags, use count, like count, collect count, owner info, covers/previews.

### 2. Inspect a Market Item

Deep-inspect any workflow or AI App to see its node structure:

```bash
runninghub discover inspect <workflow_or_webapp_id>
```

For webapps, returns the full `nodeInfoList` (editable nodes with their defaults, types, descriptions).

For workflows, returns the `byType` summary of all node classes and the editable field list.

### 3. Auto-test a Workflow

`discover test` automatically:
1. Detects whether the ID is a workflow or AI App
2. Inspects the node structure
3. Generates smart test inputs (detects prompt/text nodes, uses defaults for others)
4. Submits to RunningHub
5. Polls until completion
6. Reports elapsed time and output count

```bash
# With a custom test prompt
runninghub discover test <id> --prompt "a cinematic sunset" --timeout 600

# Default behavior (auto-generates prompt)
runninghub discover test <id> --timeout 300
```

Output (multi-line JSON for progress tracking):
```json
{"ok": true, "phase": "detect", "type": "workflow"}
{"ok": true, "phase": "generate", "overrides": [...]}
{"ok": true, "phase": "result", "test": {
  "ok": true, "taskId": "...", "duration": 45.2, "outputCount": 1, ...}}
```

### 4. Export as Hermes Agent Skill

`discover export` tests a workflow, then generates a standalone `SKILL.md` file ready for `~/.hermes/skills/`:

```bash
# Full pipeline: test → export (recommended)
runninghub discover export <id> \
  --name my_awesome_skill \
  --description "Generates awesome videos from text prompts" \
  --prompt "test prompt" \
  --timeout 600 \
  --output-dir ./exported-skills

# Export without testing (for known-good workflows)
runninghub discover export <id> --no-test --output-dir ./skills
```

The generated `SKILL.md` contains:
- YAML frontmatter (`name`, `runninghubId`, `runninghubType`)
- Parameter descriptions
- Verified request payload (if tested successfully)
- Ready-to-run `runninghub-cli` command
- Node mapping details

To use on another machine:
```bash
cp exported-skills/*.md ~/.hermes/skills/
```

Hermes loads them automatically on the next session.

### End-to-End Discovery Pipeline

```bash
# 1. Find relevant workflows
runninghub discover search --keyword "动漫" --type workflow --size 5

# 2. Inspect a promising one
runninghub discover inspect 2037071836214730753

# 3. Test and export as a Hermes skill
runninghub discover export 2037071836214730753 \
  --name txt2img_anime \
  --prompt "a cute anime girl, studio ghibli style" \
  --output-dir ./skills

# 4. Load into Hermes
cp ./skills/txt2img_anime.md ~/.hermes/skills/
```

---

## Upload Media

Use `upload` when a workflow or AI App requires an input media file. The command reuses `runninghub-sdk` upload APIs and returns `fileName` plus `downloadUrl`.

```bash
runninghub upload ./input.png --kind image
runninghub upload ./input.mp4 --kind video
runninghub upload ./input.wav --kind audio
runninghub upload ./input.bin --kind file
```

For image uploads, the CLI calls SDK `upload_image()`. For video/audio/general files, it calls SDK `upload_file()`.

Typical agent flow:

```bash
runninghub upload ./input.png --kind image
```

For AI Apps/webapps, use the returned `fileName` as the relevant media `fieldValue` inside `node_overrides`:

```json
[
  {"nodeId":"167","fieldName":"image","fieldValue":"226dd3950e650b9cf540bad4145d1e47d22a4e4c8885e66095979c2b292e2e90.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"57012cfc3d5c779ca7d8ba06c6a743cc9837f5e947cf4f06bac55f02de27bfb1.mp4"}
]
```

Use `downloadUrl` only when an inspected workflow field explicitly asks for a URL.

You can also let `submit` or `run` upload media automatically by using an upload directive in `fieldValue`:

```json
[
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:./model.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"@upload:./dance.mp4"}
]
```

`@upload:` uploads the file and replaces the value with `fileName`. Use `@upload-url:` only for fields that explicitly require `downloadUrl`.

---

## Self Update

Because this CLI is GitHub-first, updates happen by fetching Git tags from the repository and reinstalling the editable checkout.

Check the latest tag without changing files:

```bash
runninghub self-update --dry-run
```

Update to the latest tag:

```bash
runninghub self-update
```

This requires the GitHub repository to have semantic version tags such as `v0.1.0`. Before the first tag exists, use normal git workflow:

```bash
git pull
python -m pip install -e .
```

Install a specific tag:

```bash
runninghub self-update --tag v0.1.0
```

The command expects to run from an editable git checkout. By default it uses:

```text
https://github.com/difyz9/runninghub-cli.git
```

---

## Node Overrides

Node overrides use the standard RunningHub SDK format:

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A cinematic coffee shop scene"}
]
```

You can pass overrides as an inline JSON string or as a file path.

When converting a RunningHub AI App curl payload, take each `nodeInfoList` item and keep only the editable SDK fields:

```json
{
  "nodeId": "167",
  "fieldName": "image",
  "fieldValue": "uploaded-file-name.jpg"
}
```

Descriptions are useful for humans and agents, but they are not required in `node_overrides`.

---

## Without Installing The CLI

For one-off use, Hermes can run from a clone without installing the entry point:

```bash
pip install "runninghub-sdk>=1.1.5" "typer>=0.9.0"
PYTHONPATH=src python -m runninghub_cli.main doctor
```

Editable install is still preferred because it gives Hermes stable `runninghub` and `runhub` commands.

---

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

### Recommended Agent Workflow

#### For known workflows
1. `runninghub doctor`
2. `runninghub detect <id>`
3. `runninghub inspect <id> --type <type>`
4. Build `node_overrides`
5. `runninghub submit` or `runninghub run`
6. If the task fails, inspect `error_type`, `error`, `task_id`, `failed_reason`, and `task_detail`; if needed run `runninghub task-detail <task_id>`, then retry with a minimal payload change.

#### For discovering new workflows
1. `runninghub discover search --keyword "<user intent>" --type workflow`
2. `runninghub discover inspect <id>` (for each promising result)
3. `runninghub discover test <id> --prompt "<test prompt>"` (run a quick test)
4. `runninghub discover export <id> --name <skill_name> --output-dir ./skills` (export successful ones)
5. `cp ./skills/*.md ~/.hermes/skills/` (load into Hermes)
