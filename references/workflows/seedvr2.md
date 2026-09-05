---
name: seedvr2
title: seedvr2
description: >-
  基于 SeedVR2 的图生图处理工作流
outputType: image
runninghubId: 2059461117663076353
runninghubType: workflow
---

# seedvr2

基于 SeedVR2 的图生图处理工作流

**RunningHub ID**: `2059461117663076353` · **类型**: `workflow` · **输出**: `image` (约 2)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `prompt` | str | **必填** | 一只猫 | 图片描述/处理提示词
    > 💡 用中文描述对图片的处理要求。例："一只猫"、"把我变成赛博朋克风格" |
| `input_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./input.png | 输入图片
    > 💡 用户提供的输入图片路径，使用 @upload: 前缀。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2059461117663076353 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/seedvr2
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "65", "fieldName": "image", "fieldValue": "@upload:./input.png"},
      {"nodeId": "66", "fieldName": "prompt", "fieldValue": "\u4e00\u53ea\u732b"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `65` | `image` | `input_image` — 输入图片 |
| `66` | `prompt` | `prompt` — 图片描述/处理提示词 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
