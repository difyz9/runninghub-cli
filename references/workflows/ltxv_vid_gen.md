---
name: ltxv_vid_gen
title: ltxv_vid_gen
description: >-
  基于 LTX Studio 模型的视频生成工作流，支持多图输入
outputType: video
runninghubId: 2052272204712300545
runninghubType: workflow
---

# ltxv_vid_gen

基于 LTX Studio 模型的视频生成工作流，支持多图输入

**RunningHub ID**: `2052272204712300545` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `input_image` | path  (支持 @upload:/path 自动上传) | 可选 | @upload:./frame1.png | 图片输入 1
    > 💡 可选参考图片，使用 @upload: 上传。 |
| `input_image_2` | path  (支持 @upload:/path 自动上传) | 可选 | @upload:./frame2.png | 图片输入 2
    > 💡 可选参考图片，使用 @upload: 上传。 |
| `input_image_3` | path  (支持 @upload:/path 自动上传) | 可选 | @upload:./frame3.png | 图片输入 3
    > 💡 可选参考图片，使用 @upload: 上传。 |
| `action_dialogue` | str | 可选 | 动作：镜头推进
台词：古装戏，男人对话后互相拥抱 | 动作/台词描述
    > 💡 描述镜头运动和台词内容。格式："动作：xxx\n台词：xxx" |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2052272204712300545 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/ltxv_vid_gen
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "269", "fieldName": "image", "fieldValue": "@upload:./frame1.png"},
      {"nodeId": "332", "fieldName": "image", "fieldValue": "@upload:./frame2.png"},
      {"nodeId": "342", "fieldName": "image", "fieldValue": "@upload:./frame3.png"},
      {"nodeId": "325", "fieldName": "value", "fieldValue": "\u52a8\u4f5c\uff1a\u955c\u5934\u63a8\u8fdb\n\u53f0\u8bcd\uff1a\u53e4\u88c5\u620f\uff0c\u7537\u4eba\u5bf9\u8bdd\u540e\u4e92\u76f8\u62e5\u62b1"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `269` | `image` | `input_image` — 图片输入 1 |
| `332` | `image` | `input_image_2` — 图片输入 2 |
| `342` | `image` | `input_image_3` — 图片输入 3 |
| `325` | `value` | `action_dialogue` — 动作/台词描述 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
