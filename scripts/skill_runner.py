from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .skill_runtime import (
    SkillRuntimeError,
    apply_declared_defaults,
    build_node_overrides,
    parse_kv_items,
    validate_required_params,
)

BASE_DIR = Path(__file__).resolve().parent.parent
SKILL_INDEX = BASE_DIR / "registry" / "skills_index.json"


class SkillError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_skill_definition(skill_name: str) -> dict[str, Any]:
    index = load_json(SKILL_INDEX)
    for item in index.get("skills", []):
        if item.get("name") == skill_name:
            definition_rel = item.get("definition")
            if not definition_rel:
                raise SkillError(f"Skill {skill_name} has no definition path")
            definition_path = BASE_DIR / definition_rel
            if not definition_path.exists():
                raise SkillError(f"Skill definition not found: {definition_path}")
            return load_json(definition_path)
    raise SkillError(f"Skill not found: {skill_name}")


def write_temp_overrides(overrides: list[dict[str, str]]) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    with tmp:
        json.dump(overrides, tmp, ensure_ascii=False, indent=2)
    return Path(tmp.name)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scripts.skill_runner",
        description="Run RunningHub skills by stable skill name instead of raw node IDs",
    )
    p.add_argument("--skill", required=False, help="Skill name from registry/skills_index.json")
    p.add_argument(
        "--param",
        action="append",
        default=[],
        help="Skill param in key=value format; can be repeated",
    )
    p.add_argument("--instance-type", default="", help="RunningHub instance type, e.g. default or plus")
    p.add_argument("--timeout", type=float, default=0, help="Timeout in seconds; 0 means use skill default")
    p.add_argument("--poll-interval", type=float, default=0, help="Poll interval in seconds; 0 means use skill default")
    p.add_argument("--output-dir", default="", help="Output directory for downloads")
    p.add_argument("--api-key", default="", help="Optional explicit RUNNINGHUB_API_KEY")
    p.add_argument("--env-file", default="", help="Optional .env path")
    p.add_argument("--dry-run", action="store_true", help="Print resolved config without executing")
    p.add_argument("--list", action="store_true", help="List available skills")
    return p


def list_skills() -> int:
    index = load_json(SKILL_INDEX)
    print(json.dumps({"ok": True, "data": index}, ensure_ascii=False, indent=2))
    return 0


def run_skill(args: argparse.Namespace) -> int:
    if not args.skill:
        raise SkillError("--skill is required unless --list is used")

    defn = load_skill_definition(args.skill)
    params = parse_kv_items(args.param, flag_name="--param")

    inputs = defn.get("inputs", {})
    merged_params = apply_declared_defaults(params, inputs)
    required = [p["name"] for p in inputs.get("required", []) if p.get("name")]
    validate_required_params(merged_params, required)
    overrides = build_node_overrides(defn.get("mapping", []), merged_params)

    resource = defn.get("resource", {})
    resource_id = resource.get("id")
    resource_type = resource.get("type", "workflow")
    if not resource_id:
        raise SkillError("Skill definition missing resource.id")

    runtime = defn.get("runtime", {})
    instance_type = args.instance_type or runtime.get("defaultInstanceType", "default")
    timeout = args.timeout if args.timeout > 0 else runtime.get("defaultTimeout", 1800)
    poll_interval = args.poll_interval if args.poll_interval > 0 else runtime.get("defaultPollInterval", 15)

    plan = {
        "skill": defn.get("name"),
        "resource": {
            "id": resource_id,
            "type": resource_type,
        },
        "instance_type": instance_type,
        "timeout": timeout,
        "poll_interval": poll_interval,
        "overrides": overrides,
        "output_dir": args.output_dir or "",
    }

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "plan": plan}, ensure_ascii=False, indent=2))
        return 0

    overrides_path = write_temp_overrides(overrides)

    cmd = [
        "runninghub",
        "run",
        str(resource_id),
        "--type",
        str(resource_type),
        "--node-overrides",
        str(overrides_path),
        "--instance-type",
        str(instance_type),
        "--timeout",
        str(timeout),
        "--poll-interval",
        str(poll_interval),
    ]

    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    if args.api_key:
        cmd.extend(["--api-key", args.api_key])
    if args.env_file:
        cmd.extend(["--env-file", args.env_file])

    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.list:
            return list_skills()
        return run_skill(args)
    except SkillRuntimeError as e:
        print(json.dumps({"ok": False, "error_type": "SkillRuntimeError", "error": str(e)}, ensure_ascii=False))
        return 2
    except SkillError as e:
        print(json.dumps({"ok": False, "error_type": "SkillError", "error": str(e)}, ensure_ascii=False))
        return 2
    except Exception as e:  # pragma: no cover
        print(json.dumps({"ok": False, "error_type": type(e).__name__, "error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
