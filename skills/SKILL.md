---
name: runninghub
description: RunningHub media generation workflow skill. Use when Codex needs to discover, parameterize, validate, or execute RunningHub workflows or AI apps for text-to-image, image-to-video, first/last-frame video transitions, storyboard generation, video pipeline orchestration, workflow registry maintenance, or local video merging with the bundled Python CLI tools.
---

# RunningHub

Use this skill to call RunningHub workflows and AI apps through the bundled registry and Python tools. Do not guess node IDs or field names: always discover them from `registry/payloads/*.json` through the runner first.

## Quick Workflow

1. List available resources:
   ```bash
   python -m scripts.runner --list
   ```
2. Inspect the selected resource:
   ```bash
   python -m scripts.runner --info <RESOURCE_ID>
   ```
3. Build a `node_info_list` JSON array using only documented fields:
   ```json
   [
     {"nodeId":"57","fieldName":"text","fieldValue":"a cinematic sunset over the ocean"}
   ]
   ```
4. Validate before submitting:
   ```bash
   python -m scripts.runner --exec --mode workflow --id <RESOURCE_ID> --nodes '<JSON>' --dry-run
   ```
5. Execute after validation:
   ```bash
   python -m scripts.runner --exec --mode workflow --id <RESOURCE_ID> --nodes '<JSON>'
   ```

Use `--mode ai-app` for AI applications. Both modes use the same node payload shape: `{"nodeId": "...", "fieldName": "...", "fieldValue": "..."}`.

### 并发限制

默认 RunningHub 最大并发数为 **2**。可通过以下命令查看当前队列状态：

```bash
runninghub queue-status
# {"api_key_type": "NORMAL", "concurrent_limit": 2, "running_count": 0, "queued_count": 0}
```

提交任务前建议先检查队列，如果 `running_count` 或 `queued_count` 已达上限，需等待队列空闲后再提交。

### 实例规格与访问密码

调用接口时支持两个可选参数控制运行环境：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `instanceType` | string | `default` | `default` = 24GB 显存机器，`plus` = 48GB 显存机器 |
| `accessPassword` | string | — | AI 应用开启加密访问时使用的访问密码 |

在 `--node-overrides` 中无需传入上述参数，它们通过 CLI 选项传递：

```bash
# 指定 48GB 实例
python -m scripts.runner --exec --mode ai-app --id <ID> --nodes '<JSON>' --instance-type plus

# 加密 AI App
python -m scripts.runner --exec --mode ai-app --id <ID> --nodes '<JSON>' --access-password <PASSWORD>
```

使用 `runninghub` CLI 时：

```bash
# 指定实例规格
runninghub run <ID> --type webapp --instance-type plus --node-overrides '<JSON>'

# 加密 AI App
runninghub run <ID> --type webapp --access-password <PASSWORD> --node-overrides '<JSON>'
```

## Required Environment

Set `RUNNINGHUB_API_KEY` before executing remote tasks, or pass `--api-key`.

Optional variables:

- `RUNNINGHUB_POLL_INTERVAL`: polling interval in seconds, default `3.0`
- `RUNNINGHUB_TIMEOUT`: task timeout in seconds, default `600`
- `DEEPSEEK_API_KEY`: required only for `scripts.storyboard` when generating storyboard prompts through DeepSeek

Check credentials:

```bash
python -m scripts.runner --check
```

## Image Uploads

Use `@upload:` in `fieldValue` for local images. The runner uploads the file and replaces the value with RunningHub's uploaded `fileName`.

```json
[
  {"nodeId":"78","fieldName":"image","fieldValue":"@upload:./person.png"}
]
```

## Bundled Tools

- `python -m scripts.runner`: universal discovery, dry-run, and execution entry point.
- `python -m scripts.first2last`: first-frame plus last-frame transition video helper.
- `python -m scripts.storyboard`: DeepSeek prompt generation plus RunningHub storyboard workflow.
- `python -m scripts.pipeline`: end-to-end txt2img → img2vid → transitions → merge orchestration.
- `python -m scripts.merge`: local ffmpeg video merge; does not call RunningHub.

Prefer `scripts.runner` for normal workflow and AI app calls. Use the specialized tools only when their higher-level orchestration is needed.

## Registry Maintenance

All machine-readable workflow and AI app schemas live in `registry/payloads/*.json`.

To add a new resource:

1. Get the RunningHub workflow ID or AI app webapp ID.
2. Run or inspect it once to obtain a verified payload.
3. Create `registry/payloads/<ID>.json` with `template_name`, `type`, `quality`, output metadata, and node schemas under `api_params.nodeInfoList`.
4. Store detailed reports under `cases/<RESOURCE_ID>/integration_report.md` when available.
5. Do not add a new Python CLI unless the task needs orchestration beyond plain node parameter passing.

Use `references/workflows/` only for human-readable workflow notes. Treat `registry/payloads/<ID>.json` files as the source of truth.
