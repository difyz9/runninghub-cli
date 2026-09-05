---
name: seedance_vid_gen
title: seedance_vid_gen
description: >-
  Doubao/Seedance 文生视频工作流，2节点（RH_Doubao_Seedance + SaveVideo）
outputType: video
runninghubId: 2004066004755988481
runninghubType: workflow
---

# seedance_vid_gen

Doubao/Seedance 文生视频工作流，2节点（RH_Doubao_Seedance + SaveVideo）

**RunningHub ID**: `2004066004755988481` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `seed` | int | 可选 | 42 | 随机种子
    > 💡 可选。固定种子可复现结果。 |
| `prompt` | str | **必填** | 一只可爱的橘猫在草地上打滚，阳光明媚 | 视频描述提示词
    > 💡 用中文编写视频场景描述。例："一只可爱的橘猫在草地上打滚，阳光明媚" |
| `duration` | str | 可选 | 5 | 视频时长（秒）
    > 💡 默认5秒。 |
| `aspect_ratio` | str | 可选 | 16:9 | 画面比例
    > 💡 常见值："16:9"（横屏）、"9:16"（竖屏）、"1:1"（正方形） |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 2004066004755988481 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/seedance_vid_gen
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "1", "fieldName": "prompt", "fieldValue": "\u4e00\u53ea\u53ef\u7231\u7684\u6a58\u732b\u5728\u8349\u5730\u4e0a\u6253\u6eda\uff0c\u9633\u5149\u660e\u5a9a"},
      {"nodeId": "1", "fieldName": "seed", "fieldValue": "42"},
      {"nodeId": "1", "fieldName": "duration", "fieldValue": "5"},
      {"nodeId": "1", "fieldName": "aspect_ratio", "fieldValue": "16:9"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `1` | `prompt` | `prompt` — 视频描述提示词 |
| `1` | `seed` | `seed` — 随机种子 |
| `1` | `duration` | `duration` — 视频时长（秒） |
| `1` | `aspect_ratio` | `aspect_ratio` — 画面比例 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
