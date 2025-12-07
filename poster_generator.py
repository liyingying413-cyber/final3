import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import random
import math


# -----------------------------
# 工具函数
# -----------------------------
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def lerp(c1, c2, t):
    return tuple(int(c1[i]*(1-t) + c2[i]*t) for i in range(3))


# -----------------------------
# 城市固有颜色（高饱和，不受情绪影响）
# -----------------------------
CITY_COLOR_MAP = {
    "seoul": ["#FF77E9", "#8AB6FF", "#4B50FF"],
    "tokyo": ["#00F6FF", "#FF46B5", "#381AFF"],
    "paris": ["#FFE1EC", "#FFE9C4", "#FFB7D5"],
    "new york": ["#FF4F81", "#FFC857", "#1A1D4A"],
}

def pick_city_colors(city):
    city = city.lower()
    if city in CITY_COLOR_MAP:
        return [hex_to_rgb(c) for c in CITY_COLOR_MAP[city]]
    return [(200, 200, 200), (180, 180, 180), (160, 160, 160)]


# -----------------------------
# Step 1 — 生成情绪背景（柔和）
# -----------------------------
def generate_mood_gradient(size, palette, intensity):
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)

    c1 = hex_to_rgb(palette[0])
    c2 = hex_to_rgb(palette[1])

    for y in range(h):
        t = y / h
        color = lerp(c1, c2, t)
        draw.line([(0, y), (w, y)], fill=color)

    # 轻量模糊
    img = img.filter(ImageFilter.GaussianBlur(int(10 * intensity + 2)))
    return img


# -----------------------------
# Step 2 — Mist（雾）
# -----------------------------
def apply_mist_layer(img, mist_strength, smoothness, glow):
    if mist_strength <= 0.01:
        return img

    w, h = img.size
    mist = Image.new("RGB", img.size, (255, 255, 255))

    blended = Image.blend(img, mist, mist_strength)

    return blended.filter(ImageFilter.GaussianBlur(3 + glow*3))


# -----------------------------
# Step 3 — Watercolor（扩散）
# -----------------------------
def apply_watercolor(img, spread, layers, ink_sat):
    if layers <= 0:
        return img

    base = img.copy()
    for i in range(layers):
        blur = base.filter(ImageFilter.GaussianBlur(8 + spread * 12))
        base = Image.blend(base, blur, 0.3 + ink_sat * 0.4)

    return base


# -----------------------------
# Step 4 — Pastel（粉彩柔化）
# -----------------------------
def apply_pastel(img, softness, grain_amount, blend_ratio):
    pastel = img.filter(ImageFilter.GaussianBlur(softness * 15 + 2))

    # 生成颗粒
    w, h = img.size
    noise = (np.random.randn(h, w) * (grain_amount * 80)).astype(np.int16)
    noise = np.clip(noise + 128, 0, 255).astype(np.uint8)
    grain = Image.fromarray(np.stack([noise]*3, axis=2), "RGB")

    pastel = Image.blend(pastel, grain, grain_amount * 0.35)
    final = Image.blend(img, pastel, blend_ratio)

    return final


# -----------------------------
# Step 5 — 城市风格（强烈、永远叠在最顶层）
# -----------------------------
def add_city_layer(base_img, city, emotion_factor):
    city_colors = pick_city_colors(city)
    w, h = base_img.size

    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 竖线数量随 emotion_factor 增长
    count = int(30 + emotion_factor * 60)

    for _ in range(count):
        x = random.randint(0, w)
        y1 = random.randint(0, int(h*0.4))
        y2 = random.randint(int(h*0.6), h)

        color = random.choice(city_colors)
        alpha = int(160 + emotion_factor * 80)

        draw.line(
            [(x, y1), (x, y2)],
            fill=color + (alpha,),
            width=random.randint(6, 20)
        )

    # 城市层轻微发光（强化辨识度）
    overlay = overlay.filter(ImageFilter.GaussianBlur(3 + emotion_factor * 4))

    # 叠加在最顶层：不会被 Mist / Pastel 覆盖
    return Image.alpha_composite(base_img.convert("RGBA"), overlay)


# -----------------------------
# 总函数 — 生成海报
# -----------------------------
def generate_poster(
    palette,
    city="Seoul",
    mood_intensity=0.5,
    size=(1024, 1024),
    mist_params=None,
    wc_params=None,
    pastel_params=None,
    emotion_factor=0.5,
):
    # 情绪背景
    img = generate_mood_gradient(size, palette, mood_intensity)

    # Mist
    if mist_params:
        img = apply_mist_layer(img, *mist_params)

    # Watercolor
    if wc_params:
        img = apply_watercolor(img, *wc_params)

    # Pastel
    if pastel_params:
        img = apply_pastel(img, *pastel_params)

    # 最重要：城市风格永远放在最上面
    final = add_city_layer(img, city, emotion_factor)

    return final.convert("RGB")
