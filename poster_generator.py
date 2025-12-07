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


# ---------------------------------------------------------
# 生成基础渐变背景（使用 palette）
# ---------------------------------------------------------
def _generate_base_gradient(size: int, palette: List[RGB], mood_intensity: float) -> Image.Image:
    """
    使用两到三种颜色生成一个柔和的对角线渐变背景。
    """
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
            c_final = _lerp_color(c_diag, c3, (1.0 - d_center) * 0.8 * (0.4 + 0.6 * mood_intensity))

            arr[y, x, :] = c_final

    img = Image.fromarray(arr, mode="RGB")
    # 初始轻微模糊，让渐变更柔和
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

    # 雾感：创建一层接近白色的随机噪声，并进行高斯模糊后叠加
    if strength > 0:
        noise = np.random.rand(h, w).astype("float32")
        # 平滑雾
        mist_radius = 20 + smoothness * 40
        mist_layer = Image.fromarray((noise * 255).astype("uint8"), mode="L")
        mist_layer = mist_layer.filter(ImageFilter.GaussianBlur(radius=mist_radius))

        mist_rgb = Image.merge("RGB", (mist_layer, mist_layer, mist_layer))
        # 白色雾（亮部更强）
        white = Image.new("RGB", (w, h), (245, 245, 250))
        mist_rgb = Image.blend(white, mist_rgb, alpha=0.5)

        # 根据强度与原图混合
        alpha = 0.25 + strength * 0.5
        base = Image.blend(base, mist_rgb, alpha=min(alpha, 0.95))

    # Glow：对原图做一次模糊后再叠加
    if glow > 0:
        glow_radius = 8 + glow * 25
        glow_layer = base.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        glow_layer = Image.blend(base, glow_layer, alpha=0.6)
        # 更亮一点
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
    palette: List[RGB],
    spread: float,
    layers: int,
    saturation: float,
) -> Image.Image:
    """
    使用多层半透明椭圆 + 模糊模拟水彩扩散。
    """
    if spread <= 0 or layers <= 0:
        return img

    w, h = img.size
    base = img.convert("RGB")

    for _ in range(layers):
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 每层画若干“水彩斑块”
        n_blobs = int(20 + spread * 40)
        for _ in range(n_blobs):
            color = random.choice(palette)
            # 降低饱和度（偏粉彩）
            r, g, b = color
            r = int(r + (255 - r) * (0.6 * (1 - saturation)))
            g = int(g + (255 - g) * (0.6 * (1 - saturation)))
            b = int(b + (255 - b) * (0.6 * (1 - saturation)))

            cx = random.randint(0, w)
            cy = random.randint(0, h)
            max_radius = int(min(w, h) * (0.25 + spread * 0.4))
            rx = random.randint(int(max_radius * 0.2), max_radius)
            ry = random.randint(int(max_radius * 0.2), max_radius)

            alpha = int(60 + 120 * random.random())  # 半透明
            bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
            draw.ellipse(bbox, fill=(r, g, b, alpha))

        blur_radius = 10 + spread * 40
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # 混合到 base
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

    # 柔化：高斯模糊一次
    if softness > 0:
        blur_radius = 2 + softness * 8
        soft = base.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    else:
        soft = base

    # 亮度稍微提升一点
    arr = np.array(soft).astype("float32")
    arr *= 1.05
    arr = np.clip(arr, 0, 255).astype("uint8")
    soft = Image.fromarray(arr, mode="RGB")

    # 粒子：加一点高斯噪声
    if grain_amount > 0:
        noise = np.random.normal(0, grain_amount * 15, (h, w, 1)).astype("float32")
        arr = np.array(soft).astype("float32")
        arr = arr + noise
        arr = np.clip(arr, 0, 255).astype("uint8")
        soft = Image.fromarray(arr, mode="RGB")

    # 白色 / 粉彩覆盖，让整体更淡更柔
    overlay = Image.new("RGB", (w, h), (245, 245, 248))
    pastel = Image.blend(soft, overlay, alpha=0.25)

    # 与原图按比例混合
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

    # 固定随机种子，保证可复现
    try:
        seed_int = int(seed)
    except Exception:
        seed_int = 42

    np.random.seed(seed_int)
    random.seed(seed_int)

    # 画布大小（正方形海报）
    size = 1024

    # 1. 基础渐变背景
    base = _generate_base_gradient(size=size, palette=palette, mood_intensity=mood_intensity)

    # 2. Mist 柔雾
    base = _apply_mist_layer(
        img=base,
        strength=mist_strength,
        smoothness=mist_smoothness,
        glow=mist_glow,
    )

    # 3. Watercolor 水彩扩散
    base = _apply_watercolor_layer(
        img=base,
        palette=palette,
        spread=wc_spread,
        layers=wc_layers,
        saturation=wc_saturation,
    )

    # 4. Pastel 粉彩柔化 + 颗粒
    base = _apply_pastel_layer(
        img=base,
        softness=pastel_softness,
        grain_amount=pastel_grain,
        blend_ratio=pastel_blend,
    )

    # 5. 最终轻微裁剪 & 调整（可选）
    # 可以稍微缩小画面，留一点自然边界
    final_img = base

    return _to_image_bytes(final_img)
