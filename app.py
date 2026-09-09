import streamlit as st
import sqlite3
import requests
import json
import re
import hmac
from datetime import datetime
from urllib.parse import urlparse


# =========================================================
# NEXUS AI — CLIENT HUNTER
# Streamlit Cloud compatible
# =========================================================

st.set_page_config(
    page_title="NEXUS AI — Client Hunter",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top left, #182033 0%, #0b1020 35%, #070b14 100%);
    color: #f5f7fb;
}

.block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
}

h1, h2, h3 {
    letter-spacing: -0.4px;
}

[data-testid="stSidebar"] {
    background: #080d18;
    border-right: 1px solid #20283a;
}

.card {
    background: rgba(18, 25, 40, 0.88);
    border: 1px solid #263149;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 15px;
}

.metric-card {
    background: linear-gradient(
        145deg,
        rgba(24, 34, 55, .95),
        rgba(11, 17, 29, .95)
    );
    border: 1px solid #293650;
    border-radius: 18px;
    padding: 18px;
    min-height: 120px;
}

.metric-number {
    font-size: 32px;
    font-weight: 800;
}

.metric-label {
    color: #9ca9c0;
    font-size: 14px;
}

.small-muted {
    color: #8d9ab0;
    font-size: 13px;
}

.success-box {
    background: rgba(20, 120, 70, .12);
    border: 1px solid rgba(50, 200, 120, .35);
    border-radius: 14px;
    padding: 15px;
}

.warning-box {
    background: rgba(180, 120, 20, .12);
    border: 1px solid rgba(230, 170, 60, .35);
    border-radius: 14px;
    padding: 15px;
}

.danger-box {
    background: rgba(180, 40, 50, .12);
    border: 1px solid rgba(240, 80, 90, .35);
    border-radius: 14px;
    padding: 15px;
}

textarea, input {
    border-radius: 10px !important;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 650;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE
# =========================================================

DB_FILE = "nexus_ai.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business TEXT,
            website TEXT,
            city TEXT,
            country TEXT,
            category TEXT,
            contact TEXT,
            source TEXT,
            problem TEXT,
            service TEXT,
            reason TEXT,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'NEW',
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            channel TEXT,
            message TEXT,
            status TEXT DEFAULT 'DRAFT',
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            reply TEXT,
            classification TEXT,
            summary TEXT,
            next_action TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# SECRETS
# =========================================================

def secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
        return str(value) if value else default
    except Exception:
        return default


APP_PASSWORD = secret("APP_PASSWORD", "")
GEMINI_KEY = secret("GEMINI_API_KEY", "")
GEMINI_MODEL = secret("GEMINI_MODEL", "gemini-2.5-flash")


# =========================================================
# LOGIN
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def login_screen():

    st.markdown(
        """
        <div style="text-align:center;padding:70px 0 30px;">
            <div style="font-size:55px;">🤖</div>
            <h1>NEXUS AI</h1>
            <p style="color:#9ca9c0;font-size:18px;">
                Your AI + Client Hunter
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input(
        "App Password",
        type="password",
        placeholder="Enter your password",
    )

    if st.button("🔐 Login", use_container_width=True):

        if not APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()

        elif hmac.compare_digest(password, APP_PASSWORD):
            st.session_state.logged_in = True
            st.rerun()

        else:
            st.error("Incorrect password.")


if not st.session_state.logged_in:
    login_screen()
    st.stop()


# =========================================================
# HELPERS
# =========================================================

def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_url(url):
    url = clean_text(url)

    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ""

        if not parsed.netloc:
            return ""

        return url

    except Exception:
        return ""


def extract_json(text):
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.S)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    return None


# =========================================================
# GEMINI
# =========================================================

def gemini(prompt):

    if not GEMINI_KEY:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 1200,
        },
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=45,
        )

        if response.status_code != 200:
            return None

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])

        if not parts:
            return None

        return parts[0].get("text", "").strip()

    except Exception:
        return None


# =========================================================
# WEBSITE AUDIT
# =========================================================

def audit_website(url):

    url = normalize_url(url)

    if not url:
        return {
            "exists": False,
            "status": "No website provided",
            "issues": ["No public website supplied"],
        }

    try:

        response = requests.get(
            url,
            timeout=12,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 NEXUS-AI"
            },
        )

        html = response.text or ""

        issues = []

        if response.status_code >= 400:
            issues.append("Website returned an error")

        if len(html) < 1500:
            issues.append("Very small webpage")

        if "viewport" not in html.lower():
            issues.append("Mobile viewport may be missing")

        if not re.search(
            r"(contact|book|appointment|call|whatsapp|quote)",
            html,
            re.I,
        ):
            issues.append("Clear contact/booking CTA not detected")

        return {
            "exists": True,
            "status": f"HTTP {response.status_code}",
            "issues": issues or ["No obvious issue detected"],
        }

    except Exception as e:

        return {
            "exists": False,
            "status": "Website could not be checked",
            "issues": [str(e)[:120]],
        }


# =========================================================
# AI LEAD QUALIFICATION
# =========================================================

def qualify_lead(lead):

    if not GEMINI_KEY:

        return {
            "score": 50,
            "problem": "Needs manual review",
            "service": "Website / AI automation",
            "reason": "Gemini API key is not configured.",
        }

    audit = audit_website(lead.get("website", ""))

    prompt = f"""
You are a B2B lead qualification assistant.

Analyze this public business prospect.

Business: {lead.get("business")}
Category: {lead.get("category")}
City: {lead.get("city")}
Country: {lead.get("country")}
Website: {lead.get("website")}
Contact: {lead.get("contact")}
Website audit: {json.dumps(audit)}

We sell:
- modern websites
- lead capture
- CRM setup
- AI chat
- lead follow-up automation
- booking automation
- WhatsApp/email automation through official APIs

Return ONLY valid JSON:

{{
  "score": 0,
  "problem": "specific likely business problem",
  "service": "best service",
  "reason": "short evidence-based explanation"
}}

Rules:
- Score 0-100.
- Do not invent facts.
- If evidence is weak, say that manual review is needed.
- Do not claim a website problem unless supported by the audit.
"""

    result = gemini(prompt)

    data = extract_json(result)

    if not data:
        return {
            "score": 50,
            "problem": "Needs manual review",
            "service": "Website / AI automation",
            "reason": "AI returned an invalid response.",
        }

    try:
        score = int(data.get("score", 50))
    except Exception:
        score = 50

    return {
        "score": max(0, min(100, score)),
        "problem": clean_text(data.get("problem")),
        "service": clean_text(data.get("service")),
        "reason": clean_text(data.get("reason")),
    }


# =========================================================
# AI OUTREACH
# =========================================================

def create_message(lead, channel="Email"):

    if not GEMINI_KEY:

        return (
