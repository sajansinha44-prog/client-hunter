import streamlit as st
import pandas as pd
import urllib.parse

st.set_page_config(
    page_title="NEXUS AI | Zero-Cost Client Closer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(18, 20, 32) 0%, rgb(11, 13, 19) 90.2%);
        color: #F3F4F6;
    }
    .hero-container {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 22px;
        border-radius: 18px;
        backdrop-filter: blur(12px);
        margin-bottom: 20px;
    }
    .hero-title {
        font-size: 26px;
        font-weight: 800;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 24px !important;
        width: 100% !important;
    }
    .action-btn {
        display: block;
        text-align: center;
        background: #25D366;
        color: white !important;
        font-weight: 700;
        padding: 12px;
        border-radius: 10px;
        text-decoration: none;
        margin-top: 8px;
    }
    .mail-btn {
        display: block;
        text-align: center;
        background: #EA4335;
        color: white !important;
        font-weight: 700;
        padding: 12px;
        border-radius: 10px;
        text-decoration: none;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

BOT_LINK = "https://cdn.botpress.cloud/webchat/v5.0/shareable.html?configUrl=https://files.bpcontent.cloud/2026/09/06/14/20260906142629-5TMDYTSH.json"

st.markdown("""
<div class="hero-container">
    <div class="hero-title">⚡ NEXUS AI // 100% FREE CLIENT HUNTER</div>
    <div style="color: #9CA3AF; font-size: 13px;">बिना किसी खर्चे के — शहर और बिज़नेस चुनिए, 1-क्लिक में सीधा संदेश भेजिए</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    category = st.text_input("🎯 व्यवसाय की श्रेणी (Category)", value="Gym")
with col2:
    city = st.text_input("📍 शहर / इलाका (City)", value="Rohini, Delhi")

# Google Maps पर 1-क्लिक में असली बिज़नेस खोलने का लिंक
search_query = urllib.parse.quote(f"{category} in {city}")
maps_url = f"https://www.google.com/maps/search/{search_query}"

st.markdown(f"""
<a href="{maps_url}" target="_blank" style="display:block; text-align:center; background: rgba(59, 130, 246, 0.15); border: 1px solid #3B82F6; color: #60A5FA; padding: 10px; border-radius: 10px; text-decoration: none; font-weight: 600; margin-bottom: 15px;">
    📍 {city} के सभी असली {category} Google Maps पर खोलें (फ़ोन नंबर और रेटिंग देखने हेतु)
</a>
""", unsafe_allow_html=True)

st.subheader("⚡ 1-Click Client Closer")
biz_name = st.text_input("क्लाइंट/दुकान का नाम (Maps से देखकर लिखें):", value=f"Target {category}")
client_phone = st.text_input("क्लाइंट का WhatsApp नंबर (उदा: 919876543210):", value="")
client_email = st.text_input("क्लाइंट का Email (वैकल्पिक):", value="")

lang = st.radio("आउटरीच भाषा:", ["हिंदी (India)", "English (Global)"], horizontal=True)

if lang == "हिंदी (India)":
    pitch = (
        f"नमस्ते {biz_name} टीम,\n\n"
        f"हमने {city} में आपके व्यवसाय की ऑनलाइन प्रोफाइल देखी। हमें लगा कि आपकी Google Maps रैंकिंग और सोशल मीडिया रील्स पर काम करके आपके ग्राहकों की संख्या काफी बढ़ाई जा सकती है।\n\n"
        f"आपकी मुख्य चुनौती क्या है, यह समझने और समाधान देखने के लिए हमारे AI कंसल्टेंट से अभी चैट करें:\n"
        f"👉 {BOT_LINK}\n\nधन्यवाद!"
    )
else:
    pitch = (
        f"Hello Team {biz_name},\n\n"
        f"We reviewed your business profile in {city}. We noticed your digital presence could generate significantly more footfall and leads.\n\n"
        f"To discuss your bottlenecks and get a tailored solution, chat with our AI consultant here:\n"
        f"👉 {BOT_LINK}\n\nBest regards!"
    )

st.text_area("तैयार संदेश (बॉट लिंक शामिल):", value=pitch, height=180)

col_b1, col_b2 = st.columns(2)
with col_b1:
    if client_phone:
        clean_phone = client_phone.replace("+", "").replace(" ", "")
        wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(pitch)}"
        st.markdown(f'<a href="{wa_url}" target="_blank" class="action-btn">💬 सीधे WhatsApp पर भेजें</a>', unsafe_allow_html=True)
    else:
        st.caption("WhatsApp पर भेजने के लिए ऊपर नंबर भरें।")

with col_b2:
    if client_email:
        mailto_url = f"mailto:{client_email}?subject=Growth inquiry regarding {biz_name}&body={urllib.parse.quote(pitch)}"
        st.markdown(f'<a href="{mailto_url}" target="_blank" class="mail-btn">✉️ सीधे मेल ऐप से भेजें</a>', unsafe_allow_html=True)
    else:
        st.caption("ईमेल भेजने के लिए ऊपर ईमेल भरें।")
        
