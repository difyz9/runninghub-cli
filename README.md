# RunningHub CLI

**一体化 AI 媒体生成工具链** — SDK 封装 + 命令行 + 流水线编排 + Agent Skill

`runninghub-cli` 基于 [runninghub-sdk](https://pypi.org/project/runninghub-sdk/) 构建，把 RunningHub 平台上的 **ComfyUI 工作流** 和 **AI 应用** 变成可复用、可注册、可被 AI Agent 直接调用的本地工具。

## 它能做什么

| 你想做的事 | 用什么 |
|-----------|--------|
| 跑一个文生图 / 图生视频 / 音乐生成任务 | `runninghub run` |
| 在 RunningHub 市集里搜索新工作流并自动测试 | `runninghub discover search / test` |
| 用首帧+尾帧生成过渡视频 | `python -m scripts.first2last` |
| 把一句话创意变成完整分镜图 | `python -m scripts.storyboard` |
| 一条命令跑完 文生图→图生视频→转场→合并 | `python -m scripts.pipeline` |
| 本地合并视频片段（含交叉淡化） | `python -m scripts.merge` |
| 用业务参数（而非裸节点 ID）调用接口 | `python -m scripts.skill_runner --skill ...` |
| 生成高质量提示词并自动调色 | `runninghub prompt` |
| 让 Codex / Claude / Hermes 帮你调用 | `skills/SKILL.md` Agent Skill |
| 把工作流登记成可复用模版 | `runninghub config add` |

## 三层架构

```
┌─────────────────────────────────────────────────────┐
│  Agent 层   skills/SKILL.md · agents/openai.yaml    │  ← AI 助手的说明书
├─────────────────────────────────────────────────────┤
│  CLI 层     runninghub 命令 · scripts/ 编排脚本      │  ← 人类和脚本都直接用
├─────────────────────────────────────────────────────┤
│  注册表层   registry/payloads · skills · styles      │  ← 参数契约（数据，非代码）
└─────────────────────────────────────────────────────┘
```

**核心设计**：RunningHub 的所有工作流和 AI 应用都用同一个契约调用——

```
workflow_id（或 webapp_id） + node_info_list = [ {nodeId, fieldName, fieldValue}, ... ]
```

节点 ID 和字段名因工作流而异，全部沉淀在 `registry/payloads/*.json` 里。**新增工作流不需要改代码，只需添加 JSON 模版**。

---

## 目录

- [安装](#安装)
- [认证](#认证)
- [快速开始](#快速开始)
- [runninghub CLI 命令参考](#runninghub-cli-命令参考)
- [参数传递（Node Overrides）](#参数传递node-overrides)
- [任务执行细节](#任务执行细节)
- [提示词质量引擎](#提示词质量引擎)
- [编排脚本 scripts/](#编排脚本-scripts)
- [注册表 registry/](#注册表-registry)
- [新增一个工作流](#新增一个工作流)
- [Agent 集成](#agent-集成)
- [便携工具 tools/](#便携工具-tools)
- [项目结构](#项目结构)
- [环境变量总表](#环境变量总表)
- [开发与测试](#开发与测试)
- [故障排查](#故障排查)

---

## 安装

### 方式一：Git + bootstrap（推荐）

```bash
git clone https://github.com/difyz9/runninghub-cli.git
cd runninghub-cli
./scripts/bootstrap.sh
```

如果 API Key 在别的 `.env` 文件里，可以一步完成安装+验证：

```bash
./scripts/bootstrap.sh --doctor-env /absolute/path/to/.env
```

### 方式二：手动安装

```bash
pip install "runninghub-sdk>=1.1.9" "typer>=0.9.0"
pip install -e .
```

安装后两个等价命令可用：

```bash
runninghub --help
runhub --help
```

### 方式三：不安装直接用

```bash
pip install "runninghub-sdk>=1.1.9" "typer>=0.9.0"
PYTHONPATH=src python -m runninghub_cli.main doctor
```

系统要求：Python ≥ 3.10。可选依赖：`ffmpeg`（视频合并）、`openai`（DeepSeek 提示词生成）。

---

## 认证

### API Key（执行任务用）

```bash
export RUNNINGHUB_API_KEY=你的key    # 建议写入 .env，项目会自动加载
runninghub doctor                     # 验证 key + 查询余额和队列
```

也可以每次传 `--api-key`，或用 `--env-file` 指定任意 `.env` 文件。

### 手机号登录（用户级命令用）

`history`、`call-log` 等查询个人任务记录的命令需要 access_token：

```bash
runninghub login -u 手机号 -p 密码    # 凭证保存在 ~/.runninghub/auth.json
runninghub logout                    # 清除本地凭证
```

---

## 快速开始

### 场景 1：跑一个已注册的工作流

```bash
# 1. 检查环境（API key、余额、并发队列）
runninghub doctor

# 2. 列出注册表里所有可用资源
runninghub config list

# 3. 查看某个工作流的参数详情和调用指南
runninghub config guide 2037071836214730753

# 4. 一条命令：提交 → 等待 → 下载
runninghub run 2037071836214730753 --type workflow \
  --node 57:text="a cinematic sunset over the ocean, 8K"

# 输出文件自动下载到 ./runninghub_outputs/
```

### 场景 2：从市集发现新工作流

```bash
# 搜索市集（工作流 + AI 应用）
runninghub discover search --keyword "图生视频" --type both

# 查看结构
runninghub discover inspect 1972733308360675329

# 自动测试：生成测试参数 → 提交 → 等待 → 验证产物
runninghub discover test 1972733308360675329 --prompt "一个女孩跳舞"

# 测试通过后导出为 Agent Skill
runninghub discover export 1972733308360675329 --name "舞蹈生成" --output-dir ./skills
```

### 场景 3：跑一条端到端流水线

准备 `scenes.json`：

```json
{
  "title": "我的视频项目",
  "scenes": [
    { "prompt": "cinematic sunset over the ocean", "duration": 5 },
    { "prompt": "a mountain landscape at dawn", "duration": 8,
      "image": "可选的已有图片路径" }
  ]
}
```

执行（文生图 → 图生视频 → 转场 → 合并，全自动）：

```bash
export RUNNINGHUB_API_KEY=...
python -m scripts.pipeline --config scenes.json
```

---

## runninghub CLI 命令参考

所有命令输出结构化 JSON 到 stdout：成功 `{"ok": true, "data": {...}}`，失败 `{"ok": false, "error_type": "...", "error": "..."}` 且退出码非 0。人读的表格输出见 `config`/`discover` 的部分子命令。

### 基础命令

| 命令 | 用途 |
|------|------|
| `runninghub --version` | 显示版本 |
| `runninghub doctor` | 检查 SDK、API key、账户额度、队列可用性 |
| `runninghub detect <ID>` | 判断 ID 是 workflow 还是 AI App |
| `runninghub inspect <ID>` | 查看节点结构。默认精简模式（过滤内部管道节点，只显示用户可调参数），`-v` 显示全部；`--type workflow\|webapp\|ai-app` 可强制指定 |

### 任务命令

| 命令 | 用途 |
|------|------|
| `runninghub submit <ID>` | 提交任务，立即返回 `task_id`（适合长任务/并发编排） |
| `runninghub status <task_id>` | 查询任务状态 |
| `runninghub task-detail <task_id>` | 失败分析利器：状态、输出、webhook 详情、失败原因 |
| `runninghub wait-download <ID> <task_id>` | 等待完成并下载产物，可设 `--output-dir/--poll-interval/--timeout` |
| `runninghub run <ID>` | **一键执行**：submit + wait + download |
| `runninghub upload <file>` | 上传本地文件到 RunningHub 存储，`--kind image\|video\|audio\|file` |

任务命令通用参数：`--type workflow|webapp|ai-app`、`--node-overrides/-n`（JSON 或文件路径）、`--node`（`nodeId:fieldName=value` 简写，可重复）、`--file`（`nodeId:fieldName=本地路径`，自动上传）、`--instance-type`、`--access-password`、`--personal-queue`。

```bash
# 最常用：run + node 简写
runninghub run 2004066004755988481 --type workflow \
  --node 6:text="一只猫在追蝴蝶" --node 6:ratio="16:9"

# AI App + 图片自动上传
runninghub run 2005542596594331650 --type webapp \
  --file 78:image=./model.jpg

# 长任务分步走
task_id=$(runninghub submit 2052272204712300545 -n overrides.json --type workflow | jq -r .data.taskId)
runninghub wait-download 2052272204712300545 "$task_id" --output-dir ./out
```

### 账号命令

| 命令 | 用途 |
|------|------|
| `runninghub login` / `logout` | 手机号登录 / 清除凭证（`~/.runninghub/auth.json`） |
| `runninghub account` | 剩余额度、当前任务数 |
| `runninghub queue-status` | 运行中/排队中任务数、并发上限 |
| `runninghub history` | 任务历史，支持 `--status`/`--task-type`/分页 |
| `runninghub call-log <task_id>` | 单任务调用日志（请求参数、响应、费用） |
| `runninghub self-update` | 按 git tag 更新自身：`--dry-run` 预览、`--tag vX.Y.Z` 指定版本 |

### discover 子命令（市集发现）

| 命令 | 用途 |
|------|------|
| `runninghub discover search -k <关键词>` | 搜索市集工作流和 AI App，`--type workflow\|webapp\|both`，`--sort RECOMMEND\|NEWEST\|POPULAR`，`-f table\|json` |
| `runninghub discover inspect <ID>` | 检查市集资源结构 |
| `runninghub discover test <ID>` | 自动化测试：inspect → 智能生成测试输入 → 提交 → 等待 → 验证 |
| `runninghub discover export <ID>` | 测试通过后导出为 `SKILL.md`（可装载进 Hermes），`--no-test` 跳过测试直接导出 |

### config 子命令（注册表管理）

| 命令 | 用途 |
|------|------|
| `runninghub config list` | 表格列出全部注册模版，`-g txt2img` 按分组过滤、`-q verified` 按质量过滤 |
| `runninghub config ls-verified` | 只列已验证可用的（`-o json` 可机读） |
| `runninghub config groups` | 按分组树形概览（文生图/图生视频/音乐…） |
| `runninghub config guide <ID>` | 📖 调用指南：必填/可选参数、示例命令、小贴士 |
| `runninghub config payload <ID>` | 查看完整 payload JSON |
| `runninghub config quality <ID> --set verified` | 查看/设置质量等级 |
| `runninghub config defaults` | 查看/设置任务类型默认工作流 |
| `runninghub config add <ID>` | **自动注册新工作流**：inspect 远端结构 → 生成 payload 模版 |
| `runninghub config remove <ID>` | 删除模版（`-f` 免确认） |

质量等级：✅ verified（联调通过）/ 🧪 experimental（可用未充分验证）/ ⚠️ unstable / ❌ broken。

### prompt / opik 子命令（提示词质量）

```bash
# 生成高质量提示词：自动选调色风格 + 质量自检
runninghub prompt --scene "古风美女樱花树下" --workflow txt2img
# → {"prompt": "...", "style": "水墨淡染国风", "quality_score": 92, "verified": true}

# 用 DeepSeek LLM 扩写（需 DEEPSEEK_API_KEY）
runninghub prompt -c "赛博朋克城市夜景" --llm --detail

# 查看全部调色风格 / 按类别
runninghub prompt --list-styles
runninghub prompt --list-genres

# 查询运行记录（本地 JSONL 轨迹，零依赖零服务器）
runninghub opik stats
runninghub opik search --name "文生图" --limit 20
```

---

## 参数传递（Node Overrides）

三种等价写法：

```bash
# 1. inline JSON（或指向 .json 文件的路径）
runninghub run <ID> -n '[{"nodeId":"43","fieldName":"text","fieldValue":"hello"}]'

# 2. node 简写（可重复）
runninghub run <ID> --node 43:text="hello" --node 51:steps=30

# 3. file 简写 —— 本地文件自动上传后填入节点
runninghub run <ID> --file 167:image=./model.jpg
```

**媒体自动上传**：`fieldValue` 以 `@upload:` 开头（或用 `--file`）时，本地文件自动上传到 RunningHub 并替换为返回的 `fileName`，类型按扩展名自动推断：

```json
[{"nodeId": "167", "fieldName": "image", "fieldValue": "@upload:./model.jpg"}]
```

**如何知道该填哪个节点？** 三条路：

1. `runninghub config guide <ID>` — 已注册模版的中文参数说明
2. `runninghub inspect <ID>` — 实时查看远端结构（推荐用于新工作流）
3. 直接读 `registry/payloads/<ID>.json` — 含 `llmHint`（给 LLM 的参数填写指导）

---

## 任务执行细节

### 并发限制

默认最大并发 **2**。提交前建议检查：

```bash
runninghub queue-status
# {"concurrent_limit": 2, "running_count": 0, "queued_count": 0}
```

### 实例规格

| `--instance-type` | 显存 | 适用 |
|---|---|---|
| `default`（默认） | 24GB | 常规模型 |
| `plus` | 48GB | 大模型 / 高分辨率长视频 |

```bash
runninghub run <ID> --type webapp --instance-type plus -n overrides.json
```

### 访问密码

加密 AI App 需要传创建者设置的密码：

```bash
runninghub run <ID> --type webapp --access-password <密码> -n overrides.json
```

### 失败排查

```bash
runninghub status <task_id>            # 基础状态
runninghub task-detail <task_id>       # 完整诊断：失败原因、webhook 详情
runninghub call-log <task_id>          # 调用日志：请求/响应/费用
```

---

## 提示词质量引擎

提示词生成不是简单拼接，而是四步流水线（`scripts/prompt_quality.py`）：

1. **风格选择**（`scripts/style_selector.py`）— 从 `registry/color_grading_styles.yaml` 的几十种专业调色风格中按场景语义匹配（水墨国风、黄金时刻、日系清新……）
2. **LLM 扩写**（可选）— DeepSeek 把短描述扩写为专业级 prompt
3. **质量自检** — 评分 + 常见问题自动修复（缺画质词、风格冲突等）
4. **Opik 轨迹记录**（`scripts/opik_tracker.py`）— 每次生成写入 `~/.runninghub/opik_traces/`（本地 JSONL，零依赖），供 `runninghub opik` 查询

支持 `txt2img / txt2vid / img2vid / music` 四类工作流的提示词。

---

## 编排脚本 scripts/

除 `runninghub` CLI 外，`scripts/` 提供更高层的业务编排。所有脚本走同一模式：解析参数 → 构造 `node_info_list` → 提交 → 轮询 → 下载，输出到 `./outputs/` 下的时间戳目录。

### 脚本总览

| 命令 | 用途 |
|------|------|
| `python -m scripts.runner --list` | 列出注册表所有工作流/AI App |
| `python -m scripts.runner --info <ID>` | 查看节点详情 + LLM 引导提示 |
| `python -m scripts.runner --exec --mode workflow --id <ID> --nodes '<JSON>'` | 执行任意工作流（`--mode ai-app` 跑 AI 应用；`--nodes-file` 从文件读参数；`--dry-run` 只验证参数；`--no-download` 只跑不下载；`--output-dir` / `--poll-interval` / `--timeout` 可调） |
| `python -m scripts.runner --check` | 验证凭证 + 余额 |
| `python -m scripts.skill_runner --skill <名称> --param key=value` | **按业务参数调用**（无需裸节点 ID） |
| `python -m scripts.pipeline --config scenes.json` | 端到端：文生图 → 图生视频 → 首尾帧转场 → 合并 |
| `python -m scripts.storyboard --idea "探险故事"` | DeepSeek 生成分镜 prompt → RunningHub 出图 |
| `python -m scripts.first2last -f a.png -l b.png` | 首尾帧过渡视频（wan22 / dasiwa / fusionx 三引擎） |
| `python -m scripts.merge -i clip1.mp4 clip2.mp4 -o out.mp4` | 本地 ffmpeg 合并，`--transition crossfade` 交叉淡化 |
| `python -m scripts.storyboard_standalone --idea "..."` | 分镜生成单文件版（无项目内依赖） |

### skill_runner：业务参数调用

`registry/skills/*.json` 把「裸节点 ID」抽象成「业务参数 + 映射」：

```bash
python -m scripts.skill_runner --list
python -m scripts.skill_runner \
  --skill rh.webapp.txt2img.krea2_photoreal.v1 \
  --param prompt_text="cinematic portrait, realistic skin texture" \
  --output-dir ./outputs
# --dry-run 只打印解析后的配置
```

已注册 10 个 skill（全部 verified，索引见 `registry/skills_index.json`）：

| Skill | 功能 |
|-------|------|
| `rh.webapp.txt2img.krea2_photoreal.v1` | Krea2 写实 4K 文生图 |
| `rh.webapp.txt2img.zimage_art_portrait.v1` | Z-Image 4K 艺术人像 / 三视图 |
| `rh.webapp.txt2vid.minimax_h3.v1` | MiniMax H3 图文生视频 |
| `rh.webapp.img2vid.minimax_h3_fl2va.v1` | MiniMax H3 FL2VA 图生视频 |
| `rh.webapp.img2vid.minimax_h3_fl2va_oss.v1` | 同上（OSS 版） |
| `rh.webapp.firstlast.minimax_h3_fl2va.v1` | MiniMax 首尾帧过渡 |
| `rh.webapp.motion_transfer.wan22.v1` | Wan2.2 动作迁移（图+视频） |
| `rh.webapp.music.minimax_music3.v1` | MiniMax Music3 音乐生成 |
| `rh.webapp.storyboard.auto12.v1` | 自动 12 分镜 |
| `rh.webapp.image_edit.tryon.v1` | AI 试穿 |

另有数字人系列（`dhuman.minimax_h3` / `expression.dhuman` / `infinitetalk.lipsync` / `minimax_h3.audio_lipsync` 等）以 standalone 单文件脚本形式提供，见下一节。

### standalone_skills：单文件可移植脚本

`scripts/standalone_skills/*.py` 由 `tools/build_standalone_skill_scripts.py` 从 skill 定义自动生成，**只依赖 `runninghub-sdk`**，可单独拷走使用：

```bash
pip install runninghub-sdk
python scripts/standalone_skills/rh.webapp.txt2img.krea2_photoreal.v1.py \
  --prompt_text "cinematic portrait"

# 数字人口播
python scripts/standalone_skills/rh.webapp.dhuman.minimax_h3.v1.py \
  --image_path portrait.png --prompt_text "A friendly presenter speaking"

# 口型同步（InfiniTalk，默认 plus 实例）
python scripts/standalone_skills/rh.webapp.infinitetalk.lipsync.v1.py \
  --image_path portrait.png --audio_path speech.mp3
```

### MV 生产线（演示级）

`scripts/mv_plan.py`（8 场景计划）+ `scripts/build_mv.sh`（Ken Burns 动态片段 + 音乐合成）组成一条校园 MV 演示流水线，可参考改造成自己的 MV 项目。

### 其他

- `scripts/base.py` — 共享工具（env 加载、输出目录、日志）
- `scripts/bootstrap.sh` — 一键安装
- `scripts/submit_images.py` / `submit_sdk.py` — 批量提交历史演示（读 `RUNNINGHUB_API_KEY`）

---

## 注册表 registry

机器可读的参数契约仓库——**加接口只加数据，不改代码**。

```
registry/
├── payloads/<ID>.json         ← 19 个工作流/AI App 模版
│     template_name / type / group_name / quality
│     api_params.nodeInfoList  ← 节点 schema（nodeId/fieldName/llmHint/example）
│     call_guide               ← 人类可读调用指南
├── skills/<skill>.json        ← 10 个业务参数 skill 定义（skill_runner 用）
├── skills_index.json          ← skill 索引
├── workflows.yaml             ← 任务类型默认映射 + tiktok 场景映射
└── color_grading_styles.yaml  ← 提示词调色风格库
```

### 已注册工作流一览（19 个）

| ID | 名称 | 类型 | 质量 |
|----|------|------|------|
| `2037071836214730753` | 文生图 (Popular Aesthetics) | workflow | ✅ |
| `2042408661150076930` | Z-Image 文生图 AI 应用 | ai-app | ✅ |
| `2081554936466329602` | 艺术人像摄影 Z-Image 4K | ai-app | ✅ |
| `2059461117663076353` | SeedVR2 图生图 | workflow | ✅ |
| `2056908627524546561` | Flux 多参考图风格融合 | workflow | ✅ |
| `2004066004755988481` | 豆包 Seedance 视频生成 | workflow | ✅ |
| `2084968440439336962` | 加速版 MiniMax H3 图文生视频 | ai-app | ✅ |
| `1972733308360675329` | Wan I2V 舞蹈生成 | workflow | ✅ |
| `2035369813215813634` | LTX2.3 图生视频优化版 | ai-app | ✅ |
| `2069024459431956482` | LTX2.3 动漫数字人特制版 | ai-app | ✅ |
| `2052272204712300545` | LTXV 视频生成 | workflow | ✅ |
| `2059132036383858689` | LTX Director 视频生成 | workflow | ✅ |
| `1967569328524664834` | 首尾帧过渡 (First2Last Wan) | workflow | ✅ |
| `2056898489606561793` | 连续性人物分镜生成 | workflow | ✅ |
| `2044246957450858497` | ACE/Suno V5.5 音乐生成 | workflow | ✅ |
| `2005542596594331650` | 一键提取衣服 + 分离人物 | ai-app | ✅ |
| `2011275998205054977` | 首尾帧过渡 (Wan 2.2) | workflow | 🧪 |
| `2037036284312559617` | 图生视频 (Seedance 2.0) | workflow | 🧪 |
| `1923649885118058498` | Wan I2V 通用视频生成 | workflow | ⚠️ |

### 默认工作流映射（workflows.yaml）

| 任务类型 | 默认 ID | 用途 |
|---------|---------|------|
| txt2img | 2037071836214730753 | 文生图 |
| txt2vid | 2004066004755988481 | 文生视频 |
| img2vid | 1972733308360675329 | 图生视频 |
| img2img | 2059461117663076353 | 图生图 |
| music | 2044246957450858497 | 音乐生成 |
| storyboard | 2056898489606561793 | 分镜生成 |
| video_direct | 2059132036383858689 | 视频导演 |
| style_fusion | 2056908627524546561 | 风格融合 |
| first2last | 1967569328524664834 | 首尾帧过渡 |
| clothes_extract | 2005542596594331650 | 衣服提取 |
| portrait | 2042408661150076930 | 人像生成 |

`pipeline.py` / `storyboard.py` 等脚本按任务类型取默认映射，可用环境变量覆盖（见[环境变量总表](#环境变量总表)）。另有 `tiktok:` 分组（同款复刻/风格迁移/人物替换等场景到 ID 的快捷映射）。

---

## 新增一个工作流

**推荐路径**（一条命令）：

```bash
# 自动 inspect 远端结构 → 生成 payload 模版 → 写入 registry/payloads/
runninghub config add <新ID> --group img2vid --name "我的模版" --quality experimental

# 联调通过后升级质量等级
runninghub config quality <新ID> --set verified

# 之后所有工具（runner / CLI / Agent）都能发现它
python -m scripts.runner --info <新ID>
```

**手动路径**：从 Web UI 或历史报告拿到一次成功请求的 `node_info_list`，写入 `registry/payloads/<ID>.json`（可参考现有文件的结构，`llmHint` 写清楚每个参数怎么填）。

详细参考文档在 `references/workflows/*.md`（12 个工作流的逐一分析）。

---

## Agent 集成

本项目天生为 AI Agent 设计：

- **JSON 契约** — 所有命令 stdout 输出 `{"ok": bool, ...}`，失败带 `error_type`
- **`skills/SKILL.md`** — Hermes / Codex 可直接装载的 skill 定义（含完整调用流程、并发限制、参数规范）
- **`agents/openai.yaml`** — OpenAI agent 接口声明
- **`registry/payloads` 的 `llmHint`** — 每个节点字段都有给 LLM 的填写指导

### 推荐的 Agent 工作流

**调用已知工作流**：

1. `runninghub doctor` → 2. `detect <id>` → 3. `inspect <id>` → 4. 构造 overrides → 5. `run` → 6. 失败则 `task-detail` 排查重试

**发现新工作流**：

1. `discover search --keyword "<意图>"` → 2. `discover inspect <id>` 逐个检查 → 3. `discover test <id>` 快速验证 → 4. `discover export` 导出 skill → 5. `cp ./skills/*.md ~/.hermes/skills/` 装载

### 并发注意

Agent 批量提交前必须查 `queue-status`（默认并发 2），队列满时等待而非硬塞。

---

## 便携工具 tools/

| 工具 | 用途 |
|------|------|
| `tools/rh_tool.py` | **单文件便携版**：内置已验证接口 profile，拷一个文件到任何项目即可用（`python rh_tool.py run --profile krea2_txt2img --set prompt_text=...`） |
| `tools/sync_runninghub_interfaces.py` | 把接口清单同步进飞书多维表格（依赖 lark-cli） |
| `tools/build_standalone_skill_scripts.py` | 从 `registry/skills/*.json` 重新生成 `scripts/standalone_skills/` |

---

## 项目结构

```
runninghub-cli/
├── src/runninghub_cli/         ← CLI 包（pip install -e .）
│   ├── main.py                   命令入口（typer）
│   ├── service.py                RunningHub API 封装
│   ├── discover.py               市集搜索 / 自动测试 / skill 导出
│   ├── overrides.py              node overrides 解析 + @upload: 上传
│   ├── registry_ops.py           注册表读写
│   ├── auth_store.py             login 凭证存储
│   └── commands/                 命令分组：core / task / account / quality / discover
├── scripts/                    ← 编排脚本 + 共享工具
├── skills/                     ← Hermes Agent skill 定义
├── agents/                     ← AI agent 接口声明（openai.yaml）
├── registry/                   ← 参数契约（payloads / skills / styles / defaults）
├── references/workflows/       ← 12 个工作流的深度参考文档
├── examples/                   ← overrides 示例、接口清单
├── tools/                      ← 便携工具
├── .github/workflows/ci.yml    ← CI（ruff + pytest，3.10–3.12）
├── pyproject.toml
├── AGENTS.md                   ← Codex 项目指导
└── CLAUDE.md                   ← Claude 项目上下文
```

---

## 环境变量总表

| 变量 | 必需 | 用途 |
|------|------|------|
| `RUNNINGHUB_API_KEY` | ✅ | API Key（所有执行类命令） |
| `DEEPSEEK_API_KEY` | 可选 | DeepSeek 提示词生成（storyboard / prompt --llm） |
| `OPENAI_API_KEY` | 可选 | DeepSeek 不可用时的兜底 |
| `RUNNINGHUB_POLL_INTERVAL` | 可选 | 轮询间隔（默认 3s，CLI 默认 15s） |
| `RUNNINGHUB_TIMEOUT` | 可选 | 任务超时（默认 600s，CLI 默认 1800s） |
| `RUNNINGHUB_TXT2IMG_WORKFLOW_ID` 等 | 可选 | 覆盖默认工作流映射（`_IMG2VID_` / `_FIRST2LAST_` / `_FENJING_` 等，见各脚本 docstring） |
| `RUNNINGHUB_FIRST2LAST_*` | 可选 | first2last 的首帧/尾帧/引擎等参数默认值 |

---

## 开发与测试

```bash
pip install -e ".[dev]"

ruff check src/ scripts/        # lint（line-length 120）
```

CI（GitHub Actions）在 Python 3.10/3.11/3.12 上跑 lint。

版本升级：

```bash
runninghub self-update --dry-run   # 预览将更新到的 tag
runninghub self-update             # 更新到最新 tag 并重装
# 默认从 gitee 镜像拉取，可指定其它仓库：
runninghub self-update --repo-url https://github.com/difyz9/runninghub-cli.git
```

---

## 故障排查

| 症状 | 排查 |
|------|------|
| 提交报 key 无效 | `runninghub doctor`；确认 `.env` 或 `--api-key` |
| 任务一直排队 | `runninghub queue-status`——并发默认 2，等队列空闲 |
| 任务失败 | `runninghub task-detail <task_id>` 看 `failed_reason`；`call-log` 看原始请求 |
| 下载产物为空 | 检查任务类型和输出类型是否匹配（`detect` + `inspect`） |
| 节点参数不生效 | 用 `--dry-run` 验证；对照 `registry/payloads/<ID>.json` 检查 nodeId/fieldName 拼写 |
| 图片上传失败 | 确认本地路径存在；用 `runninghub upload` 单独测试 |

## License

MIT
