# Portable RunningHub Tool Script

This folder provides a single-file tool script for reusing verified RunningHub interfaces across projects.

## Why this script

- Single file: `rh_tool.py`
- Minimal dependencies: Python stdlib + `runninghub` CLI
- Built-in profiles for verified interfaces
- Works in any project by copying one script file

## Quick start

1. Ensure `runninghub` CLI is available in PATH and `RUNNINGHUB_API_KEY` is set.
2. Copy `tools/rh_tool.py` to your target project.
3. Run:

```bash
python rh_tool.py list
```

## Run a profile

```bash
python rh_tool.py run \
  --profile krea2_txt2img \
  --set "prompt_text=Ultra-realistic 4K portrait photo" \
  --output-dir ./outputs
```

## Dry run

```bash
python rh_tool.py run \
  --profile minimax_h3_dance \
  --set image_path=003.jpg \
  --set video_path=002.mp4 \
  --dry-run
```

## Notes

- Media params use local paths; script converts them to `@upload:` automatically.
- You can pass `--api-key` or `--env-file` if needed.
- Script calls `runninghub run` under the hood.
