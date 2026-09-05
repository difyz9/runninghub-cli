# Standalone Skill Scripts

These scripts are auto-generated from `registry/skills/*.json`.

## Dependency

Install the SDK:

pip install runninghub-sdk

## Run

Example:

python scripts/standalone_skills/rh.webapp.txt2img.krea2_photoreal.v1.py \
  --prompt_text "cinematic portrait, realistic skin texture"

Z-image 4K art portrait / three-view character sheet example:

python scripts/standalone_skills/rh.webapp.txt2img.zimage_art_portrait.v1.py \
  --prompt_text "游戏角色人物三视图设定图，同一角色的正面、侧面、背面三个视角并排展示，全身立绘，纯白背景，角色原画设计风格，统一配色"

Three-view tip: explicitly include 三视图 / 正面 / 侧面 / 背面 / 并排 / 白底 in the
prompt, otherwise the app defaults to a single dreamy art portrait. Only the
smaller output is kept (the 4K duplicate is skipped).

MiniMax H3 FL2VA image-to-video example:

python scripts/standalone_skills/rh.webapp.img2vid.minimax_h3_fl2va_oss.v1.py \
  --reference_image_path /path/to/woman.png \
  --prompt_text "她缓缓转头看向窗外，轻轻抿了一口咖啡，头发微微飘动，电影质感，镜头平稳"

Another example (upload image + video):

python scripts/standalone_skills/rh.webapp.motion_transfer.wan22.v1.py \
  --reference_image_path /path/to/003.jpg \
  --motion_video_path /path/to/002.mp4

Digital human video example:

python scripts/standalone_skills/rh.webapp.dhuman.minimax_h3.v1.py \
  --image_path /path/to/portrait.png \
  --prompt_text "A friendly presenter speaking clearly to camera in a clean studio"

InfiniTetalk lip-sync example (defaults to Plus):

python scripts/standalone_skills/rh.webapp.infinitetalk.lipsync.v1.py \
  --image_path /path/to/portrait.png \
  --audio_path /path/to/speech.mp3

Digital human expression example:

python scripts/standalone_skills/rh.webapp.expression.dhuman.v1.py \
  --image_path /path/to/portrait.png \
  --expression "2.哈哈大笑"

MiniMax H3 audio lip-sync example:

python scripts/standalone_skills/rh.webapp.minimax_h3.audio_lipsync.v1.py \
  --image_path /path/to/portrait.png \
  --audio_path /path/to/speech.mp3

MiniMax H3 text-to-video (加速版 图文一键生视频) example:

python scripts/standalone_skills/rh.webapp.txt2vid.minimax_h3.v1.py \
  --prompt_text "镜头缓慢向前平移，一只橘猫在阳光下的窗台上伸懒腰，柔光，温馨治愈" \
  --aspect_ratio "16:9 (Widescreen)" \
  --resolution 2 \
  --duration 6

Text-to-video defaults: 16:9 widescreen, 720P, 10s. `--duration` is a tier
1-11 (5s-15s), `--resolution` 2=720P / 1=480P. No image needed — pure
text-to-video mode.

All scripts support:
- `--api-key` (or env `RUNNINGHUB_API_KEY`)
- `--instance-type`
- `--poll-interval`
- `--timeout`
- `--output-dir`

They all submit task -> poll status -> download outputs to local `outputs/`.

## Regenerate

python tools/build_standalone_skill_scripts.py
