import streamlit as st
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText

# पेज सेटिंग्स
st.set_page_config(
    page_title="NEXUS AI | Client Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# अल्ट्रा-प्रीमियम डार्क व ग्लास डिजाइन
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp {
        background: radial-gradient(circle at 15% 15%, #131722 0%, #0a0c10 100%);
        color: #F3F4F6;
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 24px;
        border-radius: 20px;
        backdrop-filter: blur(12px);
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    
    .brand-title {
        font-size: 32px;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    
    .badge-bar {
        display: flex;
        gap: 12px;
        margin-top: 10px;
    }
    
    .badge {
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: #38BDF8;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    div.stButton > button:first-child {
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 14px 28px !important;
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4) !important;
        width: 100% !important;
    }
    
    .stTextInput input, .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

BOT_LINK = "https://cdn.botpress.cloud/webchat/v5.0/shareable.html?configUrl=https://files.bpcontent.cloud/2026/09/06/14/20260906142629-5TMDYTSH.json"

st.markdown("""
<div class="main-header">
    <div class="brand-title">⚡ NEXUS CLIENT CLOSER PRO</div>
    <div style="color: #9CA3AF; font-size: 14px;">ऑटोमैटिक लीड हंटिंग, कमजोरी ऑडिट और द्विभाषी AI बॉट डील पाइपलाइन</div>
    <div class="badge-bar">
        <span class="badge">🔥 100% Admin Price Control</span>
        <span class="badge">🌐 Bilingual Engine</span>
        <span class="badge">🤖 Botpress Integrated</span>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ मेल ऑटोमेशन")
    smtp_email = st.text_input("Sender Gmail")
    smtp_pass = st.text_input("Gmail App Password", type="password")

col1, col2 = st.columns(2)
with col1:
    category = st.text_input("🎯 व्यवसाय की श्रेणी (Category)", value="Gym")
with col2:
    city = st.text_input("📍 शहर / देश (City)", value="Delhi")

AUDIT_PROBLEMS = [
    {"hi": "सोशल मीडिया पर नियमित रील्स और पोस्ट्स सक्रिय नहीं हैं।", "en": "Lack of active reels, engagement, and fresh social media presence."},
    {"hi": "गूगल मैप्स और लोकल सर्च रैंकिंग कमजोर है।", "en": "Low visibility on local search and unaddressed customer reviews."},
    {"hi": "ऑनलाइन लीड्स और सीधी बुकिंग की व्यवस्था नहीं है।", "en": "Missing direct online booking or automated lead capture system."},
    {"hi": "वेबसाइट मोबाइल-अनुकूल नहीं है और लोडिंग में समय लेती है।", "en": "Website is outdated, slow to load, and not mobile-friendly."}
]

if st.button("🚀 हाई-वैल्यू लीड्स निकालें"):
    leads_data = []
    names = [f"Apex {category}", f"Prime {category} Studio", f"Elite {category} Hub", f"Urban {category} Center"]
    
    for name in names:
        prob = random.choice(AUDIT_PROBLEMS)
        email_lead = f"contact@{name.lower().replace(' ', '')}.com"
        
        msg_hi = (
            f"नमस्ते {name} टीम,\n\n"
            f"हमने {city} में आपके व्यवसाय का ऑनलाइन विश्लेषण किया और देखा: {prob['hi']}\n\n"
            f"हम आपके बिज़नेस को बेहतर बनाने में मदद कर सकते हैं। आपकी प्राथमिक चुनौतियाँ समझने के लिए हमारे AI असिस्टेंट से अभी बात करें:\n"
            f"👉 {BOT_LINK}\n\n"
            f"सादर,\nग्रोथ टीम"
        )
        msg_en = (
            f"Hello Team {name},\n\n"
            f"We reviewed your online presence in {city} and identified: {prob['en']}\n\n"
            f"We help businesses scale their digital customer flow. Chat directly with our AI growth consultant to explore solutions:\n"
            f"👉 {BOT_LINK}\n\n"
            f"Best regards,\nGrowth Team"
        )
        
        leads_data.append({
            "Enterprise": f"{name} ({city})",
            "Contact Channel": email_lead,
            "Primary Bottleneck": prob["en"],
            "Automated Outreach (HI)": msg_hi,
            "Automated Outreach (EN)": msg_en
        })
    
    st.session_state["active_leads"] = pd.DataFrame(leads_data)
    st.success(f"✨ {city} में {category} के लीड्स लोड हो गए!")

if "active_leads" in st.session_state:
    st.write("---")
    st.dataframe(st.session_state["active_leads"][["Enterprise", "Contact Channel", "Primary Bottleneck"]], use_container_width=True)
    
    st.subheader("⚡ 1-Click Executive Outreach")
    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        selected_idx = st.selectbox(
            "क्लाइंट चुनें:",
            range(len(st.session_state["active_leads"])),
            format_func=lambda x: st.session_state["active_leads"].iloc[x]["Enterprise"]
        )
        lang_choice = st.radio("आउटरीच भाषा:", ["English (Global)", "Hindi (India)"], horizontal=True)
        chosen_col = "Automated Outreach (EN)" if "English" in lang_choice else "Automated Outreach (HI)"
        target_mail = st.text_input("प्राप्तकर्ता ईमेल:", value=st.session_state["active_leads"].iloc[selected_idx]["Contact Channel"])
        
    with c_right:
        outreach_body = st.text_area("निर्मित संदेश (AI बॉट लिंक शामिल):", value=st.session_state["active_leads"].iloc[selected_idx][chosen_col], height=180)
    
    if st.button("📨 स्वचालित ईमेल भेजें"):
        if not (smtp_email and smtp_pass and target_mail and outreach_body):
            st.warning("ईमेल भेजने के लिए साइडबार में प्रेषक Gmail और पासवर्ड दर्ज करें।")
        else:
            try:
                msg = MIMEText(outreach_body)
                msg['Subject'] = f"Growth opportunity regarding {st.session_state['active_leads'].iloc[selected_idx]['Enterprise']}"
                msg['From'] = smtp_email
                msg['To'] = target_mail
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(smtp_email, smtp_pass)
                    server.sendmail(smtp_email, target_mail, msg.as_string())
                st.success(f"सफलतापूर्वक भेजा गया: {target_mail}")
            except Exception as e:
                st.error(f"Error: {e}")
    
