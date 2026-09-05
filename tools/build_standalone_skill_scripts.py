#!/usr/bin/env python3
"""Generate standalone Python runners from registry/skills/*.json.

Each generated script is self-contained and only depends on runninghub-sdk.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "registry" / "skills"
OUT_DIR = ROOT / "scripts" / "standalone_skills"

TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated standalone script from {skill_json_name}.

Skill: {skill_name}
Description: {skill_description}

Dependencies:
  pip install runninghub-sdk

Usage example:
  python {script_name} {required_example}
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path
from typing import Any

from runninghub_sdk import RunningHubClient, modify_nodes

SKILL_NAME = {skill_name_literal}
RESOURCE_ID = {resource_id_literal}
RESOURCE_TYPE = {resource_type_literal}
MAPPING = {mapping_literal}
DEFAULT_INSTANCE_TYPE = {default_instance_type_literal}
DEFAULT_TIMEOUT = {default_timeout_literal}
DEFAULT_POLL_INTERVAL = {default_poll_interval_literal}
DEFAULT_OUTPUT_SUBDIR = {default_output_subdir_literal}
INPUTS = {inputs_literal}
INPUT_TYPES = {{item["name"]: item.get("type", "string") for item in INPUTS.get("required", []) + INPUTS.get("optional", [])}}
DOWNLOAD_POLICY = {download_policy_literal}


def log(msg: str) -> None:
    print(f"[{{datetime.datetime.now().strftime('%H:%M:%S')}}] {{msg}}")


def section(title: str) -> None:
    print(f"\\n{{'=' * 60}}")
    print(f"  {{title}}")
    print(f"{{'=' * 60}}")


def resolve_api_key(value: str | None) -> str:
    if value:
        return value
    key = os.getenv("RUNNINGHUB_API_KEY", "").strip()
    if key:
        return key
    print("Error: RUNNINGHUB_API_KEY not set. Use --api-key or env var.", file=sys.stderr)
    sys.exit(1)


def make_output_dir(base: str | None, subdir: str) -> Path:
    root = Path(base).expanduser().resolve() if base else Path.cwd() / "outputs"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = root / f"{{subdir}}_{{ts}}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog={prog_literal}, description={description_literal})
    p.add_argument("--api-key", help="RunningHub API key (default: RUNNINGHUB_API_KEY)")
    p.add_argument("--instance-type", default=DEFAULT_INSTANCE_TYPE, help="RunningHub instance type")
    p.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL, help="Polling interval in seconds")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Task timeout in seconds")
    p.add_argument("--output-dir", default=None, help="Base output dir (default: ./outputs)")
{arg_defs}
    return p


def build_nodes(args: argparse.Namespace, client: RunningHubClient) -> list[dict[str, Any]]:
    modifier = modify_nodes()

    for m in MAPPING:
        param = m["param"]
        node_id = m["nodeId"]
        field_name = m["fieldName"]
        mode = m.get("valueMode", "literal")

        value = getattr(args, param)

        if mode == "upload":
            path = Path(str(value)).expanduser().resolve()
            if not path.exists():
                print(f"Error: file not found for {{param}}: {{path}}", file=sys.stderr)
                sys.exit(1)
            log(f"Uploading {{param}}: {{path}}")
            if INPUT_TYPES.get(param) == "image":
                uploaded = client.upload_image(str(path))
                value = uploaded["fileName"]
            else:
                uploaded = client.upload_file(str(path))
                value = uploaded.file_name
            log(f"Uploaded as: {{value}}")

        modifier.set(node_id, field_name, value)

    return modifier.to_dict_list()


def submit_and_wait(client: RunningHubClient, node_info_list: list[dict[str, Any]], instance_type: str, poll_interval: float, timeout: float) -> Any:
    section("Submitting Task")

    if RESOURCE_TYPE == "webapp":
        task = client.run_ai_app(
            webapp_id=RESOURCE_ID,
            node_info_list=node_info_list,
            add_metadata=True,
            instance_type=instance_type,
        )
    else:
        task = client.run(
            workflow_id=RESOURCE_ID,
            node_info_list=node_info_list,
            add_metadata=True,
            instance_type=instance_type,
            use_personal_queue=False,
        )

    log(f"task_id: {{task.task_id}}")
    log(f"status: {{task.task_status}}")

    if not task.task_id:
        print("Error: task_id is empty", file=sys.stderr)
        sys.exit(1)

    section("Waiting for Completion")
    last_status: Any = None

    def on_status_change(status: Any) -> None:
        nonlocal last_status
        if status != last_status:
            log(f"status -> {{status}}")
            last_status = status

    return client.wait_for_completion(
        task_id=task.task_id,
        poll_interval=poll_interval,
        timeout=timeout,
        on_status_change=on_status_change,
    )


def filter_outputs_by_policy(outputs: list[Any], policy: str) -> list[Any]:
    """Pick which outputs to download.

    'all' keeps everything. 'keep_smallest' / 'keep_largest' keep a single
    output ranked by the remote file size (a cheap HEAD request; falls back
    to list order when sizes are unknown).
    """
    if policy == "all" or len(outputs) <= 1:
        return list(outputs)

    import urllib.request

    def remote_size(output: Any) -> int:
        try:
            req = urllib.request.Request(output.file_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return int(resp.headers.get("Content-Length") or 0)
        except Exception:
            return 0

    sized = [(remote_size(out), out) for out in outputs]
    if all(size == 0 for size, _ in sized):
        log(f"could not determine output sizes; keeping first output for policy '{{policy}}'")
        return outputs[:1]
    sized.sort(key=lambda item: item[0])
    return [sized[0][1]] if policy == "keep_smallest" else [sized[-1][1]]


def download_outputs(client: RunningHubClient, outputs: Any, out_dir: Path) -> list[Path]:
    section("Downloading Outputs")
    selected = filter_outputs_by_policy(outputs, DOWNLOAD_POLICY)
    if len(selected) < len(outputs):
        log(f"download policy '{{DOWNLOAD_POLICY}}': keeping {{len(selected)}} of {{len(outputs)}} outputs")
    paths = client.download_outputs(selected, out_dir)
    for p in paths:
        size = p.stat().st_size
        size_str = f"{{size / 1024 / 1024:.1f}} MB" if size > 1024 * 1024 else f"{{size / 1024:.0f}} KB"
        log(f"saved: {{p}} ({{size_str}})")
    return paths


def main() -> int:
    args = build_parser().parse_args()
    api_key = resolve_api_key(args.api_key)

    out_dir = make_output_dir(args.output_dir, DEFAULT_OUTPUT_SUBDIR)
    section("Skill Info")
    log(f"skill: {{SKILL_NAME}}")
    log(f"resource_type: {{RESOURCE_TYPE}}")
    log(f"resource_id: {{RESOURCE_ID}}")
    log(f"instance_type: {{args.instance_type}}")

    try:
        with RunningHubClient(api_key=api_key) as client:
            node_info_list = build_nodes(args, client)
            outputs = submit_and_wait(client, node_info_list, args.instance_type, args.poll_interval, args.timeout)
            download_outputs(client, outputs, out_dir)
    except Exception as exc:
        print(f"Error: {{exc}}", file=sys.stderr)
        return 1

    section("Done")
    log(f"outputs saved to: {{out_dir}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def py_literal(value: object) -> str:
    return repr(value)


def make_arg_defs(required: list[dict], optional: list[dict]) -> str:
    lines: list[str] = []
    for item in required:
        name = item["name"]
        typ = item.get("type", "string")
        desc = item.get("description", "")
        type_expr = ""
        if typ == "int":
            type_expr = ", type=int"
        elif typ == "float":
            type_expr = ", type=float"
        lines.append(
            f"    p.add_argument('--{name}', required=True{type_expr}, help={py_literal(desc)})"
        )

    for item in optional:
        name = item["name"]
        typ = item.get("type", "string")
        default = item.get("default")
        desc = item.get("description", "")
        type_expr = ""
        if typ == "int":
            type_expr = ", type=int"
        elif typ == "float":
            type_expr = ", type=float"
        lines.append(
            f"    p.add_argument('--{name}', default={py_literal(default)}{type_expr}, help={py_literal(desc)})"
        )

    return "\n".join(lines)


def required_example(required: list[dict]) -> str:
    parts: list[str] = []
    for item in required:
        name = item["name"]
        typ = item.get("type", "string")
        if typ in {"image", "video", "audio", "file"}:
            value = f"/path/to/{name}"
        elif typ == "int":
            value = "1"
        elif typ == "float":
            value = "1.0"
        else:
            value = f"'{name}_value'"
        parts.append(f"--{name} {value}")
    return " ".join(parts)


def main() -> int:
    if not SKILLS_DIR.exists():
        print(f"Skill directory not found: {SKILLS_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    for skill_file in sorted(SKILLS_DIR.glob("*.json")):
        data = json.loads(skill_file.read_text(encoding="utf-8"))

        skill_name = data["name"]
        description = data.get("description", "")
        resource = data["resource"]
        runtime = data.get("runtime", {})
        inputs = data.get("inputs", {})
        required = inputs.get("required", [])
        optional = inputs.get("optional", [])
        mapping = data.get("mapping", [])
        outputs_spec = data.get("outputs", {})
        download_policy = outputs_spec.get("downloadPolicy", "all")

        script_name = f"{skill_file.stem}.py"
        out_path = OUT_DIR / script_name

        content = TEMPLATE.format(
            skill_json_name=skill_file.name,
            skill_name=skill_name,
            skill_description=description,
            script_name=script_name,
            required_example=required_example(required),
            skill_name_literal=py_literal(skill_name),
            resource_id_literal=py_literal(resource["id"]),
            resource_type_literal=py_literal(resource["type"]),
            mapping_literal=py_literal(mapping),
            default_instance_type_literal=py_literal(runtime.get("defaultInstanceType", "default")),
            default_timeout_literal=py_literal(runtime.get("defaultTimeout", 1800)),
            default_poll_interval_literal=py_literal(runtime.get("defaultPollInterval", 10)),
            default_output_subdir_literal=py_literal(f"{skill_file.stem}_outputs"),
            inputs_literal=py_literal(inputs),
            download_policy_literal=py_literal(download_policy),
            prog_literal=py_literal(f"rh-{skill_file.stem}"),
            description_literal=py_literal(description),
            arg_defs=make_arg_defs(required, optional),
        )

        out_path.write_text(content, encoding="utf-8")
        generated += 1

    print(f"Generated {generated} standalone scripts in: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
