"""Execution-oriented operations for RunningHub CLI service facade."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient
from runninghub_sdk.exceptions import TaskError, TimeoutError


def submit(
    identifier: str,
    type_: str,
    overrides: list[dict[str, Any]] | None,
    *,
    api_key: str | None,
    env_file: str | Path | None,
    instance_type: str,
    use_personal_queue: bool,
    access_password: str | None,
    create_client_fn: Callable[..., RunningHubClient],
    normalize_type_fn: Callable[[str], str],
    process_upload_overrides_fn: Callable[[RunningHubClient, Any], tuple[list[dict[str, Any]], list[dict[str, str]]]],
    build_modifier_fn: Callable[[Any], Any],
) -> dict[str, Any]:
    target_type = normalize_type_fn(type_)
    node_overrides = overrides or []

    with create_client_fn(api_key, env_file) as client:
        node_overrides, uploads = process_upload_overrides_fn(client, node_overrides)
        modifier = build_modifier_fn(node_overrides)

        if target_type == "webapp":
            ai_app_options: dict[str, Any] = {"instance_type": instance_type}
            if access_password:
                ai_app_options["access_password"] = access_password
            task = client.run_ai_app_with_modifier(
                webapp_id=identifier,
                modifier=modifier,
                **ai_app_options,
            )
        else:
            task = client.run_with_modifier(
                workflow_id=identifier,
                modifier=modifier,
                add_metadata=True,
                instance_type=instance_type,
                use_personal_queue=use_personal_queue,
            )

    return {
        "id": identifier,
        "type": target_type,
        "task_id": task.task_id,
        "task_status": task.task_status.value,
        "client_id": task.client_id,
        "prompt_tips": task.prompt_tips,
        "node_overrides": node_overrides,
        "uploads": uploads,
        "access_password_used": bool(access_password) if target_type == "webapp" else False,
    }


def status(
    task_id: str,
    *,
    api_key: str | None,
    env_file: str | Path | None,
    create_client_fn: Callable[..., RunningHubClient],
) -> dict[str, Any]:
    with create_client_fn(api_key, env_file) as client:
        task_status = client.get_status(task_id)
    return {"task_id": task_id, "status": task_status.value}


def task_detail_with_client(
    client: RunningHubClient,
    task_id: str,
    *,
    to_plain_fn: Callable[[Any], Any],
) -> dict[str, Any]:
    detail: dict[str, Any] = {"task_id": task_id, "detail_errors": {}}

    try:
        query_v2_result = to_plain_fn(client.query_v2(task_id))
        detail["query_v2"] = query_v2_result
        if isinstance(query_v2_result, dict):
            detail["status"] = query_v2_result.get("status")
            detail["error_code"] = query_v2_result.get("error_code")
            detail["error_message"] = query_v2_result.get("error_message")
            detail["failed_reason"] = query_v2_result.get("failed_reason")
    except Exception as exc:
        detail["detail_errors"]["query_v2"] = str(exc)

    try:
        detail.setdefault("status", to_plain_fn(client.get_status(task_id)))
    except Exception as exc:
        detail["detail_errors"]["status"] = str(exc)

    try:
        detail["outputs"] = to_plain_fn(client.get_outputs(task_id))
    except Exception as exc:
        detail["detail_errors"]["outputs"] = str(exc)

    try:
        detail["webhook_detail"] = to_plain_fn(client.get_webhook_detail(task_id))
    except Exception as exc:
        detail["detail_errors"]["webhook_detail"] = str(exc)

    if not detail["detail_errors"]:
        detail.pop("detail_errors")
    return detail


def task_detail(
    task_id: str,
    *,
    api_key: str | None,
    env_file: str | Path | None,
    create_client_fn: Callable[..., RunningHubClient],
    task_detail_with_client_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    with create_client_fn(api_key, env_file) as client:
        return task_detail_with_client_fn(client, task_id)


def wait_download(
    identifier: str,
    task_id: str,
    *,
    api_key: str | None,
    env_file: str | Path | None,
    output_dir: str | Path | None,
    poll_interval: float,
    timeout: float,
    default_output_root: Path,
    create_client_fn: Callable[..., RunningHubClient],
    task_detail_with_client_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    out_dir = Path(output_dir) if output_dir else default_output_root / identifier / task_id
    with create_client_fn(api_key, env_file) as client:
        try:
            outputs = client.wait_for_completion(
                task_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        except (TaskError, TimeoutError) as exc:
            exc.task_detail = task_detail_with_client_fn(client, task_id)
            raise
        paths = client.download_outputs(outputs, out_dir)

    files = [
        {
            "path": str(path),
            "name": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        }
        for path in paths
    ]
    return {
        "id": identifier,
        "task_id": task_id,
        "status": "SUCCESS",
        "output_dir": str(out_dir),
        "output_count": len(files),
        "output_files": files,
    }


def run(
    identifier: str,
    type_: str,
    overrides: list[dict[str, Any]] | None,
    *,
    api_key: str | None,
    env_file: str | Path | None,
    output_dir: str | Path | None,
    poll_interval: float,
    timeout: float,
    instance_type: str,
    use_personal_queue: bool,
    access_password: str | None,
    submit_fn: Callable[..., dict[str, Any]],
    wait_download_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    submitted = submit_fn(
        identifier,
        type_,
        overrides,
        api_key=api_key,
        env_file=env_file,
        instance_type=instance_type,
        use_personal_queue=use_personal_queue,
        access_password=access_password,
    )
    downloaded = wait_download_fn(
        identifier,
        submitted["task_id"],
        api_key=api_key,
        env_file=env_file,
        output_dir=output_dir,
        poll_interval=poll_interval,
        timeout=timeout,
    )
    return {**submitted, **downloaded}


def upload(
    file_path: str | Path,
    *,
    kind: str,
    api_key: str | None,
    env_file: str | Path | None,
    create_client_fn: Callable[..., RunningHubClient],
) -> dict[str, Any]:
    path = Path(file_path).expanduser()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")

    upload_kind = (kind or "file").strip().lower()
    with create_client_fn(api_key, env_file) as client:
        if upload_kind == "image":
            result = client.upload_image(path)
            data = {
                "fileName": result.get("fileName", ""),
                "downloadUrl": result.get("downloadUrl", ""),
            }
        else:
            uploaded = client.upload_file(path)
            data = {
                "fileName": uploaded.file_name,
                "downloadUrl": uploaded.download_url,
            }

    return {
        "kind": upload_kind,
        "path": str(path),
        **data,
    }
