"""RunningHub command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from . import __version__
from . import service
from . import discover as discover_mod

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


def common_api_key_option() -> Optional[str]:
    return typer.Option(None, "--api-key", help="RunningHub API Key; defaults to RUNNINGHUB_API_KEY")


def common_env_file_option() -> Optional[Path]:
    return typer.Option(None, "--env-file", help="Optional .env file to load before reading environment")


@app.callback()
def callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit", is_eager=True),
):
    if version:
        emit({"version": __version__})
        raise typer.Exit()


@app.command()
def doctor(
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Check SDK, API key, and RunningHub queue availability."""
    try:
        emit({"data": service.doctor(api_key=api_key, env_file=env_file)})
    except Exception as exc:
        fail(exc)


@app.command()
def detect(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Detect whether an ID is a workflow or AI App."""
    try:
        emit({"data": service.detect(identifier, api_key=api_key, env_file=env_file)})
    except Exception as exc:
        fail(exc)


@app.command("inspect")
def inspect_cmd(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    type: str = typer.Option("workflow", "--type", "-t", help="workflow | webapp | ai-app"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Inspect workflow or AI App structure."""
    try:
        emit({"data": service.inspect_target(identifier, type, api_key=api_key, env_file=env_file)})
    except Exception as exc:
        fail(exc)


@app.command()
def submit(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    type: str = typer.Option("workflow", "--type", "-t", help="workflow | webapp | ai-app"),
    node_overrides: Optional[str] = typer.Option(
        None,
        "--node-overrides",
        "-n",
        help="JSON array, or path to a JSON file containing node_overrides; fieldValue supports @upload:PATH",
    ),
    instance_type: str = typer.Option("default", "--instance-type", help="RunningHub instance type"),
    use_personal_queue: bool = typer.Option(False, "--personal-queue", help="Use personal queue for workflows"),
    access_password: Optional[str] = typer.Option(None, "--access-password", help="Access password for encrypted AI Apps/webapps"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Submit a task and return immediately with task_id."""
    try:
        overrides = service.parse_overrides(node_overrides)
        data = service.submit(
            identifier,
            type,
            overrides,
            api_key=api_key,
            env_file=env_file,
            instance_type=instance_type,
            use_personal_queue=use_personal_queue,
            access_password=access_password,
        )
        emit({"data": data})
    except Exception as exc:
        fail(exc)


@app.command()
def status(
    task_id: str = typer.Argument(..., help="RunningHub task_id"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Query task status."""
    try:
        emit({"data": service.status(task_id, api_key=api_key, env_file=env_file)})
    except Exception as exc:
        fail(exc)


@app.command("task-detail")
def task_detail_cmd(
    task_id: str = typer.Argument(..., help="RunningHub task_id"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Query task status, outputs, and webhook detail for failure analysis."""
    try:
        emit({"data": service.task_detail(task_id, api_key=api_key, env_file=env_file)})
    except Exception as exc:
        fail(exc)


@app.command("wait-download")
def wait_download_cmd(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    task_id: str = typer.Argument(..., help="RunningHub task_id"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Directory for downloaded outputs"),
    poll_interval: float = typer.Option(15, "--poll-interval", help="Polling interval in seconds"),
    timeout: float = typer.Option(1800, "--timeout", help="Timeout in seconds"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Wait for task completion and download outputs."""
    try:
        data = service.wait_download(
            identifier,
            task_id,
            api_key=api_key,
            env_file=env_file,
            output_dir=output_dir,
            poll_interval=poll_interval,
            timeout=timeout,
        )
        emit({"data": data})
    except Exception as exc:
        fail(exc)


@app.command("run")
def run_cmd(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    type: str = typer.Option("workflow", "--type", "-t", help="workflow | webapp | ai-app"),
    node_overrides: Optional[str] = typer.Option(
        None,
        "--node-overrides",
        "-n",
        help="JSON array, or path to a JSON file containing node_overrides; fieldValue supports @upload:PATH",
    ),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Directory for downloaded outputs"),
    poll_interval: float = typer.Option(15, "--poll-interval", help="Polling interval in seconds"),
    timeout: float = typer.Option(1800, "--timeout", help="Timeout in seconds"),
    instance_type: str = typer.Option("default", "--instance-type", help="RunningHub instance type"),
    use_personal_queue: bool = typer.Option(False, "--personal-queue", help="Use personal queue for workflows"),
    access_password: Optional[str] = typer.Option(None, "--access-password", help="Access password for encrypted AI Apps/webapps"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Submit, wait, and download outputs in one command."""
    try:
        overrides = service.parse_overrides(node_overrides)
        data = service.run(
            identifier,
            type,
            overrides,
            api_key=api_key,
            env_file=env_file,
            output_dir=output_dir,
            poll_interval=poll_interval,
            timeout=timeout,
            instance_type=instance_type,
            use_personal_queue=use_personal_queue,
            access_password=access_password,
        )
        emit({"data": data})
    except Exception as exc:
        fail(exc)


@app.command()
def upload(
    file: Path = typer.Argument(..., help="Local image/video/audio/file path to upload"),
    kind: str = typer.Option("file", "--kind", "-k", help="image | video | audio | file"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Upload a local file to RunningHub media storage."""
    try:
        emit({"data": service.upload(file, kind=kind, api_key=api_key, env_file=env_file)})
    except Exception as exc:
        fail(exc)


@app.command("self-update")
def self_update_cmd(
    repo_dir: Optional[Path] = typer.Option(None, "--repo-dir", help="runninghub-cli git checkout; defaults to this install"),
    repo_url: str = typer.Option(service.DEFAULT_REPO_URL, "--repo-url", help="GitHub repository URL used for tag discovery"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Specific tag to install; defaults to latest remote tag"),
    remote: str = typer.Option("origin", "--remote", help="Git remote name to fetch tags from"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show target tag without changing files"),
):
    """Update this git checkout to the latest GitHub tag and reinstall editable CLI."""
    try:
        data = service.self_update(
            repo_dir=repo_dir,
            repo_url=repo_url,
            tag=tag,
            remote=remote,
            dry_run=dry_run,
        )
        emit({"data": data})
    except Exception as exc:
        fail(exc)


if __name__ == "__main__":
    app()


# ── Discover command group ──────────────────────────────────

discover_app = typer.Typer(
    name="discover",
    help="Search, test, and export RunningHub workflows and AI Apps as Hermes skills.",
    no_args_is_help=True,
)


@discover_app.command("search")
def discover_search(
    keyword: str = typer.Option("", "--keyword", "-k", help="Search keyword"),
    type_filter: str = typer.Option("workflow", "--type", "-t", help="workflow | webapp | both"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    size: int = typer.Option(20, "--size", "-s", help="Results per page"),
    sort: str = typer.Option("RECOMMEND", "--sort", help="RECOMMEND | NEWEST | POPULAR"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Search RunningHub marketplace for workflows and AI Apps."""
    from .discover import search_portal, search_webapps

    try:
        client = service.create_client(api_key, env_file)
        results: dict[str, Any] = {}

        if type_filter in ("workflow", "both"):
            results["workflows"] = search_portal(client, keyword=keyword, page=page, size=size, sort=sort)
        if type_filter in ("webapp", "both"):
            results["webapps"] = search_webapps(client, keyword=keyword, page=page, size=size, sort=sort)

        emit({"data": results})
    except Exception as exc:
        fail(exc)


@discover_app.command("inspect")
def discover_inspect(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Inspect a workflow or AI App from the marketplace."""
    from .discover import inspect_item

    try:
        client = service.create_client(api_key, env_file)
        result = inspect_item(client, identifier)
        emit({"data": result})
    except Exception as exc:
        fail(exc)


@discover_app.command("test")
def discover_test(
    identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
    type_filter: str = typer.Option("auto", "--type", "-t", help="workflow | webapp | auto"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Test prompt text"),
    timeout: float = typer.Option(300, "--timeout", help="Max wait seconds"),
    poll_interval: float = typer.Option(5, "--poll-interval", help="Poll interval"),
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Auto-test a workflow: inspect → generate inputs → submit → wait → verify."""
    from .discover import test_run, inspect_item, smart_generate_test_input

    try:
        client = service.create_client(api_key, env_file)

        # Auto-detect type
        actual_type = type_filter
        if actual_type == "auto":
            info = inspect_item(client, identifier)
            actual_type = info.get("type", "workflow")
            emit({"phase": "detect", "type": actual_type})

        # Build test inputs
        info = inspect_item(client, identifier)
        overrides = smart_generate_test_input(info, prompt)
        emit({"phase": "generate", "overrides": overrides})

        # Run test
        result = test_run(
            client, identifier,
            item_type=actual_type,
            overrides=overrides,
            timeout=timeout,
            poll_interval=poll_interval,
            user_prompt=prompt,
        )
        emit({"phase": "result", "test": result})

    except Exception as exc:
        fail(exc)


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
    api_key: Optional[str] = common_api_key_option(),
    env_file: Optional[Path] = common_env_file_option(),
):
    """Test and export a workflow/AI App as a Hermes SKILL.md file."""
    from .discover import (
        generate_skill_md,
        inspect_item,
        smart_generate_test_input,
        test_run,
    )

    try:
        client = service.create_client(api_key, env_file)

        # Auto-detect type
        actual_type = type_filter
        if actual_type == "auto":
            info = inspect_item(client, identifier)
            actual_type = info.get("type", "workflow")

        # Inspect to get info
        info = inspect_item(client, identifier)

        item_name = name or info.get("name", identifier)
        item_desc = description or info.get("description", "")

        verified_overrides: list[dict[str, Any]] = []

        if not skip_test:
            emit({"phase": "test", "message": f"Testing {identifier} ({actual_type})..."})
            overrides = smart_generate_test_input(info, prompt)
            emit({"phase": "test_overrides", "overrides": overrides})

            result = test_run(
                client, identifier,
                item_type=actual_type,
                overrides=overrides,
                timeout=timeout,
            )
            if result.get("ok"):
                verified_overrides = overrides
                emit({"phase": "test_result", "test": result})
            else:
                emit({"phase": "test_failed", "error": result.get("error")})
                # Still export, but mark as untested
                item_desc = (item_desc + " [⚠️ untested]").strip()

        # Generate SKILL.md
        filepath = generate_skill_md(
            identifier,
            item_type=actual_type,
            name=item_name,
            description=item_desc,
            verified_overrides=verified_overrides,
            output_dir=str(output_dir),
        )

        emit({
            "phase": "exported",
            "path": str(filepath),
            "tested": bool(verified_overrides),
        })

    except Exception as exc:
        fail(exc)


app.add_typer(discover_app)

