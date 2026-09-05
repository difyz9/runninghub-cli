"""Account/auth/history command registrations for RunningHub CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from runninghub_cli import service


def register_account_commands(
    app: typer.Typer,
    *,
    emit: Callable[[dict[str, Any], bool], None],
    fail: Callable[[Exception], None],
    common_api_key_option: Callable[[], Any],
    common_env_file_option: Callable[[], Any],
) -> None:
    """Register self-update/login/logout/account/queue/history/call-log commands."""

    @app.command("self-update")
    def self_update_cmd(
        repo_dir: Path | None = typer.Option(None, "--repo-dir", help="runninghub-cli git checkout; defaults to this install"),
        repo_url: str = typer.Option(service.DEFAULT_REPO_URL, "--repo-url", help="GitHub repository URL used for tag discovery"),
        tag: str | None = typer.Option(None, "--tag", help="Specific tag to install; defaults to latest remote tag"),
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

    @app.command("login")
    def login_cmd(
        username: str = typer.Option(..., "--username", "-u", prompt=True, help="手机号"),
        password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="密码"),
        env_file: Path | None = common_env_file_option(),
    ):
        """使用手机号和密码登录 RunningHub，凭证自动保存到本地。"""
        try:
            emit({"data": service.login(username, password, env_file=env_file)})
        except Exception as exc:
            fail(exc)

    @app.command("logout")
    def logout_cmd():
        """清除本地保存的登录凭证。"""
        try:
            emit({"data": service.logout()})
        except Exception as exc:
            fail(exc)

    @app.command("account")
    def account_cmd(
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """查询账户状态（剩余额度、当前任务数）。"""
        try:
            emit({"data": service.get_account_status(api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)

    @app.command("queue-status")
    def queue_status_cmd(
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """查询队列状态（运行中/排队中的任务数）。"""
        try:
            emit({"data": service.get_queue_status(api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)

    @app.command("history")
    def history_cmd(
        status: str | None = typer.Option(None, "--status", "-s", help="过滤状态: SUCCESS,FAILED,RUNNING,QUEUED（逗号分隔）"),
        task_type: str | None = typer.Option(None, "--task-type", "-t", help="过滤任务类型: workflow,webapp,model_api（逗号分隔）"),
        size: int = typer.Option(20, "--size", "-n", help="每页条数"),
        page: int = typer.Option(1, "--page", "-p", help="页码"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """查询任务历史记录。"""
        try:
            emit(
                {
                    "data": service.get_task_history(
                        status=status,
                        task_type=task_type,
                        size=size,
                        page=page,
                        api_key=api_key,
                        env_file=env_file,
                    )
                }
            )
        except Exception as exc:
            fail(exc)

    @app.command("call-log")
    def call_log_cmd(
        task_id: str = typer.Argument(..., help="任务 ID"),
        user_id: str | None = typer.Option(None, "--user-id", "-u", help="用户 ID（不传则尝试从 access_token 自动提取）"),
        api_key: str | None = common_api_key_option(),
        env_file: Path | None = common_env_file_option(),
    ):
        """获取任务调用日志详情（请求参数、响应、费用等）。"""
        try:
            emit({"data": service.get_call_log_detail(task_id, user_id=user_id, api_key=api_key, env_file=env_file)})
        except Exception as exc:
            fail(exc)
