import streamlit as st
import numpy as np
from utils import analyze_memory_local, generate_palette
from poster_generator import generate_poster

# ----------------------------
# 页面配置
# ----------------------------
st.set_page_config(
    page_title="City × Memory × Emotion — AI Poster Generator",
    layout="wide"
)

st.title("🌆 City × Memory × Emotion — Art Poster Generator")

# ----------------------------
# 折叠说明区（像你的参考图）
# ----------------------------
with st.expander("📘 About This App（点击展开）"):
    st.markdown("""
本应用将 **城市 × 记忆 × 情绪** 转换为独特的生成艺术海报。

通过三种风格叠加算法：  
- **Mist（柔雾）**：朦胧、柔和、氛围感强  
- **Watercolor（水彩扩散）**：有机纹理、自然晕染  
- **Pastel（粉彩）**：柔化画面、呈现温暖的插画质感  

整个流程不依赖任何 API，全部在本地计算，可免费无限制使用。  
你可以自由调节左侧的各项参数来设计属于自己的海报风格。
    """)

st.write("---")

# ----------------------------
# 输入区
# ----------------------------
st.subheader("Step 1 — 输入你的城市与记忆文本")

city = st.text_input("城市名称（City）", placeholder="例如：Seoul / Nanjing / Tokyo ...")
memory_text = st.text_area("写下你和这个城市的记忆：", height=180)

seed = st.number_input("随机种子（相同 seed 会生成相似风格）", value=42, step=1)

st.write("---")


# 🎛️ 左侧控件
st.sidebar.header("🌫 Mist（柔雾风格）")
mist_strength = st.sidebar.slider("Mist Strength（雾化强度）", 0.0, 1.2, 0.6)
mist_smoothness = st.sidebar.slider("Gradient Smoothness（渐变柔化）", 0.0, 1.0, 0.7)
mist_glow = st.sidebar.slider("Glow Radius（光晕半径）", 0.0, 1.0, 0.4)

st.sidebar.header("🎨 Watercolor（水彩扩散）")
wc_spread = st.sidebar.slider("Spread Radius（水彩扩散半径）", 0.0, 1.0, 0.45)
wc_layers = st.sidebar.slider("Layer Count（水彩层数）", 1, 5, 2)
wc_saturation = st.sidebar.slider("Ink Saturation（色彩墨量）", 0.0, 1.0, 0.6)

st.sidebar.header("🩶 Pastel（粉彩柔化）")
pastel_softness = st.sidebar.slider("Softness（柔和度）", 0.0, 1.0, 0.5)
pastel_grain = st.sidebar.slider("Grain Amount（颗粒）", 0.0, 1.0, 0.25)
pastel_blend = st.sidebar.slider("Blend Ratio（混合比例）", 0.0, 1.0, 0.6)

st.sidebar.write("----")

generate_btn = st.sidebar.button("🎨 生成海报 Generate Poster")


# ----------------------------
# Step 2：本地分析情绪 + 颜色
# ----------------------------
st.subheader("Step 2 — AI 分析结果（可写入报告）")

if generate_btn:
    if not city.strip() or not memory_text.strip():
        st.error("城市和记忆文本不能为空！")
        st.stop()

    analysis = analyze_memory_local(city, memory_text)
    st.json(analysis)

    st.write("---")

    # ----------------------------
    # Step 3：本地生成海报
    # ----------------------------
    st.subheader("Step 3 — 本地生成艺术海报（无需 API，免费）")

    with st.spinner("正在生成海报，请稍候..."):

        poster = generate_poster(
            palette=analysis["palette"],
            mood_intensity=analysis["intensity"],
            seed=seed,

            # A+C+E 风格参数传入生成器
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

        st.image(poster, caption="🎨 海报生成结果", use_column_width=True)

        st.download_button(
            "📥 下载 PNG 文件",
            data=poster,
            file_name=f"{city}_art_poster.png",
            mime="image/png"
        )
