import io
import random
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageDraw

RGB = Tuple[int, int, int]


# ---------------------------------------------------------
# Basic Utilities
# ---------------------------------------------------------
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
    """Normalize palette format into a list of RGB tuples."""
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


# ---------------------------------------------------------
# Base Gradient Background
# ---------------------------------------------------------
def _generate_base_gradient(size: int, palette, mood_intensity: float) -> Image.Image:
    """Generate a diagonal + center-distance-based soft gradient."""
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
    img = img.filter(ImageFilter.GaussianBlur(radius=1.8))
    return img


# ---------------------------------------------------------
# Mist Layer
# ---------------------------------------------------------
def _apply_mist_layer(img: Image.Image, strength: float, smoothness: float, glow: float) -> Image.Image:
    """Apply atmospheric mist + glow."""
    if strength <= 0 and glow <= 0:
        return img

    w, h = img.size
    base = img.convert("RGB")

    # Fog / mist texture
    if strength > 0:
        noise = np.random.rand(h, w).astype("float32")
        mist_radius = 15 + smoothness * 25
        mist_layer = Image.fromarray((noise * 255).astype("uint8"), mode="L")
        mist_layer = mist_layer.filter(ImageFilter.GaussianBlur(radius=mist_radius))

        mist_rgb = Image.merge("RGB", (mist_layer, mist_layer, mist_layer))

        # Use slightly bluish-white for softer mist
        white = Image.new("RGB", (w, h), (235, 238, 247))
        mist_rgb = Image.blend(white, mist_rgb, alpha=0.4)

        alpha = 0.15 + strength * 0.35
        base = Image.blend(base, mist_rgb, alpha=min(alpha, 0.7))

    # Glow bloom
    if glow > 0:
        glow_radius = 6 + glow * 20
        glow_layer = base.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        glow_layer = Image.blend(base, glow_layer, alpha=0.55)

        enhancer = np.array(glow_layer).astype("float32")
        enhancer = enhancer * (1.03 + glow * 0.25)
        enhancer = np.clip(enhancer, 0, 255).astype("uint8")
        glow_layer = Image.fromarray(enhancer, mode="RGB")

        base = Image.blend(base, glow_layer, alpha=0.55)

    return base


# ---------------------------------------------------------
# Watercolor Spread Layer
# ---------------------------------------------------------
def _apply_watercolor_layer(img: Image.Image, palette, spread: float, layers: int, saturation: float) -> Image.Image:
    """Simulate watercolor diffusion by drawing color blobs."""
    if spread <= 0 or layers <= 0:
        return img

    palette = _normalize_palette(palette)
    w, h = img.size
    base = img.convert("RGB")

    for _ in range(layers):
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        n_blobs = int(15 + spread * 35)
        for _ in range(n_blobs):
            color = random.choice(palette)
            r, g, b = color

            r = int(r + (255 - r) * (0.4 * (1 - saturation)))
            g = int(g + (255 - g) * (0.4 * (1 - saturation)))
            b = int(b + (255 - b) * (0.4 * (1 - saturation)))

            cx = random.randint(0, w)
            cy = random.randint(0, h)
            max_radius = int(min(w, h) * (0.22 + spread * 0.35))
            rx = random.randint(int(max_radius * 0.25), max_radius)
            ry = random.randint(int(max_radius * 0.25), max_radius)

            alpha = int(70 + 110 * random.random())
            bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
            draw.ellipse(bbox, fill=(r, g, b, alpha))

        blur_radius = 8 + spread * 30
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    return base


# ---------------------------------------------------------
# Pastel Softening Layer
# ---------------------------------------------------------
def _apply_pastel_layer(img: Image.Image, softness: float, grain_amount: float, blend_ratio: float) -> Image.Image:
    """Soft pastel look."""
    base = img.convert("RGB")
    w, h = base.size

    # Soft blur
    if softness > 0:
        blur_radius = 1.5 + softness * 6
        soft = base.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    else:
        soft = base

    # Slight brightness lift
    arr = np.array(soft).astype("float32")
    arr *= 1.04
    arr = np.clip(arr, 0, 255).astype("uint8")
    soft = Image.fromarray(arr, mode="RGB")

    # Add grain
    if grain_amount > 0:
        noise = np.random.normal(0, grain_amount * 12, (h, w, 1)).astype("float32")
        arr = np.array(soft).astype("float32")
        arr = arr + noise
        arr = np.clip(arr, 0, 255).astype("uint8")
        soft = Image.fromarray(arr, mode="RGB")

    # Pastel overlay tone
    overlay = Image.new("RGB", (w, h), (245, 245, 248))
    pastel = Image.blend(soft, overlay, alpha=0.18)

    return Image.blend(base, pastel, alpha=blend_ratio * 0.8)


# ---------------------------------------------------------
# Accent palette for cities (gives each city a unique color identity)
# ---------------------------------------------------------
def _city_accent_palette(city: str, base_palette: List[RGB]) -> List[RGB]:
    """Return a city-specific accent palette."""
    name = city.lower()
    accents = _normalize_palette(base_palette)

    def hex_list(lst):
        res = []
        for hx in lst:
            hx = hx.lstrip("#")
            r = int(hx[0:2], 16)
            g = int(hx[2:4], 16)
            b = int(hx[4:6], 16)
            res.append((r, g, b))
        return res

    # South Korea — neon pink & blue
    if any(k in name for k in ["seoul", "hongdae", "gangnam"]):
        accents = hex_list(["#FF9AE5", "#A6C8FF", "#6B7CFF"])

    # Tokyo — purple + cyan pixel neon
    elif any(k in name for k in ["tokyo", "shibuya", "akihabara"]):
        accents = hex_list(["#8AF1FF", "#B388FF", "#2D0CFF"])

    # Paris — warm pastel elegance
    elif "paris" in name or "seine" in name:
        accents = hex_list(["#FFD9A0", "#FFC4D6", "#FFF2C7"])

    # Busan / Jeju — oceanic tones
    elif any(k in name for k in ["busan", "jeju"]):
        accents = hex_list(["#A5E8FF", "#87C6C9", "#5FA4A8"])

    # NYC — chaos + neon contrast
    elif any(k in name for k in ["new york", "nyc", "manhattan"]):
        accents = hex_list(["#FF4F81", "#FFC857", "#1A1D4A"])

    return accents


# ---------------------------------------------------------
# City tag detection from keywords
# ---------------------------------------------------------
def _detect_city_tags(city: str, memory_text: str) -> List[str]:
    """Detect stylistic tags based on city name & memory content."""
    text = (city + " " + memory_text).lower()
    tags = []

    def has(words):
        return any(w in text for w in words)

    # Neon-style Asian metropolis
    if has(["seoul", "busan", "hongdae", "gangnam", "k-pop", "kpop", "neon"]):
        tags.append("vertical_neon")

    # Tokyo — pixel grid + neon
    if has(["tokyo", "shibuya", "akihabara", "shinjuku", "anime"]):
        tags.append("pixel_grid")
        tags.append("vertical_neon")

    # Paris — arches motif
    if has(["paris", "eiffel", "louvre", "seine", "montmartre", "cafe"]):
        tags.append("arches")

    # London — fog layer
    if has(["london", "thames", "big ben", "fog", "rain"]):
        tags.append("fog_overlay")

    # New York chaos lines
    if has(["new york", "nyc", "manhattan", "brooklyn", "times square"]):
        tags.append("chaos_lines")
        tags.append("vertical_neon")

    # Ocean / beach cities
    if has(["island", "beach", "ocean", "sea", "harbor"]):
        tags.append("waves")

    # Mountains
    if has(["mountain", "hill", "peak", "alps"]):
        tags.append("peaks")

    # Fallback
    if not tags:
        tags = ["waves"]

    return tags


# ---------------------------------------------------------
# City Style Overlay Layer
# ---------------------------------------------------------
def _apply_city_style_layer(img: Image.Image, city: str, palette, tags: List[str], strength: float) -> Image.Image:
    """Add city-specific stylistic overlay elements."""
    palette = _city_accent_palette(city, palette)
    w, h = img.size
    base = img.convert("RGB")

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def pick_color(vivid: bool = False):
        c = random.choice(palette)
        if vivid:
            r, g, b = c
            arr = np.array([[ [r, g, b] ]], dtype="float32")
            arr *= 1.15
            arr = np.clip(arr, 0, 255).astype("uint8")
            r, g, b = arr[0, 0]
            return (int(r), int(g), int(b))
        return c

    # Wave curves
    if "waves" in tags:
        n = 4
        for i in range(n):
            color = pick_color()
            alpha = int(45 + 80 * strength)
            thickness = int(8 + 35 * strength)
            y0 = int(h * (0.3 + 0.4 * i / n))
            for x in range(0, w, 6):
                y = y0 + int(np.sin(x / 40.0 + i) * 18)
                draw.line(
                    [(x, y), (x + 10, y)],
                    fill=(color[0], color[1], color[2], alpha),
                    width=thickness,
                )

    # Vertical neon bars
    if "vertical_neon" in tags:
        n_lines = int(8 + 12 * strength)
        for _ in range(n_lines):
            color = pick_color(vivid=True)
            alpha = int(120 + 120 * strength)
            x = random.randint(0, w)
            top = random.randint(0, int(h * 0.1))
            bottom = random.randint(int(h * 0.6), h)
            width = random.randint(6, 16)
            draw.rectangle(
                (x, top, x + width, bottom),
                fill=(color[0], color[1], color[2], alpha),
            )

    # Pixel grid blocks
    if "pixel_grid" in tags:
        cell = int(18 - 10 * strength) if strength > 0 else 18
        for y in range(0, h, cell):
            for x in range(0, w, cell):
                if random.random() < 0.23 + 0.35 * strength:
                    color = pick_color(vivid=True)
                    alpha = int(80 + 120 * strength)
                    draw.rectangle(
                        (x, y, x + cell, y + cell),
                        fill=(color[0], color[1], color[2], alpha),
                    )

    # Paris arch shapes
    if "arches" in tags:
        n_arch = int(3 + 4 * strength)
        base_y = int(h * 0.78)
        for i in range(n_arch):
            color = pick_color()
            alpha = int(70 + 100 * strength)
            width = int(w * 0.16)
            gap = int(w * 0.04)
            x_center = int(w * 0.18 + i * (width + gap))
            left = x_center - width // 2
            right = x_center + width // 2
            top = int(h * (0.38 + 0.1 * random.random()))
            draw.rectangle(
                (left, (top + base_y) // 2, right, base_y),
                fill=(color[0], color[1], color[2], alpha),
            )
            draw.ellipse(
                (left, top, right, top + (base_y - top) // 2),
                fill=(color[0], color[1], color[2], alpha),
            )

    # NYC chaos strokes
    if "chaos_lines" in tags:
        n = int(35 + 45 * strength)
        for _ in range(n):
            color = pick_color(vivid=True)
            alpha = int(60 + 150 * strength)
            x1 = random.randint(0, w)
            y1 = random.randint(0, h)
            x2 = x1 + random.randint(-110, 110)
            y2 = y1 + random.randint(-90, 90)
            draw.line(
                (x1, y1, x2, y2),
                fill=(color[0], color[1], color[2], alpha),
                width=random.randint(1, 4),
            )

    # Fog layer for London
    if "fog_overlay" in tags:
        fog_noise = np.random.rand(h, w).astype("float32")
        fog = Image.fromarray((fog_noise * 255).astype("uint8"), mode="L")
        fog = fog.filter(ImageFilter.GaussianBlur(radius=35))
        fog_rgb = Image.merge("RGBA", (fog, fog, fog, fog))
        overlay = Image.alpha_composite(overlay, fog_rgb)

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=3.0))
    result = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return result


# ---------------------------------------------------------
# Main: Poster Generation Pipeline
# ---------------------------------------------------------
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
    Fully local poster generator:

    - Uses three layered styles: Mist, Watercolor, and Pastel.
    - Automatically derives city style overlays from keywords in city + memory_text.
    - emotion_link controls how strongly mood affects the final visual output.
    """
    try:
        seed_int = int(seed)
    except Exception:
        seed_int = 42

    np.random.seed(seed_int)
    random.seed(seed_int)

    # Emotion-driven strength modulation
    factor = 0.35 + 0.65 * emotion_link
    mist_strength *= factor * (0.7 + 0.6 * mood_intensity)
    wc_spread *= factor * (0.6 + 0.7 * mood_intensity)
    wc_layers = max(1, int(wc_layers * (0.6 + 0.8 * mood_intensity)))
    pastel_softness *= factor * (0.5 + 0.8 * mood_intensity)
    pastel_grain *= factor
    pastel_blend *= 0.6 + 0.3 * emotion_link

    size = 1024

    # Base gradient
    base = _generate_base_gradient(size=size, palette=palette, mood_intensity=mood_intensity)

    # Render visual layers
    base = _apply_mist_layer(base, strength=mist_strength, smoothness=mist_smoothness, glow=mist_glow)

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

    # City-specific style layer
    tags = _detect_city_tags(city, memory_text)
    city_strength = 0.45 + 0.55 * emotion_link
    base = _apply_city_style_layer(base, city, palette, tags, city_strength)

    return _to_image_bytes(base)
