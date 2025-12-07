import io
import random
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageDraw


RGB = Tuple[int, int, int]


# ---------------------------------------------------------
# 基础工具函数
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
    """
    把各种奇怪格式的 palette 统一成 [(r,g,b), ...] 形式，避免 int 之类的错误。
    支持：
    - [(r,g,b), (r,g,b)...]
    - [[r,g,b], [r,g,b]...]
    - [r,g,b]
    - numpy 数组
    """
    # numpy -> list
    if isinstance(palette, np.ndarray):
        palette = palette.tolist()

    if not palette:
        return [(200, 220, 230), (230, 240, 245), (180, 200, 210)]

    # 如果是 [r,g,b] 这种扁平形式
    if isinstance(palette[0], (int, float)):
        if len(palette) >= 3:
            r, g, b = palette[:3]
            return [(int(r), int(g), int(b))]
        else:
            v = int(palette[0])
            return [(v, v, v)]

    # 正常 list[tuple/list]
    norm: List[RGB] = []
    for c in palette:
        if isinstance(c, (list, tuple, np.ndarray)) and len(c) >= 3:
            r, g, b = c[:3]
            norm.append((int(r), int(g), int(b)))

    if not norm:
        norm = [(200, 220, 230), (230, 240, 245), (180, 200, 210)]

    return norm


# ---------------------------------------------------------
# 生成基础渐变背景（使用 palette）
# ---------------------------------------------------------
def _generate_base_gradient(size: int, palette, mood_intensity: float) -> Image.Image:
    """
    使用两到三种颜色生成一个柔和的对角线渐变背景。
    """
    palette = _normalize_palette(palette)

    if len(palette) == 0:
        palette = [(200, 220, 230), (230, 240, 245), (180, 200, 210)]
    elif len(palette) == 1:
        palette = [palette[0], palette[0], palette[0]]

    c1 = palette[0]
    c2 = palette[1] if len(palette) > 1 else palette[0]
    c3 = palette[2] if len(palette) > 2 else palette[1]

    w = h = size
    arr = np.zeros((h, w, 3), dtype=np.uint8)

    # 生成对角 + 中心渐变
    for y in range(h):
        for x in range(w):
            tx = x / (w - 1)
            ty = y / (h - 1)
            d_center = ((x - w / 2) ** 2 + (y - h / 2) ** 2) ** 0.5 / (0.75 * w)
            d_center = max(0.0, min(1.0, d_center))

            # 对角插值
            t_diag = (tx + ty) / 2.0
            c_diag = _lerp_color(c1, c2, t_diag)
            # 往中心靠近 c3
            c_final = _lerp_color(
                c_diag,
                c3,
                (1.0 - d_center) * 0.8 * (0.4 + 0.6 * mood_intensity),
            )

            arr[y, x, :] = c_final

    img = Image.fromarray(arr, mode="RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=2.0))
    return img


# ---------------------------------------------------------
# Mist（柔雾风格）
# ---------------------------------------------------------
def _apply_mist_layer(img: Image.Image, strength: float, smoothness: float, glow: float) -> Image.Image:
    """
    在图像上叠加“雾感”和“泛光”，模拟 Mist 风格。
    """
    if strength <= 0 and glow <= 0:
        return img

    w, h = img.size
    base = img.convert("RGB")

    # 雾感
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

    # Glow
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


# ---------------------------------------------------------
# Watercolor（水彩扩散）
# ---------------------------------------------------------
def _apply_watercolor_layer(
    img: Image.Image,
    palette,
    spread: float,
    layers: int,
    saturation: float,
) -> Image.Image:
    """
    使用多层半透明椭圆 + 模糊模拟水彩扩散。
    """
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


# ---------------------------------------------------------
# Pastel（粉彩柔化 + 颗粒）
# ---------------------------------------------------------
def _apply_pastel_layer(
    img: Image.Image,
    softness: float,
    grain_amount: float,
    blend_ratio: float,
) -> Image.Image:
    """
    粉彩感：整体柔化 + 轻微颗粒 + 淡色叠加。
    """
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

    return Image.blend(img, pastel, alpha=blend_ratio)


# ---------------------------------------------------------
# 总入口：生成海报
# ---------------------------------------------------------
def generate_poster(
    palette,
    mood_intensity: float,
    seed: int,
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
    核心生成函数：
    - 完全本地计算，不依赖任何外部 API；
    - 使用 A + C + E 三种风格：Mist + Watercolor + Pastel；
    - 返回 PNG 字节流，可直接给 Streamlit 显示与下载。
    """
    try:
        seed_int = int(seed)
    except Exception:
        seed_int = 42

    np.random.seed(seed_int)
    random.seed(seed_int)

    size = 1024

    base = _generate_base_gradient(size=size, palette=palette, mood_intensity=mood_intensity)

    base = _apply_mist_layer(
        img=base,
        strength=mist_strength,
        smooth
