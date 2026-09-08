import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai

st.set_page_config(page_title="AI Client Hunter Pro", layout="wide")
st.title("🎯 AI Client Hunter: Automated Pipeline")

with st.sidebar:
    st.header("⚙️ API & Mail Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    smtp_email = st.text_input("Sender Email (Gmail)")
    smtp_pass = st.text_input("Gmail App Password", type="password")
    if api_key:
        genai.configure(api_key=api_key)

tab1, tab2 = st.tabs(["🚀 Automated Lead Hunter", "📬 Auto-Outreach Queue"])

with tab1:
    col1, col2 = st.columns(2)
    niche = col1.text_input("Target Niche", value="Gyms, Real Estate, Clinics")
    city = col2.text_input("Target City", value="Delhi")
    
    if st.button("🔍 Auto-Discover & Qualify Leads"):
        if not api_key:
            st.error("Gemini API Key dalein!")
        else:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Act as an automation scraper for {niche} in {city}. Generate 3 realistic leads with: Business Name, Contact Email/Phone, Pain Point, and a 30-word personalized cold outreach message. Return format: Name | Contact | Pain Point | Pitch"
            try:
                res = model.generate_content(prompt)
                st.success("Leads Discovered & Scored via AI!")
                st.write(res.text)
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    st.write("### Direct Auto-Dispatch Engine")
    client_mail = st.text_input("Recipient Email")
    msg_body = st.text_area("Outreach Pitch Body")
    
    if st.button("⚡ Send Pitch Automatically"):
        if not (smtp_email and smtp_pass and client_mail and msg_body):
            st.error("Email, password aur message required hain.")
        else:
            try:
                msg = MIMEText(msg_body)
                msg['Subject'] = "Quick question regarding your business workflow"
                msg['From'] = smtp_email
                msg['To'] = client_mail
                
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(smtp_email, smtp_pass)
                    server.sendmail(smtp_email, client_mail, msg.as_string())
                st.success(f"Message sent directly to {client_mail}!")
            except Exception as e:
                st.error(f"Failed to send: {e}")
            
