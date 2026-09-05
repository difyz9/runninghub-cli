"""Auth cache and login helpers for RunningHub CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient

# 本地认证缓存 — login 命令保存 token，供 history/call-log 等用户级命令使用
AUTH_FILE = Path.home() / ".runninghub" / "auth.json"


def _auth_path() -> Path:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    return AUTH_FILE


def _save_auth(token: dict[str, Any]) -> None:
    """保存登录凭证到本地文件。"""
    path = _auth_path()
    path.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_auth() -> dict[str, Any] | None:
    """从本地文件加载登录凭证。"""
    path = _auth_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _clear_auth() -> None:
    """清除本地登录凭证。"""
    path = _auth_path()
    if path.exists():
        path.unlink()


def login(
    username: str,
    password: str,
    env_file: str | Path | None = None,
) -> dict[str, Any]:
    """使用手机号+密码登录并保存凭证到本地。"""
    del env_file  # kept for API compatibility

    import httpx
    from runninghub_sdk import RunningHubClient

    token = RunningHubClient.login(username, password)

    # 尝试获取真实的数据库 user_id（JWT identify 是加密版本）
    real_user_id = token.identify
    try:
        resp = httpx.post(
            f"{RunningHubClient.BASE_URL}/api/output/v2/history",
            json={"size": 1, "current": 1, "has_output": True, "from_id": "", "task_name": "", "reload_data": False},
            headers={"Authorization": f"Bearer {token.access_token}", "Content-Type": "application/json"},
            timeout=10,
        )
        body = resp.json()
        records = body.get("data") if isinstance(body.get("data"), list) else []
        if records and isinstance(records[0], dict) and records[0].get("userId"):
            real_user_id = str(records[0]["userId"])
    except Exception:
        pass

    auth_data = {
        "access_token": token.access_token,
        "refresh_token": getattr(token, "refresh_token", ""),
        "user_id": real_user_id,
        "expire_in": getattr(token, "expire_in", 0),
        "username": username,
    }
    _save_auth(auth_data)

    return {
        "user_id": real_user_id,
        "expire_in": auth_data["expire_in"],
        "message": "登录成功，凭证已保存到本地",
    }


def logout() -> dict[str, Any]:
    """清除本地登录凭证。"""
    auth = _load_auth()
    username = (auth or {}).get("username", "")
    _clear_auth()
    return {"message": f"已退出登录{' (' + username + ')' if username else ''}"}


def _resolve_auth() -> dict[str, Any] | None:
    """获取缓存的认证信息（如有）。"""
    return _load_auth()


def _resolve_bearer(client: RunningHubClient) -> str | None:
    """获取用户级 Bearer token。"""
    # 1. 优先使用本地缓存的 token
    auth = _load_auth()
    if auth and auth.get("access_token"):
        return auth["access_token"]

    # 2. 尝试通过 API key 获取
    try:
        access = client.get_access_token()
        return access.access_key
    except Exception:
        return None
