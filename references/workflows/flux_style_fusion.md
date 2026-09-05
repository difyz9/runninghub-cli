---
name: flux_style_fusion
title: flux_style_fusion
description: >-
  基于 Flux 模型的多种参考图风格融合生成
outputType: image
runninghubId: 2056908627524546561
runninghubType: workflow
---

# flux_style_fusion

基于 Flux 模型的多种参考图风格融合生成

**RunningHub ID**: `2056908627524546561` · **类型**: `workflow` · **输出**: `image` (约 12)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `reference_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./style_ref.png | 参考图片
    > 💡 风格参考图片，使用 @upload: 上传。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2056908627524546561 \
  --type workflow \
  --node-overrides '      {"nodeId": "171", "fieldName": "image", "fieldValue": "@upload:./style_ref.png"}' \
  --output-dir ./outputs/flux_style_fusion
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "171", "fieldName": "image", "fieldValue": "@upload:./style_ref.png"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `171` | `image` | `reference_image` — 参考图片 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
