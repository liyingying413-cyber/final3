import streamlit as st
from utils import analyze_memory_local
from poster_generator import generate_poster

st.set_page_config(
    page_title="City × Memory × Emotion — Art Poster Generator",
    layout="wide"
)

st.title("🌆 City × Memory × Emotion — Art Poster Generator")

# 说明折叠块
with st.expander("📘 About This App（点击展开）", expanded=True):
    st.markdown("""
本应用将 **城市 × 记忆 × 情绪** 转换为抽象艺术海报。

特点：

- 不依赖任何 API，全程本地生成（完全免费、可在 Streamlit Cloud 运行）。
- 结合三种风格：
  - **Mist（柔雾）**：朦胧、梦幻的氛围。
  - **Watercolor（水彩扩散）**：有机流动纹理。
  - **Pastel（粉彩）**：柔和颗粒与插画质感。
- 根据你的 **城市名称** 与 **记忆文本**，分析情绪并映射到色彩与构图风格。

你可以在左侧调节各项参数，探索不同的情绪化视觉表达。
    """)

st.write("---")

# ----------------------------
# 输入区
# ----------------------------
st.subheader("Step 1 — 输入你的城市与记忆文本")

city = st.text_input("城市名称（City）", placeholder="例如：Seoul / Nanjing / Tokyo ...")
memory_text = st.text_area("写下你和这个城市的记忆：", height=180)

st.write("---")

# 🎛️ 左侧控件
st.sidebar.header("🌫 Mist（柔雾风格）")
mist_strength = st.sidebar.slider("Mist Strength（雾化强度）", 0.0, 1.2, 0.6)
mist_smoothness = st.sidebar.slider("Gradient Smoothness（渐变柔化）", 0.0, 1.0, 0.7)
mist_glow = st.sidebar.slider("Glow Radius（光晕程度）", 0.0, 1.0, 0.4)

st.sidebar.header("🎨 Watercolor（水彩扩散）")
wc_spread = st.sidebar.slider("Spread Radius（扩散范围）", 0.0, 1.0, 0.45)
wc_layers = st.sidebar.slider("Layer Count（水彩层数）", 1, 5, 2)
wc_saturation = st.sidebar.slider("Ink Saturation（墨色浓度）", 0.0, 1.0, 0.6)

st.sidebar.header("🩶 Pastel（粉彩柔化）")
pastel_softness = st.sidebar.slider("Softness（柔和度）", 0.0, 1.0, 0.5)
pastel_grain = st.sidebar.slider("Grain Amount（颗粒）", 0.0, 1.0, 0.25)
pastel_blend = st.sidebar.slider("Blend Ratio（混合比例）", 0.0, 1.0, 0.6)

st.sidebar.header("💗 情绪影响（Emotion Link）")
emotion_link = st.sidebar.slider("情绪对效果的影响强度", 0.0, 1.0, 0.7)

st.sidebar.header("🎲 随机种子 Seed")
manual_seed = st.sidebar.number_input("Seed（可选，不改则自动随文本变化）", value=42, step=1)
use_auto_seed = st.sidebar.checkbox("自动根据城市 + 文本生成种子", value=True)

st.sidebar.write("----")
generate_btn = st.sidebar.button("🎨 生成海报 Generate Poster")

# ----------------------------
# Step 2：本地情绪分析
# ----------------------------
st.subheader("Step 2 — 文本情绪与色彩分析结果")

if generate_btn:
    if not city.strip() or not memory_text.strip():
        st.error("城市和记忆文本不能为空！")
        st.stop()

    analysis = analyze_memory_local(city, memory_text)
    st.json(analysis)

    # 自动 seed：基于 city + memory_text
    if use_auto_seed:
        seed = abs(hash(city.strip() + memory_text.strip())) % 10**6
    else:
        seed = int(manual_seed)

    st.write("---")

    # ----------------------------
    # Step 3：本地生成艺术海报
    # ----------------------------
    st.subheader("Step 3 — 本地生成艺术海报（完全离线）")

    with st.spinner("正在生成海报，请稍候..."):
        poster_bytes = generate_poster(
            city=city,
            memory_text=memory_text,
            mood=analysis["mood"],
            palette=analysis["palette"],
            mood_intensity=analysis["intensity"],
            seed=seed,
            emotion_link=emotion_link,
            mist_strength=mist_strength,
            mist_smoothness=mist_smoothness,
            mist_glow=mist_glow,
            wc_spread=wc_spread,
            wc_layers=wc_layers,
            wc_saturation=wc_saturation,
            pastel_softness=pastel_softness,
            pastel_grain=pastel_grain,
            pastel_blend=pastel_blend,
        )

        st.image(poster_bytes, caption="🎨 海报生成结果", use_column_width=True)

        st.download_button(
            "📥 下载 PNG 文件",
            data=poster_bytes,
            file_name=f"{city}_art_poster.png",
            mime="image/png"
        )
