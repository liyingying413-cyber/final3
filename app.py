import numpy as np
import colorsys


def generate_palette(mood: str, intensity: float):
    """
    根据情绪和强度生成一组 3～5 个颜色的柔和色板。
    输出为 [(r,g,b), ...]，值在 0–255。
    """

    # 各情绪对应基础 HSV
    mood_to_hsv = {
        "calm":      (200 / 360, 0.25, 0.95),  # 蓝绿
        "nostalgic": (35  / 360, 0.35, 0.96),  # 暖橙黄
        "dreamy":    (260 / 360, 0.30, 0.98),  # 紫蓝
        "sad":       (210 / 360, 0.22, 0.90),  # 暗蓝
        "happy":     (50  / 360, 0.45, 0.99),  # 明亮黄
        "romantic":  (330 / 360, 0.35, 0.97),  # 粉紫
        "tense":     (350 / 360, 0.60, 0.92),  # 偏红
    }

    base_h, base_s, base_v = mood_to_hsv.get(mood, mood_to_hsv["calm"])
    colors = []
    num_colors = np.random.randint(3, 6)

    for _ in range(num_colors):
        # 增大扰动范围，让差异更明显
        h = (base_h + np.random.uniform(-0.12, 0.12)) % 1.0
        s = np.clip(base_s + np.random.uniform(-0.25, 0.2), 0.05, 0.95)
        v = np.clip(base_v + np.random.uniform(-0.2, 0.2), 0.4, 1.0)

        # 情绪强度越高，色彩对比越强 / 稍微偏暗一点
        v *= (0.9 - 0.3 * intensity)

        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))

    return colors


def analyze_memory_local(city: str, memory: str):
    """
    本地情绪分析（不依赖任何 API）。
    通过关键词 + 标点 + 文本长度，估计情绪标签与强度。
    """

    text = (city + " " + memory).lower()

    mood = "calm"
    intensity = 0.4

    # 强情绪关键词
    sad_words = ["sad", "cry", "alone", "lonely", "lost", "empty", "寂寞", "失落", "难过"]
    happy_words = ["happy", "joy", "excited", "smile", "满足", "开心", "快乐"]
    romantic_words = ["romantic", "love", "kiss", "date", "牵手", "告白", "浪漫"]
    nostalgic_words = ["nostalgic", "memory", "childhood", "old", "过去", "从前", "回忆"]
    dreamy_words = ["dream", "dreamy", "fog", "mist", "night", "neon", "幻", "朦胧"]
    tense_words = ["fight", "argue", "anxious", "压力", "紧张", "争吵"]

    def contains_any(words):
        return any(w in text for w in words)

    if contains_any(sad_words):
        mood = "sad"
        intensity = 0.7
    elif contains_any(happy_words):
        mood = "happy"
        intensity = 0.6
    elif contains_any(romantic_words):
        mood = "romantic"
        intensity = 0.55
    elif contains_any(nostalgic_words):
        mood = "nostalgic"
        intensity = 0.6
    elif contains_any(dreamy_words):
        mood = "dreamy"
        intensity = 0.65
    elif contains_any(tense_words):
        mood = "tense"
        intensity = 0.7
    else:
        # 没明显情绪词时，根据一些中性词判断
        if any(w in text for w in ["rain", "fog", "mist", "雨", "雾"]):
            mood = "nostalgic"
            intensity = 0.55
        elif any(w in text for w in ["sea", "ocean", "港口", "海边", "海"]):
            mood = "calm"
            intensity = 0.5
        elif any(w in text for w in ["night", "灯光", "城市", "霓虹"]):
            mood = "dreamy"
            intensity = 0.6

    # 情绪强度额外修正：文本越长、感叹号越多，强度越高一点
    length_factor = min(len(memory) / 400.0, 1.0)  # 最多加到 1
    exclam = memory.count("!") + memory.count("！")
    intensity += 0.1 * length_factor + 0.05 * exclam
    intensity = float(np.clip(intensity, 0.3, 0.85))

    palette = generate_palette(mood, intensity)

    return {
        "city": city,
        "mood": mood,
        "intensity": intensity,
        "palette": palette,
        "summary": f"在 {city} 的记忆呈现 {mood} 情绪基调，强度约为 {intensity:.2f}。",
    }
