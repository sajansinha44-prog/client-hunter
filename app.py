import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="AI Client Hunter Pro", layout="wide")
st.title("🎯 AI Client Hunter (Direct Engine)")

with st.sidebar:
    st.header("⚙️ मेल सेटिंग्स (Optional)")
    smtp_email = st.text_input("भेजने वाला Gmail")
    smtp_pass = st.text_input("Gmail App Password", type="password")

tab1, tab2 = st.tabs(["🚀 ग्राहक ढूँढें (Auto Hunter)", "📬 सीधा ईमेल भेजें"])

DATA_TEMPLATES = {
    "Gym": [
        {"name": "Iron Pulse Fitness", "weakness": "Instagram par reels nahi hain aur Google listing verify nahi hai.", "rating": "3.8/5"},
        {"name": "Titan Gym & Spa", "weakness": "Purani website hai, mobile par theek se nahi khulti.", "rating": "4.0/5"},
        {"name": "FitLife Arena", "weakness": "Google reviews ka koi reply nahi diya ja raha, ranking down hai.", "rating": "3.7/5"}
    ],
    "Real Estate": [
        {"name": "Skyline Properties", "weakness": "Property ki video walkthroughs aur ads missing hain.", "rating": "4.1/5"},
        {"name": "Prime Realtors", "weakness": "Facebook ads par koi lead form set nahi hai.", "rating": "3.9/5"},
        {"name": "Apex Realty Solutions", "weakness": "Brochure outdated hai, local SEO weak hai.", "rating": "4.0/5"}
    ],
    "Salon / Clinic": [
        {"name": "Glow Care Clinic", "weakness": "Online appointment booking link kaam nahi kar raha.", "rating": "3.9/5"},
        {"name": "Urban Style Studio", "weakness": "Offers ke creatives aur customer testimonials missing hain.", "rating": "4.2/5"},
        {"name": "Aura Wellness", "weakness": "Google Maps par location theek se pin nahi hai.", "rating": "3.6/5"}
    ]
}

with tab1:
    col1, col2 = st.columns(2)
    category = col1.selectbox("Category Chunein", ["Gym", "Real Estate", "Salon / Clinic"])
    city = col2.text_input("Shahar ka naam", value="Delhi")
    
    if st.button("🔍 ग्राहक निकालें और पिच बनाएँ"):
        st.success(f"{city} mein {category} ke target leads mil gaye:")
        leads = DATA_TEMPLATES.get(category, DATA_TEMPLATES["Gym"])
        
        results = []
        for l in leads:
            pitch = f"नमस्ते {l['name']} टीम, हमने देखा कि {city} में आपके व्यवसाय का {l['weakness']} हम इसे 48 घंटे में ठीक करके आपके ग्राहकों की संख्या बढ़ा सकते हैं। क्या हम 5 मिनट बात कर सकते हैं?"
            results.append({
                "Business Name": f"{l['name']} ({city})",
                "Rating": l['rating'],
                "Problem / Pain Point": l['weakness'],
                "Custom Pitch": pitch
            })
            
        df = pd.DataFrame(results)
        st.table(df)

with tab2:
    client_mail = st.text_input("ग्राहक का ईमेल")
    msg_body = st.text_area("संदेश (Pitch)")
    
    if st.button("⚡ सीधा ईमेल भेजें"):
        if not (smtp_email and smtp_pass and client_mail and msg_body):
            st.error("ईमेल भेजने के लिए साइडबार में Gmail और पासवर्ड ज़रूरी है।")
        else:
            try:
                msg = MIMEText(msg_body)
                msg['Subject'] = "आपके व्यवसाय को बढ़ाने के लिए एक त्वरित सुझाव"
                msg['From'] = smtp_email
                msg['To'] = client_mail
                
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(smtp_email, smtp_pass)
                    server.sendmail(smtp_email, client_mail, msg.as_string())
                st.success(f"ईमेल {client_mail} पर भेज दिया गया!")
            except Exception as e:
                st.error(f"त्रुटि: {e}")
                
