"""Core diagnostic/discovery command registrations for RunningHub CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from runninghub_cli import service


def register_core_commands(
    app: typer.Typer,
    *,
    emit: Callable[[dict[str, Any], bool], None],
    fail: Callable[[Exception], None],
    common_api_key_option: Callable[[], Any],
    common_env_file_option: Callable[[], Any],
) -> None:
    """Register doctor/detect/inspect commands."""

    @app.command()
    def doctor(
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Check SDK, API key, and RunningHub queue availability."""
        try:
            emit({"data": service.doctor(api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)

    @app.command()
    def detect(
        identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Detect whether an ID is a workflow or AI App."""
        try:
            emit({"data": service.detect(identifier, api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)

    @app.command("inspect")
    def inspect_cmd(
        identifier: str = typer.Argument(..., help="RunningHub workflow ID or AI App ID"),
        type: str = typer.Option("auto", "--type", "-t", help="auto | workflow | webapp | ai-app"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="显示完整节点信息（含内部管道节点）"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """Inspect workflow or AI App structure."""
        try:
            emit({"data": service.inspect_target(identifier, type, verbose=verbose, api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)
