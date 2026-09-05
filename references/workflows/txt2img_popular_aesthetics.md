---
name: txt2img_popular_aesthetics
title: txt2img_popular_aesthetics
description: >-
  基于 Popular Aesthetics 工作流的文本生成图片
outputType: image
runninghubId: 2037071836214730753
runninghubType: workflow
---

# txt2img_popular_aesthetics

基于 Popular Aesthetics 工作流的文本生成图片

**RunningHub ID**: `2037071836214730753` · **类型**: `workflow` · **输出**: `image` (约 1 ~ N (由 batch_size 决定))

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `cfg` | float | 可选 | 7.0 | CFG 引导强度
    > 💡 默认7.0。值越高越严格按照提示词但可能过饱和，值越低越有创意但可能偏离。 |
| `seed` | int | 可选 | 42 | 随机种子
    > 💡 可选。固定种子可复现相同结果。用户未指定时可不传此字段。 |
| `steps` | int | 可选 | 25 | 采样步数
    > 💡 默认25。值越高细节越多但越慢。快速预览用20，高质量用30。 |
| `width` | int | 可选 | 1024 | 图片宽度
    > 💡 默认1024。常见尺寸：1024x1024（正方形）、1216x832（横屏）、832x1216（竖屏）。根据用户描述的场景类型推测：风景用横屏，人像用竖屏，不指定用默认。 |
| `height` | int | 可选 | 1024 | 图片高度
    > 💡 配合width使用。默认1024。 |
| `prompt` | str | **必填** | a majestic white wolf standing on a rocky cliff, glowing blue eyes, aurora borealis in the sky, epic fantasy, highly detailed, 8K | 正向提示词
    > 💡 用英文编写。将用户的简短描述扩展为详细prompt，包含：主体、环境、动作、光线、构图、画质词。例："a cinematic sunset over the ocean, highly detailed, volumetric lighti |
| `batch_size` | int | 可选 | 1 | 生成数量
    > 💡 默认1。用户想要多张不同结果时设置>1。 |
| `negative_prompt` | str | 可选 | 低质量，模糊，错误透视，人物崩坏，手部异常，额外肢体 | 负向提示词
    > 💡 可选。描述不希望出现的元素，用中文或英文逗号分隔。例："blurry, low quality, distorted hands, extra limbs" |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2037071836214730753 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/txt2img_popular_aesthetics
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "57", "fieldName": "text", "fieldValue": "a majestic white wolf standing on a rocky cliff, glowing blue eyes, aurora borealis in the sky, epic fantasy, highly detailed, 8K"},
      {"nodeId": "43", "fieldName": "text", "fieldValue": "\u4f4e\u8d28\u91cf\uff0c\u6a21\u7cca\uff0c\u9519\u8bef\u900f\u89c6\uff0c\u4eba\u7269\u5d29\u574f\uff0c\u624b\u90e8\u5f02\u5e38\uff0c\u989d\u5916\u80a2\u4f53"},
      {"nodeId": "51", "fieldName": "steps", "fieldValue": "25"},
      {"nodeId": "51", "fieldName": "cfg", "fieldValue": "7.0"},
      {"nodeId": "51", "fieldName": "seed", "fieldValue": "42"},
      {"nodeId": "39", "fieldName": "width", "fieldValue": "1024"},
      {"nodeId": "39", "fieldName": "height", "fieldValue": "1024"},
      {"nodeId": "39", "fieldName": "batch_size", "fieldValue": "1"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `57` | `text` | `prompt` — 正向提示词 |
| `43` | `text` | `negative_prompt` — 负向提示词 |
| `51` | `steps` | `steps` — 采样步数 |
| `51` | `cfg` | `cfg` — CFG 引导强度 |
| `51` | `seed` | `seed` — 随机种子 |
| `39` | `width` | `width` — 图片宽度 |
| `39` | `height` | `height` — 图片高度 |
| `39` | `batch_size` | `batch_size` — 生成数量 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
