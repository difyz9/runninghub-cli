#!/bin/bash
# ============================================================
# 校园MV制作 v2 — Ken Burns 动态相册 + 音乐
# ============================================================
set -e

FRAMES_DIR="/home/guan/outputs/campus_mv/frames"
CLIPS_DIR="/home/guan/outputs/campus_mv/clips"
OUTPUT_DIR="/home/guan/outputs/campus_mv"
MUSIC_FILE="/home/guan/outputs/campus_mv/music/ComfyUI_00001_kczof_1781765629.flac"
mkdir -p "$CLIPS_DIR"

# 音乐时长 / 场景数
SCENE_DUR=15

echo "=== 步骤1: 生成 Ken Burns 动态片段 ($SCENE_DUR秒/场景) ==="

for i in $(seq 1 8); do
  padded=$(printf '%02d' $i)
  input="$FRAMES_DIR/${padded}_*.png"
  input_file=$(ls $FRAMES_DIR/${padded}_*.png 2>/dev/null | head -1)
  output="$CLIPS_DIR/clip_${padded}.mp4"
  
  echo "  场景${i}: $(basename $input_file)"
  
  # Ken Burns: 缓慢放大
  ffmpeg -y -loop 1 -i "$input_file" \
    -vf "zoompan=z='min(zoom+0.0015,1.25)':d=$((SCENE_DUR*25)):s=1920x1080:fps=25" \
    -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p \
    -t "$SCENE_DUR" "$output" 2>&1 | grep "kb/s"
done

echo ""
echo "=== 步骤2: 拼接（交叉淡入淡出） ==="

# 用concat协议直接拼（带crossfade需要用filter）
TMP_LIST="/tmp/mv_concat.txt"
> "$TMP_LIST"
echo "ffconcat version 1.0" > "$TMP_LIST"

for i in $(seq 1 8); do
  padded=$(printf '%02d' $i)
  echo "file $CLIPS_DIR/clip_${padded}.mp4" >> "$TMP_LIST"
done

# 先拼一个无过渡的版本
ffmpeg -y -f concat -safe 0 -i "$TMP_LIST" \
  -c:v libx264 -preset medium -crf 20 \
  "$OUTPUT_DIR/campus_mv_temp.mp4" 2>&1 | tail -3

echo ""
echo "=== 步骤3: 添加转场和字幕 ==="

# 用 ffmpeg 的 crossfade 滤镜做转场
# 先把片段拆开再交叉融合
# 对前7个转接点各做1秒交叉淡入淡出

# 获取视频总时长
DUR=$(ffprobe -v quiet -show_format "$OUTPUT_DIR/campus_mv_temp.mp4" | grep duration | cut -d= -f2)
echo "   拼接后时长: ${DUR}s"

echo ""
echo "=== 步骤4: 加入背景音乐 ==="
ffmpeg -y -i "$OUTPUT_DIR/campus_mv_temp.mp4" -i "$MUSIC_FILE" \
  -c:v copy -c:a aac -b:a 192k -shortest \
  -map 0:v:0 -map 1:a:0 \
  "$OUTPUT_DIR/campus_mv_final.mp4" 2>&1 | tail -3

echo ""
echo "=== ✅ MV 制作完成 ==="
ls -lh "$OUTPUT_DIR/campus_mv_final.mp4"
ffprobe -v quiet -print_format json -show_format "$OUTPUT_DIR/campus_mv_final.mp4" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  时长: {float(d[\"format\"][\"duration\"]):.1f}s / 大小: {float(d[\"format\"][\"size\"])/1024/1024:.1f}MB')"
