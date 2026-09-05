"""
风格选择器 — 从 color_grading_styles.yaml 自动选择匹配的风格关键词
并注入到提示词中，确保每次生成的提示词都带专业调色描述

用法:
    from style_selector import StyleSelector
    selector = StyleSelector()
    result = selector.select("古风美女在樱花树下", workflow_type="txt2img")
    # → {"style": "ink_wash_guofeng", "prompt": "..."}
"""

import yaml
import os
import re
from pathlib import Path

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry" / "color_grading_styles.yaml"
_default_styles = None


def load_styles(path=None):
    """加载风格注册表"""
    p = Path(path or _REGISTRY_PATH)
    if not p.exists():
        raise FileNotFoundError(f"风格注册表未找到: {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("styles", {}), data.get("universal_enhancers", [])


# ============================================================
# 关键词 → 风格 匹配规则
# ============================================================

# 中文场景关键词 → 风格归类
_SCENE_TAGS = {
    # 人像
    "人像_韩系": ["韩系奶油", "韩系奶油柔光", "奶油调", "韩系", "粉嫩"],
    "人像_日系": ["日系", "清新", "治愈", "生活记录", "自然光"],
    "人像_港风": ["港风", "港式", "港味", "复古人像", "红橙"],
    "人像_胶片": ["胶片", "复古人像", "富士", "柯达", "暖黄"],
    "人像_ins": ["INS", "极简", "冷淡", "冷白", "莫兰迪", "高级感"],
    "人像_y2k": ["Y2K", "千禧", "辣妹", "甜辣", "街头", "荧光"],
    "美食_暖调": ["美食", "探店", "烹饪", "做菜", "美食特写", "食欲", "面", "饭", "汤", "菜", "烤肉", "火锅", "炒", "蒸", "煎", "煮", "甜品", "饮料", "饮品",
"诱人", "热气腾腾"],

    "美食_纪实": ["市井", "街头美食", "夜市", "小吃", "摆摊", "路边摊", "大排档"],

    "美食_暗调": ["西餐", "甜品", "咖啡", "精致料理", "高级餐厅", "法餐", "日料", "摆盘", "精致"],

    # 旅拍
    "旅拍_通透": ["旅拍", "旅行", "航拍", "蓝天", "海边", "山野", "风景", "大自然", "户外", "度假", "旅游", "沙滩"],
    "旅拍_电影": ["电影感", "宽屏", "史诗", "大片", "风光大片", "航拍"],
    "旅拍_公路": ["公路", "旷野", "自驾", "旅行记录", "复古旅行"],

    # 国风
    "国风_水墨": ["古风", "汉服", "水墨", "国风", "新中式", "江南", "烟雨", "青灰", "素雅"],
    "国风_青绿": ["青绿", "山水", "园林", "中式", "亭台楼阁", "茶室", "新中式"],
    "国风_敦煌": ["敦煌", "国潮", "飞天", "壁画", "鎏金", "复古国风"],

    # 潮流
    "潮流_赛博": ["赛博朋克", "霓虹", "赛博", "未来", "科幻", "夜景城市"],
    "潮流_工业": ["工业", "机能", "冷调", "硬朗", "数码测评", "金属"],
    "潮流_vhs": ["VHS", "复古录像", "80年代", "录像带", "老电视", "回忆"],
    "潮流_漫画": ["漫画", "美式", "波普", "卡通", "变装", "趣味", "潮流"],

    # 情绪
    "情绪_忧郁": ["忧郁", "伤感", "孤独", "深夜", "暗调", "独处"],
    "情绪_黄昏": ["黄昏", "夕阳", "日落", "橘调", "治愈", "温暖"],
    "情绪_黑白": ["黑白", "文艺", "故事感", "电影感情绪", "独白"],

    # 电商
    "电商_纯白": ["电商", "护肤品", "化妆品", "饰品", "纯白背景"],
    "电商_马卡龙": ["母婴", "童装", "零食", "可爱", "马卡龙", "柔和"],
    "电商_冷灰": ["数码", "机械", "科技", "数码产品", "冷灰"],

    # 手绘
    "手绘_扁平": ["口播", "科普", "知识", "图解", "扁平", "简约卡通"],
    "手绘_黏土": ["黏土", "软陶", "可爱插画", "零食动画", "宠物"],
    "手绘_新海诚": ["新海诚", "治愈插画", "云彩", "丁达尔", "动漫背景"],
    "手绘_素描": ["素描", "速写", "手绘", "线稿", "走心", "语录"],

    # 影视风格
    "影视_韦斯安德森": ["韦斯安德森", "韦斯·安德森", "对称构图", "粉彩", "古怪", "复古布景", "怪诞"],
    "影视_王家卫": ["王家卫", "王家卫式", "霓虹迷离", "拖影", "抽帧", "2046", "花样年华", "重庆森林", "春光乍泄"],
    "影视_芬奇": ["大卫·芬奇", "芬奇", "暗调冷峻", "青绿调", "悬疑暗调", "七宗罪", "社交网络"],
    "影视_张艺谋": ["张艺谋", "英雄", "十面埋伏", "大红", "色彩浓烈", "史诗古风", "高饱和红", "大片"],
    "影视_维伦纽瓦": ["维伦纽瓦", "维伦纽瓦式", "沙丘", "银翼杀手", "极简宏大", "空旷", "孤寂", "科幻史诗"],
    "影视_吉卜力": ["吉卜力", "宫崎骏", "龙猫", "千与千寻", "哈尔", "治愈动画", "动画温暖", "魔法", "治愈", "温暖", "森林", "小镇", "动漫风"],
    "影视_黑色电影": ["黑色电影", "film noir", "黑白悬疑", "侦探片", "硬汉", "蛇蝎美人", "光影对比"],
    "影视_诺兰": ["诺兰", "诺兰式", "IMAX", "星际穿越", "盗梦空间", "信条", "黑暗骑士", "时间"],
    "影视_马利克": ["泰伦斯·马利克", "马利克", "生命之树", "天堂之日", "诗意自然", "神性", "逆光", "意识流"],
    "影视_雷德利": ["雷德利·斯科特", "异形", "普罗米修斯", "角斗士", "银翼杀手工业", "烟雾光束", "暗金"],
    "影视_今敏": ["今敏", "未麻的部屋", "千年女优", "红辣椒", "东京教父", "迷幻动画", "超现实", "梦"],
    "影视_黑泽明": ["黑泽明", "七武士", "罗生门", "乱", "影武者", "武士", "狂风", "暴雨"],
    "影视_卡隆": ["阿方索·卡隆", "卡隆", "人类之子", "地心引力", "罗马", "长镜头", "斯坦尼康"],
    "影视_合成波": ["合成波", "synthwave", "复古未来", "迈阿密", "霓虹80", "outrun", "蒸汽波", "跑车"],
    "影视_阿伦诺夫斯基": ["阿伦诺夫斯基", "黑天鹅", "梦之安魂曲", "母性", "心理压迫", "特写", "鱼眼"],
}

# 场景风格标签 → 风格ID映射
_TAG_TO_STYLE = {
    "人像_韩系": "korean_creamy_soft",
    "人像_日系": "japanese_fresh",
    "人像_港风": "hk_90s_retro",
    "人像_胶片": "fuji_film",
    "人像_ins": "ins_minimal_cold",
    "人像_y2k": "y2k_kitsch",
    "美食_暖调": "food_warm_hearth",
    "美食_纪实": "food_documentary",
    "美食_暗调": "food_dark_elegant",
    "旅拍_通透": "travel_clear_sky",
    "旅拍_电影": "cinematic_widescreen",
    "旅拍_公路": "retro_road_film",
    "国风_水墨": "ink_wash_guofeng",
    "国风_青绿": "green_mountain",
    "国风_敦煌": "dunhuang_chic",
    "潮流_赛博": "cyberpunk",
    "潮流_工业": "industrial_cold",
    "潮流_vhs": "vhs_vintage",
    "潮流_漫画": "american_comic",
    "情绪_忧郁": "dark_melancholy",
    "情绪_黄昏": "golden_hour_warm",
    "情绪_黑白": "bw_film_noir",
    "电商_纯白": "luxury_white",
    "电商_马卡龙": "macaron_pastel",
    "电商_冷灰": "industrial_tech",
    "手绘_扁平": "flat_minimal",
    "手绘_黏土": "clay_soft",
    "手绘_新海诚": "shinkai_painterly",
    "手绘_素描": "sketch_pencil",
    "影视_韦斯安德森": "wes_anderson",
    "影视_王家卫": "wong_kar_wai",
    "影视_芬奇": "fincher_dark",
    "影视_张艺谋": "zhang_yimou",
    "影视_维伦纽瓦": "villeneuve_epic",
    "影视_吉卜力": "ghibli_whimsy",
    "影视_黑色电影": "film_noir",
    "影视_诺兰": "nolan_imax",
    "影视_马利克": "malick_nature",
    "影视_雷德利": "ridley_scott",
    "影视_今敏": "satoshi_kon",
    "影视_黑泽明": "kurosawa_epic",
    "影视_卡隆": "cuaron_long_take",
    "影视_合成波": "synthwave_retrowave",
    "影视_阿伦诺夫斯基": "aronofsky_intense",
}


def match_style(scene_desc: str) -> list:
    """
    根据场景描述，返回最匹配的风格ID列表（按匹配度排序）
    """
    desc_lower = scene_desc.lower()
    matches = []

    for tag_key, keywords in _SCENE_TAGS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in desc_lower:
                score += 1
        if score > 0:
            matches.append((tag_key, score))

    # 按匹配度降序
    matches.sort(key=lambda x: -x[1])
    return [m[0] for m in matches]


def pick_enhancers(style_id: str, styles: dict, enhancers: list, count: int = 2) -> list:
    """
    为选中的风格挑选合适的通用增强词（用于英文标签模式）
    """
    style = styles.get(style_id, {})
    style_for = style.get("best_for", [])
    style_mood = style.get("mood", "")

    chosen = []
    for e in enhancers:
        if len(chosen) >= count:
            break
        e_for = e.get("for", [])
        # 如果增强词适合该风格的情绪或场景
        if style_mood in e_for or any(f in str(style_for) for f in e_for):
            chosen.append(e["tags"])
    return chosen


class StyleSelector:
    """
    风格选择器 — 根据场景描述和工作流类型，自动选择最匹配的调色风格
    """

    def __init__(self, path=None):
        self.styles, self.enhancers = load_styles(path)

    def select(self, scene_desc: str, workflow_type: str = "txt2img") -> dict:
        """
        选择风格并生成完整提示词

        参数:
            scene_desc: 场景描述（中文或英文）
            workflow_type: txt2img / txt2vid / img2vid / music

        返回:
            {
                "style_id": "风格ID",
                "style_name": "风格中文名",
                "keywords": "中文描述（T2V用）",
                "tags": "英文标签（T2I用）",
                "enhancers": "额外叠加的增强词",
                "prompt": "已经混入风格关键词的完整提示词"
            }
        """
        matched = match_style(scene_desc)
        if not matched:
            # 无匹配 → 用通用模式
            return self._generic_prompt(scene_desc, workflow_type)

        style_id = _TAG_TO_STYLE.get(matched[0])
        if not style_id or style_id not in self.styles:
            return self._generic_prompt(scene_desc, workflow_type)

        style = self.styles[style_id]
        enhancer_tags = pick_enhancers(style_id, self.styles, self.enhancers, count=2)

        if workflow_type in ("txt2img", "txt2image"):
            # 英文标签模式（Z-Image / Flux 等 T2I 工作流）
            tags = style["tags"]
            if enhancer_tags:
                tags += ", " + ", ".join(enhancer_tags)
            prompt = f"{scene_desc}, {tags}"
        elif workflow_type in ("img2vid", "txt2vid", "txt2video", "i2v"):
            # 中文叙事模式（T2V / I2V 视频工作流）
            kw = style["keywords"]
            prompt = f"场景：{scene_desc}\n风格：{kw}"
        else:
            prompt = scene_desc

        return {
            "style_id": style_id,
            "style_name": style["name"],
            "keywords": style["keywords"],
            "tags": style["tags"],
            "enhancers": enhancer_tags,
            "prompt": prompt,
        }

    def _generic_prompt(self, scene_desc: str, workflow_type: str) -> dict:
        """场景无风格匹配时，返回通用处理"""
        if workflow_type in ("txt2img", "txt2image", "t2i"):
            prompt = f"{scene_desc}, high quality, detailed, cinematic lighting, 8K, sharp focus"
        elif workflow_type in ("txt2vid", "txt2video", "img2vid", "i2v", "t2v"):
            prompt = f"场景：{scene_desc}"
        else:
            prompt = scene_desc

        return {
            "style_id": "generic",
            "style_name": "通用",
            "keywords": "",
            "tags": "",
            "enhancers": [],
            "prompt": prompt,
        }

    def list_all_styles(self) -> list:
        """列出所有可用风格"""
        result = []
        for sid, style in self.styles.items():
            result.append({
                "id": sid,
                "name": style["name"],
                "genre": style.get("genre", ""),
                "mood": style.get("mood", ""),
                "best_for": style.get("best_for", []),
            })
        return result

    def list_by_genre(self) -> dict:
        """按类别分组列出风格"""
        groups = {}
        for sid, style in self.styles.items():
            g = style.get("genre", "其他")
            if g not in groups:
                groups[g] = []
            groups[g].append({
                "id": sid,
                "name": style["name"],
                "mood": style.get("mood", ""),
            })
        return groups


# ============================================================
# 快速测试
# ============================================================

if __name__ == "__main__":
    selector = StyleSelector()

    print("=== 所有可用风格 ===")
    for s in selector.list_all_styles():
        print(f"  {s['id']}: {s['name']} [{s['genre']}] — {s['mood']}")

    print("\n=== 测试场景匹配 ===")

    tests = [
        ("古风美女在樱花树下", "txt2img"),
        ("黄昏操场少年少女散步", "txt2vid"),
        ("一碗热气腾腾的牛肉面特写", "txt2img"),
        ("城市夜景赛博朋克霓虹灯", "txt2img"),
        ("伤感深夜独处窗边", "txt2vid"),
        ("海边航拍日落", "txt2img"),
        ("数码产品开箱测评", "txt2img"),
    ]

    for desc, wtype in tests:
        result = selector.select(desc, wtype)
        print(f"\n📝 [{wtype}] {desc}")
        print(f"   风格: {result['style_name']} ({result['style_id']})")
        print(f"   提示词: {result['prompt'][:120]}...")
