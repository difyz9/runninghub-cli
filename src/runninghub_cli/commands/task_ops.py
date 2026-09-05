"""Task-oriented command registrations for RunningHub CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from runninghub_cli import service


def register_task_commands(
    app: typer.Typer,
    *,
    emit: Callable[[dict[str, Any], bool], None],
    fail: Callable[[Exception], None],
    common_api_key_option: Callable[[], Any],
    common_env_file_option: Callable[[], Any],
    build_cli_overrides: Callable[[str | None, list[str], list[str]], list[dict[str, Any]]],
) -> None:
    """Register submit/run/status/task-detail/wait-download/upload commands."""

    @app.command()
    def submit(
        identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
        type: str = typer.Option("workflow", "--type", "-t", help="workflow | webapp | ai-app"),
        node_overrides: str | None = typer.Option(
            None,
            "--node-overrides",
            "-n",
            help="JSON array, or path to a JSON file containing node_overrides; fieldValue supports @upload:PATH",
        ),
        node: list[str] = typer.Option([], "--node", help="设置节点值: nodeId:fieldName=value，可重复"),
        file: list[str] = typer.Option([], "--file", help="上传文件并设置节点: nodeId:fieldName=path，可重复"),
        instance_type: str = typer.Option("default", "--instance-type", help="RunningHub instance type"),
        use_personal_queue: bool = typer.Option(False, "--personal-queue", help="Use personal queue for workflows"),
        access_password: str | None = typer.Option(None, "--access-password", help="Access password for encrypted AI Apps/webapps"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Submit a task and return immediately with task_id."""
        try:
            overrides = build_cli_overrides(node_overrides, node, file)
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
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Query task status."""
        try:
            emit({"data": service.status(task_id, api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)

    @app.command("task-detail")
    def task_detail_cmd(
        task_id: str = typer.Argument(..., help="RunningHub task_id"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
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
        output_dir: Path | None = typer.Option(None, "--output-dir", help="Directory for downloaded outputs"),
        poll_interval: float = typer.Option(15, "--poll-interval", help="Polling interval in seconds"),
        timeout: float = typer.Option(1800, "--timeout", help="Timeout in seconds"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
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
        node_overrides: str | None = typer.Option(
            None,
            "--node-overrides",
            "-n",
            help="JSON array, or path to a JSON file containing node_overrides; fieldValue supports @upload:PATH",
        ),
        node: list[str] = typer.Option([], "--node", help="设置节点值: nodeId:fieldName=value，可重复"),
        file: list[str] = typer.Option([], "--file", help="上传文件并设置节点: nodeId:fieldName=path，可重复"),
        output_dir: Path | None = typer.Option(None, "--output-dir", help="Directory for downloaded outputs"),
        poll_interval: float = typer.Option(15, "--poll-interval", help="Polling interval in seconds"),
        timeout: float = typer.Option(1800, "--timeout", help="Timeout in seconds"),
        instance_type: str = typer.Option("default", "--instance-type", help="RunningHub instance type"),
        use_personal_queue: bool = typer.Option(False, "--personal-queue", help="Use personal queue for workflows"),
        access_password: str | None = typer.Option(None, "--access-password", help="Access password for encrypted AI Apps/webapps"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Submit, wait, and download outputs in one command."""
        try:
            overrides = build_cli_overrides(node_overrides, node, file)
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
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Upload a local file to RunningHub media storage."""
        try:
            emit({"data": service.upload(file, kind=kind, api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)
