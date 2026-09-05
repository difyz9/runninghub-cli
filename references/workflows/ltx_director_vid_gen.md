---
name: ltx_director_vid_gen
title: ltx_director_vid_gen
description: >-
  基于 LTX Director 模型的文本驱动视频生成
outputType: video
runninghubId: 2059132036383858689
runninghubType: workflow
---

# ltx_director_vid_gen

基于 LTX Director 模型的文本驱动视频生成

**RunningHub ID**: `2059132036383858689` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `duration` | str | 可选 | 10 | 视频时长（秒）
    > 💡 默认10秒。 |
| `frame_rate` | str | 可选 | 24 | 帧率
    > 💡 默认24fps。 |
| `global_prompt` | str | **必填** | A cinematic shot of a futuristic city at night, with neon lights reflecting on wet streets | 全局场景提示词
    > 💡 用英文描述整个视频场景。例："A cinematic shot of a futuristic city at night, with neon lights reflecting on wet streets" |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2059132036383858689 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/ltx_director_vid_gen
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "46", "fieldName": "global_prompt", "fieldValue": "A cinematic shot of a futuristic city at night, with neon lights reflecting on wet streets"},
      {"nodeId": "46", "fieldName": "duration_seconds", "fieldValue": "10"},
      {"nodeId": "46", "fieldName": "frame_rate", "fieldValue": "24"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `46` | `global_prompt` | `global_prompt` — 全局场景提示词 |
| `46` | `duration_seconds` | `duration` — 视频时长（秒） |
| `46` | `frame_rate` | `frame_rate` — 帧率 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
