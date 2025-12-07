import os
import requests
from io import BytesIO
from PIL import Image


def _style_phrase_from_controls(controls: dict) -> str:
    """
    根据用户在 sidebar 的控制项，构造一段更细腻的风格描述文本，
    用于 Stable Diffusion 的 prompt。
    """
    style_mode_user = controls.get("style_mode_user", "Pastel Mist")

    pastel = controls.get("pastel_intensity", 0.7)
    desat = controls.get("desaturation", 0.3)
    blur = controls.get("dreamy_blur", 12.0)
    bloom = controls.get("bloom", 0.4)
    grain = controls.get("grain", 0.15)
    vignette = controls.get("vignette", 0.2)
    whitespace = controls.get("whitespace", 0.25)

    pieces = []

    # 主风格关键词
    if "Pastel" in style_mode_user:
        pieces.append("pastel soft color palette")
    if "Dreamy" in style_mode_user:
        pieces.append("dreamy atmosphere")
    if "Magazine" in style_mode_user:
        pieces.append("magazine editorial minimal layout")
    if "Film Grain" in style_mode_user:
        pieces.append("subtle film grain texture")
    if "Glow" in style_mode_user:
        pieces.append("soft glow light")
    if "Hazy" in style_mode_user:
        pieces.append("hazy soft focus")

    # 数值型控制映射
    if pastel > 0.6:
        pieces.append("very gentle pastel tones")
    if desat > 0.2:
        pieces.append("low saturation, gentle colors")
    if blur > 10:
        pieces.append("strong dreamy blur")
    if bloom > 0.3:
        pieces.append("noticeable light bloom")
    if grain > 0.1:
        pieces.append("fine film grain")
    if vignette > 0.15:
        pieces.append("subtle vignette for focus")
    if whitespace > 0.2:
        pieces.append("a lot of whitespace, clean composition")

    return ", ".join(pieces)


def generate_poster_with_stable_diffusion(analysis: dict, controls: dict, seed: int = 42):
    """
    调用 Stability AI Stable Diffusion（sd3）生成 1:1 比例的小红书风情绪海报。
    返回：(PIL.Image 或 None, 错误信息字符串 或 None)
    """
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        return None, "环境变量 STABILITY_API_KEY 未设置。"

    mood = analysis.get("mood", "calm nostalgic")
    palette = analysis.get("palette", [])
    style_mode_ai = analysis.get("style_mode", "misty_gradient")

    palette_str = ", ".join(palette) if isinstance(palette, (list, tuple)) else str(palette)

    style_phrase_user = _style_phrase_from_controls(controls)

    # 情绪影响程度，控制一些额外描述
    mood_inf = controls.get("mood_influence", 0.5)
    if mood_inf > 0.7:
        mood_phrase = "emotion is strongly reflected in the shapes and colors"
    elif mood_inf > 0.3:
        mood_phrase = "emotion subtly influences the shapes and colors"
    else:
        mood_phrase = "emotion is softly present but not overwhelming"

    # 构建最终 prompt
    prompt = (
        "xiao hong shu style abstract emotional poster, 1:1 aspect ratio, "
        f"city memory mood: {mood}, "
        f"color palette: {palette_str}, "
        f"base style: {style_mode_ai}, "
        f"{style_phrase_user}, "
        f"{mood_phrase}, "
        "soft gradients, dreamy blur, gentle light, clean modern layout, "
        "high quality illustration, no text, no logo, no watermark."
    )

    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    headers = {
        "authorization": f"Bearer {api_key}",
        "accept": "image/*",
    }

    data = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": "1:1",
        "seed": seed,
        "negative_prompt": "text, letters, logo, watermark, frame, border",
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            files={"none": ""},
            data=data,
            timeout=60,
        )

        if resp.status_code != 200:
            # 尝试解析错误信息
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            return None, f"HTTP {resp.status_code}: {err}"

        img_bytes = resp.content
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        return img, None

    except Exception as e:
        return None, f"Exception when calling Stability API: {e}"
