import streamlit as st
from utils import analyze_with_openai, local_analyze
from poster_generator import generate_poster_with_stable_diffusion

# -------------------------
# 页面标题 / 布局
# -------------------------
st.set_page_config(page_title="City × Memory × Emotion — AI Poster", layout="wide")

st.title("✨ City × Memory × Emotion — AI Poster Generator")

st.markdown(
    """
    输入城市名和记忆文本，AI 会分析其中的情绪、颜色、意象，并自动生成唯美渐变风格的小红书风海报。
    左侧可调节艺术风格参数（形状、模糊、柔和度、色彩等），获得更高自由度与更具风格化的艺术呈现。
    """
)

# -------------------------
# Layout: 左侧 Sidebar 控件
# -------------------------
with st.sidebar:
    st.header("🟣 形状 Shapes（液态 / 云雾感）")

    blob_count = st.slider("形状数量 Blob Count", 5, 80, 25)
    blob_size = st.slider("形状大小 Blob Size", 20, 120, 80)
    edge_softness = st.slider("边缘柔和度 Edge Softness", 0.0, 1.0, 0.8)

    st.header("💓 情绪影响 Emotion Influence")
    mood_influence = st.slider("情绪对画面的影响 Mood Influence", 0.0, 1.0, 0.5)

    st.header("🎨 Style Parameters 风格参数")
    style_mode_user = st.selectbox(
        "风格模式 Style Mode",
        [
            "Pastel Mist",
            "Dreamy Film",
            "Magazine Clean",
            "Glow Bloom",
            "Hazy Fade",
        ],
    )

    pastel_intensity = st.slider("柔和度 Pastel Intensity", 0.0, 1.0, 0.7)
    desaturation = st.slider("饱和度降低 Desaturation", 0.0, 1.0, 0.3)
    dreamy_blur = st.slider("景深模糊 Dreamy Blur", 0, 30, 12)
    bloom = st.slider("高光扩散 Bloom", 0.0, 1.0, 0.4)
    grain = st.slider("胶片颗粒 Grain", 0.0, 1.0, 0.15)
    vignette = st.slider("暗角强度 Vignette", 0.0, 1.0, 0.2)
    whitespace = st.slider("留白比例 Whitespace", 0.0, 0.5, 0.25)

    st.header("🎲 随机种子 Seed")
    seed = st.number_input("随机种子（相同 seed 会生成相似风格海报）", value=42, step=1)

    st.write("---")
    submit_btn = st.button("✨ 生成海报 Generate Poster")

# 将控件封装为字典传给生成器
style_controls = {
    "blob_count": blob_count,
    "blob_size": blob_size,
    "edge_softness": edge_softness,
    "mood_influence": mood_influence,
    "style_mode_user": style_mode_user,
    "pastel_intensity": pastel_intensity,
    "desaturation": desaturation,
    "dreamy_blur": dreamy_blur,
    "bloom": bloom,
    "grain": grain,
    "vignette": vignette,
    "whitespace": whitespace,
}

# -------------------------
# Step 1 — 用户输入
# -------------------------
st.subheader("Step 1 — 输入你的城市记忆")

city = st.text_input("城市名（City）", placeholder="如：Seoul / Tokyo / Paris …")
memory = st.text_area("写下你和这座城市的记忆：", height=200)

# -------------------------
# Step 2 — AI 分析
# -------------------------
if submit_btn:
    if not city.strip() or not memory.strip():
        st.error("❗ 城市名与记忆内容不能为空。")
        st.stop()

    # 调用 OpenAI
    with st.spinner("Step 1 — 使用 OpenAI AI 分析文本风格…"):
        analysis = analyze_with_openai(city, memory)

    if analysis is None:
        st.warning("⚠ OpenAI 调用失败，改用本地 fallback 分析。")
        analysis = local_analyze(city, memory)

    st.subheader("Step 2 — AI 分析结果（可写入报告）")
    st.json(analysis)

    # -------------------------
    # Step 3 — Stable Diffusion 生成海报
    # -------------------------
    st.subheader("Step 3 — 使用 Stable Diffusion 生成海报")

    with st.spinner("Stable Diffusion 正在生成小红书风格海报…"):
        img, err_msg = generate_poster_with_stable_diffusion(
            analysis=analysis,
            controls=style_controls,
            seed=int(seed),
        )

    if img is None:
        st.error(f"❌ Stable Diffusion 生成失败：{err_msg}")
        st.stop()

    # -------------------------
    # Step 4 — 海报预览 + 下载
    # -------------------------
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
