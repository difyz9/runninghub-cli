#!/usr/bin/env python3
"""Sync a RunningHub interface manifest into a Feishu Base table.

The script delegates authentication and Base operations to lark-cli. It is
safe to run repeatedly: existing rows are matched by the configured resource
ID field and updated instead of duplicated.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_FIELDS = {
    "name": "接口名称",
    "resource_id": "资源ID",
    "resource_type": "接口类型",
    "instance_type": "运行模式",
    "inputs": "输入参数",
    "status": "联调状态",
    "script_files": "独立脚本",
    "artifact_files": "联调产物",
}


def run_lark(args: list[str], *, dry_run: bool = False) -> dict[str, Any]:
    command = ["lark-cli", "base", *args, "--as", "user", "--format", "json"]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "lark-cli failed"
        raise RuntimeError(message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned invalid JSON: {result.stdout[:500]}") from exc


def resolve_target(base_url: str) -> tuple[str, str]:
    response = run_lark(["+url-resolve", "--url", base_url])
    data = response["data"]
    base_token = data.get("base_token")
    table_id = data.get("table_id")
    if not base_token or not table_id:
        raise RuntimeError("URL must resolve to a table with base_token and table_id")
    return base_token, table_id


def load_manifest(path: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fields = {**DEFAULT_FIELDS, **payload.get("fields", {})}
    records = payload.get("interfaces")
    if not isinstance(records, list) or not records:
        raise ValueError("manifest.interfaces must be a non-empty array")
    for index, record in enumerate(records, start=1):
        if not record.get("resource_id"):
            raise ValueError(f"interfaces[{index}].resource_id is required")
        if not record.get("name"):
            raise ValueError(f"interfaces[{index}].name is required")
    return fields, records


def get_fields(base_token: str, table_id: str) -> list[dict[str, Any]]:
    return run_lark(["+field-list", "--base-token", base_token, "--table-id", table_id])["data"]["fields"]


def ensure_fields(base_token: str, table_id: str, field_types: dict[str, str], *, dry_run: bool) -> None:
    existing = {field["name"] for field in get_fields(base_token, table_id)}
    for name in sorted(set(field_types) - existing):
        run_lark(
            [
                "+field-create",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--json",
                json.dumps({"type": field_types[name], "name": name}, ensure_ascii=False),
            ],
            dry_run=dry_run,
        )
        print(f"field {'would be created' if dry_run else 'created'}: {name}")


def get_records(base_token: str, table_id: str, fields: dict[str, str]) -> dict[str, dict[str, Any]]:
    response = run_lark(["+record-list", "--base-token", base_token, "--table-id", table_id])
    data = response["data"]
    returned_fields = data.get("fields", [])
    resource_name = fields["resource_id"]
    resource_index = returned_fields.index(resource_name) if resource_name in returned_fields else -1
    if resource_index < 0:
        return {}
    records = {}
    for row, record_id in zip(data.get("data", []), data.get("record_id_list", []), strict=True):
        if len(row) <= resource_index or not row[resource_index]:
            continue
        attachments = {}
        for field_name in (fields.get("script_files"), fields.get("artifact_files")):
            if field_name in returned_fields:
                value = row[returned_fields.index(field_name)]
                attachments[field_name] = {item.get("name") for item in (value or []) if isinstance(item, dict)}
        records[row[resource_index]] = {"record_id": record_id, "attachments": attachments}
    return records


def make_row(fields: dict[str, str], item: dict[str, Any]) -> dict[str, Any]:
    return {
        fields["name"]: item["name"],
        fields["resource_id"]: str(item["resource_id"]),
        fields["resource_type"]: item.get("resource_type", "webapp"),
        fields["instance_type"]: item.get("instance_type", "default"),
        fields["inputs"]: item.get("inputs", ""),
        fields["status"]: item.get("status", "SUCCESS"),
    }


def relative_files(paths: list[str], manifest_path: Path) -> list[Path]:
    root = manifest_path.parent.resolve()
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            raise ValueError(f"attachment paths must be relative to the manifest: {raw_path}")
        resolved = (root / path).resolve()
        if not resolved.is_file():
            print(f"warning: attachment not found, skipped: {raw_path}", file=sys.stderr)
            continue
        files.append(resolved)
    return files


def upload_attachments(
    base_token: str,
    table_id: str,
    record_id: str,
    field_id: str,
    files: list[Path],
    *,
    dry_run: bool,
) -> None:
    if not files:
        return
    args = [
        "+record-upload-attachment",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--record-id",
        record_id,
        "--field-id",
        field_id,
    ]
    for path in files:
        args.extend(["--file", os.path.relpath(path, Path.cwd())])
    run_lark(args, dry_run=dry_run)
    print(f"attachments {'would be uploaded' if dry_run else 'uploaded'}: {len(files)} -> {record_id}")


def sync_records(
    base_token: str,
    table_id: str,
    fields: dict[str, str],
    field_ids: dict[str, str],
    items: list[dict[str, Any]],
    manifest_path: Path,
    *,
    dry_run: bool,
) -> None:
    existing = get_records(base_token, table_id, fields)
    creates: list[dict[str, Any]] = []
    updates: dict[str, dict[str, Any]] = {}
    item_files: dict[str, dict[str, list[Path]]] = {}
    for item in items:
        row = make_row(fields, item)
        resource_id = str(item["resource_id"])
        existing_record = existing.get(resource_id)
        record_id = existing_record["record_id"] if existing_record else None
        if record_id:
            updates[record_id] = row
        else:
            creates.append(row)
        item_files[resource_id] = {
            "script_files": relative_files(item.get("script_files", []), manifest_path),
            "artifact_files": relative_files(item.get("artifact_files", []), manifest_path),
        }

    created_ids: dict[str, str] = {}
    if creates:
        response = run_lark(
            [
                "+record-batch-create",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--json",
                json.dumps({"create_records": creates}, ensure_ascii=False),
            ],
            dry_run=dry_run,
        )
        if not dry_run:
            record_ids = response["data"]["record_id_list"]
            for item, record_id in zip((item for item in items if str(item["resource_id"]) not in existing), record_ids, strict=True):
                created_ids[str(item["resource_id"])] = record_id
        print(f"records {'would be created' if dry_run else 'created'}: {len(creates)}")
    if updates:
        run_lark(
            [
                "+record-batch-update",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--json",
                json.dumps({"update_records": updates}, ensure_ascii=False),
            ],
            dry_run=dry_run,
        )
        print(f"records {'would be updated' if dry_run else 'updated'}: {len(updates)}")

    if "script_files" in field_ids or "artifact_files" in field_ids:
        for resource_id, file_groups in item_files.items():
            record_id = (existing.get(resource_id) or {}).get("record_id") or created_ids.get(resource_id)
            if not record_id:
                continue
            if "script_files" in field_ids:
                existing_names = (existing.get(resource_id) or {}).get("attachments", {}).get(fields["script_files"], set())
                upload_attachments(
                    base_token,
                    table_id,
                    record_id,
                    field_ids["script_files"],
                    [path for path in file_groups["script_files"] if path.name not in existing_names],
                    dry_run=dry_run,
                )
            if "artifact_files" in field_ids:
                existing_names = (existing.get(resource_id) or {}).get("attachments", {}).get(fields["artifact_files"], set())
                upload_attachments(
                    base_token,
                    table_id,
                    record_id,
                    field_ids["artifact_files"],
                    [path for path in file_groups["artifact_files"] if path.name not in existing_names],
                    dry_run=dry_run,
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Feishu Base table URL")
    parser.add_argument("--manifest", type=Path, required=True, help="JSON interface manifest")
    parser.add_argument("--dry-run", action="store_true", help="Preview field and record writes")
    parser.add_argument("--yes", action="store_true", help="Confirm writes")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        fields, items = load_manifest(args.manifest)
        base_token, table_id = resolve_target(args.base_url)
        print(f"target table: {table_id}")
        if not args.dry_run and not args.yes:
            raise RuntimeError("writes require --yes; use --dry-run to preview")
        field_types = {name: "text" for name in fields.values()}
        field_types[fields["script_files"]] = "attachment"
        field_types[fields["artifact_files"]] = "attachment"
        ensure_fields(base_token, table_id, field_types, dry_run=args.dry_run)
        actual_fields = get_fields(base_token, table_id)
        field_ids = {field["name"]: field["id"] for field in actual_fields}
        attachment_field_ids = {
            key: field_ids[name]
            for key, name in fields.items()
            if key in {"script_files", "artifact_files"} and name in field_ids
        }
        sync_records(base_token, table_id, fields, attachment_field_ids, items, args.manifest, dry_run=args.dry_run)
        if not args.dry_run:
            print("sync complete")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
