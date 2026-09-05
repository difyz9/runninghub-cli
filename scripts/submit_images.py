#!/usr/bin/env python3
"""批量提交文生图任务 - 使用shell=True调用runhub CLI"""

import json
import os
import subprocess
import time

API_KEY = os.environ.get("RUNNINGHUB_API_KEY", "")
if not API_KEY:
    raise SystemExit("请先设置环境变量 RUNNINGHUB_API_KEY")
APP_ID = "2065150199546335234"
TASK_FILE = "/Users/apple/Documents/电子书合集/EPUB/task_ids.txt"

PROMPTS = [
    "In the style of E.H. Shepard, delicate pen and ink with soft watercolor wash. A lone modern figure in a suit sits slumped at a desk, surrounded by a labyrinth of tall wooden rulers that form cage-like walls around him. Each ruler is marked with tiny numbers. Muted sepia and grey tones. Gentle nostalgic melancholy atmosphere. Simple expressive lines. Storybook illustration composition.",
    "In the style of E.H. Shepard, soft watercolor illustration. An ancient Chinese philosopher in flowing robes stands calmly among crumbling wooden rulers that break apart like dry twigs. Warm golden light breaks through from above. Fine cross-hatched pen work on the robes. Gentle hopeful atmosphere. Pastoral English countryside meets classical Chinese figure. Storybook charm.",
    "In the style of E.H. Shepard, fine pen and ink drawing with faint warm watercolor wash. A young girl's hand resting on a wooden table, six slender fingers gently splayed. The sixth finger catches a soft ray of light through a window. Simple domestic interior. Nostalgic and tender. Minimalist composition with lots of negative space. Watercolor in warm ochre and pale cream.",
    "In the style of E.H. Shepard, soft watercolor illustration. Two shadowy adult figures stand on opposite sides of a small kitchen table, leaning toward each other in heated argument. A broken wooden ruler lies on the table between them. A child's silhouette watches from the doorway. Muted evening tones. Gentle sadness. Expressive simple linework.",
    "In the style of E.H. Shepard, delicate pen drawing. A young girl curled up on the floor in a corner of a room, her face buried in her knees. Soft grey and pale blue watercolor wash around her like a puddle of shadow. A single fallen ruler nearby. Simple poignant composition. Deep empathy in the linework. Nostalgic melancholy.",
    "In the style of E.H. Shepard, fine ink illustration with watercolor. An open ancient Chinese book on a wooden desk. One page shows the handwritten characters '骈拇' in elegant brushstrokes, the other page has a delicate drawing of a six-fingered hand. Soft candlelight illuminates the pages. Warm sepia and parchment tones. Quiet scholarly atmosphere.",
    "In the style of E.H. Shepard, pen drawing with soft wash. A crowd of identical faceless figures in muted grey walking in one direction, while a single small figure in warm ochre walks the opposite way. The lone figure stands out vividly against the grey crowd. Gentle pastoral background of rolling hills. Poignant, understated. Classic storybook composition.",
    "In the style of E.H. Shepard, delicate watercolor illustration. A wildflower growing from a crack in an old stone wall, untrimmed and unshaped, swaying gently in the breeze. Soft green and pale pink washes. Fine pen detail on the leaves and stone texture. Open sky background with soft clouds. Peaceful, natural beauty. Classic English countryside charm.",
    "In the style of E.H. Shepard, fine ink illustration. A man stands before a full-length mirror, but his reflection is covered in tiny measurement marks and labels like a tailor's pattern. Soft grey watercolor wash. The man's posture is slumped, defeated. Simple bedroom interior with wooden floorboards. Quiet contemplation. Gentle poignant mood.",
    "In the style of E.H. Shepard, pen and ink with watercolor wash. Two figures stand facing each other in a field, each holding a long wooden ruler that points at the other. The rulers cross in the middle forming an X shape. Soft green hills in background. Muted autumn colors. Symmetrical composition. Gentle absurdity with warmth.",
    "In the style of E.H. Shepard, intimate pen drawing. A young person's face in close profile, a tiny golden coin reflected in their eye. Soft warm watercolor in amber and cream tones. The rest of the face remains in delicate ink outline. Minimalist. Introspective. Gentle melancholy. Storybook portrait style.",
    "In the style of E.H. Shepard, fine line drawing. A face drawn as a blank oval with delicate dotted guide lines crossing it like a proportion study. Soft pale watercolor wash. A wooden ruler rests against the cheek. Clinical yet gentle. Academic sketch quality. Warm beige paper texture.",
    "In the style of E.H. Shepard, ink and wash illustration. A stack of old leather-bound books piled unevenly like a tower, with a traditional scholar's cap perched precariously on top. Soft golden light from a nearby window. Warm brown and faded red tones. Quiet library atmosphere. Gentle whimsy.",
    "In the style of E.H. Shepard, delicate pen drawing with watercolor. A scholar's ink brush, a qin zither, a scroll, and a Go board float in a gentle spiral around a seated figure. Fine lines and soft washes in muted ink tones with a touch of faded gold. Dreamy, whimsical. Open window showing a pastoral view. Storybook magic.",
    "In the style of E.H. Shepard, intimate watercolor. A person sits alone holding an old round bronze mirror, gazing at their own reflection. The reflection in the mirror glows with a soft warm light. Candlelit room. Gentle introspection. Fine pen detail on the mirror's ornate edge. Deep calm and acceptance. Nostalgic warmth.",
    "In the style of E.H. Shepard, soft watercolor illustration. A hand over a heart, gently lifting a glowing wooden ruler away from the chest. The ruler begins to dissolve into floating ink particles. Warm golden light emanates from where the ruler was. Simple backdrop. Quiet powerful moment. Redemption and release. Storybook tenderness.",
    "In the style of E.H. Shepard, watercolor illustration. A young ancient Chinese woman in traditional robes sits in a simple wooden carriage, weeping into her sleeve as the carriage departs down a dusty road. Her family stands small in the distance. Soft grey and muted blue washes. Autumn trees with bare branches. Melancholic yet beautiful.",
    "In the style of E.H. Shepard, warm watercolor scene. The same woman now stands in a grand palace hall, wearing elegant silk robes in soft crimson and gold. Warm lantern light fills the room. Delicate architectural details in fine pen. She looks around with quiet wonder. Rich warm palette contrasting with the previous grey tones. Fairy tale transformation.",
    "In the style of E.H. Shepard, delicate ink and wash. The woman turns her head and smiles softly over her shoulder, her earlier tears transforming into tiny flower petals carried away by the wind. The left half of the composition is muted grey past, the right half warm golden light present. Poetic visual metaphor. Gentle whimsy.",
    "In the style of E.H. Shepard, watercolor nature study. A single branch with two blossoms: one side withering in soft brown tones, the other side blooming in pale pink. Gentle gradient transition between the two states. Soft blurred background in green and cream. Poetic simplicity. Classic botanical illustration charm.",
    "In the style of E.H. Shepard, expansive watercolor landscape. A small figure stands in an open field, releasing a wooden ruler from their hand as it dissolves into floating particles. Wide sky with soft clouds. Rolling green hills stretching to the horizon. Warm golden hour light. Sense of release and freedom. Pastoral serenity.",
    "In the style of E.H. Shepard, elegant pen and ink with soft wash. The Chinese characters '当下' written in flowing calligraphy, but rendered with a fine nib like E.H. Shepard's hand. Soft warm golden watercolor glow behind the characters. Simple, uncluttered. Meditative quality. Ink splatters like tiny birds in the margins.",
    "In the style of E.H. Shepard, storybook illustration. A figure with their back to us tears open a heavy curtain covered in dense tiny handwriting, a script written by others. Through the torn opening, a beautiful pastoral landscape is revealed. Curtain fragments fall like masks. Dramatic warm light pours through the tear. Liberation. Hope.",
    "In the style of E.H. Shepard, wide landscape watercolor. A lone figure walks toward the distant horizon along a winding path. Behind them lie broken rulers and discarded masks. Ahead: open rolling hills under a soft golden sky. Fine pen lines in the grass and distant trees. The ultimate sense of peace and freedom. Closing storybook image. Full circle warmth.",
]

def submit(label, prompt):
    """提交一个任务，返回(task_id, ok)"""
    node_overrides = json.dumps([{"nodeId": "70", "fieldName": "text", "fieldValue": prompt}])
    cmd = f"RUNNINGHUB_API_KEY={API_KEY} runhub submit {APP_ID} --type webapp --node-overrides '{node_overrides}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            return data["data"]["task_id"], True
        else:
            return data.get("error", "unknown"), False
    except:
        return result.stderr[:100], False

def check_status(task_id):
    """查询任务状态"""
    cmd = f"RUNNINGHUB_API_KEY={API_KEY} runhub status {task_id}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return data.get("data", {}).get("task_status", "UNKNOWN")
    except:
        return "ERROR"

# === 主流程 ===
results = []
active = {}  # task_id -> label
total = len(PROMPTS)
done = 0

print(f"开始提交 {total} 个文生图任务（2并发）...")
print("=" * 50)

while done < total:
    # 补满活跃任务到2个
    while len(active) < 2 and done < total:
        label = f"场景{done + 1}"
        prompt = PROMPTS[done]
        print(f"  {label} 提交中...", end=" ", flush=True)
        task_id, ok = submit(label, prompt)
        if ok:
            active[task_id] = label
            results.append(f"{label}:{task_id}")
            print(f"✓ {task_id}")
            done += 1
            # 即时保存
            with open(TASK_FILE, "w") as f:
                f.write("\n".join(results))
        else:
            if "TASK_QUEUE_MAXED" in str(task_id):
                print("⏳ 队列满")
                break
            else:
                print(f"✗ {task_id}")
                done += 1  # 跳过失败
        time.sleep(0.3)

    # 如果活跃任务已达上限，轮询等待
    if len(active) >= 2 or done >= total:
        if not active:
            break
        time.sleep(8)
        finished = []
        for tid, lbl in active.items():
            status = check_status(tid)
            print(f"  {lbl}: {status}")
            if status in ("SUCCESS", "FAILED", "ERROR"):
                finished.append(tid)
        for tid in finished:
            del active[tid]
    else:
        time.sleep(3)

print("=" * 50)
print(f"✅ 提交完成: {len(results)}/{total}")
print(f"📄 {TASK_FILE}")

# 最终保存
with open(TASK_FILE, "w") as f:
    f.write("\n".join(results))
print("\n已保存 task_ids:")
for r in results:
    print(f"  {r}")
