---
name: oneclickextractclothes_person_clothesextract
title: oneclickextractclothes_person_clothesextract
description: >-
  输入人物图片，自动提取衣服、分离人物、衣服提取
outputType: image
runninghubId: 2005542596594331650
runninghubType: webapp
---

# oneclickextractclothes_person_clothesextract

输入人物图片，自动提取衣服、分离人物、衣服提取

**RunningHub ID**: `2005542596594331650` · **类型**: `webapp` · **输出**: `image` (约 3)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `input_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./person.png | 输入人物图片
    > 💡 用户提供的人物全身图片路径，使用 @upload: 前缀上传。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2005542596594331650 \
  --type webapp \
  --node-overrides '      {"nodeId": "78", "fieldName": "image", "fieldValue": "@upload:./person.png"}' \
  --output-dir ./outputs/oneclickextractclothes_person_clothesextract
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "78", "fieldName": "image", "fieldValue": "@upload:./person.png"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `78` | `image` | `input_image` — 输入人物图片 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
