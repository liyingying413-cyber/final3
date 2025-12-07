import os
import json
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None


def analyze_with_openai(city: str, memory: str):
    """
    使用 OpenAI Responses API 分析情绪、色彩与风格。
    如果没有 OPENAI_API_KEY，则返回 None，由前端使用 fallback。
    """
    if client is None:
        return None

    instructions = (
        "You are an art director for minimalist, pastel, dreamy posters. "
        "Analyze the user's memory text about a city and output clean JSON "
        "design parameters for an abstract emotional poster. "
        "The poster style is similar to Xiaohongshu aesthetic: soft gradients, "
        "pastel tones, dreamy blur, subtle film grain, plenty of whitespace."
    )

    prompt = (
        "Return ONLY valid JSON in this exact schema:\n"
        "{\n"
        '  \"title\": \"short poetic title\",\n'
        '  \"subtitle\": \"1-2 short emotional lines\",\n'
        '  \"mood\": \"2-3 word mood label\",\n'
        '  \"intensity\": 0.0,\n'
        '  \"palette\": [\"#AABBCC\", \"#112233\", \"#FFEEDD\"],\n'
        '  \"style_mode\": \"misty_gradient|ocean_dream|warm_glow|night_neon\",\n'
        '  \"typography_focus\": \"balanced|text_on_bottom|text_on_top\"\n'
        "}\n\n"
        f"City: {city}\n"
        f"Memory: {memory}\n"
    )

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            instructions=instructions,
            input=prompt,
        )
        text = resp.output_text
        data = json.loads(text)
    except Exception as e:
        print("OpenAI error:", e)
        return None

    # 把 Stable Diffusion 的 key 也塞进去，方便后面使用
    data["stability_key"] = os.getenv("STABILITY_API_KEY")
    return data


def local_analyze(city: str, memory: str):
    """
    当 OpenAI 不可用时的简易分析：
    基于关键词推断情绪，并给出一组柔和色彩与风格。
    """
    text = (city + " " + memory).lower()

    mood = "calm nostalgic"
    palette = ["#A9C8D8", "#E4EEF5", "#6FA3C8"]  # 柔和蓝绿
    style_mode = "misty_gradient"

    if any(w in text for w in ["rain", "fog", "mist", "雾", "雨", "sad", "lonely", "寂寞"]):
        mood = "melancholic soft"
        palette = ["#7FA2C8", "#E7EDF5", "#405B88"]
        style_mode = "misty_gradient"
    elif any(w in text for w in ["sea", "ocean", "wave", "beach", "海"]):
        mood = "ocean dream"
        palette = ["#6EC3D6", "#E3F6FD", "#2C5B8A"]
        style_mode = "ocean_dream"
    elif any(w in text for w in ["summer", "sun", "阳光", "暖", "bright", "festival"]):
        mood = "warm bright"
        palette = ["#F9E8A5", "#FFBE88", "#7FD2C3"]
        style_mode = "warm_glow"
    elif any(w in text for w in ["night", "neon", "city lights", "夜", "霓虹"]):
        mood = "night neon"
        palette = ["#13002B", "#432371", "#F25F5C"]
        style_mode = "night_neon"

    return {
        "title": f"{city} 的记忆",
        "subtitle": "关于这座城市的情绪片段。",
        "mood": mood,
        "intensity": 0.6,
        "palette": palette,
        "style_mode": style_mode,
        "typography_focus": "balanced",
        "stability_key": os.getenv("STABILITY_API_KEY"),
    }
