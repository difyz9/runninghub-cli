---
name: chinese_fantasysword_fairycombat
title: chinese_fantasysword_fairycombat
description: >-
  生成国风女剑仙打斗场景视频，支持首尾帧
outputType: video
runninghubId: 1967569328524664834
runninghubType: workflow
---

# chinese_fantasysword_fairycombat

生成国风女剑仙打斗场景视频，支持首尾帧

**RunningHub ID**: `1967569328524664834` · **类型**: `workflow` · **输出**: `video` (约 1)

---

## 参数说明

| 参数名 | 类型 | 必填 | 示例 | 说明 |
|--------|------|------|------|------|
| `prompt` | str | **必填** | 绝色国风女剑仙，激烈打斗动作，凌空飞跃，飘逸红色汉服，长剑萦绕发光剑气，黑发随风狂舞，冷艳锋利五官，山间迷雾战场，发光粒子特效，赛璐璐上色，二次元画风，超高精细细节，鲜亮饱和色彩，电影运镜 | 正向提示词
    > 💡 用中文详细描述场景、角色、动作、风格。例："绝色国风女剑仙，激烈打斗动作，凌空飞跃..." |
| `last_frame_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./last_frame.png | 尾帧图片
    > 💡 结束帧图片路径，使用 @upload: 上传。 |
| `first_frame_image` | path  (支持 @upload:/path 自动上传) | **必填** | @upload:./first_frame.png | 首帧图片
    > 💡 起始帧图片路径，使用 @upload: 上传。 |

---

## 运行命令

```bash
# 使用 runninghub-cli 直接调用（无需 HTTP 代理）
runninghub run 1967569328524664834 \
  --type workflow \
  --node-overrides ''<见下方>'' \
  --output-dir ./outputs/chinese_fantasysword_fairycombat
```

> **图片参数**：对于 `image` 类型的字段，`fieldValue` 支持 `@upload:/path/to/image.png` 语法，CLI 会自动上传到 RunningHub。

---

## 完整请求载荷示例

```json
[
      {"nodeId": "27", "fieldName": "text", "fieldValue": "\u7edd\u8272\u56fd\u98ce\u5973\u5251\u4ed9\uff0c\u6fc0\u70c8\u6253\u6597\u52a8\u4f5c\uff0c\u51cc\u7a7a\u98de\u8dc3\uff0c\u98d8\u9038\u7ea2\u8272\u6c49\u670d\uff0c\u957f\u5251\u8426\u7ed5\u53d1\u5149\u5251\u6c14\uff0c\u9ed1\u53d1\u968f\u98ce\u72c2\u821e\uff0c\u51b7\u8273\u950b\u5229\u4e94\u5b98\uff0c\u5c71\u95f4\u8ff7\u96fe\u6218\u573a\uff0c\u53d1\u5149\u7c92\u5b50\u7279\u6548\uff0c\u8d5b\u7490\u7490\u4e0a\u8272\uff0c\u4e8c\u6b21\u5143\u753b\u98ce\uff0c\u8d85\u9ad8\u7cbe\u7ec6\u7ec6\u8282\uff0c\u9c9c\u4eae\u9971\u548c\u8272\u5f69\uff0c\u7535\u5f71\u8fd0\u955c"},
      {"nodeId": "36", "fieldName": "image", "fieldValue": "@upload:./first_frame.png"},
      {"nodeId": "37", "fieldName": "image", "fieldValue": "@upload:./last_frame.png"}
    ]
```

---

## 节点映射（nodeMappings）

| NodeId | fieldName | 映射自输入参数 |
|--------|-----------|---------------|
| `27` | `text` | `prompt` — 正向提示词 |
| `36` | `image` | `first_frame_image` — 首帧图片 |
| `37` | `image` | `last_frame_image` — 尾帧图片 |


---

## 注意事项

- 需要安装 `runninghub-cli`：`pip install runninghub-sdk typer && pip install -e /path/to/runninghub-cli`
- 需要设置 `RUNNINGHUB_API_KEY` 环境变量
- 任务超时默认 1800 秒（30 分钟），可通过 `--timeout` 调整
- 输出文件下载到 `--output-dir` 指定的目录

---

> 由 feishu-media-generator 自动导出 · export_feishu_skills.py
