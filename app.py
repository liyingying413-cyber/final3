import streamlit as st
from utils import analyze_with_openai, local_analyze
from poster_generator import generate_poster_with_stable_diffusion

st.set_page_config(
    page_title="City × Memory × Emotion — AI Poster",
    layout="wide",
)


# ----------------- 左侧控制面板：小红书风格控件 -----------------
with st.sidebar:
    st.title("🎛️ 控制面板")

    st.markdown("在这里调节海报的**风格 / 氛围 / 留白 / 形状**。")

    style_mode_user = st.selectbox(
        "海报主风格 Style Mode",
        [
            "Pastel Mist",
            "Dreamy Soft",
            "Magazine Minimal",
            "Film Grain Soft",
            "Glow Gradient",
            "Hazy Bloom",
        ],
        index=2,
    )

    st.markdown("### 🎨 色彩 Color")
    color_temp = st.slider("色温 Color Temperature", -1.0, 1.0, 0.2)
    pastel_intensity = st.slider("粉彩感 Pastel Intensity", 0.0, 1.0, 0.7)
    desaturation = st.slider("低饱和度 Desaturation", 0.0, 1.0, 0.3)

    st.markdown("### 🌫 氛围 Atmosphere")
    dreamy_blur = st.slider("梦幻模糊 Dreamy Blur", 0.0, 30.0, 12.0)
    bloom = st.slider("光晕 Bloom", 0.0, 1.0, 0.4)
    grain = st.slider("胶片颗粒 Film Grain", 0.0, 1.0, 0.15)
    vignette = st.slider("暗角 Vignette", 0.0, 1.0, 0.2)

    st.markdown("### 🖼 构图 Composition")
    whitespace = st.slider("留白比例 Whitespace", 0.0, 0.6, 0.25)
    focal_shift = st.slider("视觉中心偏移 Focal Shift", -1.0, 1.0, 0.1)
    soft_overlay = st.slider("柔光叠加 Soft Overlay", 0.0, 1.0, 0.5)

    st.markdown("### 🫧 形状 Shapes（液态 / 云雾感）")
    blob_count = st.slider("形状数量 Blob Count", 5, 80, 25)
    blob_size = st.slider("形状大小 Blob Size", 20, 200, 80)
    blob_softness = st.slider("边缘柔和度 Edge Softness", 0.0, 1.0, 0.8)

    st.markdown("### 💗 情绪影响 Emotion Influence")
    mood_influence = st.slider("情绪对画面的影响 Mood Influence", 0.0, 1.0, 0.5)

    seed = st.number_input("随机种子 Seed（同样的 seed 会生成相似海报）", 0, 999999, 42, step=1)

    generate_clicked = st.button("✨ 生成海报 Generate Poster")

# 把所有控制项打包成一个 dict 传给生成函数
style_controls = dict(
    style_mode_user=style_mode_user,
    color_temp=color_temp,
    pastel_intensity=pastel_intensity,
    desaturation=desaturation,
    dreamy_blur=dreamy_blur,
    bloom=bloom,
    grain=grain,
    vignette=vignette,
    whitespace=whitespace,
    focal_shift=focal_shift,
    soft_overlay=soft_overlay,
    blob_count=blob_count,
    blob_size=blob_size,
    blob_softness=blob_softness,
    mood_influence=mood_influence,
)

# ----------------- 右侧主体区域：标题 + 说明 + 输入 + 结果 -----------------
col_main, = st.columns([1])

with col_main:
    st.title("🌆 Emotional City Poster — 城市 × 记忆 × 情绪海报")

    with st.expander("📘 Instructions 使用说明", expanded=True):
        st.markdown(
            """
这个应用可以把你的 **城市记忆（City + Memory）** 转化为一张具有“小红书美感”的抽象情绪海报：

1. 在下方输入：一个城市名 + 一段关于这个城市的记忆。
2. 点击左侧的滑块，调节海报的 **风格、模糊、光晕、颗粒、留白** 等艺术参数。
3. 点击「生成海报」，AI 会：
   - 使用 **OpenAI** 分析记忆文本的情绪、色彩和氛围；
   - 使用 **Stable Diffusion** 生成一张 1:1 比例的抽象情绪海报；
   - 展示可写入报告的分析 JSON + PNG 下载按钮。

> 这个项目可以作为 “Generative Art + Data-driven Design + Web-based Creativity” 的 Final Project。
"""
        )

    st.subheader("Step 0 — 输入你的城市记忆")
    city = st.text_input("城市名 City（例如：Seoul / Tokyo / Paris）")
    memory = st.text_area("写下你和这座城市的记忆文本：", height=180)

    if generate_clicked:
        if not city.strip() or not memory.strip():
            st.error("请输入城市名和记忆文本。")
        else:
            # Step 1: 文本分析
            with st.spinner("Step 1 — 使用 OpenAI 分析情绪与色彩…"):
                analysis = analyze_with_openai(city, memory)
                if analysis is None:
                    st.warning("⚠ OpenAI 调用失败，改用本地 fallback 规则分析。")
                    analysis = local_analyze(city, memory)

            st.subheader("Step 2 — AI 分析结果（可写入报告）")
            st.json(analysis)

            # Step 2: 生成海报
            with st.spinner("Step 3 — Stable Diffusion 正在生成小红书风格海报…"):
                img = generate_poster_with_stable_diffusion(
                    analysis=analysis,
                    controls=style_controls,
                    seed=int(seed),
                )

            if img is None:
                st.error("❌ Stable Diffusion 生成失败，请检查 STABILITY_API_KEY 或稍后重试。")
            else:
                st.subheader("Step 4 — 海报预览 Preview")
                st.image(img, use_column_width=True)

                import io
                buf = io.BytesIO()
                img.save(buf, format="PNG")

                st.download_button(
                    "⬇ 下载 PNG 海报",
                    data=buf.getvalue(),
                    file_name="city_memory_poster.png",
                    mime="image/png",
                )
