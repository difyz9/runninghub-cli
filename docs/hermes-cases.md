# Hermes RunningHub Case Templates

This file keeps self-contained, verified RunningHub case templates for Hermes. These examples were distilled from prior integration cases and are now part of this project, so `backend/` and `runninghub_skill/` are not required at runtime.

Use these templates as references after running `runninghub inspect <id> --type <type>`. Replace local media with `@upload:/absolute/path/file.ext`.

## General Rules

- Override only user-facing inputs: prompt/text/value, media, size, duration, aspect ratio, seed, steps, cfg, frame rate, and select fields.
- Keep system prompts, model names, LoRA strengths, API configuration, and connected internal nodes unchanged unless explicitly requested.
- Use `@upload:` for local image, video, audio, or file inputs. Use `@upload-url:` only when inspection clearly shows a URL is required.
- Set seed only when the user asks for reproducibility.
- Use portrait/mobile: `9:16` or 720x1280; landscape/cinematic: `16:9` or 1280x720; square/product/avatar: `1:1` or 1024x1024.

## Field Name Cheat Sheet

| Node or intent | Usual `fieldName` | Notes |
|---|---|---|
| `CLIPTextEncode` | `text` | Positive/negative prompt text. |
| `CR Prompt Text` | `prompt` | Prompt node in storyboard flows. |
| `PrimitiveStringMultiline` | `value` | Often `value`, not `text`. |
| `Text Multiline`, `JjkText` | `text` | Free text input. |
| `TextEncodeQwenImageEdit*` | `prompt` | Image edit / try-on instruction. |
| `LoadImage` | `image` | Use `@upload:` for local images. |
| `LoadVideo`, `VHS_LoadVideo` | `video` or `file` | Use `@upload:` for local videos. |
| `LoadAudio`, `VHS_LoadAudioUpload` | `audio` | Use `@upload:` for local audio. |
| `KSampler` | `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise` | Keep defaults unless requested. |
| `KSamplerAdvanced` | `noise_seed`, `steps`, `cfg`, `start_at_step`, `end_at_step` | Keep paired sampler values consistent. |
| `WanVideoEmptyEmbeds` | `width`, `height`, `num_frames` | Derive frames from duration x fps when needed. |
| `EmptySD3LatentImage` | `width`, `height`, `batch_size` | Use aspect from user intent. |
| `VHS_VideoCombine`, `CreateVideo` | `frame_rate` | Usually 24 unless specified. |

## Text To Video: Doubao Seedance `2004066004755988481`

Use for simple Chinese text-to-video requests.

```json
[
  {"nodeId":"1","fieldName":"prompt","fieldValue":"一只可爱的橘猫在草地上打滚，阳光明媚，镜头缓慢推进"},
  {"nodeId":"1","fieldName":"duration","fieldValue":"5"},
  {"nodeId":"1","fieldName":"aspect_ratio","fieldValue":"16:9"}
]
```

## Image To Video: Seedance `2037036284312559617`

Use when the user gives one image and wants motion.

```json
[
  {"nodeId":"2","fieldName":"image","fieldValue":"@upload:/absolute/path/scene.png"},
  {"nodeId":"1","fieldName":"prompt","fieldValue":"camera slowly panning right, gentle motion, cinematic lighting"},
  {"nodeId":"1","fieldName":"duration","fieldValue":"5"}
]
```

## First And Last Frame Transition: Wan 2.2 `2011275998205054977`

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

## Storyboard Images: Continuous Character `2056898489606561793`

Use for six-image continuity storyboard requests.

```json
[
  {"nodeId":"366","fieldName":"prompt","fieldValue":"生成六段连续性分镜：同一位角色在水塘边从发现线索、靠近水面、观察倒影到转身离开，保持人物服装和环境一致，电影感构图"},
  {"nodeId":"342","fieldName":"image","fieldValue":"@upload:/absolute/path/reference.png"}
]
```

Omit the image node if the user has no reference image.

## Image Edit: SeedVR2 `2059461117663076353`

Use for image-to-image transformation or enhancement.

```json
[
  {"nodeId":"65","fieldName":"image","fieldValue":"@upload:/absolute/path/input.png"},
  {"nodeId":"66","fieldName":"prompt","fieldValue":"把图片处理成赛博朋克风格，保留主体结构，增强霓虹光影和细节"}
]
```

## Dance / Pose Image To Video: Wan I2V `1972733308360675329`

Use when a reference person image should move or dance.

```json
[
  {"nodeId":"73","fieldName":"positive","fieldValue":"一个女孩正在跳现代舞，动作流畅，镜头稳定，舞台灯光柔和"},
  {"nodeId":"341","fieldName":"image","fieldValue":"@upload:/absolute/path/person.png"}
]
```

## Multi-Image LTXV Video `2052272204712300545`

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

## LTXV Two-Image Video With Negative Prompt `2060674924032905217`

Use when two source images guide an LTXV video and the workflow exposes a negative text node.

```json
[
  {"nodeId":"98","fieldName":"image","fieldValue":"@upload:/absolute/path/source1.png"},
  {"nodeId":"214","fieldName":"image","fieldValue":"@upload:/absolute/path/source2.png"},
  {"nodeId":"113","fieldName":"text","fieldValue":"pc game, console game, video game, cartoon, childish, ugly, subtitles, caption, captions, closed captions"}
]
```

## LTX Director Text Video `2059132036383858689`

Use for English cinematic text-to-video with duration and fps.

```json
[
  {"nodeId":"46","fieldName":"global_prompt","fieldValue":"A cinematic shot of a futuristic city at night, neon lights reflecting on wet streets, slow dolly forward"},
  {"nodeId":"46","fieldName":"duration_seconds","fieldValue":"10"},
  {"nodeId":"46","fieldName":"frame_rate","fieldValue":"24"}
]
```

## Virtual Try-On / Qwen Image Edit `2061692914857766913`

Use for person image plus garment or style instruction.

```json
[
  {"nodeId":"74","fieldName":"image","fieldValue":"@upload:/absolute/path/person.png"},
  {"nodeId":"68","fieldName":"prompt","fieldValue":"一位穿着时尚连衣裙的模特站在白色背景前，保留人物姿态和身份"},
  {"nodeId":"61","fieldName":"prompt","fieldValue":"文字、水印、低质量"},
  {"nodeId":"103","fieldName":"text","fieldValue":"时尚连衣裙"}
]
```

## AI App: Clothing Extraction `2005542596594331650`

Use for one-person image AI App calls. Run with `--type webapp`.

```json
[
  {"nodeId":"78","fieldName":"image","fieldValue":"@upload:/absolute/path/person.png"}
]
```

## AI App: Image + Video Garment Dance `2046575818536652802`

Use when the app requires matching image/video aspect ratio and exposes width, height, duration, image, and video nodes. Run with `--type webapp`.

```json
[
  {"nodeId":"255","fieldName":"value","fieldValue":"10"},
  {"nodeId":"264","fieldName":"value","fieldValue":"720"},
  {"nodeId":"265","fieldName":"value","fieldValue":"1280"},
  {"nodeId":"167","fieldName":"image","fieldValue":"@upload:/absolute/path/model.jpg"},
  {"nodeId":"52","fieldName":"video","fieldValue":"@upload:/absolute/path/dance.mp4"}
]
```

Keep image and video aspect ratio consistent. For vertical dance/selfie content use 720x1280; for walking landscape use 1280x720; for 4:3 walking use 1280x960.
