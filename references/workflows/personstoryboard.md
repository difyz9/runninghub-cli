---
name: personstoryboard
title: personstoryboard
description: >-
  生成6段连续性人物分镜图片
outputType: image
runninghubId: 2056898489606561793
runninghubType: workflow
---

# personstoryboard

生成6段连续性人物分镜图片

**RunningHub ID**: `2056898489606561793` · **类型**: `workflow` · **输出**: `image` (约 6)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `prompt` | str | **必填** | 生成六段关于连续性的人物在水塘边的分镜 | 分镜描述提示词
    > 💡 用中文描述分镜需求。例："生成六段关于连续性的人物在水塘边的分镜" |
| `reference_image` | path  (支持 @upload:/path 自动上传) | 可选 | @upload:./reference.png | 参考图片
    > 💡 可选。如有参考图用 @upload: 上传。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2056898489606561793 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/personstoryboard
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "366", "fieldName": "prompt", "fieldValue": "\u751f\u6210\u516d\u6bb5\u5173\u4e8e\u8fde\u7eed\u6027\u7684\u4eba\u7269\u5728\u6c34\u5858\u8fb9\u7684\u5206\u955c"},
      {"nodeId": "342", "fieldName": "image", "fieldValue": "@upload:./reference.png"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `366` | `prompt` | `prompt` — 分镜描述提示词 |
| `342` | `image` | `reference_image` — 参考图片 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
