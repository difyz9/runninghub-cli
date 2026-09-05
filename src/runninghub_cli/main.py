"""RunningHub command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from . import __version__, service
from . import registry_ops as registry
from .commands.account_ops import register_account_commands
from .commands.core_ops import register_core_commands
from .commands.quality_ops import register_quality_commands
from .commands.task_ops import register_task_commands

app = typer.Typer(
    help="RunningHub CLI: inspect, submit, wait, download, and debug workflows or AI Apps.",
    no_args_is_help=True,
    invoke_without_command=True,
)


def emit(data: dict, ok: bool = True) -> None:
    payload = {"ok": ok, **data}
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(exc: Exception) -> None:
    emit(service.error_payload(exc), ok=False)
    raise typer.Exit(1)


def common_api_key_option() -> str | None:
    return typer.Option(None, "--api-key", help="RunningHub API Key; defaults to RUNNINGHUB_API_KEY")


def common_env_file_option() -> Path | None:
    return typer.Option(None, "--env-file", help="Optional .env file to load before reading environment")


def build_cli_overrides(
    node_overrides: str | None,
    node: list[str],
    file: list[str],
) -> list[dict[str, Any]]:
    """Build a unified override list from --node-overrides/--node/--file flags."""
    overrides = service.parse_overrides(node_overrides)

    for arg in node:
        overrides.append(service.parse_node_shorthand(arg))

    for arg in file:
        nd = service.parse_node_shorthand(arg)
        nd["fieldValue"] = f"@upload:{nd['fieldValue']}"
        overrides.append(nd)

    return overrides


@app.callback()
def callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit", is_eager=True),
):
    if version:
        emit({"version": __version__})
        raise typer.Exit()


register_core_commands(
    app,
    emit=emit,
    fail=fail,
    common_api_key_option=common_api_key_option,
    common_env_file_option=common_env_file_option,
)


register_task_commands(
    app,
    emit=emit,
    fail=fail,
    common_api_key_option=common_api_key_option,
    common_env_file_option=common_env_file_option,
    build_cli_overrides=build_cli_overrides,
)

register_account_commands(
    app,
    emit=emit,
    fail=fail,
    common_api_key_option=common_api_key_option,
    common_env_file_option=common_env_file_option,
)


# ── Config command group ──────────────────────────────────


config_app = typer.Typer(
    name="config",
    help="配置管理：质量分级、默认工作流映射",
    no_args_is_help=True,
)


@config_app.command("list")
def config_list(
    group: str | None = typer.Option(None, "--group", "-g", help="按分组过滤: txt2img, img2vid, ..."),
    quality_filter: str | None = typer.Option(None, "--quality", "-q", help="按质量过滤: verified, experimental, ..."),
):
    """列出注册表中所有工作流/AI App 及其质量等级"""
    try:
        entries = registry.get_registry_summary()

        # 过滤
        if group:
            entries = [e for e in entries if e["group"] == group]
        if quality_filter:
            entries = [e for e in entries if e["quality"] == quality_filter]

        entries.sort(key=lambda e: (registry.QUALITY_ORDER.get(e["quality"], 99), e["id"]))

        icons = {"verified": "✅", "experimental": "🧪", "unstable": "⚠️", "broken": "❌", "unknown": "❓"}
        guide_icon = "📖"  # has call_guide

        print(f"\n{'='*120}")
        print(f"  📋 RunningHub 工作流 & AI App 注册表  (共 {len(entries)} 条)")
        if group:
            print(f"  分组: {group}")
        print(f"{'='*120}")
        print(f"  {'质量':<10} {'ID':<24} {'类型':<8} {'输出':<8} {'节点':<4} {'示例':<4} {'分组':<14} {'名称':<30}")
        print(f"  {'─'*10} {'─'*24} {'─'*8} {'─'*8} {'─'*4} {'─'*4} {'─'*14} {'─'*30}")

        for e in entries:
            icon = icons.get(e["quality"], "❓")
            label = f"{icon} {e['quality']}"
            etype = e["type"]
            otype = e["outputType"]
            nc = str(e["nodeCount"])
            ec = str(e["exampleCount"])
            group_name = (e.get("group") or "")[:12]
            name = (e["name"] or "")[:28]
            guide = guide_icon if e["hasGuide"] else "  "
            print(f"  {label:<10} {e['id']:<24} {etype:<8} {otype:<8} {nc:<4} {ec:<4} {group_name:<14} {guide} {name}")

        print("\n  📖 = 有 call_guide 调用指南  |  📦 = 完整 payload")
        print("  ✅ verified  |  🧪 experimental  |  ⚠️ unstable  |  ❌ broken")
        print()
    except Exception as exc:
        fail(exc)


@config_app.command("ls-verified")
def config_ls_verified(
    output: str = typer.Option("table", "--output", "-o", help="table | json"),
):
    """仅列出已验证（verified）的工作流/AI App"""
    try:
        entries = registry.get_verified_entries()
        if output == "json":
            emit({"count": len(entries), "entries": entries})
            return

        print(f"\n{'='*100}")
        print(f"  ✅ 已验证可用的工作流 & AI App  (共 {len(entries)} 条)")
        print(f"{'='*100}")
        print(f"  {'ID':<24} {'类型':<10} {'输出':<8} {'节点':<6} {'名称':<30}")
        print(f"  {'─'*24} {'─'*10} {'─'*8} {'─'*6} {'─'*30}")
        for e in entries:
            print(f"  {e['id']:<24} {e['type']:<10} {e['outputType']:<8} {e['nodeCount']:<6} {(e['name'] or '')[:28]}")
        print()
    except Exception as exc:
        fail(exc)


@config_app.command("quality")
def config_quality(
    entry_id: str = typer.Argument(..., help="工作流或 AI App ID"),
    set_level: str | None = typer.Option(None, "--set", help="设置质量等级: verified, experimental, unstable, broken"),
):
    """查看或设置指定 ID 的质量等级"""
    try:
        if set_level:
            result = registry.set_entry_quality(entry_id, set_level)
            emit(result)
        else:
            qc = registry.check_quality(entry_id)
            if qc["ok"]:
                emit({
                    "id": qc["id"],
                    "name": qc["name"],
                    "quality": qc["quality"],
                    "icon": qc["icon"],
                })
            else:
                emit(qc, ok=False)
    except Exception as exc:
        fail(exc)


@config_app.command("defaults")
def config_defaults(
    task_type: str | None = typer.Option(None, "--task-type", "-t", help="任务类型: txt2img, txt2vid, img2vid, music, ..."),
    entry_id: str | None = typer.Option(None, "--id", help="要设置的工作流/AI App ID"),
):
    """查看或设置默认工作流映射"""
    try:
        if task_type and entry_id:
            result = registry.set_default(task_type, entry_id)
            emit(result)
        else:
            defaults = registry.get_defaults()
            if not defaults:
                emit({"defaults": {}, "message": "暂无默认映射"})
                return

            task_type_names = {
                "txt2img": "文生图",
                "txt2vid": "文生视频",
                "img2vid": "图生视频",
                "img2img": "图生图",
                "music": "音乐生成",
                "storyboard": "分镜生成",
                "video_direct": "视频导演",
                "style_fusion": "风格融合",
                "first2last": "首尾帧过渡",
                "clothes_extract": "衣服提取",
                "portrait": "人像生成",
            }

            print(f"\n{'='*80}")
            print("  📌 默认工作流映射")
            print(f"{'='*80}")
            print(f"  {'任务类型':<16} {'默认 ID':<24} {'名称':<30}")
            print(f"  {'─'*16} {'─'*24} {'─'*30}")
            for ttype, tid in sorted(defaults.items()):
                if ttype in ("tiktok",):
                    continue
                name = (registry._get_payload_field(tid, "template_name", "?") or "?")[:28]
                label = task_type_names.get(ttype, ttype)
                print(f"  {label:<16} {tid:<24} {name}")
            print()
    except Exception as exc:
        fail(exc)


@config_app.command("groups")
def config_groups():
    """🗂️ 按分组列出所有注册模版"""
    try:
        entries = registry.get_registry_summary()
        groups: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            g = e.get("group") or "未分组"
            if g not in groups:
                groups[g] = []
            groups[g].append(e)

        print(f"\n{'='*80}")
        print(f"  🗂️  注册表分组概览  (共 {len(groups)} 个分组)")
        print(f"{'='*80}")

        icons = {"verified": "✅", "experimental": "🧪", "unstable": "⚠️", "broken": "❌", "unknown": "❓"}

        # 推断分组用途
        group_labels: dict[str, str] = {
            "txt2img": "文生图", "img2img": "图生图", "img2vid": "图生视频",
            "txt2vid": "文生视频", "first2last": "首尾帧过渡",
            "style_fusion": "风格融合", "clothes_extract": "衣服提取",
            "music": "音乐生成", "storyboard": "分镜生成",
            "img2vid_opt": "图生视频优化", "dance": "舞蹈生成",
            "person": "人像生成",
        }

        for gname, members in sorted(groups.items()):
            label = group_labels.get(gname, gname)
            verified_count = sum(1 for m in members if m["quality"] == "verified")
            print(f"\n  📂 {label} ({gname})  — {len(members)} 个模版, {verified_count} 个已验证")
            print(f"  {'─'*60}")
            for m in sorted(members, key=lambda x: (registry.QUALITY_ORDER.get(x["quality"], 99), x["id"])):
                icon = icons.get(m["quality"], "❓")
                guide = "📖" if m["hasGuide"] else "  "
                print(f"    {icon} {m['name'][:30]:<32} {guide} ID: {m['id']}")
        print("\n  📖 = 有 call_guide 调用指南")
        print()
    except Exception as exc:
        fail(exc)


@config_app.command("add")
def config_add(
    identifier: str = typer.Argument(..., help="要注册的工作流或 AI App ID"),
    name: str | None = typer.Option(None, "--name", "-n", help="模版名称（留空则自动从 inspect 获取）"),
    group: str = typer.Option("other", "--group", "-g", help="分组名: txt2img, img2vid, style_fusion, first2last, ..."),
    quality: str = typer.Option("experimental", "--quality", "-q", help="质量等级: verified, experimental, unstable, broken"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出类型: image, video, audio, text"),
):
    """➕ 自动从 inspect 数据生成 payload 模版并注册到注册表

    示例:
        runninghub config add 2035369813215813634
        runninghub config add 2035369813215813634 --group img2vid --name "我的模版" --quality verified
    """
    try:
        # 先检查是否已存在
        if registry._has_payload(identifier):
            print(f"\n  ⚠️  模版已存在: registry/payloads/{identifier}.json")
            print(f"  如需覆盖请先运行: runninghub config remove {identifier}\n")
            return

        # inspect 获取节点信息
        from runninghub_cli.discover import inspect_item

        from . import service as svc

        api_key = None  # will use env
        env_file = None
        client = svc.create_client(api_key, env_file)
        info = inspect_item(client, identifier)
        if info.get("error"):
            print(f"\n  ❌ inspect 失败: {info['error']}\n")
            return

        item_type = info.get("type", "workflow")
        item_name = name or info.get("name", identifier)
        nodes_raw = info.get("nodes", [])

        # 从 nodeInfoList 构建 api_params 的 nodeInfoList
        if item_type == "webapp":
            node_info_list = []
            for n in nodes_raw:
                entry = {
                    "nodeId": n.get("nodeId", ""),
                    "fieldName": n.get("fieldName", ""),
                    "fieldValue": n.get("fieldValue", ""),
                    "fieldType": n.get("fieldType", "string"),
                    "description": n.get("description", ""),
                    "required": False,
                    "llmHint": "",
                    "example": "",
                }
                # 解析 fieldData 获取选项/范围/默认值
                field_data = n.get("fieldData", "")
                if field_data:
                    try:
                        parsed = json.loads(field_data)
                        if isinstance(parsed, list) and len(parsed) == 2:
                            constraints = parsed[1] if isinstance(parsed[1], dict) else {}
                            if constraints.get("multiline"):
                                entry["multiline"] = True
                            for k in ("default", "min", "max"):
                                if k in constraints:
                                    entry[k] = constraints[k]
                        # SWITCH 选项
                        if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
                            entry["options"] = [
                                {"value": str(x.get("index", i+1)), "label": x.get("name", f"选项{i+1}")}
                                for i, x in enumerate(parsed)
                            ]
                    except Exception:
                        pass
                node_info_list.append(entry)

            payload = {
                "template_name": item_name,
                "runninghub_id": identifier,
                "type": "ai-app",
                "group_name": group,
                "tags": ["ai-app", quality, group],
                "workflow_type": group,
                "overall_score": 10.0,
                "tested_at": "2026-07-01T00:00:00",
                "api_params": {
                    "apiKey": "your-runninghub-api-key",
                    "webhookUrl": "",
                    "instanceType": "default",
                    "accessPassword": "",
                    "webappId": identifier,
                    "nodeInfoList": node_info_list,
                },
                "description": f"由 {item_name} 自动生成的模版，{len(node_info_list)} 个可配节点",
                "outputType": output or "video",
                "outputCount": "1",
                "quality": quality,
            }
        else:
            # workflow 类型 — 从 get_workflow_json_parsed 获取
            node_info_list = []
            for n in nodes_raw:
                node_info_list.append({
                    "nodeId": n.get("nodeId", ""),
                    "fieldName": "",
                    "fieldValue": "",
                    "fieldType": "string",
                    "description": f"classType: {n.get('classType', '')}, fields: {', '.join(n.get('fields', []))}",
                    "required": False,
                    "llmHint": "",
                    "example": "",
                })

            payload = {
                "template_name": item_name,
                "runninghub_id": identifier,
                "type": "workflow",
                "group_name": group,
                "tags": ["workflow", quality, group],
                "workflow_type": group,
                "overall_score": 5.0,
                "tested_at": "2026-07-01T00:00:00",
                "api_params": {
                    "apiKey": "your-runninghub-api-key",
                    "webhookUrl": "",
                    "instanceType": "default",
                    "accessPassword": "",
                    "workflowId": identifier,
                    "nodeInfoList": node_info_list,
                },
                "description": f"由 {item_name} 自动生成的 workflow 模版",
                "outputType": output or "image",
                "outputCount": "1",
                "quality": quality,
            }

        # 写入文件
        import json
        payload_path = service._payload_path(identifier)
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"\n  ✅ 模版已创建: {payload_path}")
        print(f"  📝 {item_name} ({identifier})")
        print(f"  📂 分组: {group}  |  质量: {quality}  |  节点: {len(node_info_list)} 个")
        print("\n  💡 编辑指南:")
        print(f"     - 修改 call_guide 等字段: 直接编辑 {payload_path}")
        print(f"     - 设置质量等级: runninghub config quality {identifier} --set verified")
        print(f"     - 查看调用指南: runninghub config guide {identifier}")
        print(f"     - 查看原始 JSON: runninghub config payload {identifier}")
        print()

    except Exception as exc:
        fail(exc)


@config_app.command("remove")
def config_remove(
    identifier: str = typer.Argument(..., help="要移除的工作流或 AI App ID"),
    force: bool = typer.Option(False, "--force", "-f", help="直接删除，无需确认"),
):
    """🗑️ 从注册表中移除指定的 payload 模版"""
    try:
        payload_path = service._payload_path(identifier)
        if not payload_path.exists():
            print(f"\n  ⚠️  未找到 payload 文件: {payload_path}\n")
            return

        name = registry._get_payload_field(identifier, "template_name", identifier)

        if not force:
            print(f"\n  即将删除: {name} ({identifier})")
            print(f"  文件: {payload_path}")
            answer = input("  确认删除？(y/N): ").strip().lower()
            if answer not in ("y", "yes"):
                print("  已取消\n")
                return

        payload_path.unlink()
        print(f"\n  ✅ 已删除: {name} ({identifier})\n")

    except Exception as exc:
        fail(exc)


@config_app.command("payload")
def config_payload(
    entry_id: str = typer.Argument(..., help="工作流或 AI App ID"),
    pretty: bool = typer.Option(True, "--pretty/--raw", help="美化输出 (default: pretty)"),
):
    """📦 查看指定 ID 的完整 payload JSON 文件"""
    try:
        payload = registry._load_payload(entry_id)
        if payload is None:
            print(f"\n  ⚠️  未找到 payload 文件: registry/payloads/{entry_id}.json")
            print("  💡 可将 RunningHub 请求体保存到该路径后直接使用\n")
            return

        indent = 2 if pretty else None
        print()
        print(json.dumps(payload, indent=indent, ensure_ascii=False))
        print()
    except Exception as exc:
        fail(exc)


@config_app.command("guide")
def config_guide(
    entry_id: str = typer.Argument(..., help="工作流或 AI App ID"),
):
    """📖 查看工作流/AI App 的调用指南 — 参数说明 + 命令示例"""
    try:
        payload = registry._load_payload(entry_id)
        if payload is None:
            print(f"\n  ⚠️  未找到 payload 文件: registry/payloads/{entry_id}.json\n")
            return

        name = payload.get("template_name", entry_id)
        quality = payload.get("quality", "?")
        icons = {"verified": "✅", "experimental": "🧪", "unstable": "⚠️", "broken": "❌"}
        qicon = icons.get(quality, "❓")

        head = f"{qicon} {name}"
        sep = "═" * max(60, len(head) + 4)
        print(f"\n  ╔{sep}╗")
        print(f"  ║  {head:<{len(sep)-2}} ║")
        print(f"  ╚{sep}╝")
        print(f"  ID: {entry_id}")
        print(f"  类型: {payload.get('type', '?')}  |  输出: {payload.get('outputType', '?')}  |  质量: {qicon} {quality}")
        if payload.get("description"):
            print(f"\n  📝 {payload['description']}")
        print()

        # ── Required args ──
        guide = payload.get("call_guide")
        if guide:
            print(f"  ┌─ 🔧 调用方式 {'─'*50}")
            print(f"  │  {guide.get('method', 'runninghub run <ID> --type <mode>')}")
            print()

            required = guide.get("required", [])
            if required:
                print("  ├─ 📌 必填参数")
                for r in required:
                    print(f"  │    {r['arg']}")
                    print(f"  │    → {r['label']}: {r['hint']}")
                print()

            optional = guide.get("optional", [])
            if optional:
                print("  ├─ 🔹 可选参数")
                for o in optional:
                    default_str = f"  (默认: {o['default']})" if o.get("default") else ""
                    print(f"  │    {o['arg']}{default_str}")
                    print(f"  │    → {o['label']}: {o['hint']}")
                    if o.get("options_map"):
                        for k, v in o["options_map"].items():
                            print(f"  │      {k} = {v}")
                    if o.get("condition"):
                        print(f"  │    ⚡ {o['condition']}")
                print()
        else:
            print(f"  ┌─ 🔧 调用方式 {'─'*50}")
            print(f"  │  runninghub run {entry_id} --type {payload.get('type', 'workflow')} --node ...")
            print()

        # ── Examples ──
        examples = payload.get("examples", [])
        if examples:
            print("  ├─ 📋 使用示例")
            for i, ex in enumerate(examples, 1):
                print("  │")
                print(f"  │  [{i}] {ex['title']}")
                print(f"  │     {ex['description']}")
                print(f"  │     $ {ex['command']}")
                for note in ex.get("notes", []):
                    print(f"  │     💡 {note}")
            print()

        # ── Tips ──
        tips = payload.get("tips", [])
        if tips:
            print("  ├─ 💡 小贴士")
            for tip in tips:
                print(f"  │   • {tip}")
            print()

        # ── Inputs / Outputs ──
        inputs = payload.get("inputs", [])
        outputs = payload.get("outputs", [])
        if inputs or outputs:
            print("  ├─ 📦 输入/输出")
            for inp in inputs:
                req = "必填" if inp.get("required") else "可选"
                print(f"  │   📥 {inp['label']} ({inp['type']}, {req}) — 节点 {inp['nodeId']}.{inp['fieldName']}")
                if inp.get("depends"):
                    d = inp["depends"]
                    print(f"  │     仅在节点 {d['nodeId']}=选择 {d['value']} 时生效")
            for out in outputs:
                print(f"  │   📤 {out['label']} ({out['type']}, {out.get('count', 1)}个)")
            print()

        # ── Raw api_params count ──
        node_count = len(payload.get("api_params", {}).get("nodeInfoList", []))
        print(f"  └─ 📊 {node_count} 个可配节点 (见 api_params.nodeInfoList)")
        print()

    except Exception as exc:
        fail(exc)

register_quality_commands(
    app,
    emit=emit,
    fail=fail,
)


# ── Command groups ──────────────────────────────────────────

from runninghub_cli.commands.discover import discover_app

app.add_typer(discover_app)
app.add_typer(config_app)


if __name__ == "__main__":
    app()

