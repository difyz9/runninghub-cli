"""CLI tool: Unified RunningHub runner.

Supports discovery and execution modes:
  --check         Verify API key and check account balance
  --list          List all registered workflows and AI apps
  --info   ID     Show workflow/AI app node details with LLM guidance
  --exec          Execute a workflow or AI app (requires --mode + --id + --nodes)

Usage:
    # Discovery
    python -m scripts.runner --check
    python -m scripts.runner --list
    python -m scripts.runner --info 2037071836214730753

    # Execute a workflow
    python -m scripts.runner --exec --mode workflow --id 2004066004755988481 \
        --nodes '[{"nodeId":"1","fieldName":"prompt","fieldValue":"一只猫"}]'

    # Execute an AI app with image upload
    python -m scripts.runner --exec --mode ai-app --id 2005542596594331650 \
        --nodes '[{"nodeId":"78","fieldName":"image","fieldValue":"@upload:./input.png"}]'

    # Dry run to validate parameters without executing
    python -m scripts.runner --exec --mode workflow --id 2056898489606561793 \
        --nodes '[...]' --dry-run

Environment variables:
    RUNNINGHUB_API_KEY            (required unless --api-key is provided)
    RUNNINGHUB_POLL_INTERVAL      (default: 3.0)
    RUNNINGHUB_TIMEOUT            (default: 600)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from runninghub_sdk import RunningHubClient

from .base import (
    UPLOAD_PREFIX,
    bootstrap_env,
    get_env_float,
    log,
    print_request_summary,
    resolve_api_key,
    section,
)

# Path to workflow registry
REGISTRY_DIR = Path(__file__).resolve().parent.parent / "registry"
WORKFLOWS_YAML = REGISTRY_DIR / "workflows.yaml"
PAYLOAD_DIR = REGISTRY_DIR / "payloads"


# ==================== Registry loader ====================


def load_workflows() -> Dict[str, Any]:
    """Load the workflow registry from workflows.yaml + payloads/ directory."""
    entries: List[Dict[str, Any]] = []
    if not PAYLOAD_DIR.exists():
        return {"workflows": [], "ai_apps": []}
    for f in sorted(PAYLOAD_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                payload = json.load(fh)
            entry: Dict[str, Any] = {
                "id": f.stem,
                "name": payload.get("template_name", f.stem),
                "type": payload.get("type", "workflow"),
                "outputType": payload.get("outputType", "?"),
                "quality": payload.get("quality", "unknown"),
            }
            # 从 api_params.nodeInfoList 提取节点 schema
            api_params = payload.get("api_params", {})
            node_list = api_params.get("nodeInfoList", []) if isinstance(api_params, dict) else []
            if node_list:
                entry["nodes"] = []
                for node in node_list:
                    entry["nodes"].append({
                        "nodeId": node.get("nodeId"),
                        "fieldName": node.get("fieldName"),
                        "fieldType": node.get("fieldType", "string"),
                        "description": node.get("description", ""),
                        "required": node.get("required", False),
                        "default": node.get("default", ""),
                        "range": node.get("range", ""),
                        "llmHint": node.get("llmHint", ""),
                        "example": node.get("example", ""),
                    })
                entry["verifiedPayload"] = node_list

            target = "ai_apps" if entry["type"] == "ai-app" else "workflows"
            entries.append((target, entry))
        except Exception:
            pass

    result: Dict[str, List[Dict[str, Any]]] = {"workflows": [], "ai_apps": []}
    for target, entry in entries:
        result[target].append(entry)
    return result


def find_workflow(registry: Dict[str, Any], resource_id: str) -> Dict[str, Any] | None:
    """Find a workflow or AI app by ID in the registry."""
    for wf in registry.get("workflows", []):
        if wf["id"] == resource_id:
            return wf
    for app in registry.get("ai_apps", []):
        if app["id"] == resource_id:
            return app
    return None


def find_verified_payload(registry: Dict[str, Any], resource_id: str) -> List[Dict[str, Any]]:
    """Get the verified payload for a resource, if any."""
    entry = find_workflow(registry, resource_id)
    if entry:
        return entry.get("verifiedPayload", [])
    return []


def _format_node_doc(node: Dict[str, Any], level: int = 0) -> str:
    """Format a single node entry as LLM-readable text."""
    indent = "  " * level
    lines = [f"{indent}- **nodeId {node['nodeId']} · fieldName `{node['fieldName']}`**"]
    lines.append(f"{indent}  类型: {node['fieldType']}")
    lines.append(f"{indent}  说明: {node['description']}")
    if node.get("required"):
        lines.append(f"{indent}  📌 必填")
    if node.get("default"):
        lines.append(f"{indent}  默认值: {node['default']}")
    if node.get("range"):
        lines.append(f"{indent}  范围: {node['range']}")
    if node.get("llmHint"):
        lines.append(f"{indent}  💡 {node['llmHint']}")
    if node.get("example"):
        lines.append(f"{indent}  📝 示例: `{node['example']}`")
    return "\n".join(lines)


def _print_resource_info(entry: Dict[str, Any], verified: List[Dict[str, Any]]) -> None:
    """Print a workflow or AI app entry details."""
    res_type = "AI App" if entry["type"] == "ai-app" else "Workflow"
    print(f"\n{'=' * 60}")
    print(f"  {entry['name']}")
    print(f"{'=' * 60}")
    print(f"  ID:        {entry['id']}")
    print(f"  类型:      {res_type}")
    print(f"  说明:      {entry['description']}")
    print(f"  输出:      {entry['outputType']} × {entry['outputCount']}")
    print()

    nodes = entry.get("nodes", [])
    if nodes:
        print(f"  📋 可用参数（{len(nodes)} 个节点字段）")
        print(f"  {'─' * 58}")
        print("  LLM 根据任务描述从以下参数中选择所需项即可，不需要全部提供")
        print()
        for node in nodes:
            print(_format_node_doc(node, 1))
            print()

    if verified:
        print("  ✅ 已验证的请求载荷（来自集成测试）")
        print(f"  {'─' * 58}")
        print(json.dumps(verified, indent=2, ensure_ascii=False))
        print()

    print("  调用方式:")
    mode_flag = "ai-app" if entry["type"] == "ai-app" else "workflow"
    print(f"    python -m scripts.runner --exec --mode {mode_flag} --id {entry['id']} \\")
    print("      --nodes '<JSON_NODES>'")
    print()


# ==================== Parser ====================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rh-runner",
        description="Unified RunningHub runner — discover and call workflows/AI apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode flags
    mode_group = p.add_mutually_exclusive_group()
    mode_group.add_argument("--check", action="store_true",
                            help="Verify API key and check account balance")
    mode_group.add_argument("--list", action="store_true",
                            help="List all registered workflows and AI apps")
    mode_group.add_argument("--info", metavar="ID",
                            help="Show workflow/AI app node details with LLM guidance")
    mode_group.add_argument("--exec", action="store_true",
                            help="Execute a workflow or AI app (requires --mode + --id + --nodes)")

    # Execution-only args
    p.add_argument("--mode", choices=["workflow", "ai-app"],
                   help="Resource type: workflow or ai-app (required with --exec)")
    p.add_argument("--id",
                   help="Workflow ID or AI app (webapp) ID (required with --exec)")

    # Node overrides
    p.add_argument("--nodes",
                   help="JSON array of node overrides: "
                   '[{"nodeId":"1","fieldName":"prompt","fieldValue":"..."}, ...] (required with --exec)')
    p.add_argument("--nodes-file",
                   help="Path to JSON file containing the node overrides array")

    # Auth
    p.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")

    # Output
    p.add_argument("--output-dir", default="",
                   help="Output directory (default: ./outputs/runner_*)")
    p.add_argument("--no-download", action="store_true",
                   help="Skip downloading outputs (just submit and wait)")

    # Polling / timeout
    p.add_argument("--poll-interval", type=float,
                   default=get_env_float("RUNNINGHUB_POLL_INTERVAL", 3.0),
                   help="Poll interval in seconds (default: 3)")
    p.add_argument("--timeout", type=float,
                   default=get_env_float("RUNNINGHUB_TIMEOUT", 600),
                   help="Timeout in seconds (default: 600)")

    # Dry run
    p.add_argument("--dry-run", action="store_true",
                   help="Parse and validate inputs, print plan, but do not execute")

    return p


# ==================== Discovery commands ====================


def cmd_check(api_key: str) -> int:
    """Check API key validity and account balance."""
    section("Account Status")

    try:
        client = RunningHubClient(api_key=api_key)
        try:
            status = client.get_account_status()
        except Exception:
            # Fallback: try validate_api_key
            valid = client.validate_api_key()
            if not valid:
                print("  API Key: ❌ 无效")
                print("  请在 https://www.runninghub.cn/enterprise-api/sharedApi 创建 API Key")
                return 1
            print("  API Key: ✅ 有效")
            print("  (余额信息不可用，仅验证了 Key 有效性)")
            return 0

        if not status:
            print("  无法获取账户状态（返回为空）")
            return 1

        data = status if isinstance(status, dict) else {}

        # Try to extract info — the exact structure depends on SDK version
        code = data.get("code", 0)
        if code != 0:
            print(f"  API Key: ❌ {data.get('msg', '验证失败')}")
            return 1

        info = data.get("data", data)
        balance = info.get("remainMoney") or info.get("balance")
        currency = info.get("currency", "CNY")
        coins = info.get("remainCoins", "N/A")
        running_tasks = info.get("currentTaskCounts", "N/A")

        print("  API Key:     ✅ 有效")
        if balance is not None:
            print(f"  余额:        ¥{balance} {currency}")
        if coins != "N/A":
            print(f"  算力币:      {coins}")
        if running_tasks != "N/A":
            print(f"  运行中任务:  {running_tasks}")
        return 0

    except Exception as e:
        print(f"  查询失败: {e}", file=sys.stderr)
        return 1


def cmd_list() -> int:
    """List all registered workflows and AI apps from the registry."""
    registry = load_workflows()
    if not registry.get("workflows") and not registry.get("ai_apps"):
        print("Error: registry empty — no payload JSON files found in registry/payloads/", file=sys.stderr)
        return 1

    section("Available Workflows")

    for wf in registry.get("workflows", []):
        nodes_info = f"{len(wf.get('nodes', []))} 个参数"
        verified = "✅" if wf.get("verifiedPayload") else " "
        print(f"  [{wf['outputType']}] {wf['name']}")
        print(f"      ID: {wf['id']} | {nodes_info} | {verified}已验证 | 输出: {wf['outputCount']}")
        print()

    section("Available AI Apps")

    for app in registry.get("ai_apps", []):
        nodes_info = f"{len(app.get('nodes', []))} 个参数"
        verified = "✅" if app.get("verifiedPayload") else " "
        print(f"  [{app['outputType']}] {app['name']}")
        print(f"      ID: {app['id']} | {nodes_info} | {verified}已验证 | 输出: {app['outputCount']}")
        print()

    section("Usage")
    print("  查看详情:  python -m scripts.runner --info <ID>")
    print("  执行调用:  python -m scripts.runner --exec --mode workflow|ai-app --id <ID> --nodes '<JSON>'")
    return 0


def cmd_info(resource_id: str) -> int:
    """Show workflow/AI app details with LLM guidance."""
    registry = load_workflows()
    entry = find_workflow(registry, resource_id)

    if not entry:
        # Try dynamic discovery from SDK
        print(f"资源 '{resource_id}' 不在注册表中，尝试运行时发现...", file=sys.stderr)
        bootstrap_env()
        api_key = resolve_api_key(None)
        try:
            with RunningHubClient(api_key=api_key) as client:
                wf_json = client.get_workflow_json_parsed(resource_id)
                if wf_json:
                    section(f"Workflow {resource_id} — 原始节点信息")
                    print("(来自 SDK 运行时发现，未加工)")
                    print()
                    # Print key info
                    if isinstance(wf_json, dict):
                        node_count = len(wf_json)
                        print(f"  节点总数: {node_count}")
                        print()
                        for nid, ndata in list(wf_json.items())[:20]:
                            class_type = ndata.get("class_type", "?")
                            inputs = ndata.get("inputs", {})
                            input_keys = list(inputs.keys())
                            print(f"  Node {nid}: [{class_type}]")
                            if input_keys:
                                print(f"    可设置字段: {', '.join(input_keys[:6])}")
                            print()
                    return 0
                else:
                    print(f"  无法获取工作流 {resource_id} 的信息", file=sys.stderr)
                    return 1
        except Exception as e:
            print(f"  获取失败: {e}", file=sys.stderr)
            return 1

    verified = find_verified_payload(registry, resource_id)
    _print_resource_info(entry, verified)
    return 0


# ==================== Node loader (for --exec) ====================


def load_nodes(nodes_str: str | None, nodes_file: str | None) -> List[Dict[str, Any]]:
    """Load node overrides from JSON string or file."""
    if nodes_file:
        p = Path(nodes_file).expanduser().resolve()
        if not p.exists():
            raise ValueError(f"Nodes file not found: {p}")
        try:
            with open(p, encoding="utf-8") as f:
                data: List[Dict[str, Any]] = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in nodes file: {e}") from e
    elif nodes_str:
        try:
            data = json.loads(nodes_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in --nodes: {e}") from e
    else:
        raise ValueError("--nodes is required with --exec")

    if not isinstance(data, list):
        raise ValueError("Nodes must be a JSON array")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Nodes[{i}] is not a JSON object")
        required_keys = {"nodeId", "fieldName", "fieldValue"}
        missing = required_keys.difference(item)
        if missing:
            raise ValueError(f"Nodes[{i}] missing keys: {sorted(missing)}")

    return data


# ==================== Execution command ====================


def cmd_exec(args: argparse.Namespace) -> int:
    """Execute a workflow or AI app."""
    if not args.mode:
        print("Error: --mode is required with --exec (workflow or ai-app)", file=sys.stderr)
        return 1
    if not args.id:
        print("Error: --id is required with --exec", file=sys.stderr)
        return 1

    try:
        nodes = load_nodes(args.nodes, args.nodes_file)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    bootstrap_env()
    api_key = resolve_api_key(args.api_key)

    # Check registry for verified payload reference
    registry = load_workflows()
    verified = find_verified_payload(registry, args.id)
    if verified:
        log(f"Found verified payload for {args.id} in registry — {len(verified)} nodes documented")
    else:
        log(f"No verified payload in registry for {args.id} — proceeding with provided nodes")

    # Summary
    summary_nodes = [{"nodeId": n["nodeId"], "fieldName": n["fieldName"],
                      "fieldValue": n["fieldValue"][:80] + "..." if len(n.get("fieldValue", "")) > 80 else n.get("fieldValue", "")}
                     for n in nodes]
    print_request_summary(f"RunningHubClient.{'run' if args.mode == 'workflow' else 'run_ai_app'}",
                          args.id, summary_nodes)
    log(f"  mode:         {args.mode}")
    log(f"  dry-run:      {args.dry_run}")
    log(f"  poll_interval: {args.poll_interval}s")
    log(f"  timeout:      {args.timeout}s")

    upload_count = sum(1 for n in nodes if isinstance(n.get("fieldValue", ""), str)
                       and n["fieldValue"].startswith(UPLOAD_PREFIX))
    if upload_count:
        log(f"  images to upload: {upload_count}")

    if args.dry_run:
        section("Dry Run Complete")
        log("Remove --dry-run to execute.")
        return 0

    from runninghub_cli import service as _service

    target_type = "ai-app" if args.mode == "ai-app" else "workflow"
    try:
        if args.no_download:
            # submit only — uses service.submit() for upload+modifier handling
            result = _service.submit(
                args.id, target_type, nodes,
                api_key=api_key,
            )
            log(f"Task submitted: {result['task_id']} (status: {result['task_status']})")
            log("Skipping download (--no-download)")
        else:
            result = _service.run(
                args.id, target_type, nodes,
                api_key=api_key,
                output_dir=args.output_dir or None,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
            )
            files = result.get("output_files", [])
            if files:
                section("Outputs")
                for f in files:
                    size_str = f"{f['size_mb']:.1f} MB" if f['size_mb'] >= 1 else f"{f['size_bytes']/1024:.0f} KB"
                    log(f"  {f['name']} ({size_str})")
    except _service.ValidationError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 1

    section("Done")
    return 0


# ==================== Main ====================


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Route to appropriate command
    if args.check:
        bootstrap_env()
        api_key = resolve_api_key(args.api_key)
        return cmd_check(api_key)

    if args.list:
        return cmd_list()

    if args.info:
        return cmd_info(args.info)

    if args.exec:
        return cmd_exec(args)

    # No mode flag given — show help
    parser.print_help()
    print("\n使用 --exec 执行任务，或 --check/--list/--info 进行发现", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
