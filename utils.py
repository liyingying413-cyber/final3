import numpy as np


def analyze_memory_local(city: str, memory_text: str):
    """
    本地情绪分析（无 API）
    -------------------------------------
    根据用户的文本自动推断情绪方向与色彩倾向，
    返回颜色 palette、情绪标签、强度等。
    """

    text = (city + " " + memory_text).lower()

    # -----------------------------
    # 1）默认情绪
    # -----------------------------
    mood = "calm"
    intensity = 0.5  # 0~1，用于海报中水彩 / 雾化的强弱

    # -----------------------------
    # 2）情绪关键词判定
    # -----------------------------
    sad_words = ["sad", "lonely", "blue", "empty", "lost", "cold",
                 "寂寞", "失落", "冷", "孤独", "忧郁"]
    warm_words = ["warm", "love", "sun", "light", "summer", "sweet",
                  "温暖", "明亮", "阳光", "喜欢", "治愈", "幸福"]
    energetic_words = ["busy", "rush", "crowd", "energy", "fast", "noise",
                       "热闹", "人群", "快速", "喧嚣", "活力"]

    if any(w in text for w in sad_words):
        mood = "melancholic"
        intensity = 0.6

    elif any(w in text for w in warm_words):
        mood = "warm"
        intensity = 0.5

    elif any(w in text for w in energetic_words):
        mood = "energetic"
        intensity = 0.7

    # -----------------------------
    # 3）生成柔和风格 palette（适配 Mist + Watercolor + Pastel）
    # -----------------------------
    palette = generate_palette(mood)

    # 输出结构
    return {
        "city": city,
        "mood": mood,
        "intensity": float(intensity),
        "palette": palette,
        "memory_excerpt": memory_text[:60] + "..." if len(memory_text) > 60 else memory_text,
    }


# -------------------------------------------------
# 色彩生成器：根据情绪生成柔和小红书风调色板
# -------------------------------------------------

def generate_palette(mood: str):
    """
    根据 mood 生成柔和风格的小红书配色。
    每种情绪对应一个基础色，然后生成三色渐变。
    """

    # 基础色表（RGB）
    base_colors = {
        "calm":        np.array([150, 180, 210]),  # 冷静蓝
        "melancholic": np.array([120, 140, 180]),  # 灰蓝紫
        "warm":        np.array([255, 200, 160]),  # 暖橙粉
        "energetic":   np.array([255, 130, 130]),  # 红粉
    }

    # 如果没找到，就默认 calm
    base = base_colors.get(mood, base_colors["calm"]) / 255.0

    # -----------------------------
    # 生成三色渐变调色板
    # -----------------------------
    palette = []

    for shift in [0.85, 1.0, 1.15]:
        c = np.clip(base * shift, 0, 1)
        hex_color = rgb_to_hex(c)
        palette.append(hex_color)

    return palette


def rgb_to_hex(rgb):
    """将 0~1 RGB 转为 #RRGGBB"""
    r, g, b = (rgb * 255).astype(int)
    return f"#{r:02X}{g:02X}{b:02X}"
