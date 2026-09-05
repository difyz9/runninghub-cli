"""Discover command group — search, test, and export RunningHub workflows/AI Apps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from runninghub_cli import service

discover_app = typer.Typer(
    name="discover",
    help="Search, test, and export RunningHub workflows and AI Apps as Hermes skills.",
    no_args_is_help=True,
)


def _emit(data: dict, ok: bool = True) -> None:
    payload = {"ok": ok, **data}
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def _fail(exc: Exception) -> None:
    _emit(service.error_payload(exc), ok=False)
    raise typer.Exit(1)


@discover_app.command("search")
def discover_search(
    keyword: str = typer.Option("", "--keyword", "-k", help="搜索关键词"),
    type_filter: str = typer.Option("workflow", "--type", "-t", help="workflow | webapp | both"),
    page: int = typer.Option(1, "--page", "-p", help="页码"),
    size: int = typer.Option(20, "--size", "-s", help="每页条数"),
    sort: str = typer.Option("RECOMMEND", "--sort", help="RECOMMEND | NEWEST | POPULAR"),
    output_format: str = typer.Option("table", "--format", "-f", help="table | json"),
    api_key: str | None = typer.Option(None, "--api-key", help="RunningHub API Key; defaults to RUNNINGHUB_API_KEY"),
    env_file: Path | None = typer.Option(None, "--env-file", help="Optional .env file to load before reading environment"),
):
    """搜索 RunningHub 市集中的工作流和 AI App。"""
    from runninghub_cli.discover import search_portal, search_webapps

    try:
        client = service.create_client(api_key, env_file)
        results: dict[str, Any] = {}

        if type_filter in ("workflow", "both"):
            results["workflows"] = search_portal(client, keyword=keyword, page=page, size=size, sort=sort)
        if type_filter in ("webapp", "both"):
            results["webapps"] = search_webapps(client, keyword=keyword, page=page, size=size, sort=sort)

        if output_format == "json":
            _emit({"data": results})
            return

        # ── Table format ────────────────────────────────────────
        def fmt_number(n: Any) -> str:
            try:
                v = int(str(n))
                if v >= 10000:
                    return f"{v/10000:.1f}w"
                return str(v)
            except (ValueError, TypeError):
                return "0"

        def fmt_time(ts: str) -> str:
            if ts and len(ts) >= 10:
                return ts[:10]
            return ""

        def print_table(records: list[dict], label: str, id_field: str = "id"):
            if not records:
                return
            print(f"\n{'='*100}")
            print(f"  {label}  (共 {len(records)} 条)")
            print(f"{'='*100}")

            print(f"  {'ID':<22} {'名称':<32} {'使用':<8} {'收藏':<6} {'发布':<12} {'作者':<16}")
            print(f"  {'─'*22} {'─'*32} {'─'*8} {'─'*6} {'─'*12} {'─'*16}")

            for r in records:
                rid = str(r.get(id_field, ""))
                name = (r.get("name") or "")[:30]
                stats = r.get("statisticsInfo") or {}
                use_cnt = fmt_number(stats.get("useCount", 0))
                fav_cnt = fmt_number(stats.get("collectCount", 0))
                pub = fmt_time(r.get("publishTime") or r.get("publish_time", ""))
                owner = r.get("owner") or {}
                author = (owner.get("name") or "")[:14]
                link = f"https://www.runninghub.cn/workflow/{rid}" if id_field == "id" else ""

                print(f"  {rid:<22} {name:<32} {use_cnt:<8} {fav_cnt:<6} {pub:<12} {author:<16}")
                desc = (r.get("desc") or "")[:90]
                if desc:
                    print(f"  {'':22} 📝 {desc}")
                tags_list = [t.get("name", "") for t in (r.get("tags") or [])]
                if tags_list:
                    tags_str = "  ".join(tags_list[:4])
                    print(f"  {'':22} 🏷️  {tags_str}")
                if link:
                    print(f"  {'':22} 🔗 {link}")
                print()

        wf_records = (results.get("workflows") or {}).get("records") or []
        if type_filter in ("workflow", "both") and wf_records:
            total = (results.get("workflows") or {}).get("total", 0)
            print_table(wf_records, f"📦 工作流 (Workflows) — 共 {total} 条匹配")

        wa_records = (results.get("webapps") or {}).get("records") or []
        if type_filter in ("webapp", "both") and wa_records:
            total = (results.get("webapps") or {}).get("total", 0)
            print(f"\n{'='*100}")
            print(f"  🧩 AI 应用 (Webapps) — 共 {total} 条匹配")
            print(f"{'='*100}")
            for r in wa_records:
                rid = str(r.get("id", ""))
                name = (r.get("name") or "")[:40]
                desc = (r.get("desc") or "")[:80]
                print(f"\n  🆔 {rid}")
                print(f"  📛 {name}")
                if desc:
                    print(f"  📝 {desc}")

        if not wf_records and not wa_records:
            print("⚠️  没有找到匹配的结果")
        print()

    except Exception as exc:
        _fail(exc)


@discover_app.command("inspect")
def discover_inspect(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    api_key: str | None = typer.Option(None, "--api-key", help="RunningHub API Key; defaults to RUNNINGHUB_API_KEY"),
    env_file: Path | None = typer.Option(None, "--env-file", help="Optional .env file to load before reading environment"),
):
    """Inspect a workflow or AI App from the marketplace."""
    from runninghub_cli.discover import inspect_item

    try:
        client = service.create_client(api_key, env_file)
        result = inspect_item(client, identifier)
        _emit({"data": result})
    except Exception as exc:
        _fail(exc)


@discover_app.command("test")
def discover_test(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    type_filter: str = typer.Option("auto", "--type", "-t", help="workflow | webapp | auto"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Test prompt text"),
    timeout: float = typer.Option(300, "--timeout", help="Max wait seconds"),
    poll_interval: float = typer.Option(5, "--poll-interval", help="Poll interval"),
    api_key: str | None = typer.Option(None, "--api-key", help="RunningHub API Key; defaults to RUNNINGHUB_API_KEY"),
    env_file: Path | None = typer.Option(None, "--env-file", help="Optional .env file to load before reading environment"),
):
    """Auto-test a workflow: inspect → generate inputs → submit → wait → verify."""
    from runninghub_cli.discover import inspect_item, smart_generate_test_input, test_run

    try:
        client = service.create_client(api_key, env_file)

        actual_type = type_filter
        if actual_type == "auto":
            info = inspect_item(client, identifier)
            actual_type = info.get("type", "workflow")
            _emit({"phase": "detect", "type": actual_type})

        info = inspect_item(client, identifier)
        overrides = smart_generate_test_input(info, prompt)
        _emit({"phase": "generate", "overrides": overrides})

        result = test_run(
            client, identifier,
            item_type=actual_type,
            overrides=overrides,
            timeout=timeout,
            poll_interval=poll_interval,
            user_prompt=prompt,
        )
        _emit({"phase": "result", "test": result})

    except Exception as exc:
        _fail(exc)


@discover_app.command("export")
def discover_export(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    type_filter: str = typer.Option("auto", "--type", "-t", help="workflow | webapp | auto"),
    name: str = typer.Option("", "--name", "-n", help="Skill name (default: auto)"),
    description: str = typer.Option("", "--description", "-d", help="Skill description"),
    output_dir: Path = typer.Option("./exported-skills", "--output-dir", "-o", help="Output directory"),
    skip_test: bool = typer.Option(False, "--no-test", help="Skip test run before export"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Test prompt when --no-test is not set"),
    timeout: float = typer.Option(300, "--timeout", help="Test timeout seconds"),
    api_key: str | None = typer.Option(None, "--api-key", help="RunningHub API Key; defaults to RUNNINGHUB_API_KEY"),
    env_file: Path | None = typer.Option(None, "--env-file", help="Optional .env file to load before reading environment"),
):
    """Test and export a workflow/AI App as a Hermes SKILL.md file."""
    from runninghub_cli.discover import (
        generate_skill_md,
        inspect_item,
        smart_generate_test_input,
        test_run,
    )

    try:
        client = service.create_client(api_key, env_file)

        actual_type = type_filter
        if actual_type == "auto":
            info = inspect_item(client, identifier)
            actual_type = info.get("type", "workflow")

        info = inspect_item(client, identifier)

        item_name = name or info.get("name", identifier)
        item_desc = description or info.get("description", "")

        verified_overrides: list[dict[str, Any]] = []

        if not skip_test:
            _emit({"phase": "test", "message": f"Testing {identifier} ({actual_type})..."})
            overrides = smart_generate_test_input(info, prompt)
            _emit({"phase": "test_overrides", "overrides": overrides})

            result = test_run(
                client, identifier,
                item_type=actual_type,
                overrides=overrides,
                timeout=timeout,
            )
            if result.get("ok"):
                verified_overrides = overrides
                _emit({"phase": "test_result", "test": result})
            else:
                _emit({"phase": "test_failed", "error": result.get("error")})
                item_desc = (item_desc + " [⚠️ untested]").strip()

        filepath = generate_skill_md(
            identifier,
            item_type=actual_type,
            name=item_name,
            description=item_desc,
            verified_overrides=verified_overrides,
            output_dir=str(output_dir),
        )

        _emit({
            "phase": "exported",
            "path": str(filepath),
            "tested": bool(verified_overrides),
        })

    except Exception as exc:
        _fail(exc)
