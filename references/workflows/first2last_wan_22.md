---
name: first2last_wan_22
title: first2last_wan_22
description: >-
  从起始帧到结束帧生成过渡视频，Wan 2.2 模型
outputType: video
runninghubId: 2011275998205054977
runninghubType: workflow
---

# first2last_wan_22

从起始帧到结束帧生成过渡视频，Wan 2.2 模型

**RunningHub ID**: `2011275998205054977` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `seed` | int | 可选 | 42 | 随机种子（高噪采样器）
    > 💡 与 node 28 的 seed 同步设置或同时省略。 |
| `prompt` | str | 可选 | smooth transition, seamless, cinematic camera movement | 正向提示词
    > 💡 描述期望的过渡效果。默认用 "smooth transition, seamless"。 |
| `seed_2` | int | 可选 | 42 | 随机种子（低噪采样器）
    > 💡 与 node 27 的 seed 同步设置或同时省略。 |
| `last_frame_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./end_frame.png | 结束帧图片
    > 💡 用户提供的结束图片路径，使用 @upload: 前缀上传。 |
| `first_frame_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./start_frame.png | 起始帧图片
    > 💡 用户提供的起始图片路径，使用 @upload: 前缀上传。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2011275998205054977 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/first2last_wan_22
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "43", "fieldName": "image", "fieldValue": "@upload:./start_frame.png"},
      {"nodeId": "44", "fieldName": "image", "fieldValue": "@upload:./end_frame.png"},
      {"nodeId": "30", "fieldName": "positive_prompt", "fieldValue": "smooth transition, seamless, cinematic camera movement"},
      {"nodeId": "27", "fieldName": "seed", "fieldValue": "42"},
      {"nodeId": "28", "fieldName": "seed", "fieldValue": "42"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `43` | `image` | `first_frame_image` — 起始帧图片 |
| `44` | `image` | `last_frame_image` — 结束帧图片 |
| `30` | `positive_prompt` | `prompt` — 正向提示词 |
| `27` | `seed` | `seed` — 随机种子（高噪采样器） |
| `28` | `seed` | `seed_2` — 随机种子（低噪采样器） |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
