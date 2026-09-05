# RunningHub CLI

**一体化项目** — SDK + CLI + 工作流编排脚本 + Hermes Agent Skill

`runninghub-cli` is a unified toolkit built on top of [`runninghub-sdk`](https://pypi.org/project/runninghub-sdk/). It provides:

- **SDK CLI** — `runninghub` / `runhub` commands for submitting, polling, downloading workflows & AI Apps
- **Workflow Scripts** — `python -m scripts.runner`, `python -m scripts.pipeline` etc. for media generation pipelines
- **Skill Integration** — Hermes Agent skill definitions in `skills/`
- **Workflow Registry** — verified `registry/workflows.yaml` + `registry/payloads/*.json` and integration test reports in `registry/`

## Features

- ✅ **Submit, poll, download** — end-to-end workflow/webapp execution
- ✅ **Auto-upload media** — `@upload:` prefix in fieldValue uploads files automatically
- ✅ **Task debugging** — detailed failure analysis with `task-detail`
- ✅ **Marketplace discovery** — search, inspect, auto-test portal templates & AI Apps (`discover` subcommand)
- ✅ **Hermes Skill export** — auto-generate `SKILL.md` from tested workflows (`discover export`)
- ✅ **Agent-friendly JSON** — all commands return structured JSON on stdout
- ✅ **Self-update** — git tag-based update mechanism
- ✅ **Smart inspect output** — automatically filters internal plumbing nodes, shows only user-customizable parameters

## Project Structure

```
runninghub-cli/
├── src/runninghub_cli/       ← Python SDK（pip install -e .）
│   ├── main.py                 runninghub CLI 入口
│   ├── service.py              RunningHub API 封装
│   └── discover.py             工作流发现 & 市场搜索
├── scripts/                  ← 业务编排脚本（python -m scripts.*）
│   ├── runner.py               通用运行器
│   ├── pipeline.py             端到端流水线（txt2img → img2vid → 过渡 → 合并）
│   ├── storyboard.py           分镜生成
│   ├── first2last.py           首尾帧过渡
│   ├── merge.py                视频合并
│   └── base.py                 共享工具
├── skills/                   ← Hermes Agent skill 定义
│   ├── SKILL.md
│   └── runninghub-cli.md
├── registry/                 ← 流程注册表
│   ├── workflows.yaml           工作流/AI App YAML 索引
│   ├── payloads/*.json          节点参数定义 (按 ID) + 质量分级
│   └── cases/                  集成测试报告
├── references/               ← 12个工作流参考文档
├── agents/                   ← AI agent 配置文件
├── tests/                    ← 单元测试
├── docs/                     ← 文档
├── examples/                 ← 示例
├── pyproject.toml            ← 统一配置（v0.2.0）
├── AGENTS.md                 ← Codex / Claude 指导
├── CLAUDE.md                 ← Claude 项目上下文
├── README.md
└── README.zh-CN.md
```

## Installation

### From Git (Recommended)

```bash
git clone https://gitee.com/difyz/runninghub-cli.git
cd runninghub-cli
./scripts/bootstrap.sh
```

If your API key is in another `.env` file, bootstrap and verify in one go:

```bash
./scripts/bootstrap.sh --doctor-env /absolute/path/to/.env
```

### Manual Install

```bash
cd runninghub-cli
pip install "runninghub-sdk>=1.1.9" "typer>=0.9.0"
pip install -e .
```

After installation, both commands are available:

```bash
runninghub --help
runhub --help
```

### Run Without Installing

```bash
pip install "runninghub-sdk>=1.1.9" "typer>=0.9.0"
PYTHONPATH=src python -m runninghub_cli.main doctor
```

---

## Auth

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

### Global Options

```bash
runninghub --version
# {"ok": true, "version": "0.2.2"}
```

### Core Commands

| Command | Purpose |
|---------|---------|
| [`doctor`](#doctor) | Check SDK, API key, and queue access |
| [`detect`](#detect) | Detect whether an ID is a workflow or webapp |
| [`inspect`](#inspect) | Inspect node structure (plumbing auto-filtered) |
| [`submit`](#submit) | Submit a task, return task_id immediately |
| [`status`](#status) | Query task status |
| [`wait-download`](#wait-download) | Wait for completion and download outputs |
| [`run`](#run) | Submit, wait, and download in one command |
| [`task-detail`](#task-detail) | Fetch detailed failure analysis |
| [`upload`](#upload) | Upload image/video/audio/file to RunningHub |
| [`self-update`](#self-update) | Update CLI to the latest git tag |

### Discover Commands (Marketplace + Auto-test + Export)

| Command | Purpose |
|---------|---------|
| [`discover search`](#discover-search) | Search the marketplace (table by default, `--format json` for agents) |
| [`discover inspect`](#discover-inspect) | Deep-inspect a marketplace item structure |
| [`discover test`](#discover-test) | Auto-test: detect type → build inputs → submit → wait → verify |
| [`discover export`](#discover-export) | Test and export as a Hermes Agent `SKILL.md` |

---

## Command Details

### doctor

Check SDK connectivity, API key validity, and queue availability.

```bash
runninghub doctor
runninghub doctor --api-key your_key
runninghub doctor --env-file /path/to/.env
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--api-key` | string | `RUNNINGHUB_API_KEY` env | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### detect

Detect whether an ID is a workflow or AI App (webapp).

```bash
runninghub detect 2038921358817632258
```

**Output:**
```json
{
  "id": "2038921358817632258",
  "type": "webapp",
  "name": "角色三视图klein9b",
  "node_count": 1
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### inspect

View node structure of a workflow or AI App. **Automatically filters internal ComfyUI plumbing nodes** (CLIPLoader, VAEEncode, KSamplerSelect, etc.) to show only user-customizable parameters.

```bash
# Default (compact mode): key nodes only
runninghub inspect 2013908081847046145

# Specify type
runninghub inspect 2038921358817632258 --type webapp

# Verbose mode: show all nodes (including plumbing)
runninghub inspect 2013908081847046145 --verbose
# or -v
```

**Output structure (compact mode):**
```json
{
  "id": "2013908081847046145",
  "type": "workflow",
  "node_count": 44,
  "plumbing_count": 37,
  "key_nodes": [
    {
      "nodeId": "115",
      "classType": "LoadImage",
      "label": "图片输入",
      "fields": ["image"],
      "params": {"image": "xxx.png"}
    }
  ]
}
```

Each `key_nodes` entry contains:
- `nodeId` — used when constructing node_overrides
- `classType` — ComfyUI node type
- `label` — Chinese label (Image Input, Text Prompt, etc.)
- `fields` — all overridable field names
- `params` — current actual values

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--type` / `-t` | string | `auto` | `auto` \| `workflow` \| `webapp` \| `ai-app` |
| `--verbose` / `-v` | bool | `false` | Show full node info (including plumbing) |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### submit

Submit a task to RunningHub and **return immediately** with `task_id` (no waiting).

```bash
runninghub submit 2037071836214730753 \
  --type workflow \
  --node-overrides '[
    {"nodeId": "57", "fieldName": "text", "fieldValue": "a cinematic sunset"}
  ]'

# Load from JSON file
runninghub submit <id> --type workflow --node-overrides overrides.json

# Encrypted AI App
runninghub submit <id> --type webapp --access-password "mypassword" \
  --node-overrides overrides.json
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--type` / `-t` | string | `workflow` | `workflow` \| `webapp` \| `ai-app` |
| `--node-overrides` / `-n` | string | — | JSON array or JSON file path; `fieldValue` supports `@upload:PATH` |
| `--instance-type` | string | `default` | RunningHub instance type |
| `--personal-queue` | bool | `false` | Use personal queue (workflows only) |
| `--access-password` | string | — | Access password for encrypted AI Apps/webapps |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### status

Query current status of a task.

```bash
runninghub status task_abc123
```

**Output:**
```json
{
  "task_id": "task_abc123",
  "status": "SUCCESS",
  "client_id": "...",
  "prompt_tips": ""
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `task_id` | string (arg) | **required** | Task ID |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### task-detail

Fetch detailed task execution info including status, outputs, failure reason, and webhook callback data. **The go-to command for debugging failures.**

```bash
runninghub task-detail task_abc123
```

**Output:**
```json
{
  "task_id": "task_abc123",
  "status": "FAILED",
  "error_code": "805",
  "error_message": "工作流运行失败",
  "failed_reason": {"node_id": "99", "exception_message": "bad prompt"},
  "outputs": [{"node_id": "99", "file_url": "https://..."}],
  "webhook_detail": {...}
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `task_id` | string (arg) | **required** | Task ID |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### wait-download

Wait for a task to complete and download its output files.

```bash
# Basic usage
runninghub wait-download <workflow_id> <task_id>

# Custom output directory and timeout
runninghub wait-download <id> <task_id> \
  --output-dir ./outputs \
  --poll-interval 10 \
  --timeout 600
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `task_id` | string (arg) | **required** | Task ID |
| `--output-dir` | path | `./runninghub_outputs/<id>/` | Output directory |
| `--poll-interval` | float | `15` | Polling interval (seconds) |
| `--timeout` | float | `1800` | Timeout (seconds) |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### run

**Most commonly used command** — submit, wait, and download in one step.

```bash
# Basic usage
runninghub run 2037071836214730753 \
  --type workflow \
  --node-overrides '[
    {"nodeId": "57", "fieldName": "text", "fieldValue": "a cinematic sunset"}
  ]'

# With auto media upload
runninghub run <id> --type webapp \
  --node-overrides '[
    {"nodeId": "167", "fieldName": "image", "fieldValue": "@upload:./model.jpg"}
  ]'

# Full options
runninghub run <id> --type workflow \
  --node-overrides overrides.json \
  --output-dir ./outputs \
  --poll-interval 10 \
  --timeout 600 \
  --personal-queue
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--type` / `-t` | string | `workflow` | `workflow` \| `webapp` \| `ai-app` |
| `--node-overrides` / `-n` | string | — | JSON array or JSON file path; `fieldValue` supports `@upload:PATH` |
| `--output-dir` | path | `./runninghub_outputs/<id>/` | Output directory |
| `--poll-interval` | float | `15` | Polling interval (seconds) |
| `--timeout` | float | `1800` | Timeout (seconds) |
| `--instance-type` | string | `default` | RunningHub instance type |
| `--personal-queue` | bool | `false` | Use personal queue (workflows only) |
| `--access-password` | string | — | Access password for encrypted AI Apps/webapps |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### upload

Upload a local media file to RunningHub storage. Images use `upload_image()`, other types use `upload_file()`.

```bash
runninghub upload ./input.png --kind image
runninghub upload ./input.mp4 --kind video
runninghub upload ./input.wav --kind audio
runninghub upload ./input.bin --kind file
```

**Output:**
```json
{
  "kind": "image",
  "fileName": "226dd3950e....jpg",
  "downloadUrl": "https://..."
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `file` | path (arg) | **required** | Local file path |
| `--kind` / `-k` | string | `file` | `image` \| `video` \| `audio` \| `file` |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### self-update

Git tag-based update mechanism — fetches the latest tag from the remote and reinstalls the editable checkout.

```bash
# Dry-run: show target tag without updating
runninghub self-update --dry-run

# Update to the latest tag
runninghub self-update

# Install a specific tag
runninghub self-update --tag v0.2.0

# Use a custom repository URL
runninghub self-update --repo-url https://gitee.com/difyz/runninghub-cli.git
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--repo-dir` | path | auto-detected | Local git checkout root |
| `--repo-url` | string | `https://gitee.com/difyz/runninghub-cli.git` | Repository URL for tag discovery |
| `--tag` | string | latest remote tag | Specific tag to install |
| `--remote` | string | `origin` | Git remote name |
| `--dry-run` | bool | `false` | Show target tag without changing files |

---

### discover search

Search the RunningHub marketplace for workflows and AI Apps.

```bash
# Search workflows (table output, human-readable)
runninghub discover search --keyword "LTX" --type workflow --size 10

# Search AI Apps
runninghub discover search --keyword "video" --type webapp --size 10

# Search both
runninghub discover search --keyword "anime" --type both --size 5

# JSON output for agents/scripts
runninghub discover search --keyword "style transfer" --type workflow \
  --size 3 --format json
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keyword` / `-k` | string | `""` | Search keyword |
| `--type` / `-t` | string | `workflow` | `workflow` \| `webapp` \| `both` |
| `--page` / `-p` | int | `1` | Page number |
| `--size` / `-s` | int | `20` | Results per page |
| `--sort` | string | `RECOMMEND` | `RECOMMEND` \| `NEWEST` \| `POPULAR` |
| `--format` / `-f` | string | `table` | `table` \| `json` |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### discover inspect

Deep-inspect any marketplace workflow or AI App to see its node structure. Auto-detects type.

```bash
runninghub discover inspect 2037071836214730753
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### discover test

Auto-test a marketplace item: detect type → inspect → generate inputs → submit → poll → verify.

```bash
# With a custom test prompt
runninghub discover test <id> --prompt "a cinematic sunset" --timeout 600

# Auto-generate default prompt
runninghub discover test <id> --timeout 300
```

**Output** (multi-line JSON for progress tracking):
```json
{"ok": true, "phase": "detect", "type": "workflow"}
{"ok": true, "phase": "generate", "overrides": [...]}
{"ok": true, "phase": "result", "test": {"ok": true, "taskId": "...", "duration": 45.2, ...}}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--type` / `-t` | string | `auto` | `workflow` \| `webapp` \| `auto` |
| `--prompt` / `-p` | string | `""` | Test prompt text |
| `--timeout` | float | `300` | Max wait (seconds) |
| `--poll-interval` | float | `5` | Poll interval (seconds) |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

### discover export

Test a workflow and generate a standalone `SKILL.md` file for `~/.hermes/skills/`.

```bash
# Full pipeline: test → export (recommended)
runninghub discover export 2037071836214730753 \
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

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `identifier` | string (arg) | **required** | Workflow or AI App ID |
| `--type` / `-t` | string | `auto` | `workflow` \| `webapp` \| `auto` |
| `--name` / `-n` | string | auto-inferred | Skill name |
| `--description` / `-d` | string | `""` | Skill description |
| `--output-dir` / `-o` | path | `./exported-skills` | Output directory |
| `--no-test` | bool | `false` | Skip test run before export |
| `--prompt` / `-p` | string | `""` | Test prompt (when `--no-test` is not set) |
| `--timeout` | float | `300` | Test timeout (seconds) |
| `--api-key` | string | env var | API Key |
| `--env-file` | path | — | Load `.env` file |

---

## Quickstart: Core Workflow

```bash
# 1. Check environment
runninghub doctor

# 2. Detect ID type
runninghub detect <workflow_or_webapp_id>

# 3. Inspect node structure (compact by default)
runninghub inspect <id>

# 4. Create an overrides.json file
```

```json
[
  {"nodeId":"43","fieldName":"text","fieldValue":"A cinematic coffee shop scene"}
]
```

For local media inputs, use `@upload:`:

```json
[
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:./model.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"@upload:./dance.mp4"}
]
```

```bash
# 5. Run everything in one step
runninghub run <id> --type webapp --node-overrides overrides.json
```

For long-running tasks, do it step by step:

```bash
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub task-detail <task_id>
runninghub wait-download <id> <task_id>
```

For encrypted AI Apps:

```bash
export APP_ACCESS_PASSWORD='<app_password>'
runninghub run <id> --type webapp --access-password "$APP_ACCESS_PASSWORD" \
  --node-overrides overrides.json
```

Useful maintenance commands:

```bash
runninghub upload ./input.png --kind image
runninghub self-update --dry-run
runninghub self-update
```

---

## Task Failure Handling

If a workflow or webapp fails, inspect the JSON error first. `run` and `wait-download` include `task_id`, `failed_reason`, and best-effort `task_detail`. If you only have a task ID:

```bash
runninghub task-detail <task_id>
```

Use the returned `status`, `error_code`, `error_message`, `failed_reason`, `outputs`, and `webhook_detail` to locate the problem.

**Retry strategy:**
1. Fix the smallest necessary part of the payload based on the error
2. If the same workflow keeps failing, strip the payload to essential fields only
3. If content is suspected, make the prompt more conservative
4. Stop after 3 retries and report the latest failure details

---

## Node Overrides

Node overrides use the standard RunningHub SDK format:

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A cinematic coffee shop scene"}
]
```

You can pass overrides as an inline JSON string or as a file path:

```bash
# Inline JSON
runninghub run <id> --node-overrides '[{"nodeId":"43","fieldName":"text","fieldValue":"hello"}]'

# File path
runninghub run <id> --node-overrides overrides.json
```

**Auto media upload:** `fieldValue` prefixed with `@upload:` is automatically uploaded and replaced with the RunningHub `fileName`:

```json
[
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:./model.jpg"}
]
```

---

## Workflow Scripts

Media generation pipelines provided by `scripts/`:

| Command | Purpose |
|---------|---------|
| `python -m scripts.runner --list` | List all registered workflows/AI Apps |
| `python -m scripts.runner --exec --mode workflow --id <ID> --nodes '[...]'` | Execute any workflow |
| `python -m scripts.skill_runner --skill <SKILL_NAME> --param key=value` | Execute reusable skill by business params (no raw node IDs) |
| `python -m scripts.pipeline --config scenes.json` | End-to-end: txt2img → img2vid → transitions → merge |
| `python -m scripts.storyboard --idea "探险故事"` | DeepSeek + RunningHub storyboard generation |
| `python -m scripts.first2last -f start.png -l end.png` | First+last frame transition video |
| `python -m scripts.merge -i clip1.mp4 clip2.mp4` | Local video merging |

---

## Agent Contract

All commands write JSON to stdout:

```json
{"ok": true, "data": {}}
```

Failures also return JSON and exit non-zero:

```json
{"ok": false, "error_type": "ValidationError", "error": "..."}
```

### Recommended Agent Workflow

#### For known workflows
1. `runninghub doctor`
2. `runninghub detect <id>`
3. `runninghub inspect <id>` (compact mode — key nodes only)
4. Build `node_overrides`
5. `runninghub submit` or `runninghub run`
6. If the task fails, inspect `error_type`, `error`, `task_id`, `failed_reason`, and `task_detail`; if needed run `runninghub task-detail <task_id>`, then retry with a minimal payload change.

#### For discovering new workflows
1. `runninghub discover search --keyword "<user intent>" --type workflow`
2. `runninghub discover inspect <id>` (for each promising result)
3. `runninghub discover test <id> --prompt "<test prompt>"` (run a quick test)
4. `runninghub discover export <id> --name <skill_name> --output-dir ./skills` (export successful ones)
5. `cp ./skills/*.md ~/.hermes/skills/` (load into Hermes)
