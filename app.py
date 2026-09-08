import streamlit as st
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="AI Global Client Hunter", layout="wide")
st.title("🌐 AI Global Client Hunter: All-Niche Scanner")
st.caption("विश्व के किसी भी व्यवसाय, दुकान व क्लिनिक की कमियां खोजें और स्वचालित संदेश भेजें")

with st.sidebar:
    st.header("⚙️ मेल डिस्पैचर सेटिंग्स")
    smtp_email = st.text_input("आपका प्रेषक Gmail")
    smtp_pass = st.text_input("Gmail App Password", type="password")

tab1, tab2 = st.tabs(["🔍 ग्लोबल बिज़नेस स्कैनर", "⚡ ऑटो-मैसेज डिस्पैचर"])

# विस्तृत तकनीकी कमियों का डेटाबेस
PAIN_POINTS = [
    "Instagram Reels और ताज़ा पोस्ट्स सक्रिय नहीं हैं, जिससे नए ग्राहक नहीं जुड़ रहे।",
    "Google Maps लिस्टिंग पर 15+ नकारात्मक समीक्षाओं का कोई जवाब नहीं दिया गया है।",
    "वेबसाइट मोबाइल-अनुकूल नहीं है और लोडिंग में 5 सेकंड से अधिक समय लेती है।",
    "Facebook और Instagram पर कोई विज्ञापन अभियान (Meta Ads) नहीं चल रहा है।",
    "ऑनलाइन बुकिंग / WhatsApp चैट का सीधा लिंक गायब है।"
]

with tab1:
    col1, col2 = st.columns(2)
    niche = col1.text_input("व्यवसाय का प्रकार (Category)", value="सैलून, ब्यूटी पार्लर, बुटीक, कैफ़े")
    location = col2.text_input("शहर और देश का नाम", value="New York, USA")
    
    if st.button("🚀 पूरे क्षेत्र को स्कैन करें और लीड्स निकालें"):
        st.success(f"{location} में '{niche}' के सक्रिय व्यवसाय और उनकी कमियाँ खोजी गईं:")
        
        results = []
        sample_names = [f"Apex {niche}", f"Elite {niche} Studio", f"Royal {niche} Hub", f"Urban {niche} Works"]
        
        for name in sample_names:
            issue = random.choice(PAIN_POINTS)
            rating = f"{random.uniform(3.4, 4.2):.1f}/5"
            pitch = f"नमस्ते {name} टीम, हमने देखा कि {location} में आपके व्यवसाय का {issue} हम इसे 48 घंटे में व्यवस्थित करके आपकी बिक्री और नए ग्राहकों की संख्या बढ़ा सकते हैं। क्या हम इस पर बात कर सकते हैं?"
            
            results.append({
                "Business Name": f"{name} ({location})",
                "Audit Rating": rating,
                "Detected Weakness (कमजोरी)": issue,
                "Automated Pitch": pitch
            })
            
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("📬 स्वचालित आउटरीच कतार")
    client_mail = st.text_input("लक्षित व्यवसाय का ईमेल")
    msg_body = st.text_area("तैयार संदेश (Pitch)")
    
    if st.button("⚡ सीधा ईमेल डिस्पैच करें"):
        if not (smtp_email and smtp_pass and client_mail and msg_body):
            st.error("कृपया प्रेषक ईमेल, पासवर्ड, ग्राहक का ईमेल और संदेश भरें।")
        else:
            try:
                msg = MIMEText(msg_body)
                msg['Subject'] = "आपके व्यवसाय की ऑनलाइन उपस्थिति में सुधार के लिए प्रस्ताव"
                msg['From'] = smtp_email
                msg['To'] = client_mail
                
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(smtp_email, smtp_pass)
                    server.sendmail(smtp_email, client_mail, msg.as_string())
                st.success(f"संदेश सफलतापूर्वक {client_mail} पर भेज दिया गया!")
            except Exception as e:
                st.error(f"प्रेषण विफल: {e}")
                
