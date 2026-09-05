---
name: wan_i2v_dance
title: wan_i2v_dance
description: >-
  基于 Wan 模型的图片驱动舞蹈视频生成
outputType: video
runninghubId: 1972733308360675329
runninghubType: workflow
---

# wan_i2v_dance

基于 Wan 模型的图片驱动舞蹈视频生成

**RunningHub ID**: `1972733308360675329` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `prompt` | str | **必填** | 一个女孩正在跳现代舞，动作流畅 | 正向提示词
    > 💡 用中文描述舞蹈动作和场景。例："一个女孩正在跳现代舞，动作流畅" |
| `reference_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./pose.png | 参考图片
    > 💡 用户提供的参考图片，使用 @upload: 前缀上传。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 1972733308360675329 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/wan_i2v_dance
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "73", "fieldName": "positive", "fieldValue": "\u4e00\u4e2a\u5973\u5b69\u6b63\u5728\u8df3\u73b0\u4ee3\u821e\uff0c\u52a8\u4f5c\u6d41\u7545"},
      {"nodeId": "341", "fieldName": "image", "fieldValue": "@upload:./pose.png"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `73` | `positive` | `prompt` — 正向提示词 |
| `341` | `image` | `reference_image` — 参考图片 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
