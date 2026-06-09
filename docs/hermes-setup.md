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
runninghub self-update --dry-run
runninghub self-update
```

`self-update` expects GitHub release tags such as `v0.1.0`. Before the first tag exists, update manually:

```bash
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
runninghub upload /absolute/path/input.png --kind image
runninghub upload /absolute/path/input.mp4 --kind video
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

## Media Uploads

Use uploads when local files must become RunningHub media inputs:

```bash
runninghub upload /absolute/path/image.png --kind image
runninghub upload /absolute/path/video.mp4 --kind video
runninghub upload /absolute/path/audio.wav --kind audio
```

For AI Apps/webapps, copy the returned `fileName` into the media node's `fieldValue` in `node_overrides`. Do not use the local path or base64 data. Use `downloadUrl` only when inspection clearly shows that the target field expects a URL.

Hermes prompt rule for media nodes:

```text
If a RunningHub AI App node has fieldName=image, video, audio, or file and the user provides a local file, set that node's fieldValue to @upload:/absolute/path/to/file. The CLI uploads it before submission and replaces it with fileName. Preserve non-media node values from the user's payload. Write the final array as node_overrides and run the app with `runninghub run <app_id> --type webapp --node-overrides <file>`.
```
