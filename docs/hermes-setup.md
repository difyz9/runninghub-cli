# Hermes Setup

This guide treats `runninghub-cli` as a GitHub-hosted project tool. Hermes should clone it and install it locally. Only `runninghub-sdk` needs to come from PyPI.

## Recommended Install

```bash
mkdir -p ~/tools
cd ~/tools
git clone https://github.com/difyz9/runninghub-cli.git
cd runninghub-cli
./scripts/bootstrap.sh
```

Then verify:

```bash
runninghub --version
runninghub doctor
```

If the API key is stored in another project, pass its env file:

```bash
runninghub doctor --env-file /path/to/runninghub-crew/backend/.env
```

## Update

```bash
cd ~/tools/runninghub-cli
git pull
python -m pip install -e .
```

## Why Not PyPI For The CLI

`runninghub-sdk` is the stable library dependency and belongs on PyPI.

`runninghub-cli` is currently an agent-facing workflow layer. It may change quickly as Hermes learns better integration flows, error handling, retries, and payload conventions. Git clone plus editable install keeps the feedback loop short.

## Hermes Command Pattern

Use JSON commands and parse stdout:

```bash
runninghub doctor
runninghub detect <id>
runninghub inspect <id> --type webapp
runninghub run <id> --type webapp --node-overrides overrides.json
```

For long tasks:

```bash
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub wait-download <id> <task_id>
```

## Environment

Preferred:

```bash
export RUNNINGHUB_API_KEY=...
```

Alternative:

```bash
runninghub doctor --env-file /absolute/path/to/.env
```

Do not print API keys in conversation logs.

