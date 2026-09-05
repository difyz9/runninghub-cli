"""RunningHub SDK CLI Tools

Standalone CLI tools:
  - rh-first2last: First+last frame to transition video
  - rh-merge:      Local video merging via ffmpeg
  - rh-pipeline:   Full pipeline orchestrator
  - rh-storyboard: Storyboard generation via DeepSeek + RunningHub
  - rh-runner:     Universal runner — call any workflow/AI app by ID + node overrides

For text-to-image and image-to-video, use the runner directly:
  rh-runner --mode workflow --id 2037071836214730753 --nodes '...'   # txt2img
  rh-runner --mode workflow --id 2037036284312559617 --nodes '...'   # img2vid
  See SKILL.md for complete parameter documentation.
"""
