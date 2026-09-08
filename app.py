import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="AI Client Hunter", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 AI Client Hunter")
st.caption("Zero-Cost Lead Scoring & Outreach Hub")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key (Optional)", type="password", help="aistudio.google.com se free le sakte ho")
    if api_key:
        genai.configure(api_key=api_key)

if "leads" not in st.session_state:
    st.session_state.leads = []

with st.expander("➕ Add New Lead / Business", expanded=True):
    col1, col2 = st.columns(2)
    business_name = col1.text_input("Client / Company Name")
    channel = col2.selectbox("Outreach Platform", ["LinkedIn", "Instagram", "Email", "WhatsApp"])
    business_context = st.text_area("Client Bio, Website ya Pain Point")

    if st.button("🧠 Qualify & Generate Hook"):
        if not business_name or not business_context:
            st.error("Naam aur business context dono likho!")
        else:
            if api_key:
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    prompt = f"Analyze lead: Name: {business_name}, Details: {business_context}, Platform: {channel}. Give Score 1-100, Status, and a short 40-word personalized cold pitch."
                    response = model.generate_content(prompt)
                    output_text = response.text
                except Exception as e:
                    output_text = f"API Error: {str(e)}"
            else:
                output_text = f"Score: 88/100 | Status: Hot Lead\nPitch: Hey {business_name}, noticed your manual workflow. We built an automated pipeline that can save 10+ hrs/week. Want a quick 2-min breakdown?"

            new_lead = {
                "Name": business_name,
                "Platform": channel,
                "Context": business_context,
                "AI_Analysis": output_text
            }
            st.session_state.leads.append(new_lead)
            st.success("Lead qualify ho gayi!")
            st.write(output_text)

st.subheader("⚡ Outreach Action Queue")
if len(st.session_state.leads) == 0:
    st.info("Abhi koi lead nahi hai. Upar details daal kar button dabayein.")
else:
    for idx, item in enumerate(st.session_state.leads):
        st.markdown(f"**{item['Name']}** ({item['Platform']})")
        st.caption(item['AI_Analysis'])
        if st.button(f"🚀 Action Required: Send Pitch manually #{idx+1}"):
            st.warning("Platform policy bypass nahi hogi. Pitch copy karke direct send karein.")

    df = pd.DataFrame(st.session_state.leads)
    st.download_button(
        label="💾 Export Leads (CSV)",
        data=df.to_csv(index=False),
        file_name="client_hunter_leads.csv",
        mime="text/csv"
    )
