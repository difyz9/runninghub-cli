---
name: runninghub-cli
description: Use the runninghub CLI to inspect, submit, wait for, download, and debug RunningHub workflows or AI Apps.
---

# RunningHub CLI Agent Workflow

Use `runninghub` when the user asks to integrate, debug, submit, inspect, or validate a RunningHub workflow or AI App.

## Install Or Refresh

If `runninghub` is not available, clone this GitHub project and install it locally. Do not install `runninghub-cli` from PyPI. Only `runninghub-sdk` is expected to come from PyPI.

```bash
mkdir -p ~/tools
cd ~/tools
git clone https://github.com/difyz9/runninghub-cli.git
cd runninghub-cli
./scripts/bootstrap.sh
```

If the repository already exists:

```bash
cd ~/tools/runninghub-cli
runninghub self-update
```

## First Check

```bash
runninghub doctor
```

Stop and report the environment issue if `ok` is false.

If the API key lives in another project, pass its env file:

```bash
runninghub doctor --env-file /absolute/path/to/.env
```

## Detect Type

```bash
runninghub detect <id>
```

Use the returned `type` for later commands:

- `workflow`
- `webapp`

## Inspect

```bash
runninghub inspect <id> --type workflow
runninghub inspect <id> --type webapp
```

Use the returned nodes and fields to build `node_overrides`.

## Submit And Debug

For a quick end-to-end validation:

```bash
runninghub run <id> --type webapp --node-overrides overrides.json
```

For encrypted AI Apps/webapps, include the access password through a private environment variable:

```bash
runninghub run <id> --type webapp --access-password "$APP_ACCESS_PASSWORD" --node-overrides overrides.json
```

If an encrypted app needs a password and `APP_ACCESS_PASSWORD` is missing, ask the user to set it in their shell or private environment before submitting. Do not request, print, store, or commit the real password in docs, skills, case files, overrides, tests, or logs.

For long tasks, submit first:

```bash
runninghub submit <id> --type workflow --node-overrides overrides.json
runninghub status <task_id>
runninghub task-detail <task_id>
runninghub wait-download <id> <task_id>
```

## Upload Media

When a workflow or AI App needs an image, video, audio, or file input, upload the local file first:

```bash
runninghub upload /absolute/path/input.png --kind image
runninghub upload /absolute/path/input.mp4 --kind video
runninghub upload /absolute/path/input.wav --kind audio
```

For AI Apps and webapps, media input fields normally expect the uploaded RunningHub `fileName`, not the local path and not the public `downloadUrl`. Use the `downloadUrl` only when inspection or workflow JSON explicitly shows that a URL is required.

Hermes can also let the CLI upload automatically by setting the media `fieldValue` to `@upload:/absolute/path/to/file`. The CLI uploads the file before submission and replaces the value with the returned `fileName`.

Use `@upload-url:/absolute/path/to/file` only when an inspected field explicitly requires a URL instead of a RunningHub file name.

## AI App Media Input Prompt

When the user provides a RunningHub AI App curl payload with `nodeInfoList`, convert it to `node_overrides` and handle media fields like this:

1. Inspect or read the payload and preserve each editable node as `{ "nodeId", "fieldName", "fieldValue" }`.
2. For text, number, width, height, duration, seed, and other scalar fields, copy the user-provided value directly as a string unless the inspected field clearly requires another JSON type.
3. For `fieldName` values such as `image`, `video`, `audio`, or `file`, check whether `fieldValue` is already a RunningHub uploaded file name such as `abc123.jpg` or `abc123.mp4`.
4. If the user supplied a local file path or asks to use a local image/video/audio, prefer the automatic upload directive in the override payload:

```json
[
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:/absolute/path/model.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"@upload:/absolute/path/dance.mp4"}
]
```

Manual upload is also valid when the agent needs to inspect or reuse the uploaded file:

```bash
runninghub upload /absolute/path/model.jpg --kind image
runninghub upload /absolute/path/dance.mp4 --kind video
```

5. Put the returned `fileName` into the corresponding media node's `fieldValue`.
6. Do not put a bare local path, base64 data, multipart form data, or `downloadUrl` into AI App media `fieldValue` unless RunningHub inspection explicitly requires a URL.
7. Write long override payloads to a JSON file and pass that file with `--node-overrides`.

Example converted override file for an AI App that needs a model image and a dance video:

```json
[
  {"nodeId":"255","fieldName":"value","fieldValue":"10"},
  {"nodeId":"264","fieldName":"value","fieldValue":"720"},
  {"nodeId":"265","fieldName":"value","fieldValue":"1280"},
  {"nodeId":"370","fieldName":"text","fieldValue":"跳舞/对镜自拍 9:16   720×1280\n\n走拍16:9   1280×720       走拍4:3   1280×960\n\n上传的图片和视频比例要一致"},
  {"nodeId":"167","fieldName":"image","fieldValue":"226dd3950e650b9cf540bad4145d1e47d22a4e4c8885e66095979c2b292e2e90.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"57012cfc3d5c779ca7d8ba06c6a743cc9837f5e947cf4f06bac55f02de27bfb1.mp4"},
  {"nodeId":"369","fieldName":"text","fieldValue":"上传的图片和视频比例要一致\n\n本应用只适合做服装带货视频\n不要做一些乱七八糟的视频\n\n请各位成员自觉遵守\n珍惜团队资源与共同权益\n\n本应用是团队内部免费分享\n密码不定期更换 请勿上当受骗"}
]
```

Then submit or run it as an AI App/webapp:

```bash
runninghub run 2046575818536652802 --type webapp --node-overrides overrides.json
```

## Payload Rules

`node_overrides` must use RunningHub SDK format:

```json
[
  {"nodeId": "43", "fieldName": "text", "fieldValue": "A test prompt"}
]
```

Prefer writing long JSON to a temporary file and passing its path with `--node-overrides`.

## Hermes Payload Builder Playbook

Use these rules when building `node_overrides` from user intent, inspected workflow JSON, AI App demo nodes, or historical integration cases.

### Construction Order

1. Run `runninghub detect <id>` unless the caller already gives the type.
2. Run `runninghub inspect <id> --type <type>` before choosing node IDs or field names.
3. Override only user-facing inputs: prompt/text/value, media fields, size, duration, aspect ratio, seed, steps, cfg, frame rate, and select fields.
4. Keep system prompts, model names, LoRA strengths, API configuration, and connected internal nodes unchanged unless the user explicitly asks.
5. Prefer the smallest useful payload. For complex workflows, changing 1-5 key fields is usually safer than rebuilding every parameter.
6. For local media, use `@upload:/absolute/path/file.ext` in `fieldValue`; use already-uploaded `fileName` or URL only when supplied by RunningHub or visible in a verified payload.
7. If a field mismatch occurs, re-run `inspect`, find the exact node's fields, and change only the bad field.

### Field Name Cheat Sheet

Common workflow node classes and the field names Hermes should try after inspection confirms the node exists:

| Node or intent | Usual `fieldName` | Notes |
|---|---|---|
| `CLIPTextEncode` | `text` | Positive/negative prompt text. |
| `CR Prompt Text` | `prompt` | Prompt node in many storyboard flows. |
| `PrimitiveStringMultiline` | `value` | Important: often `value`, not `text`. |
| `Text Multiline`, `JjkText` | `text` | Free text input. |
| `TextEncodeQwenImageEdit*` | `prompt` | Image edit / try-on instruction. |
| `LoadImage` | `image` | Use `@upload:` for local images. |
| `LoadVideo`, `VHS_LoadVideo` | `video` or `file` | Use `@upload:` for local videos. |
| `LoadAudio`, `VHS_LoadAudioUpload` | `audio` | Use `@upload:` for local audio. |
| `KSampler` | `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise` | Keep defaults unless user asks for quality/speed/seed. |
| `KSamplerAdvanced` | `noise_seed`, `steps`, `cfg`, `start_at_step`, `end_at_step` | For paired high/low-noise samplers, keep paired values consistent. |
| `WanVideoEmptyEmbeds` | `width`, `height`, `num_frames` | Derive frames from duration × fps when needed. |
| `EmptySD3LatentImage` | `width`, `height`, `batch_size` | Use portrait/landscape/square from user intent. |
| `VHS_VideoCombine`, `CreateVideo` | `frame_rate` | Usually 24 unless user specifies. |
| `ImpactSwitch` or select controls | `select` | Use inspected option/index semantics; do not invent labels. |

### Prompt Writing Rules

- Text-to-image: expand short user intent into subject, environment, action, style, light, composition, and quality. Use English for SD/Flux-style image prompts unless the inspected examples are Chinese.
- Text-to-video: describe subject, action, camera movement, temporal change, lighting, and mood. For Doubao/Seedance workflows, Chinese prompts are usually accepted and natural.
- Image-to-video: preserve the uploaded image's subject and add motion only. Use phrases like `camera slowly pushes in`, `subtle hair and cloth movement`, `cinematic lighting`, and avoid changing identity/clothing unless requested.
- Storyboard: use Chinese if the app/workflow examples are Chinese. Include shot count, continuity, character consistency, scene progression, camera angle, and output aspect if relevant.
- Virtual try-on or clothing workflows: keep the person's identity/body pose, describe the garment plainly, and add a negative prompt such as `文字、水印、低质量` when a negative prompt node exists.
- Multi-reference workflows: map images in the order implied by descriptions: first/reference/style/person/garment/last frame. If the user supplies fewer images than required, ask for the missing media.
- Seed: set only when the user asks for reproducibility or a verified case requires it. Otherwise omit seed to preserve workflow defaults.
- Resolution/aspect: portrait people/mobile content → `9:16` or 720×1280; landscape/cinematic → `16:9` or 1280×720; square/product/avatar → `1:1` or 1024×1024.

## Verified Case Templates

These templates are copied into this project from verified RunningHub integration cases. The self-contained case reference lives in `docs/hermes-cases.md`. Replace media values with `@upload:/path` for local files.

### Text To Video: Doubao Seedance `2004066004755988481`

Use for simple Chinese text-to-video requests.

```json
[
  {"nodeId":"1","fieldName":"prompt","fieldValue":"一只可爱的橘猫在草地上打滚，阳光明媚，镜头缓慢推进"},
  {"nodeId":"1","fieldName":"duration","fieldValue":"5"},
  {"nodeId":"1","fieldName":"aspect_ratio","fieldValue":"16:9"}
]
```

Add `seed` only for reproducibility.

### Image To Video: Seedance `2037036284312559617`

Use when the user gives one image and wants motion.

```json
[
  {"nodeId":"2","fieldName":"image","fieldValue":"@upload:/absolute/path/scene.png"},
  {"nodeId":"1","fieldName":"prompt","fieldValue":"camera slowly panning right, gentle motion, cinematic lighting"},
  {"nodeId":"1","fieldName":"duration","fieldValue":"5"}
]
```

### First And Last Frame Transition: Wan 2.2 `2011275998205054977`

Use when the user supplies start and end frames.

```json
[
  {"nodeId":"43","fieldName":"image","fieldValue":"@upload:/absolute/path/start.png"},
  {"nodeId":"44","fieldName":"image","fieldValue":"@upload:/absolute/path/end.png"},
  {"nodeId":"30","fieldName":"positive_prompt","fieldValue":"smooth transition, seamless, cinematic camera movement"}
]
```

If setting seed, keep both sampler seeds aligned:

```json
[
  {"nodeId":"27","fieldName":"seed","fieldValue":"42"},
  {"nodeId":"28","fieldName":"seed","fieldValue":"42"}
]
```

### Storyboard Images: Continuous Character `2056898489606561793`

Use for six-image continuity storyboard requests.

```json
[
  {"nodeId":"366","fieldName":"prompt","fieldValue":"生成六段连续性分镜：同一位角色在水塘边从发现线索、靠近水面、观察倒影到转身离开，保持人物服装和环境一致，电影感构图"},
  {"nodeId":"342","fieldName":"image","fieldValue":"@upload:/absolute/path/reference.png"}
]
```

Omit the image node if the user has no reference image.

### Image Edit: SeedVR2 `2059461117663076353`

Use for image-to-image transformation or enhancement.

```json
[
  {"nodeId":"65","fieldName":"image","fieldValue":"@upload:/absolute/path/input.png"},
  {"nodeId":"66","fieldName":"prompt","fieldValue":"把图片处理成赛博朋克风格，保留主体结构，增强霓虹光影和细节"}
]
```

### Dance / Pose Image To Video: Wan I2V `1972733308360675329`

Use when a reference person image should move or dance.

```json
[
  {"nodeId":"73","fieldName":"positive","fieldValue":"一个女孩正在跳现代舞，动作流畅，镜头稳定，舞台灯光柔和"},
  {"nodeId":"341","fieldName":"image","fieldValue":"@upload:/absolute/path/person.png"}
]
```

### Multi-Image LTXV Video `2052272204712300545`

Use when the workflow expects up to three reference frames/images plus action/dialogue text.

```json
[
  {"nodeId":"269","fieldName":"image","fieldValue":"@upload:/absolute/path/frame1.png"},
  {"nodeId":"332","fieldName":"image","fieldValue":"@upload:/absolute/path/frame2.png"},
  {"nodeId":"342","fieldName":"image","fieldValue":"@upload:/absolute/path/frame3.png"},
  {"nodeId":"325","fieldName":"value","fieldValue":"动作：镜头推进，人物自然转身\n台词：保持简短自然的一句话"}
]
```

If only one image is provided, use the first image node and omit the others unless inspection marks them required.

### LTXV Two-Image Video With Negative Prompt `2060674924032905217`

Use when two source images guide an LTXV video and the workflow exposes a negative text node.

```json
[
  {"nodeId":"98","fieldName":"image","fieldValue":"@upload:/absolute/path/source1.png"},
  {"nodeId":"214","fieldName":"image","fieldValue":"@upload:/absolute/path/source2.png"},
  {"nodeId":"113","fieldName":"text","fieldValue":"pc game, console game, video game, cartoon, childish, ugly, subtitles, caption, captions, closed captions"}
]
```

### LTX Director Text Video `2059132036383858689`

Use for English cinematic text-to-video with duration and fps.

```json
[
  {"nodeId":"46","fieldName":"global_prompt","fieldValue":"A cinematic shot of a futuristic city at night, neon lights reflecting on wet streets, slow dolly forward"},
  {"nodeId":"46","fieldName":"duration_seconds","fieldValue":"10"},
  {"nodeId":"46","fieldName":"frame_rate","fieldValue":"24"}
]
```

### Virtual Try-On / Qwen Image Edit `2061692914857766913`

Use for person image plus garment or style instruction.

```json
[
  {"nodeId":"74","fieldName":"image","fieldValue":"@upload:/absolute/path/person.png"},
  {"nodeId":"68","fieldName":"prompt","fieldValue":"一位穿着时尚连衣裙的模特站在白色背景前，保留人物姿态和身份"},
  {"nodeId":"61","fieldName":"prompt","fieldValue":"文字、水印、低质量"},
  {"nodeId":"103","fieldName":"text","fieldValue":"时尚连衣裙"}
]
```

Only add `seed` when reproducibility is requested.

### AI App: Clothing Extraction `2005542596594331650`

Use for one-person image AI App calls.

```json
[
  {"nodeId":"78","fieldName":"image","fieldValue":"@upload:/absolute/path/person.png"}
]
```

Run with `--type webapp`.

### AI App: Image + Video Garment Dance `2046575818536652802`

Use when the app requires matching image/video aspect ratio and exposes width, height, duration, image, and video nodes.

Known posture migration app lines with the same payload shape. If the app is encrypted, use `--access-password "$APP_ACCESS_PASSWORD"`; if the variable is missing, ask the user to set it privately before submitting.

| Line | App ID | Notes |
|---|---|---|
| A | `2046575818536652802` | Standard line. |
| B | `2046896962057801729` | Same function; use to avoid peak failures. |
| Plus | `2047005172739608578` | More stable and higher cost. |

```json
[
  {"nodeId":"255","fieldName":"value","fieldValue":"10"},
  {"nodeId":"264","fieldName":"value","fieldValue":"720"},
  {"nodeId":"265","fieldName":"value","fieldValue":"1280"},
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:/absolute/path/model.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"@upload:/absolute/path/dance.mp4"}
]
```

Keep image and video aspect ratio consistent. For vertical dance/selfie content use 720×1280; for walking landscape use 1280×720; for 4:3 walking use 1280×960.

Run these encrypted AI Apps with:

```bash
runninghub run <app_id> --type webapp --access-password "$APP_ACCESS_PASSWORD" --node-overrides overrides.json
```

## Failure Handling

All commands return JSON on stdout. On failure, parse:

- `error_type`
- `error`
- `code`
- `task_id`
- `failed_reason`
- `task_detail`

If `run` or `wait-download` fails after submission, first inspect the returned `task_id`, `failed_reason`, and `task_detail`. If the error JSON does not include enough context but has a task ID, run:

```bash
runninghub task-detail <task_id>
```

Use `task_detail.status`, `task_detail.error_code`, `task_detail.error_message`, `task_detail.failed_reason`, `task_detail.query_v2`, `task_detail.outputs`, `task_detail.webhook_detail`, and `task_detail.detail_errors` to infer the likely failing node or parameter.

Retry policy for Hermes:

1. Attempt 1: fix the most concrete issue from the failure data. Examples: replace an invalid `fieldName`, remove/adjust the node named in `failed_reason.node_id`, lower unsafe resolution/duration, or rewrite blocked prompts using safer neutral wording.
2. Attempt 2: if the same workflow still fails, simplify the payload to only required user-facing inputs and preserve more defaults. Re-run `inspect` before changing node IDs or field names.
3. Attempt 3: if the failure looks content-related, rewrite the prompt more conservatively; if it looks parameter-related, reduce only one parameter class at a time, such as duration, frame count, resolution, steps, or cfg.
4. After 3 failed attempts for the same user request and target ID, stop retrying. Tell the user the task still failed, include the latest `task_id`, `error_code`, `error_message`, `failed_reason.node_id`, `failed_reason.node_name`, and `failed_reason.exception_message`, and ask the user to specify the exact intended change, acceptable prompt/content constraints, or which node/parameter should be adjusted next.

If a field is invalid, re-run `runninghub inspect` and choose a valid `fieldName`. If a task fails during generation, change only the minimum necessary payload field per retry.

## Version Update

To update the CLI itself, use:

```bash
runninghub self-update --dry-run
runninghub self-update
```

This fetches the latest GitHub tag and reinstalls the editable checkout. If the command is unavailable or fails because the checkout is missing, fall back to the install steps above.
