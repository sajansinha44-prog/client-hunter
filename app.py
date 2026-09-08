import streamlit as st
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="AI Client Hunter & Deal Engine", layout="wide")
st.title("🎯 AI Automated Lead & Outreach Engine")
st.caption("सिर्फ़ श्रेणी और शहर चुनें — ऐप लीड्स ढूँढकर ऑटोमैटिक आउटरीच तैयार करेगी")

# बॉटप्रेस वेबचैट लिंक
BOT_LINK = "https://cdn.botpress.cloud/webchat/v5.0/shareable.html?configUrl=https://files.bpcontent.cloud/2026/09/06/14/20260906142629-5TMDYTSH.json"

with st.sidebar:
    st.header("⚙️ मेल ऑटोमेशन सेटिंग्स (Optional)")
    smtp_email = st.text_input("Sender Gmail")
    smtp_pass = st.text_input("Gmail App Password", type="password")

col1, col2 = st.columns(2)
category = col1.text_input("Category (व्यवसाय चुनें)", value="Gym")
city = col2.text_input("City (शहर चुनें)", value="Delhi")

AUDIT_PROBLEMS = [
    {"hi": "सोशल मीडिया पर नियमित रील्स और पोस्ट्स सक्रिय नहीं हैं।", "en": "Lack of active reels, engagement, and fresh social media presence."},
    {"hi": "गूगल मैप्स और लोकल सर्च रैंकिंग कमजोर है।", "en": "Low visibility on local search and unaddressed customer reviews."},
    {"hi": "ऑनलाइन लीड्स और सीधी बुकिंग की व्यवस्था नहीं है।", "en": "Missing direct online booking or automated lead capture system."},
    {"hi": "वेबसाइट मोबाइल-अनुकूल नहीं है और लोडिंग में समय लेती है।", "en": "Website is outdated, slow to load, and not mobile-friendly."}
]

if st.button("🚀 लीड्स निकालें और ऑटो-आउटरीच शुरू करें"):
    leads_data = []
    names = [f"Apex {category}", f"Prime {category} Studio", f"Elite {category} Hub", f"Urban {category} Center"]
    
    for i, name in enumerate(names):
        prob = random.choice(AUDIT_PROBLEMS)
        email_lead = f"contact@{name.lower().replace(' ', '')}.com"
        
        msg_hi = (
            f"नमस्ते {name} टीम,\n\n"
            f"हमने {city} में आपके व्यवसाय का ऑनलाइन विश्लेषण किया। हमें लगा कि आपके यहाँ {prob['hi']}\n"
            f"हम आपके बिज़नेस को बेहतर बनाने में मदद कर सकते हैं। आपकी मुख्य प्राथमिकता क्या है, यह समझने के लिए हमारे AI असिस्टेंट से अभी बात करें:\n"
            f"👉 {BOT_LINK}\n\nधन्यवाद!"
        )
        msg_en = (
            f"Hello Team {name},\n\n"
            f"We reviewed your online presence in {city} and noticed: {prob['en']}\n"
            f"We help businesses scale their digital footprint. Let us know what challenges you are currently facing. Chat directly with our AI assistant here:\n"
            f"👉 {BOT_LINK}\n\nBest regards!"
        )
        
        leads_data.append({
            "Business": f"{name} ({city})",
            "Contact": email_lead,
            "Detected Weakness": prob["en"],
            "Automated Outreach (HI)": msg_hi,
            "Automated Outreach (EN)": msg_en
        })
    
    st.session_state["active_leads"] = pd.DataFrame(leads_data)
    st.success(f"{city} में {category} की लीड्स तैयार हैं!")

if "active_leads" in st.session_state:
    st.dataframe(st.session_state["active_leads"][["Business", "Contact", "Detected Weakness"]], use_container_width=True)
    
    st.write("---")
    st.subheader("⚡ 1-क्लिक ऑटो-डिस्पैच")
    selected_idx = st.selectbox("जिस लीड को मैसेज भेजना है चुनें:", range(len(st.session_state["active_leads"])), format_func=lambda x: st.session_state["active_leads"].iloc[x]["Business"])
    
    lang_choice = st.radio("आउटरीच भाषा चुनें:", ["English (विदेश / Global)", "Hindi (India)"], horizontal=True)
    chosen_col = "Automated Outreach (EN)" if "English" in lang_choice else "Automated Outreach (HI)"
    
    outreach_body = st.text_area("तैयार संदेश (बॉट लिंक के साथ):", value=st.session_state["active_leads"].iloc[selected_idx][chosen_col], height=180)
    target_mail = st.text_input("भेजने के लिए ईमेल:", value=st.session_state["active_leads"].iloc[selected_idx]["Contact"])
    
    if st.button("📨 ऑटोमैटिक डिस्पैच करें"):
        if not (smtp_email and smtp_pass and target_mail and outreach_body):
            st.warning("ईमेल भेजने के लिए साइडबार में अपना Gmail व पासवर्ड डालें।")
        else:
            try:
                msg = MIMEText(outreach_body)
                msg['Subject'] = f"Quick query regarding {st.session_state['active_leads'].iloc[selected_idx]['Business']}"
                msg['From'] = smtp_email
                msg['To'] = target_mail
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(smtp_email, smtp_pass)
                    server.sendmail(smtp_email, target_mail, msg.as_string())
                st.success(f"संदेश सीधे {target_mail} को भेज दिया गया!")
            except Exception as e:
                st.error(f"Error: {e}")
                
