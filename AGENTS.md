# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

This project is a **RunningHub Skill** — a collection of Python CLI tools and integration reports for the RunningHub platform, which orchestrates AI-powered media generation workflows (text-to-image, image-to-video, storyboard, video transitions, etc.).

The core pattern: RunningHub exposes **workflows** and **AI apps**, each identified by a numeric ID. Both are invoked by sending a `workflow_id` (or `webapp_id`) + a `node_info_list` — an array of `{nodeId, fieldName, fieldValue}` overrides — then polling for completion and downloading outputs.

## Architecture

### `scripts/` — Reusable Python CLI tools

Six CLI entry points, all sharing `base.py` for common utilities:

| CLI tool / runner | File / Source | Description |
|------------------|--------------|-------------|
| `rh-runner` | `runner.py` | **通用运行器** — 发现和调用任意 workflow/AI app |
| `rh-first2last` | `first2last.py` | First+last frame transition video (多变体) |
| `rh-storyboard` | `storyboard.py` | DeepSeek + RunningHub storyboard pipeline |
| `rh-pipeline` | `pipeline.py` | End-to-end orchestration: txt2img → img2vid → transitions → merge |
| `rh-merge` | `merge.py` | Local video merging via ffmpeg (no RunningHub) |

All workflow/AI app parameter schemas live in `registry/payloads/*.json`. To discover and call any workflow:
```bash
python -m scripts.runner --list                    # 查看所有可用资源
python -m scripts.runner --info <ID>              # 查询参数详情
python -m scripts.runner --exec --mode ... --id ... --nodes '...'  # 执行
```

**Common calling pattern (the universal interface):**
```
client.run(workflow_id=..., node_info_list=[{nodeId, fieldName, fieldValue}, ...])
client.run_ai_app(webapp_id=..., node_info_list=[{nodeId, fieldName, fieldValue}, ...])
```

All CLI tools share this sequence:
1. Parse args (`build_parser()`)
2. Build node overrides (`build_modifier()` → returns `node_info_list`)
3. Submit task (`submit_task()` → `client.run()` or `client.run_ai_app()`)
4. Wait & download (`wait_and_download()` → `client.wait_for_completion()` + `client.download_outputs()`)

Key SDK helpers used:
- `modify_nodes()` — builder for `node_info_list`; methods: `.set(nodeId, fieldName, value)`, `.image(nodeId, fileName)`, `.seed(nodeId, value)`, `.size(nodeId, w, h, count)`, `.steps(nodeId, value)`, `.to_dict_list()`
- `client.upload_image(path)` → `{fileName: ...}`
- `client.get_workflow_json_parsed(workflow_id)` → workflow node graph (used to auto-discover nodes)

### `base.py` — Shared utilities

- **Environment**: `bootstrap_env()`, `get_required_env()`, `get_env()`, `get_env_int()`, `get_env_float()`, `resolve_api_key()`
- **Output**: `make_output_dir(base, subdir)` — timestamped dirs under `./outputs/`
- **Helpers**: `create_node_info_list(overrides)` — builds payload from simple dicts; `print_request_summary()`
  > **DEPRECATED**: Use `runninghub_cli.service.parse_overrides()` + `build_modifier()` instead.
- **Logging**: `log()`, `section()` — timestamped console output

### `cases/` — Integration test reports

Each subfolder is a numeric ID matching a RunningHub workflow or AI app. Contains:
- `integration_report.md` — auto-generated test report with structure analysis, execution steps, and the exact `node_info_list` payload used

The reports show two API patterns:
- **Workflow**: `run(workflow_id=...)` — the `cases/` folder name IS the workflow_id
- **AI App**: `run_ai_app(webapp_id=...)` — same folder naming convention

Each report's `📦 请求载荷` (Request Payload) section shows the `[{nodeId, fieldName, fieldValue}]` array — this is the parameterization contract that makes the scripts reusable.

### `cases/` folder naming convention

Folder names are the **RunningHub resource IDs**:
- `1923649885118058498` → Wan I2V workflow (failed)
- `1967569328524664834` → 国风女剑仙 workflow (first2last)
- `1972733308360675329` → Wan I2V 舞蹈 workflow
- `2004066004755988481` → 豆包Seedance video (workflow)
- `2005542596594331650` → AI 应用 (AI app, uses `run_ai_app`)
- `2052272204712300545` → LTXV video workflow
- `2056898489606561793` → 连续性人物水塘边 workflow
- `2056908627524546561` → Flux 多参考图 workflow
- `2059132036383858689` → LTX Director workflow
- `2059461117663076353` → SeedVR2 workflow
- `2057249300442337282` → Contains `integration_test/` subfolder (image test)

## Key Design Principles

1. **Unified calling pattern**: Every workflow/AI app is callable with just `workflow_id` + `node_info_list`. The `node_info_list` is the universal parameterization interface.
2. **Hardcoded node IDs are fragile**: Current scripts bake in specific workflow node IDs (e.g., `TXT2IMG_PROMPT_NODE = "57"`). These differ across workflows — the case reports show every workflow has different node IDs and field names.
3. **Two API families**: `client.run()` for workflows, `client.run_ai_app()` for AI apps — same `node_info_list` payload format.
4. **All workflows use `runninghub_sdk.RunningHubClient`** — no direct HTTP calls.

## Development Workflow

### Environment setup

```bash
export RUNNINGHUB_API_KEY=your_key_here
```

Optional per-tool env vars (see `get_env()` calls in each script):
- `RUNNINGHUB_TXT2IMG_WORKFLOW_ID`, `RUNNINGHUB_IMG2VID_WORKFLOW_ID`, etc.
- `DEEPSEEK_API_KEY` (for storyboard.py)

### Running CLI tools

```bash
# 发现工作流
python -m scripts.runner --list                 # 列出所有可用工作流
python -m scripts.runner --info <ID>            # 查询参数详情

# 执行任务
python -m scripts.runner --exec --mode workflow|ai-app --id <ID> --nodes '<JSON>'

# 验证参数
python -m scripts.runner --exec --mode workflow --id <ID> --nodes '[...]' --dry-run

# 验证凭证
python -m scripts.runner --check

# 专用脚本（保留复杂功能）
python -m scripts.pipeline --config scenes.json
python -m scripts.storyboard --idea "探险故事"
python -m scripts.first2last -f start.png -l end.png
python -m scripts.merge -i clip1.mp4 clip2.mp4 -o merged.mp4
```

### Adding a new workflow to the registry

Don't create a new CLI tool. Instead:
1. Find the workflow/AI app ID from the RunningHub platform
2. Run it once through the web UI or runner to get the first payload
3. Add a new entry in `registry/payloads/*.json` with node schemas and `llmHint`
4. Copy the verified payload from `cases/<ID>/integration_report.md` into `verifiedPayload`
5. **No Python code changes needed** — the runner handles everything via parameter passing

## Skill Knowledge Base

工作流和 AI 应用的节点 schema 统一存储在 `registry/payloads/*.json`（机器可读注册表），包含：
- 每个节点的 nodeId、fieldName、fieldType、description
- LLM 引导提示（`llmHint`）指导 LLM 如何构造参数
- 已验证的请求载荷（`verifiedPayload`）来自 cases/ 的集成测试报告

**LLM 获取参数信息**：使用 `--info <ID>` 命令运行时查询，无需依赖过时的文档。

**新增接口**：在 `registry/payloads/*.json` 中添加节点 schema 和已验证 payload，无需修改 Python 代码。

## Runner 命令速查

| 命令 | 用途 |
|------|------|
| `--check` | 验证 API Key + 查询余额 |
| `--list` | 列出所有注册的工作流/AI 应用 |
| `--info <ID>` | 显示节点详情 + LLM 引导提示 |
| `--exec --mode ... --id ... --nodes ...` | 执行任务 |
| `--exec --mode ... --id ... --nodes '[...]' --dry-run` | 验证参数不执行 |

## Memory Context

The memory directory at `/Users/apple/.Codex/projects/-Users-apple-opt-difyz-0329-0530-runninghub-skill/memory/` stores project-specific facts. See `MEMORY.md` for the index.
