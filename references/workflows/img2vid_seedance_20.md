---
name: img2vid_seedance_20
title: img2vid_seedance_20
description: >-
  基于 Seedance 2.0 的图片生成视频
outputType: video
runninghubId: 2037036284312559617
runninghubType: workflow
---

# img2vid_seedance_20

基于 Seedance 2.0 的图片生成视频

**RunningHub ID**: `2037036284312559617` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `seed` | int | 可选 | 42 | 随机种子
    > 💡 可选。固定种子可复现结果。 |
| `duration` | str | 可选 | 5 | 视频时长（秒）
    > 💡 默认5秒。用户明确要求时长时设置。 |
| `motion_prompt` | str | 可选 | camera slowly panning right, ocean waves gently rolling, cinematic lighting, 4K | 动作描述提示词
    > 💡 用英文描述画面中应有的运动。例："camera slowly panning right, gentle waves, cinematic lighting"。用户未提供时可智能生成或跳过。 |
| `first_frame_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./scene.png | 输入图片（起始帧）
    > 💡 用户提供的图片路径，使用 @upload: 前缀上传。如用户未提供图片则询问。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2037036284312559617 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/img2vid_seedance_20
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "2", "fieldName": "image", "fieldValue": "@upload:./scene.png"},
      {"nodeId": "1", "fieldName": "prompt", "fieldValue": "camera slowly panning right, ocean waves gently rolling, cinematic lighting, 4K"},
      {"nodeId": "1", "fieldName": "duration", "fieldValue": "5"},
      {"nodeId": "1", "fieldName": "seed", "fieldValue": "42"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `2` | `image` | `first_frame_image` — 输入图片（起始帧） |
| `1` | `prompt` | `motion_prompt` — 动作描述提示词 |
| `1` | `duration` | `duration` — 视频时长（秒） |
| `1` | `seed` | `seed` — 随机种子 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
