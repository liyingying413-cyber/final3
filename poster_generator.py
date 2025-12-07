import io
import random
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageDraw

RGB = Tuple[int, int, int]


def _lerp_color(c1: RGB, c2: RGB, t: float) -> RGB:
    return (
        int(c1[0] * (1 - t) + c2[0] * t),
        int(c1[1] * (1 - t) + c2[1] * t),
        int(c1[2] * (1 - t) + c2[2] * t),
    )


def _to_image_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _normalize_palette(palette) -> List[RGB]:
    if isinstance(palette, np.ndarray):
        palette = palette.tolist()

    if not palette:
        return [(200, 220, 230), (230, 240, 245), (180, 200, 210)]

    if isinstance(palette[0], (int, float)):
        if len(palette) >= 3:
            r, g, b = palette[:3]
            return [(int(r), int(g), int(b))]
        else:
            v = int(palette[0])
            return [(v, v, v)]

    norm: List[RGB] = []
    for c in palette:
        if isinstance(c, (list, tuple, np.ndarray)) and len(c) >= 3:
            r, g, b = c[:3]
            norm.append((int(r), int(g), int(b)))

    if not norm:
        norm = [(200, 220, 230), (230, 240, 245), (180, 200, 210)]

    return norm


# ---------------- 基础渐变背景 ----------------
def _generate_base_gradient(size: int, palette, mood_intensity: float) -> Image.Image:
    palette = _normalize_palette(palette)

    if len(palette) == 1:
        palette = [palette[0], palette[0], palette[0]]
    elif len(palette) == 2:
        palette = [palette[0], palette[1], palette[0]]

    c1, c2, c3 = palette[0], palette[1], palette[2]

    w = h = size
    arr = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            tx = x / (w - 1)
            ty = y / (h - 1)
            d_center = ((x - w / 2) ** 2 + (y - h / 2) ** 2) ** 0.5 / (0.75 * w)
            d_center = max(0.0, min(1.0, d_center))

            t_diag = (tx + ty) / 2.0
            c_diag = _lerp_color(c1, c2, t_diag)
            factor = (1.0 - d_center) * 0.8 * (0.4 + 0.6 * mood_intensity)
            c_final = _lerp_color(c_diag, c3, factor)
            arr[y, x, :] = c_final

    img = Image.fromarray(arr, mode="RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=2.0))
    return img


# ---------------- Mist 柔雾 ----------------
def _apply_mist_layer(img: Image.Image, strength: float, smoothness: float, glow: float) -> Image.Image:
    if strength <= 0 and glow <= 0:
        return img

    w, h = img.size
    base = img.convert("RGB")

    if strength > 0:
        noise = np.random.rand(h, w).astype("float32")
        mist_radius = 20 + smoothness * 40
        mist_layer = Image.fromarray((noise * 255).astype("uint8"), mode="L")
        mist_layer = mist_layer.filter(ImageFilter.GaussianBlur(radius=mist_radius))

        mist_rgb = Image.merge("RGB", (mist_layer, mist_layer, mist_layer))
        white = Image.new("RGB", (w, h), (245, 245, 250))
        mist_rgb = Image.blend(white, mist_rgb, alpha=0.5)

        alpha = 0.25 + strength * 0.5
        base = Image.blend(base, mist_rgb, alpha=min(alpha, 0.95))

    if glow > 0:
        glow_radius = 8 + glow * 25
        glow_layer = base.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        glow_layer = Image.blend(base, glow_layer, alpha=0.6)

        enhancer = np.array(glow_layer).astype("float32")
        enhancer = enhancer * (1.05 + glow * 0.3)
        enhancer = np.clip(enhancer, 0, 255).astype("uint8")
        glow_layer = Image.fromarray(enhancer, mode="RGB")

        base = Image.blend(base, glow_layer, alpha=0.6)

    return base


# ---------------- Watercolor 水彩 ----------------
def _apply_watercolor_layer(img: Image.Image, palette, spread: float, layers: int, saturation: float) -> Image.Image:
    if spread <= 0 or layers <= 0:
        return img

    palette = _normalize_palette(palette)
    w, h = img.size
    base = img.convert("RGB")

    for _ in range(layers):
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        n_blobs = int(20 + spread * 40)
        for _ in range(n_blobs):
            color = random.choice(palette)
            r, g, b = color
            r = int(r + (255 - r) * (0.6 * (1 - saturation)))
            g = int(g + (255 - g) * (0.6 * (1 - saturation)))
            b = int(b + (255 - b) * (0.6 * (1 - saturation)))

            cx = random.randint(0, w)
            cy = random.randint(0, h)
            max_radius = int(min(w, h) * (0.25 + spread * 0.4))
            rx = random.randint(int(max_radius * 0.2), max_radius)
            ry = random.randint(int(max_radius * 0.2), max_radius)

            alpha = int(60 + 120 * random.random())
            bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
            draw.ellipse(bbox, fill=(r, g, b, alpha))

        blur_radius = 10 + spread * 40
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    return base


# ---------------- Pastel 粉彩 ----------------
def _apply_pastel_layer(img: Image.Image, softness: float, grain_amount: float, blend_ratio: float) -> Image.Image:
    base = img.convert("RGB")
    w, h = base.size

    if softness > 0:
        blur_radius = 2 + softness * 8
        soft = base.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    else:
        soft = base

    arr = np.array(soft).astype("float32")
    arr *= 1.05
    arr = np.clip(arr, 0, 255).astype("uint8")
    soft = Image.fromarray(arr, mode="RGB")

    if grain_amount > 0:
        noise = np.random.normal(0, grain_amount * 15, (h, w, 1)).astype("float32")
        arr = np.array(soft).astype("float32")
        arr = arr + noise
        arr = np.clip(arr, 0, 255).astype("uint8")
        soft = Image.fromarray(arr, mode="RGB")

    overlay = Image.new("RGB", (w, h), (245, 245, 248))
    pastel = Image.blend(soft, overlay, alpha=0.25)

    return Image.blend(base, pastel, alpha=blend_ratio)


# ---------------- 城市风格检测 ----------------
def _detect_city_tags(city: str, memory_text: str) -> List[str]:
    text = (city + " " + memory_text).lower()
    tags = []

    def has(words):
        return any(w in text for w in words)

    if has(["seoul", "busan", "hongdae", "gangnam", "k-pop", "kpop", "neon"]):
        tags.append("vertical_neon")

    if has(["tokyo", "shibuya", "akihabara", "shinjuku", "anime"]):
        tags.append("pixel_grid")
        tags.append("vertical_neon")

    if has(["paris", "eiffel", "louvre", "seine", "montmartre", "cafe"]):
        tags.append("arches")

    if has(["london", "thames", "big ben", "fog", "rain", "雨", "雾"]):
        tags.append("fog_overlay")

    if has(["new york", "nyc", "manhattan", "brooklyn", "times square"]):
        tags.append("chaos_lines")
        tags.append("vertical_neon")

    if has(["island", "beach", "ocean", "sea", "harbor", "港口", "海"]):
        tags.append("waves")

    if has(["mountain", "hill", "peak", "alps", "山"]):
        tags.append("peaks")

    if not tags:
        # 没匹配到明确城市风格时，给一个通用“波浪 + 雾”
        tags = ["waves"]

    return tags


# ---------------- 城市风格叠加 ----------------
def _apply_city_style_layer(img: Image.Image, palette, tags: List[str], strength: float) -> Image.Image:
    palette = _normalize_palette(palette)
    w, h = img.size
    base = img.convert("RGB")

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def pick_color():
        return random.choice(palette)

    # waves
    if "waves" in tags:
        n = 4
        for i in range(n):
            color = pick_color()
            alpha = int(40 + 80 * strength)
            thickness = int(10 + 40 * strength)
            y0 = int(h * (0.3 + 0.4 * i / n))
            for x in range(0, w, 8):
                y = y0 + int(np.sin(x / 40.0 + i) * 15)
                draw.line(
                    [(x, y), (x + 10, y)],
                    fill=(color[0], color[1], color[2], alpha),
                    width=thickness,
                )

    # vertical neon
    if "vertical_neon" in tags:
        n_lines = int(6 + 10 * strength)
        for _ in range(n_lines):
            color = pick_color()
            alpha = int(60 + 120 * strength)
            x = random.randint(0, w)
            top = random.randint(0, int(h * 0.3))
            bottom = random.randint(int(h * 0.6), h)
            width = random.randint(6, 18)
            draw.rectangle(
                (x, top, x + width, bottom),
                fill=(color[0], color[1], color[2], alpha),
            )

    # pixel grid
    if "pixel_grid" in tags:
        cell = int(16 - 8 * strength) if strength > 0 else 16
        for y in range(0, h, cell):
            for x in range(0, w, cell):
                if random.random() < 0.25 + 0.35 * strength:
                    color = pick_color()
                    alpha = int(40 + 80 * strength)
                    draw.rectangle(
                        (x, y, x + cell, y + cell),
                        fill=(color[0], color[1], color[2], alpha),
                    )

    # arches
    if "arches" in tags:
        n_arch = int(3 + 4 * strength)
        base_y = int(h * 0.75)
        for i in range(n_arch):
            color = pick_color()
            alpha = int(50 + 100 * strength)
            width = int(w * 0.15)
            gap = int(w * 0.05)
            x_center = int(w * 0.2 + i * (width + gap))
            left = x_center - width // 2
            right = x_center + width // 2
            top = int(h * (0.4 + 0.1 * random.random()))
            # 矩形+半圆
            draw.rectangle(
                (left, (top + base_y) // 2, right, base_y),
                fill=(color[0], color[1], color[2], alpha),
            )
            draw.ellipse(
                (left, top, right, top + (base_y - top) // 2),
                fill=(color[0], color[1], color[2], alpha),
            )

    # chaos lines
    if "chaos_lines" in tags:
        n = int(30 + 40 * strength)
        for _ in range(n):
            color = pick_color()
            alpha = int(30 + 120 * strength)
            x1 = random.randint(0, w)
            y1 = random.randint(0, h)
            x2 = x1 + random.randint(-100, 100)
            y2 = y1 + random.randint(-80, 80)
            draw.line(
                (x1, y1, x2, y2),
                fill=(color[0], color[1], color[2], alpha),
                width=random.randint(1, 4),
            )

    # fog overlay
    if "fog_overlay" in tags:
        fog = Image.new("L", (w, h), 0)
        fog_noise = np.random.rand(h, w).astype("float32")
        fog = Image.fromarray((fog_noise * 255).astype("uint8"), mode="L")
        fog = fog.filter(ImageFilter.GaussianBlur(radius=40))
        fog_rgb = Image.merge("RGBA", (fog, fog, fog, fog))
        overlay = Image.alpha_composite(overlay, fog_rgb)

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=4))
    result = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return result


# ---------------- 总入口：生成海报 ----------------
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
) -> bytes:
    """
    完全本地生成的海报：
    - 使用 Mist + Watercolor + Pastel 三种风格；
    - 根据 city + memory_text 的关键词自动加入城市风格叠加层；
    - emotion_link 控制情绪对这些风格的影响强度。
    """
    try:
        seed_int = int(seed)
    except Exception:
        seed_int = 42

    np.random.seed(seed_int)
    random.seed(seed_int)

    # 情绪连动：用 emotion_link 和 mood_intensity 调整各层强度
    factor = 0.3 + 0.7 * emotion_link
    mist_strength *= factor * (0.7 + 0.6 * mood_intensity)
    wc_spread *= factor * (0.6 + 0.7 * mood_intensity)
    wc_layers = max(1, int(wc_layers * (0.5 + 0.8 * mood_intensity)))
    pastel_softness *= factor * (0.5 + 0.8 * mood_intensity)
    pastel_grain *= factor
    pastel_blend *= 0.7 + 0.3 * emotion_link

    size = 1024
    base = _generate_base_gradient(size=size, palette=palette, mood_intensity=mood_intensity)

    base = _apply_mist_layer(
        img=base,
        strength=mist_strength,
        smoothness=mist_smoothness,
        glow=mist_glow,
    )

    base = _apply_watercolor_layer(
        img=base,
        palette=palette,
        spread=wc_spread,
        layers=wc_layers,
        saturation=wc_saturation,
    )

    base = _apply_pastel_layer(
        img=base,
        softness=pastel_softness,
        grain_amount=pastel_grain,
        blend_ratio=pastel_blend,
    )

    # 城市风格层
    tags = _detect_city_tags(city, memory_text)
    city_strength = 0.4 + 0.6 * emotion_link
    base = _apply_city_style_layer(base, palette, tags, city_strength)

    return _to_image_bytes(base)
