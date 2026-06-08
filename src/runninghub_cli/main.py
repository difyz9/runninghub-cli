"""RunningHub command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from . import service

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
        help="JSON array, or path to a JSON file containing node_overrides",
    ),
    instance_type: str = typer.Option("default", "--instance-type", help="RunningHub instance type"),
    use_personal_queue: bool = typer.Option(False, "--personal-queue", help="Use personal queue for workflows"),
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
        help="JSON array, or path to a JSON file containing node_overrides",
    ),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Directory for downloaded outputs"),
    poll_interval: float = typer.Option(15, "--poll-interval", help="Polling interval in seconds"),
    timeout: float = typer.Option(1800, "--timeout", help="Timeout in seconds"),
    instance_type: str = typer.Option("default", "--instance-type", help="RunningHub instance type"),
    use_personal_queue: bool = typer.Option(False, "--personal-queue", help="Use personal queue for workflows"),
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
        )
        emit({"data": data})
    except Exception as exc:
        fail(exc)


if __name__ == "__main__":
    app()
