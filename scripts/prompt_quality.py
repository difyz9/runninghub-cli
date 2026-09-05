"""
Prompt Quality Engine — 高质量的提示词生成与验证系统

核心功能:
1. 自动选择合适风格 (StyleSelector)
2. LLM 扩写为专业提示词 (DeepSeek)
3. 质量自检评分并自动修复
4. 提供已验证的提示词模板参考

用法:
    from prompt_quality import PromptEngine
    engine = PromptEngine()
    result = engine.generate("古风美女樱花树下", workflow_type="txt2img")
    # → {"prompt": "...", "style": "水墨淡染国风", "score": 92, "verified": true}
"""

import json
import os
import sys
import re
import time
from pathlib import Path
from typing import Optional

# Opik 运行记录跟踪（可选 — 无依赖、零服务器）
try:
    from scripts.opik_tracker import tracker as opik_tracker
    _OPIK_AVAILABLE = True
except ImportError:
    _OPIK_AVAILABLE = False

# 尝试导入 style_selector
try:
    from scripts.style_selector import StyleSelector, load_styles
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.style_selector import StyleSelector, load_styles


# ════════════════════════════════════════════════════════════════
# 规则引擎 — 不需要 LLM 即可做基础质量验证
# ════════════════════════════════════════════════════════════════

# 每种工作流类型的质量规则
QUALITY_RULES = {
    "txt2img": {
        "language": "en",  # T2I 必须英文
        "min_words": 15,
        "max_words": 120,
        "required_elements": ["主体(subject)", "光线(lighting)", "画质词(quality)"],
        "must_contain": ["highly detailed", "detailed", "quality", "8K", "cinematic", "sharp"],
        "must_avoid": ["中文", "模糊", "低质量"],
        "good_examples": [
            "a majestic white wolf standing on a rocky cliff, glowing blue eyes, aurora borealis, epic fantasy, highly detailed, cinematic lighting, 8K",
            "a traditional Chinese girl in hanfu under cherry blossom tree, soft pink petals falling, ink wash painting style, low saturation, ethereal mist, elegant composition, 8K",
        ],
        "bad_examples": [
            "古风美女樱花树下",  # 中文给英文工作流
            "a girl, tree, flowers",  # 太简单
            "beautiful woman cherry blossom ultra HD",  # 缺少光线/构图
        ],
    },
    "txt2vid": {
        "language": "zh",  # T2V 中文叙事
        "min_words": 20,
        "max_words": 200,
        "required_elements": ["场景描述(scene)", "动作(motion)", "氛围(atmosphere)"],
        "must_contain": [],
        "must_avoid": ["英文长句"],
        "good_examples": [
            "场景：黄昏时分的大学操场，少年少女在夕阳下散步，金色阳光透过树叶洒在地面，微风吹动发梢和裙摆，画面温暖治愈，光影柔和",
            "场景：古风美女站在樱花树下，微风拂过花瓣纷飞，她抬头看向飘落的花瓣，眼神温柔，水墨淡彩中国风，素雅清冷",
        ],
        "bad_examples": [
            "a girl walking under cherry blossom tree",  # 英文给视频，不适合
            "美女樱花树下",  # 太简单，无动作场景
        ],
    },
    "img2vid": {
        "language": "zh",
        "min_words": 10,
        "max_words": 100,
        "required_elements": ["运动描述(motion)", "氛围(atmosphere)"],
        "must_contain": [],
        "must_avoid": ["无意义的描述"],
        "good_examples": [
            "镜头缓慢推进，微风吹动发梢和花瓣，夕阳金色光晕在镜头中闪烁，画面温暖治愈",
            "镜头缓缓上移，从水面倒影拉至人物全景，烟雾缭绕，意境悠远",
        ],
        "bad_examples": [
            "人物动起来",  # 太简单
        ],
    },
    "music": {
        "language": "zh",
        "min_words": 15,
        "max_words": 100,
        "required_elements": ["风格(genre)", "情绪(mood)", "乐器(instruments)"],
        "must_contain": [],
        "must_avoid": ["英文作词"],
        "good_examples": [
            "一首青春校园风格的流行歌曲，男声温暖治愈，钢琴轻快节奏，吉他扫弦，歌词关于夏天和暗恋，BPM 90",
            "古风抒情曲，女声柔美，琵琶古笛合奏，意境空灵悠远，节奏舒缓",
        ],
        "bad_examples": [
            "write a pop song about love",
        ],
    },
}


def detect_language(text: str) -> str:
    """检测文本主要语言"""
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    return "zh" if cn_chars > en_chars else "en"


def score_prompt_quality(prompt: str, workflow_type: str = "txt2img") -> dict:
    """
    对提示词进行质量评分 (0-100)
    完全基于规则引擎，无需 LLM

    扣分项:
    - 语言不匹配
    - 字数过多/过少
    - 缺少必填要素
    - 出现坏词汇
    - 缺少画质词 (T2I)
    """
    rules = QUALITY_RULES.get(workflow_type, QUALITY_RULES["txt2img"])
    score = 100
    issues = []

    # 1. 语言检查
    lang = detect_language(prompt)
    if lang != rules["language"]:
        if rules["language"] == "en":
            score -= 30
            issues.append(f"语言错误: 工作流要求英文，检测到中文。建议将中文场景描述转为英文关键词")
        else:
            score -= 30
            issues.append(f"语言错误: 工作流要求中文，检测到英文。建议使用中文叙事段落")

    # 2. 字数检查
    word_count = len(prompt.split())
    if lang == "zh":
        # 中文字数按字符
        word_count = len(re.findall(r'[\u4e00-\u9fff]', prompt))

    if word_count < rules["min_words"]:
        score -= 20
        issues.append(f"字数不足: 仅{word_count}字/{rules['min_words']}字最少要求。建议增加细节描述")
    elif word_count > rules["max_words"]:
        score -= 10
        issues.append(f"字数过多: {word_count}>{rules['max_words']}。可以精简冗余词")

    # 3. 必须包含的关键词
    if rules["must_contain"]:
        has_quality_words = any(kw in prompt.lower() for kw in rules["must_contain"])
        if not has_quality_words and lang == "en":
            score -= 15
            issues.append(f"缺少画质词: 建议加入画质修饰词 (highly detailed, cinematic lighting, 8K)")

    # 4. 坏词汇检查
    for bad in rules["must_avoid"]:
        if bad.lower() in prompt.lower():
            score -= 15
            issues.append(f"包含不推荐元素: '{bad}'")

    # 5. 风格检查
    style_keywords = _check_style_keywords(prompt, workflow_type)
    if style_keywords:
        score += min(15, style_keywords * 5)
        if style_keywords >= 2:
            issues.append(f"✓ 已含风格关键词 ({style_keywords}个)")
    else:
        score -= 10
        issues.append("缺少风格关键词: 建议加入调色风格描述 (如韩系奶油、赛博朋克、水墨国风等)")

    # 6. 结构检查
    if workflow_type in ("txt2vid", "txt2video", "img2vid", "i2v"):
        if "场景：" in prompt or "风格：" in prompt or "画面" in prompt:
            score += 10
            issues.append("✓ 结构完整: 场景+风格分层清晰")
        else:
            score -= 10
            issues.append("建议结构化: 使用'场景：'开头，描述画面+动作+氛围")

    # 最终分数限定
    score = max(0, min(100, score))

    return {
        "score": score,
        "issues": issues,
        "language": lang,
        "word_count": word_count,
    }


def _check_style_keywords(prompt: str, workflow_type: str) -> int:
    """检查提示词中是否包含风格关键词"""
    style_terms = [
        "奶油", "日系", "港风", "胶片", "富士", "柯达", "INS", "极简",
        "Y2K", "千禧", "赛博朋克", "赛博", "霓虹", "工业", "机能",
        "VHS", "漫画", "水墨", "国风", "青绿", "敦煌", "国潮",
        "油画", "水彩", "素描", "新海诚", "黏土", "扁平",
        "古风", "汉服", "新中式",
        "色调", "调色", "光晕", "暖调", "冷调", "暗调",
        "vintage", "retro", "cyberpunk", "cinematic", "film",
        "glow", "neon", "pastel", "moody", "dramatic",
        "soft light", "golden hour", "rim light", "volumetric",
        # 影视风格关键词
        "韦斯安德森", "wes anderson", "王家卫", "wong kar",
        "芬奇", "fincher", "张艺谋", "维伦纽瓦", "villeneuve",
        "吉卜力", "ghibli", "宫崎骏", "film noir", "黑色电影",
        "诺兰", "nolan", "马利克", "malick", "雷德利", "ridley scott",
        "今敏", "satoshi kon", "黑泽明", "kurosawa",
        "卡隆", "cuaron", "合成波", "synthwave",
        "阿伦诺夫斯基", "aronofsky", "IMAX", "65mm",
        # 电影镜头语言
        "对称构图", "长镜头", "深焦", "推轨", "斯坦尼康",
        "手持镜头", "特写", "大广角", "抽帧",
        "chiaroscuro", "long take", "deep focus",
    ]
    count = 0
    prompt_lower = prompt.lower()
    for term in style_terms:
        if term.lower() in prompt_lower:
            count += 1
    return count


def auto_fix_prompt(prompt: str, workflow_type: str = "txt2img", scene_desc: str = "") -> dict:
    """
    自动修复提示词质量
    返回修复后的提示词和质量报告
    """
    report = score_prompt_quality(prompt, workflow_type)
    fixed = prompt

    if report["score"] >= 80:
        return {"prompt": fixed, "report": report, "fixed": False}

    # 尝试使用 StyleSelector 注入风格
    try:
        selector = StyleSelector()
        style_result = selector.select(scene_desc or prompt, workflow_type)
        if style_result["style_id"] != "generic":
            fixed = style_result["prompt"]
    except Exception:
        pass

    # 如果还是分数低，做基础增强
    new_report = score_prompt_quality(fixed, workflow_type)
    if new_report["score"] < 80:
        # 手动注入一些通用质量词
        if workflow_type in ("txt2img", "txt2image", "t2i"):
            if not any(kw in fixed.lower() for kw in ["8k", "detailed", "hdr"]):
                fixed += ", highly detailed, cinematic lighting, 8K, sharp focus, HDR"
        elif workflow_type in ("txt2vid", "txt2video", "t2v"):
            if not fixed.startswith("场景："):
                fixed = f"场景：{scene_desc or prompt}\n风格：电影感叙事，光影柔和，色彩自然"

    final_report = score_prompt_quality(fixed, workflow_type)
    return {"prompt": fixed, "report": final_report, "fixed": True, "original_report": report}


# ════════════════════════════════════════════════════════════════
# LLM 增强 — 调用 DeepSeek 扩写高质量提示词
# ════════════════════════════════════════════════════════════════

def _call_llm(prompt: str, system: str, timeout: int = 30) -> Optional[str]:
    """调用 DeepSeek API 进行提示词扩写"""
    import urllib.request
    import urllib.error

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("RUNNINGHUB_API_KEY")
    if not api_key:
        return None

    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except Exception:
        return None


def llm_enhance(scene_desc: str, workflow_type: str = "txt2img", style_name: str = "") -> Optional[str]:
    """
    用 LLM 将场景描述扩写为高质量提示词
    返回 None 表示 LLM 不可用
    """
    style_hint = f"使用'{style_name}'风格" if style_name else "自动选择最合适的调色风格"

    if workflow_type in ("txt2img", "txt2image", "t2i"):
        system = (
            "你是一位专业的 AI 绘画提示词工程师。你的任务是将用户的中文场景描述，"
            "转换成一组高质量的英文提示词（仅输出提示词本身，不要额外解释）。\n\n"
            "要求：\n"
            "1. 必须使用英文，语法正确\n"
            "2. 包含：主体描述、环境/背景、光线、构图、画质词\n"
            "3. 适当使用风格标签（如: cinematic, volumetric lighting, 8K）\n"
            "4. {style_hint}\n"
            "5. 如果用户描述中有风格暗示（古风、日系、赛博朋克等），自动融入\n"
            "6. 输出的提示词应当简洁有力，20-60个英文词为宜\n\n"
            "参考好例子：\n"
            "- 'a traditional Chinese ink painting style beauty under cherry blossom tree, hanfu dress, soft pink petals falling, misty atmosphere, low saturation, elegant composition, highly detailed, 8K'"
        )

    elif workflow_type in ("txt2vid", "txt2video", "t2v"):
        system = (
            "你是一位专业的 AI 视频提示词工程师。你的任务是将用户的中文场景描述，"
            "扩展为高质量的叙事性提示词（中文，仅输出提示词本身）。\n\n"
            "要求：\n"
            "1. 使用中文，以'场景：'开头\n"
            "2. 描述画面构成 + 人物动作 + 光线氛围 + 镜头运动\n"
            "3. {style_hint}\n"
            "4. 输出应当像一段有画面感的文字，30-80字\n\n"
            "参考好例子：\n"
            "- '场景：黄昏时分的大学操场，少年少女在夕阳下散步，金色阳光透过树叶洒在地面，微风吹动发梢和裙摆，画面温暖治愈，柔光漫射'"
        )

    elif workflow_type in ("img2vid", "i2v"):
        system = (
            "你是一位专业的 AI 视频提示词工程师。你的任务是将用户的中文场景描述，"
            "转换为镜头运动+氛围描述（中文，仅输出提示词本身）。\n\n"
            "要求：\n"
            "1. 描述画面中的运动（镜头推拉摇移、人物动作、自然动态）\n"
            "2. 描述光照变化和氛围\n"
            "3. 10-50字\n\n"
            "参考好例子：\n"
            "- '镜头缓慢推进，微风吹动发梢和花瓣，夕阳金色光晕在镜头中闪烁，画面温暖治愈'"
        )

    elif workflow_type == "music":
        system = (
            "你是一位专业的 AI 音乐提示词工程师。你的任务是将用户的中文描述，"
            "转换为高质量的音乐生成提示词（中文，仅输出提示词本身）。\n\n"
            "要求：\n"
            "1. 包含：风格、情绪、乐器、节奏\n"
            "2. {style_hint}\n"
            "3. 20-60字\n\n"
            "参考好例子：\n"
            "- '一首青春校园风格的流行歌曲，男声温暖治愈，钢琴轻快节奏，吉他扫弦，BPM 90'"
        )

    else:
        return None

    system = system.replace("{style_hint}", style_hint)
    return _call_llm(scene_desc, system)


# ════════════════════════════════════════════════════════════════
# 主引擎
# ════════════════════════════════════════════════════════════════

class PromptEngine:
    """提示词质量引擎 — 一站式生成高质量提示词"""

    def __init__(self):
        self.selector = StyleSelector()
        self.styles, self.enhancers = load_styles()

    def list_styles(self, genre: str = None) -> list:
        """列出可用风格，可按类别筛选"""
        all_styles = self.selector.list_all_styles()
        if genre:
            return [s for s in all_styles if s.get("genre") == genre]
        return all_styles

    def list_genres(self) -> dict:
        """按类别分组列出"""
        return self.selector.list_by_genre()

    def generate(
        self,
        scene_desc: str,
        workflow_type: str = "txt2img",
        force_style: str = "",
        use_llm: bool = True,
        quality_check: bool = True,
    ) -> dict:
        """
        高质量提示词生成

        参数:
            scene_desc: 场景描述（中文/英文）
            workflow_type: txt2img / txt2vid / img2vid / music
            force_style: 强制指定风格ID（可选）
            use_llm: 是否使用 LLM 扩写
            quality_check: 是否进行质量自检

        返回:
            {
                "prompt": "最终提示词",
                "style": {"id": ..., "name": ...},
                "quality": {"score": ..., "issues": [...]},
                "verified": true/false,
                "mode": "llm" / "quick" / "auto_fixed"
            }
        """
        # 1. 选择风格
        if force_style and force_style in self.selector.styles:
            style_info = self.selector.styles[force_style]
            style = {
                "id": force_style,
                "name": style_info["name"],
                "keywords": style_info.get("keywords", ""),
                "tags": style_info.get("tags", ""),
            }
        else:
            matched = self.selector.select(scene_desc, workflow_type)
            style = {
                "id": matched["style_id"],
                "name": matched["style_name"],
                "keywords": matched.get("keywords", ""),
                "tags": matched.get("tags", ""),
            }

        # 2. 生成提示词
        prompt = ""
        mode = "quick"

        if use_llm:
            llm_result = llm_enhance(scene_desc, workflow_type, style["name"])
            if llm_result:
                prompt = llm_result
                mode = "llm"

        # LLM 失败或未启用时的回退方案
        if not prompt:
            if workflow_type in ("txt2img", "txt2image", "t2i"):
                prompt = f"{scene_desc}, {style['tags']}, highly detailed, cinematic lighting, 8K, sharp focus"
            elif workflow_type in ("txt2vid", "txt2video", "t2v"):
                prompt = f"场景：{scene_desc}\n风格：{style['keywords']}"
            elif workflow_type in ("img2vid", "i2v"):
                prompt = f"{scene_desc}，{style['keywords']}"
            else:
                prompt = scene_desc

        # 3. 质量自检
        quality = None
        verified = False
        if quality_check:
            quality = score_prompt_quality(prompt, workflow_type)
            if quality["score"] < 80:
                # 自动修复
                fixed = auto_fix_prompt(prompt, workflow_type, scene_desc)
                if fixed["fixed"] and fixed["report"]["score"] > quality["score"]:
                    prompt = fixed["prompt"]
                    quality = fixed["report"]
                    mode = "auto_fixed"
            if quality["score"] >= 80:
                verified = True

        # 4. 记录 Opik trace（自动追踪每次提示词生成）
        if _OPIK_AVAILABLE:
            try:
                opik_tracker.start_trace(
                    name=f"提示词生成 ({workflow_type})",
                    project="prompt-quality",
                    metadata={
                        "workflow_type": workflow_type,
                        "style_id": style["id"],
                        "style_name": style["name"],
                        "verified": verified,
                        "mode": mode,
                    },
                )
                opik_tracker.log_input({
                    "scene_desc": scene_desc,
                    "force_style": force_style if force_style else "auto",
                    "use_llm": use_llm,
                })
                opik_tracker.log("风格选择", {
                    "scene": scene_desc,
                }, {
                    "style": style["name"],
                    "style_id": style["id"],
                })
                if quality:
                    opik_tracker.log("质量检测", {
                        "score": quality["score"],
                        "issues": quality.get("issues", []),
                    }, {
                        "verified": verified,
                    })
                opik_tracker.end_trace({
                    "prompt_preview": prompt[:150],
                    "score": quality["score"] if quality else None,
                    "verified": verified,
                })
            except Exception:
                pass  # 追踪失败不影响主流程

        return {
            "prompt": prompt,
            "style": style,
            "quality": quality,
            "verified": verified,
            "mode": mode,
        }


# ════════════════════════════════════════════════════════════════
# 快速测试
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = PromptEngine()

    print("=" * 60)
    print("🎨 提示词质量引擎 — 测试运行")
    print("=" * 60)

    test_cases = [
        ("古风美女樱花树下", "txt2img"),
        ("黄昏操场少年少女散步", "txt2vid"),
        ("一碗热气腾腾的牛肉面", "txt2img"),
        ("城市夜景赛博朋克霓虹灯", "txt2img"),
        ("伤感深夜独处窗边", "txt2vid"),
    ]

    for desc, wtype in test_cases:
        print(f"\n{'─' * 50}")
        print(f"📝 场景: {desc}  [{wtype}]")

        # 快速模式
        result = engine.generate(desc, wtype, use_llm=False)
        print(f"  风格: {result['style']['name']} ({result['style']['id']})")
        print(f"  模式: {result['mode']}")
        print(f"  质量: {result['quality']['score']}/100")
        if result['verified']:
            print(f"  ✅ 已验证通过 (≥80分)")
        for issue in result['quality']['issues']:
            print(f"     ⚡ {issue}")
        print(f"  提示词:\n    {result['prompt'][:200]}...")

        # 尝试 LLM 模式
        if os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("RUNNINGHUB_API_KEY"):
            llm_result = engine.generate(desc, wtype, use_llm=True)
            if llm_result["mode"] == "llm":
                print(f"\n  🤖 LLM增强版:")
                print(f"  提示词: {llm_result['prompt'][:200]}...")

    print(f"\n{'=' * 60}")
    print("✅ 测试完成")
