import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import random


# -----------------------------
# 小工具
# -----------------------------
def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def lerp(c1, c2, t: float):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


# -----------------------------
# 城市专属高饱和颜色（不再依赖情绪 palette）
# -----------------------------
CITY_COLOR_MAP = {
    "seoul": ["#FF77E9", "#8AB6FF", "#4B50FF"],
    "tokyo": ["#00F6FF", "#FF46B5", "#381AFF"],
    "paris": ["#FFE1EC", "#FFE9C4", "#FFB7D5"],
    "new york": ["#FF4F81", "#FFC857", "#1A1D4A"],
}

def pick_city_colors(city: str, fallback_palette_hex):
    """
    如果识别到是首尔/东京/巴黎/纽约，就用预设高饱和调色板，
    否则用情绪 palette 略微提亮。
    """
    city_l = (city or "").lower()

    for key in CITY_COLOR_MAP:
        if key in city_l:
            return [hex_to_rgb(c) for c in CITY_COLOR_MAP[key]]

    # 没命中就用情绪颜色作为城市色，但提高一点饱和与亮度
    colors = []
    for hx in (fallback_palette_hex or []):
        try:
            r, g, b = hex_to_rgb(hx)
            arr = np.array([[[r, g, b]]], dtype="float32")
            arr *= 1.2
            arr = np.clip(arr, 0, 255).astype("uint8")
            r2, g2, b2 = arr[0, 0]
            colors.append((int(r2), int(g2), int(b2)))
        except Exception:
            continue

    if not colors:
        colors = [(200, 200, 200), (180, 180, 180), (160, 160, 160)]
    return colors


# -----------------------------
# Step 1 — 情绪渐变背景
# -----------------------------
def generate_mood_gradient(size, palette_hex, intensity: float):
    w, h = size

    # palette 来自 AI 分析，通常是 ["#A9C8D8", "#E4EEF5", ...]
    if not palette_hex:
        palette_hex = ["#A9C8D8", "#E4EEF5"]
    if len(palette_hex) == 1:
        palette_hex = palette_hex * 2

    c1 = hex_to_rgb(palette_hex[0])
    c2 = hex_to_rgb(palette_hex[1])

    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / max(h - 1, 1)
        color = lerp(c1, c2, t)
        draw.line([(0, y), (w, y)], fill=color)

    # 轻微模糊，让背景更柔和
    blur_r = 8 + intensity * 10
    img = img.filter(ImageFilter.GaussianBlur(blur_r))
    return img


# -----------------------------
# Step 2 — Mist（雾）
# -----------------------------
def apply_mist_layer(img, mist_strength: float, smoothness: float, glow: float):
    if mist_strength <= 0.01:
        return img

    w, h = img.size
    mist = Image.new("RGB", (w, h), (240, 244, 250))
    # 降低雾的混合程度，避免“洗白”
    alpha = 0.1 + mist_strength * 0.3
    img = Image.blend(img, mist, alpha)

    # glow 控制轻微模糊
    glow_r = 2 + glow * 4
    img = img.filter(ImageFilter.GaussianBlur(glow_r))
    return img


# -----------------------------
# Step 3 — Watercolor（水彩扩散）
# -----------------------------
def apply_watercolor(img, spread: float, layers: int, ink_sat: float):
    if layers <= 0 or spread <= 0:
        return img

    base = img.copy()
    for _ in range(layers):
        blur_r = 6 + spread * 16
        blur = base.filter(ImageFilter.GaussianBlur(blur_r))
        blend_alpha = 0.2 + ink_sat * 0.4  # 不要太重
        base = Image.blend(base, blur, blend_alpha)

    return base


# -----------------------------
# Step 4 — Pastel（粉彩柔化）
# -----------------------------
def apply_pastel(img, softness: float, grain_amount: float, blend_ratio: float):
    if blend_ratio <= 0:
        return img

    pastel = img.filter(ImageFilter.GaussianBlur(2 + softness * 12))

    w, h = img.size
    if grain_amount > 0:
        noise = (np.random.randn(h, w) * (grain_amount * 80)).astype(np.int16)
        noise = np.clip(noise + 128, 0, 255).astype(np.uint8)
        grain = Image.fromarray(np.stack([noise] * 3, axis=2), "RGB")
        pastel = Image.blend(pastel, grain, grain_amount * 0.35)

    final = Image.blend(img, pastel, blend_ratio * 0.8)
    return final


# -----------------------------
# Step 5 — 城市风格层（竖直霓虹线，永远在最顶层）
# -----------------------------
def add_city_layer(base_img, city: str, emotion_link: float, palette_hex):
    city_colors = pick_city_colors(city, palette_hex)
    w, h = base_img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 竖线数量随 emotion_link 增长，情绪越强，线越多越亮
    count = int(25 + emotion_link * 60)

    city_l = (city or "").lower()

    for _ in range(count):
        x = random.randint(0, w)

        # 不同城市稍微不同的线条长度 / 粗细
        if "tokyo" in city_l:
            y1 = random.randint(0, int(h * 0.2))
            y2 = random.randint(int(h * 0.5), h)
            width = random.randint(4, 12)
        elif "paris" in city_l:
            y1 = random.randint(int(h * 0.3), int(h * 0.5))
            y2 = h
            width = random.randint(6, 14)
        else:  # seoul / nyc / 其他
            y1 = random.randint(0, int(h * 0.4))
            y2 = random.randint(int(h * 0.6), h)
            width = random.randint(8, 18)

        color = random.choice(city_colors)
        alpha = int(170 + emotion_link * 80)

        draw.line(
            [(x, y1), (x, y2)],
            fill=color + (alpha,),
            width=width,
        )

    # 轻微 glow，让城市风格更“发光”
    overlay = overlay.filter(ImageFilter.GaussianBlur(3 + emotion_link * 4))

    # ⚠ 最关键：城市层叠在最顶层，不再被后续操作覆盖
    result = Image.alpha_composite(base_img.convert("RGBA"), overlay)
    return result.convert("RGB")


# -----------------------------
# 总入口：生成海报（兼容原 app.py 的所有参数）
# -----------------------------
def generate_poster(
    city: str,
    memory_text: str,
    mood: str,
    palette,
    mood_intensity: float,
    seed: int,
    emotion_link: float,
    mist_strength: float,
    mist_smoothness: float,
    mist_glow: float,
    wc_spread: float,
    wc_layers: int,
    wc_saturation: float,
    pastel_softness: float,
    pastel_grain: float,
    pastel_blend: float,
):
    """
    完全本地生成，不依赖任何 API。
    参数签名兼容你现有的 app.py。
    """

    # 保证每次同一个 seed → 画面可以复现
    try:
        random.seed(int(seed))
        np.random.seed(int(seed))
    except Exception:
        random.seed(42)
        np.random.seed(42)

    size = (1024, 1024)

    # 1) 情绪背景（用 AI 分析到的 palette）
    palette_hex = palette or ["#A9C8D8", "#E4EEF5"]
    bg = generate_mood_gradient(size, palette_hex, mood_intensity)

    # 2) Mist
    bg = apply_mist_layer(bg, mist_strength, mist_smoothness, mist_glow)

    # 3) Watercolor
    bg = apply_watercolor(bg, wc_spread, wc_layers, wc_saturation)

    # 4) Pastel
    bg = apply_pastel(bg, pastel_softness, pastel_grain, pastel_blend)

    # 5) 城市风格层（竖直霓虹线，使用高饱和城市色）
    final_img = add_city_layer(bg, city, emotion_link, palette_hex)

    # 返回 PNG bytes（你的 app.py 应该是用 BytesIO 展示的）
    import io
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    return buf.getvalue()
