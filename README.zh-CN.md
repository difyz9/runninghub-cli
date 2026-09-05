# RunningHub CLI

RunningHub 命令行工具 — 面向人类、脚本和 AI Agent（如 Hermes）。

基于 [`runninghub-sdk`](https://pypi.org/project/runninghub-sdk/) 构建，所有命令输出稳定的 JSON 到 stdout。

---

## 功能一览

- ✅ **提交→轮询→下载** — 一条命令完成工作流/AI App 的完整执行
- ✅ **自动上传媒体文件** — `fieldValue` 中用 `@upload:` 前缀自动上传
- ✅ **任务调试** — `task-detail` 命令输出详细失败原因分析
- ✅ **市集发现** — 搜索、查看、自动测试 RunningHub 市集的工作流和 AI App（`discover` 子命令）
- ✅ **Hermes Skill 导出** — 测试通过后自动生成 `SKILL.md`，直接给 Agent 使用
- ✅ **Agent 友好** — 所有命令输出结构化 JSON
- ✅ **自更新** — 基于 Git tag 的更新机制
- ✅ **inspect 智能精简** — 自动过滤内部管道节点，只展示用户可定制的参数

---

## 安装

### 从 Git 安装（推荐）

```bash
git clone https://gitee.com/difyz/runninghub-cli.git
cd runninghub-cli
./scripts/bootstrap.sh
```

如果 API Key 在其他项目的 `.env` 文件里，可以一键安装并验证：

```bash
./scripts/bootstrap.sh --doctor-env /absolute/path/to/.env
```

### 手动安装

```bash
cd runninghub-cli
pip install "runninghub-sdk>=1.1.9" "typer>=0.9.0"
pip install -e .
```

安装后可用两个命令（短别名也支持）：

```bash
runninghub --help
runhub --help
```

### 不安装也能用

```bash
pip install "runninghub-sdk>=1.1.9" "typer>=0.9.0"
PYTHONPATH=src python -m runninghub_cli.main doctor
```

---

## 认证

```bash
export RUNNINGHUB_API_KEY=你的API_Key
```

或显式传入：

```bash
runninghub doctor --api-key 你的API_Key
```

也支持加载 `.env` 文件：

```bash
runninghub doctor --env-file /path/to/.env
```

---

## 命令参考

### 全局选项

所有命令前可加 `--version` 查看版本号：

```bash
runninghub --version
# {"ok": true, "version": "0.2.2"}
```

### 基础命令

| 命令 | 用途 |
|------|------|
| [`doctor`](#doctor) | 检查 SDK、API Key 和队列可用性 |
| [`detect`](#detect) | 检测 ID 是工作流还是 AI App |
| [`inspect`](#inspect) | 查看节点结构，自动过滤管道节点 |
| [`submit`](#submit) | 提交任务，立即返回 task_id |
| [`status`](#status) | 查询任务状态 |
| [`wait-download`](#wait-download) | 等待任务完成并下载输出 |
| [`run`](#run) | 提交、等待、下载一步到位 |
| [`task-detail`](#task-detail) | 获取详细失败分析信息 |
| [`upload`](#upload) | 上传图片/视频/音频/文件到 RunningHub |
| [`self-update`](#self-update) | 更新 CLI 到最新 Git tag |

### 发现命令（市集 + 自动测试 + 导出）

| 命令 | 用途 |
|------|------|
| [`discover search`](#discover-search) | 搜索市集（默认表格输出，`--format json` 给 Agent 用） |
| [`discover inspect`](#discover-inspect) | 深度查看市集项目结构 |
| [`discover test`](#discover-test) | 自动测试：检测类型→构建参数→提交→等待→验证 |
| [`discover export`](#discover-export) | 测试通过后导出为 Hermes 可直接加载的 `SKILL.md` |

---

## 命令详情

### doctor

检查 SDK 连通性、API Key 有效性、队列可用性。

```bash
runninghub doctor
runninghub doctor --api-key your_key
runninghub doctor --env-file /path/to/.env
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--api-key` | string | `RUNNINGHUB_API_KEY` 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### detect

检测一个 ID 是工作流（workflow）还是 AI App（webapp）。

```bash
runninghub detect 2038921358817632258
```

**输出示例：**
```json
{
  "id": "2038921358817632258",
  "type": "webapp",
  "name": "角色三视图klein9b",
  "node_count": 1
}
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### inspect

查看工作流或 AI App 的节点结构。**默认自动过滤 ComfyUI 内部管道节点**（CLIPLoader、VAEEncode、KSamplerSelect 等），只展示用户可定制的关键节点。

```bash
# 默认（精简模式）：只显示关键节点
runninghub inspect 2013908081847046145

# 指定类型
runninghub inspect 2038921358817632258 --type webapp

# 完整模式：显示所有节点（含管道节点）
runninghub inspect 2013908081847046145 --verbose
# 或 -v
```

**输出结构（精简模式）：**
```json
{
  "id": "2013908081847046145",
  "type": "workflow",
  "node_count": 44,
  "plumbing_count": 37,
  "key_nodes": [
    {
      "nodeId": "115",
      "classType": "LoadImage",
      "label": "图片输入",
      "fields": ["image"],
      "params": {"image": "xxx.png"}
    }
  ]
}
```

`key_nodes` 中每条包含：
- `nodeId` — 构造 node_overrides 时使用
- `classType` — ComfyUI 节点类型
- `label` — 中文标签（图片输入、文本提示词等）
- `fields` — 所有可覆盖的字段名列表
- `params` — 字段当前实际值

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--type` / `-t` | string | `auto` | `auto` \| `workflow` \| `webapp` \| `ai-app` |
| `--verbose` / `-v` | bool | `false` | 显示完整节点信息（含内部管道节点） |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### submit

提交任务到 RunningHub，**立即返回** `task_id`，不等待完成。

```bash
runninghub submit 2037071836214730753 \
  --type workflow \
  --node-overrides '[
    {"nodeId": "57", "fieldName": "text", "fieldValue": "a cinematic sunset"}
  ]'

# 从 JSON 文件加载参数
runninghub submit <id> --type workflow --node-overrides overrides.json

# 加密 AI App
runninghub submit <id> --type webapp --access-password "mypassword" --node-overrides overrides.json
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--type` / `-t` | string | `workflow` | `workflow` \| `webapp` \| `ai-app` |
| `--node-overrides` / `-n` | string | — | JSON 数组或 JSON 文件路径；`fieldValue` 支持 `@upload:PATH` |
| `--instance-type` | string | `default` | RunningHub 实例类型 |
| `--personal-queue` | bool | `false` | 使用个人队列（仅工作流） |
| `--access-password` | string | — | 加密 AI App/Webapp 的访问密码 |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### status

查询任务的当前状态。

```bash
runninghub status task_abc123
```

**输出示例：**
```json
{
  "task_id": "task_abc123",
  "status": "SUCCESS",
  "client_id": "...",
  "prompt_tips": ""
}
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `task_id` | string（参数） | **必填** | 任务 ID |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### task-detail

获取任务的详细执行信息，包括状态、输出列表、失败原因和 webhook 回调数据。**任务调试首选命令。**

```bash
runninghub task-detail task_abc123
```

**输出示例：**
```json
{
  "task_id": "task_abc123",
  "status": "FAILED",
  "error_code": "805",
  "error_message": "工作流运行失败",
  "failed_reason": {"node_id": "99", "exception_message": "bad prompt"},
  "outputs": [{"node_id": "99", "file_url": "https://..."}],
  "webhook_detail": {...}
}
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `task_id` | string（参数） | **必填** | 任务 ID |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### wait-download

等待任务完成并下载输出文件。

```bash
# 基本用法
runninghub wait-download <workflow_id> <task_id>

# 指定输出目录和超时
runninghub wait-download <id> <task_id> \
  --output-dir ./outputs \
  --poll-interval 10 \
  --timeout 600
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `task_id` | string（参数） | **必填** | 任务 ID |
| `--output-dir` | path | `./runninghub_outputs/<id>/` | 输出文件保存目录 |
| `--poll-interval` | float | `15` | 轮询间隔（秒） |
| `--timeout` | float | `1800` | 超时时间（秒） |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### run

**最常用的命令** — 提交任务、等待完成、下载输出，一步到位。

```bash
# 基本用法
runninghub run 2037071836214730753 \
  --type workflow \
  --node-overrides '[
    {"nodeId": "57", "fieldName": "text", "fieldValue": "a cinematic sunset"}
  ]'

# 带媒体文件自动上传
runninghub run <id> --type webapp \
  --node-overrides '[
    {"nodeId": "167", "fieldName": "image", "fieldValue": "@upload:./model.jpg"}
  ]'

# 完整参数
runninghub run <id> --type workflow \
  --node-overrides overrides.json \
  --output-dir ./outputs \
  --poll-interval 10 \
  --timeout 600 \
  --personal-queue
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--type` / `-t` | string | `workflow` | `workflow` \| `webapp` \| `ai-app` |
| `--node-overrides` / `-n` | string | — | JSON 数组或 JSON 文件路径；`fieldValue` 支持 `@upload:PATH` |
| `--output-dir` | path | `./runninghub_outputs/<id>/` | 输出文件保存目录 |
| `--poll-interval` | float | `15` | 轮询间隔（秒） |
| `--timeout` | float | `1800` | 超时时间（秒） |
| `--instance-type` | string | `default` | RunningHub 实例类型 |
| `--personal-queue` | bool | `false` | 使用个人队列（仅工作流） |
| `--access-password` | string | — | 加密 AI App/Webapp 的访问密码 |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### upload

将本地媒体文件上传到 RunningHub 存储。图片使用 `upload_image()`，其他类型使用 `upload_file()`。

```bash
runninghub upload ./input.png --kind image
runninghub upload ./input.mp4 --kind video
runninghub upload ./input.wav --kind audio
runninghub upload ./input.bin --kind file
```

**输出示例：**
```json
{
  "ok": true,
  "data": {
    "kind": "image",
    "fileName": "226dd3950e....jpg",
    "downloadUrl": "https://..."
  }
}
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file` | path（参数） | **必填** | 本地文件路径 |
| `--kind` / `-k` | string | `file` | `image` \| `video` \| `audio` \| `file` |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### self-update

基于 Git tag 的更新机制，从远程仓库拉取最新 tag 并重新安装。

```bash
# 查看最新 tag（不执行更新）
runninghub self-update --dry-run

# 更新到最新 tag
runninghub self-update

# 更新到指定版本
runninghub self-update --tag v0.2.0

# 使用自定义仓库地址
runninghub self-update --repo-url https://gitee.com/difyz/runninghub-cli.git
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--repo-dir` | path | 自动检测 | CLI 本地 Git 仓库路径 |
| `--repo-url` | string | `https://gitee.com/difyz/runninghub-cli.git` | 用于发现 tag 的仓库地址 |
| `--tag` | string | 最新远程 tag | 要安装的指定 tag |
| `--remote` | string | `origin` | Git remote 名称 |
| `--dry-run` | bool | `false` | 仅显示目标 tag，不实际更新 |

---

### discover search

搜索 RunningHub 市集中的工作流和 AI App。

```bash
# 搜索工作流（默认表格输出，人类可读）
runninghub discover search --keyword "换脸" --type workflow --size 10

# 搜索 AI App
runninghub discover search --keyword "视频" --type webapp --size 10

# 同时搜索两种类型
runninghub discover search --keyword "动漫" --type both --size 5

# JSON 输出（给 Agent/脚本用）
runninghub discover search --keyword "换脸" --type workflow --size 3 --format json
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--keyword` / `-k` | string | `""` | 搜索关键词 |
| `--type` / `-t` | string | `workflow` | `workflow` \| `webapp` \| `both` |
| `--page` / `-p` | int | `1` | 页码 |
| `--size` / `-s` | int | `20` | 每页条数 |
| `--sort` | string | `RECOMMEND` | `RECOMMEND` \| `NEWEST` \| `POPULAR` |
| `--format` / `-f` | string | `table` | `table` \| `json` |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### discover inspect

深度查看市集项目的节点结构。自动检测类型，无需指定 `--type`。

```bash
runninghub discover inspect 2037071836214730753
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### discover test

自动测试市集项目：检测类型 → 分析节点 → 生成参数 → 提交 → 轮询 → 验证。

```bash
# 使用自定义测试提示词
runninghub discover test <id> --prompt "a cinematic sunset" --timeout 600

# 自动生成默认提示词
runninghub discover test <id> --timeout 300
```

**输出**（多行 JSON，方便追踪进度）：
```json
{"ok": true, "phase": "detect", "type": "workflow"}
{"ok": true, "phase": "generate", "overrides": [...]}
{"ok": true, "phase": "result", "test": {"ok": true, "taskId": "...", "duration": 45.2, ...}}
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--type` / `-t` | string | `auto` | `workflow` \| `webapp` \| `auto` |
| `--prompt` / `-p` | string | `""` | 测试提示词文本 |
| `--timeout` | float | `300` | 最大等待时间（秒） |
| `--poll-interval` | float | `5` | 轮询间隔（秒） |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

### discover export

测试工作流后，生成独立的 `SKILL.md` 文件，可直接放入 `~/.hermes/skills/`。

```bash
# 完整流程：测试 → 导出（推荐）
runninghub discover export 2037071836214730753 \
  --name 文生图_动漫 \
  --description "根据提示词生成动漫风格图片" \
  --prompt "a cute anime girl, studio ghibli style" \
  --timeout 600 \
  --output-dir ./skills

# 跳过测试直接导出（确认好用的工作流）
runninghub discover export <id> --no-test --output-dir ./skills
```

**生成的 `SKILL.md` 包含：**
- YAML 头部（`name`、`runninghubId`、`runninghubType`）
- 参数说明
- 已验证的请求载荷（测试通过时）
- 可直接运行的 `runninghub-cli` 命令
- Node 映射关系

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `identifier` | string（参数） | **必填** | 工作流或 AI App ID |
| `--type` / `-t` | string | `auto` | `workflow` \| `webapp` \| `auto` |
| `--name` / `-n` | string | 自动推断 | Skill 名称 |
| `--description` / `-d` | string | `""` | Skill 描述 |
| `--output-dir` / `-o` | path | `./exported-skills` | 输出目录 |
| `--no-test` | bool | `false` | 跳过测试直接导出 |
| `--prompt` / `-p` | string | `""` | 测试提示词（当 `--no-test` 未设置时） |
| `--timeout` | float | `300` | 测试超时时间（秒） |
| `--api-key` | string | 环境变量 | API Key |
| `--env-file` | path | — | 加载 `.env` 文件 |

---

## 快速上手

### 基础工作流

```bash
# 1. 环境检查
runninghub doctor

# 2. 检测 ID 类型
runninghub detect 2037071836214730753

# 3. 查看节点结构（自动精简）
runninghub inspect 2037071836214730753

# 4. 提交任务并等待结果
runninghub run 2037071836214730753 \
  --type workflow \
  --node-overrides '[
    {"nodeId": "57", "fieldName": "text", "fieldValue": "a cinematic sunset"}
  ]'

# 5. 输出文件自动下载到 ./runninghub_outputs/
```

### 分步执行（适合长时间任务）

```bash
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub task-detail <task_id>
runninghub wait-download <id> <task_id>
```

### 带媒体文件的任务

图片/视频/音频字段支持 `@upload:` 前缀，CLI 会自动上传：

```json
[
  {"nodeId": "167", "fieldName": "image", "fieldValue": "@upload:./model.jpg"},
  {"nodeId": "52", "fieldName": "video", "fieldValue": "@upload:./dance.mp4"}
]
```

```bash
runninghub run <id> --type webapp --node-overrides overrides.json
```

### 加密 AI App

```bash
export APP_ACCESS_PASSWORD='<密码>'
runninghub run <id> --type webapp --access-password "$APP_ACCESS_PASSWORD" \
  --node-overrides overrides.json
```

---

## 市集发现、自动测试与导出

`runninghub discover` 命令组让你直接在终端浏览 RunningHub 市集、自动测试工作流、并导出为 Hermes Agent 可直接使用的 Skill 文件。

### 1. 搜索市集

```bash
# 搜索工作流（默认表格视图）
runninghub discover search --keyword "换脸" --type workflow --size 10

# 搜索 AI App
runninghub discover search --keyword "视频" --type webapp --size 10

# JSON 输出（Agent/脚本用）
runninghub discover search --keyword "换脸" --type workflow --size 3 --format json
```

表格输出示例：

```
====================================================================================================
  📦 工作流 (Workflows) — 共 1234 条匹配  (共 5 条)
====================================================================================================
  ID                     名称                               使用       收藏     发布           作者
  ────────────────────── ──────────────────────────────── ──────── ────── ──────────── ────────────────
  1895719152445751298    FLUX Redux+ACE++ 换脸工作流          0        0      2025-03-01   设计师学Ai
                         📝 使用方法：1. 上传脸部参考图和模特背景效果图2...
                         🏷️  角色一致性  换脸  图生图
                         🔗 https://www.runninghub.cn/workflow/1895719152445751298
```

### 2. 查看详情

```bash
runninghub discover inspect <工作流或AI_App_ID>
```

### 3. 自动测试

```bash
# 使用自定义提示词
runninghub discover test <id> --prompt "a cinematic sunset" --timeout 600

# 自动生成默认提示词
runninghub discover test <id> --timeout 300
```

### 4. 导出为 Hermes Skill

```bash
runninghub discover export <id> \
  --name 文生图_动漫 \
  --description "根据提示词生成动漫风格图片" \
  --prompt "a cute anime girl, studio ghibli style" \
  --output-dir ./skills
```

### 端到端示例

```bash
# 1. 搜索相关工作流
runninghub discover search --keyword "动漫" --type workflow --size 5

# 2. 查看感兴趣的
runninghub discover inspect 2037071836214730753

# 3. 测试并导出为 Hermes Skill
runninghub discover export 2037071836214730753 \
  --name txt2img_anime \
  --prompt "a cute anime girl" \
  --output-dir ./skills

# 4. 加载到 Hermes
cp ./skills/txt2img_anime.md ~/.hermes/skills/
```

---

## 节点覆盖（Node Overrides）

标准格式：

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A cinematic coffee shop scene"}
]
```

可以内联传 JSON 字符串，也可以传文件路径：

```bash
# 内联 JSON
runninghub run <id> --node-overrides '[{"nodeId":"43","fieldName":"text","fieldValue":"hello"}]'

# 文件路径
runninghub run <id> --node-overrides overrides.json
```

**媒体文件自动上传：** `fieldValue` 以 `@upload:` 开头的，CLI 在上传后将值替换为 RunningHub 的 `fileName`：

```json
[
  {"nodeId": "167", "fieldName": "image", "fieldValue": "@upload:./model.jpg"}
]
```

---

## 任务失败处理

如果工作流或 AI App 执行失败，先看 JSON 错误信息：

```bash
# 如果有 task_id
runninghub task-detail <task_id>
```

返回的 `status`、`error_code`、`error_message`、`failed_reason`、`outputs` 等信息用于定位问题。

**重试策略：**
1. 根据失败信息修复最小的 payload 字段
2. 如果相同工作流继续失败，精简 payload，只保留必要的用户输入
3. 如果怀疑内容问题，改写提示词更保守
4. 3 次重试后停止，向用户报告最新的失败详情

---

## 上传媒体文件

```bash
runninghub upload ./input.png --kind image
runninghub upload ./input.mp4 --kind video
runninghub upload ./input.wav --kind audio
runninghub upload ./input.bin --kind file
```

图片使用 SDK 的 `upload_image()`，其他类型使用 `upload_file()`。

---

## 自更新

```bash
# 查看最新 tag 但不更新
runninghub self-update --dry-run

# 更新到最新 tag
runninghub self-update

# 更新到指定版本
runninghub self-update --tag v0.2.0
```

首次打 tag 前，手动更新：

```bash
git pull
python -m pip install -e .
```

---

## Agent 契约

成功输出：

```json
{"ok": true, "data": {}}
```

失败输出（退出码非零）：

```json
{"ok": false, "error_type": "ValidationError", "error": "..."}
```

### Agent 推荐工作流

#### 对已知工作流
1. `runninghub doctor`
2. `runninghub detect <id>`
3. `runninghub inspect <id>`（默认精简模式，只看关键节点）
4. 构建 `node_overrides`
5. `runninghub submit` 或 `runninghub run`
6. 失败时检查 `error_type`、`task_id`、`failed_reason`，必要时 `runninghub task-detail <task_id>`，最小化修改后重试

#### 发现新工作流
1. `runninghub discover search --keyword "<用户需求>" --type workflow`
2. `runninghub discover inspect <id>`（对每个候选）
3. `runninghub discover test <id> --prompt "<测试提示>"`（快速测试）
4. `runninghub discover export <id> --name <技能名> --output-dir ./skills`（导出好用的）
5. `cp ./skills/*.md ~/.hermes/skills/`（加载到 Hermes）
