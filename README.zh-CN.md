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

---

## 安装

### 从 Git 安装（推荐）

```bash
git clone https://github.com/difyz9/runninghub-cli.git
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
pip install "runninghub-sdk>=1.1.5" "typer>=0.9.0"
pip install -e .
```

安装后可用两个命令（短别名也支持）：

```bash
runninghub --help
runhub --help
```

### 不安装也能用

```bash
pip install "runninghub-sdk>=1.1.5" "typer>=0.9.0"
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

### 基础命令

| 命令 | 用途 |
|------|------|
| `runninghub doctor` | 检查 SDK、API Key 和队列可用性 |
| `runninghub detect <id>` | 检测 ID 是工作流还是 AI App |
| `runninghub inspect <id> --type <type>` | 查看节点和字段结构 |
| `runninghub submit` | 提交任务，立即返回 task_id |
| `runninghub status <task_id>` | 查询任务状态 |
| `runninghub wait-download` | 等待任务完成并下载输出 |
| `runninghub run` | 提交、等待、下载一步到位 |
| `runninghub task-detail <task_id>` | 获取详细失败分析信息 |
| `runninghub upload <file> --kind <kind>` | 上传图片/视频/音频/文件到 RunningHub |
| `runninghub self-update` | 更新 CLI 到最新 Git tag |

### 发现命令（市集 + 自动测试 + 导出）

| 命令 | 用途 |
|------|------|
| `runninghub discover search` | 搜索 RunningHub 市集的工作流和 AI App |
| `runninghub discover inspect <id>` | 深度查看市集项目结构 |
| `runninghub discover test <id>` | 自动测试：检测类型→构建参数→提交→等待→验证 |
| `runninghub discover export <id>` | 测试通过后导出为 Hermes 可直接加载的 `SKILL.md` |

---

## 快速上手

### 基础工作流

```bash
# 1. 环境检查
runninghub doctor

# 2. 检测 ID 类型
runninghub detect 2037071836214730753

# 3. 查看节点结构
runninghub inspect 2037071836214730753 --type workflow

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
runninghub run <id> --type webapp --access-password "$APP_ACCESS_PASSWORD" --node-overrides overrides.json
```

---

## 市集发现、自动测试与导出

`runninghub discover` 命令组让你直接在终端浏览 RunningHub 市集、自动测试工作流、并导出为 Hermes Agent 可直接使用的 Skill 文件。

### 1. 搜索市集

```bash
# 搜索工作流
runninghub discover search --keyword "换脸" --type workflow --size 10

# 搜索 AI App
runninghub discover search --keyword "视频" --type webapp --size 10

# 同时搜索两种类型
runninghub discover search --keyword "动漫" --type both --size 5
```

可选参数：
- `--sort RECOMMEND|NEWEST|POPULAR` — 排序方式（默认：推荐）
- `--page 2` — 分页
- `--size 30` — 每页条数

返回结果包含：名称、描述、标签、使用次数、点赞数、收藏数、作者信息、封面预览。

### 2. 查看详情

```bash
runninghub discover inspect <工作流或AI_App_ID>
```

- **AI App**：返回完整的可编辑节点列表（nodeId、fieldName、fieldType、description、默认值）
- **工作流**：返回节点类型分布统计和可编辑字段列表

### 3. 自动测试

`discover test` 自动完成以下步骤：
1. 检测是工作流还是 AI App
2. 分析节点结构
3. 智能生成测试参数（自动识别 prompt/text 节点）
4. 提交到 RunningHub
5. 轮询直至完成
6. 报告耗时和输出数量

```bash
# 使用自定义提示词
runninghub discover test <id> --prompt "a cinematic sunset" --timeout 600

# 自动生成默认提示词
runninghub discover test <id> --timeout 300
```

输出（多行 JSON，便于追踪进度）：
```json
{"ok": true, "phase": "detect", "type": "workflow"}
{"ok": true, "phase": "generate", "overrides": [...]}
{"ok": true, "phase": "result", "test": {"ok": true, "taskId": "...", "duration": 45.2, ...}}
```

### 4. 导出为 Hermes Skill

`discover export` 测试工作流后，生成一个独立的 `SKILL.md` 文件，可直接放入 `~/.hermes/skills/`：

```bash
# 完整流程：测试 → 导出（推荐）
runninghub discover export <id> \
  --name 文生图_动漫 \
  --description "根据提示词生成动漫风格图片" \
  --prompt "a cute anime girl, studio ghibli style" \
  --timeout 600 \
  --output-dir ./skills

# 跳过测试直接导出（确认好用的工作流）
runninghub discover export <id> --no-test --output-dir ./skills
```

生成的 `SKILL.md` 包含：
- YAML 头部（`name`, `runninghubId`, `runninghubType`）
- 参数说明
- 已验证的请求载荷（测试通过时）
- 可直接运行的 `runninghub-cli` 命令
- Node 映射关系

跨机器使用：
```bash
cp exported-skills/*.md ~/.hermes/skills/
```
Hermes 下次启动时会自动加载。

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

## 任务失败处理

如果工作流或 AI App 执行失败，先看 JSON 错误信息。`run` 和 `wait-download` 会返回 `task_id`、`failed_reason` 和 `task_detail`。

如果只有 task_id：

```bash
runninghub task-detail <task_id>
```

返回的 `status`、`error_code`、`error_message`、`failed_reason`、`outputs`、`webhook_detail` 等信息用于定位问题。

重试策略：
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

上传后返回 `fileName` 和 `downloadUrl`，`fileName` 用于 node_overrides 中的 media 字段：

```json
[
  {"nodeId": "167", "fieldName": "image", "fieldValue": "226dd3950e6....jpg"},
  {"nodeId": "52", "fieldName": "video", "fieldValue": "57012cfc3d5....mp4"}
]
```

也可以用 `@upload:` 在提交时自动上传：

```json
[
  {"nodeId": "167", "fieldName": "image", "fieldValue": "@upload:./model.jpg"},
  {"nodeId": "52", "fieldName": "video", "fieldValue": "@upload:./dance.mp4"}
]
```

`@upload:` 会上传文件并用 `fileName` 替换。`@upload-url:` 只在字段明确要求 URL 时使用。

---

## 自更新

```bash
# 查看最新 tag 但不更新
runninghub self-update --dry-run

# 更新到最新 tag
runninghub self-update

# 更新到指定版本
runninghub self-update --tag v0.1.0
```

首次打 tag 前，手动更新：

```bash
git pull
python -m pip install -e .
```

---

## 节点覆盖（Node Overrides）

标准格式：

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A cinematic coffee shop scene"}
]
```

可以内联传 JSON 字符串，也可以传文件路径。`description` 字段对人有用但不必要。

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
3. `runninghub inspect <id> --type <type>`
4. 构建 `node_overrides`
5. `runninghub submit` 或 `runninghub run`
6. 失败时检查 `error_type`、`task_id`、`failed_reason`，必要时 `runninghub task-detail <task_id>`，最小化修改后重试

#### 发现新工作流
1. `runninghub discover search --keyword "<用户需求>" --type workflow`
2. `runninghub discover inspect <id>`（对每个候选）
3. `runninghub discover test <id> --prompt "<测试提示>"`（快速测试）
4. `runninghub discover export <id> --name <技能名> --output-dir ./skills`（导出好用的）
5. `cp ./skills/*.md ~/.hermes/skills/`（加载到 Hermes）
