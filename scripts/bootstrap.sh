#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${1:-}" == "--doctor-env" && -z "${2:-}" ]]; then
  echo "Usage: ./scripts/bootstrap.sh --doctor-env /absolute/path/to/.env" >&2
  exit 2
fi

python -m pip install --upgrade pip
python -m pip install "runninghub-sdk>=1.1.5" "typer>=0.9.0"
python -m pip install -e .

echo "runninghub-cli is installed."
echo "Try: runninghub --help"

if [[ "${1:-}" == "--doctor-env" ]]; then
  runninghub doctor --env-file "$2"
fi
