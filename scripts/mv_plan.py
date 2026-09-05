# ============================================================
# 大学生校园生活 MV — 8场景计划
# ============================================================
# 总时长: ~3分钟
# 每个场景: ~20秒（含2秒过渡）
# 音乐: 校园青春风格
# ============================================================

SCENES = [
    {
        "id": "morning",
        "title": "☀️ 清晨校园·学生走向教学楼",
        "prompt": "sunrise over university campus, students walking towards teaching buildings with backpacks, golden morning light filtering through trees, dewy grass, majestic academic buildings in background, cinematic lighting, golden hour, warm glow, highly detailed, 8K, sharp focus, hazy morning mist",
        "style": "travel_clear_sky",
        "i2v": True,  # 要动画化
        "i2v_motion": "students walking forward slowly, camera gently panning right, morning light changing subtly",
    },
    {
        "id": "classroom",
        "title": "📚 教室课堂·老师在讲台上",
        "prompt": "sunlit university classroom, professor writing on blackboard, students taking notes at wooden desks, windows with green trees outside, soft natural light streaming in, warm atmosphere, scholarly ambiance, detailed classroom interior, cinematic, highly detailed, 8K",
        "style": "japanese_fresh",
        "i2v": True,
        "i2v_motion": "camera slowly pushing in, sunlight rays shifting slightly, dust particles floating in light",
    },
    {
        "id": "library",
        "title": "📖 图书馆·安静阅读时光",
        "prompt": "university library interior, tall bookshelves filled with books, students reading at study desks, warm lamp light, afternoon sunlight through large windows, quiet study atmosphere, cozy academic environment, detailed books and wood textures, cinematic lighting, 8K",
        "style": "golden_hour_warm",
        "i2v": True,
        "i2v_motion": "camera slowly dollying through bookshelves, pages turning gently, soft dust motes in light beams",
    },
    {
        "id": "sports",
        "title": "🏀 操场·青春活力",
        "prompt": "vibrant university sports field, students playing basketball on outdoor court, blue sky with white clouds, green trees around the field, energetic sporty atmosphere, afternoon sunlight, dynamic action, youthful energy, cinematic, highly detailed, 8K, sharp focus",
        "style": "travel_clear_sky",
        "i2v": False,  # 静态+Ken Burns
        "i2v_motion": "",
    },
    {
        "id": "cafeteria",
        "title": "🍜 食堂·午餐时光",
        "prompt": "busy university cafeteria at lunch time, students eating and chatting at tables, warm indoor lighting, variety of food on trays, steam rising from dishes, cozy social atmosphere, modern clean dining hall, cinematic warm tone, highly detailed, 8K",
        "style": "food_warm_hearth",
        "i2v": False,
        "i2v_motion": "",
    },
    {
        "id": "avenue",
        "title": "🌸 林荫道·花季漫步",
        "prompt": "beautiful university tree-lined avenue in spring, cherry blossom petals falling, students walking and cycling under blooming trees, soft pink and white flowers canopy, sunlight filtering through blossoms, romantic campus atmosphere, dreamy, highly detailed, 8K, cinematic",
        "style": "japanese_fresh",
        "i2v": True,
        "i2v_motion": "petals falling slowly, students walking gently, camera tracking sideways, breeze moving branches",
    },
    {
        "id": "sunset",
        "title": "🌇 黄昏·夕阳下的校园",
        "prompt": "golden hour sunset over university campus, warm orange and purple sky, teaching building silhouettes, students walking on campus paths, long soft shadows, romantic warm atmosphere, cinematic wide shot, epic golden light, highly detailed, 8K, sharp focus",
        "style": "golden_hour_warm",
        "i2v": False,
        "i2v_motion": "",
    },
    {
        "id": "night",
        "title": "🌙 夜晚·教学楼灯火通明",
        "prompt": "night view of university campus, teaching buildings with warm lit windows, students under street lamps walking home, starry sky above, quiet peaceful atmosphere, reflection in puddles, cinematic night photography, moody, highly detailed, 8K",
        "style": "dark_melancholy",
        "i2v": True,
        "i2v_motion": "lights flickering gently, students walking slowly under lamps, camera slowly pushing in on building",
    },
]

# 哪些场景需要 I2V 动画化
I2V_SCENES = [s for s in SCENES if s["i2v"]]

# 工作流
T2I_WORKFLOW = "2037071836214730753"      # 文生图 Popular Aesthetics
I2V_WORKFLOW = "2060674924032905217"       # LTX I2V
MUSIC_WORKFLOW = "2044246957450858497"     # ACE/Suno V5.5 音乐

print(f"场景总数: {len(SCENES)}")
print(f"需动画: {len(I2V_SCENES)}")
print(f"音乐: 1首")
