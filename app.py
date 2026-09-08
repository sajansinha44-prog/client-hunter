import streamlit as st
import sqlite3
import requests
import json
import re
import hmac
from datetime import datetime
from urllib.parse import urlparse

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI Client Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB = "client_hunter.db"

# -----------------------------
# STYLE
# -----------------------------
st.markdown("""
<style>
.stApp {
    background: #080b12;
    color: #f5f7fb;
}
.block-container {
    max-width: 1400px;
    padding-top: 2rem;
}
.card {
    background: #111620;
    border: 1px solid #222a38;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
}
.metric {
    font-size: 30px;
    font-weight: 700;
}
.small {
    color: #8f9bad;
    font-size: 13px;
}
h1, h2, h3 {
    letter-spacing: -0.5px;
}
button {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# DATABASE
# -----------------------------
def db():
    return sqlite3.connect(DB, check_same_thread=False)


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business TEXT NOT NULL,
            website TEXT,
            city TEXT,
            country TEXT,
            category TEXT,
            contact TEXT,
            source TEXT,
            problem TEXT,
            service TEXT,
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
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# SECRETS
# -----------------------------
def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


APP_PASSWORD = secret("APP_PASSWORD")
GEMINI_KEY = secret("GEMINI_API_KEY")
GEMINI_MODEL = secret("GEMINI_MODEL", "gemini-2.5-flash")


# -----------------------------
# LOGIN
# -----------------------------
def login():
    st.markdown("# 🎯 AI Client Hunter")
    st.caption("Find → Qualify → Personalize → Close")

    if not APP_PASSWORD:
        st.warning(
            "APP_PASSWORD Streamlit Secrets में सेट नहीं है. "
            "Temporary access के लिए नीचे password डालने की सुविधा disabled है."
        )
        st.info(
            "Streamlit Secrets में APP_PASSWORD और GEMINI_API_KEY जोड़ने के बाद app सुरक्षित रूप से चलेगा."
        )
        return False

    password = st.text_input(
        "App Password",
        type="password",
        placeholder="अपना password डालें",
    )

    if st.button("🔐 Login", use_container_width=True):
        if hmac.compare_digest(password, APP_PASSWORD):
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("गलत password.")

    return False


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if APP_PASSWORD and not st.session_state["logged_in"]:
    login()
    st.stop()


# -----------------------------
# GEMINI
# -----------------------------
def gemini(prompt):
    if not GEMINI_KEY:
        return "Gemini API key configured नहीं है."

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=45,
        )

        if response.status_code != 200:
            return f"Gemini API error: {response.status_code}"

        data = response.json()

        return (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

    except Exception as e:
        return f"AI error: {str(e)}"


# -----------------------------
# WEBSITE AUDIT
# -----------------------------
def valid_url(url):
    if not url:
        return False

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        return bool(parsed.netloc)
    except Exception:
        return False


def audit_website(url):
    if not valid_url(url):
        return {
            "status": "No valid website",
            "details": "Business website उपलब्ध नहीं है या URL invalid है."
        }

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        r = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "AIClientHunter/1.0"
            },
            allow_redirects=True,
        )

        html = r.text[:500000]
        text = re.sub("<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        problems = []

        if r.status_code >= 400:
            problems.append(f"HTTP status {r.status_code}")

        if len(text) < 300:
            problems.append("बहुत कम readable website content मिला.")

        if "contact" not in text.lower():
            problems.append("Contact information स्पष्ट रूप से नहीं मिली.")

        if not problems:
            problems.append("कोई obvious issue automatically verify नहीं हुआ.")

        return {
            "status": f"HTTP {r.status_code}",
            "details": " ".join(problems),
        }

    except Exception as e:
        return {
            "status": "Audit failed",
            "details": str(e),
        }


# -----------------------------
# AI QUALIFICATION
# -----------------------------
def qualify_lead(business, category, city, website, audit):
    prompt = f"""
You are a professional B2B lead qualification assistant.

Business: {business}
Category: {category}
City: {city}
Website: {website}
Website audit: {audit}

Return ONLY valid JSON:

{{
  "score": 0,
  "problem": "",
  "service": "",
  "reason": ""
}}

Rules:
- score must be 0-100.
- Do not invent facts.
- Recommend a realistic website, automation or AI service.
- Keep reason short.
"""

    result = gemini(prompt)

    try:
        match = re.search(r"\{.*\}", result, re.S)
        if match:
            data = json.loads(match.group())
            return {
                "score": int(data.get("score", 0)),
                "problem": data.get("problem", ""),
                "service": data.get("service", ""),
                "reason": data.get("reason", ""),
            }
    except Exception:
        pass

    return {
        "score": 0,
        "problem": audit,
        "service": "Website / AI automation",
        "reason": "AI qualification unavailable.",
    }


# -----------------------------
# OUTREACH
# -----------------------------
def create_message(lead):
    prompt = f"""
Write a short professional B2B outreach message.

Business: {lead['business']}
Category: {lead['category']}
City: {lead['city']}
Website: {lead['website']}
Problem: {lead['problem']}
Recommended service: {lead['service']}

Rules:
- 70 words maximum.
- Sound human.
- No spam.
- No fake claims.
- Mention the actual opportunity.
- Offer a quick idea/demo.
- Do not pretend previous contact happened.
"""

    return gemini(prompt)


# -----------------------------
# REPLY CLASSIFICATION
# -----------------------------
def classify_reply(reply):
    prompt = f"""
Classify this business reply.

Reply:
{reply}

Return ONLY JSON:

{{
  "classification": "INTERESTED",
  "summary": "",
  "next_action": ""
}}

Allowed classification:
INTERESTED
WANTS PRICE
WANTS CALL
NEEDS INFORMATION
MAYBE LATER
NOT INTERESTED
SPAM
UNKNOWN
"""

    result = gemini(prompt)

    try:
        match = re.search(r"\{.*\}", result, re.S)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "classification": "UNKNOWN",
        "summary": "AI classification unavailable.",
        "next_action": "Review manually.",
    }


# -----------------------------
# LEAD FINDER
# -----------------------------
def find_businesses(city, category, limit):
    """
    Uses public OpenStreetMap/Overpass data.
    This does not access private data or bypass restrictions.
    """

    query = f"""
[out:json][timeout:25];
area["name"="{city}"]["boundary"="administrative"]->.searchArea;
(
  nwr["name"]["amenity"="{category}"](area.searchArea);
  nwr["name"]["shop"="{category}"](area.searchArea);
  nwr["name"]["office"="{category}"](area.searchArea);
);
out center tags {limit};
"""

    try:
        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=35,
            headers={
                "User-Agent": "AIClientHunter/1.0"
            },
        )

        if r.status_code != 200:
            return []

        data = r.json()
        results = []

        for item in data.get("elements", []):
            tags = item.get("tags", {})
            name = tags.get("name")

            if not name:
                continue

            results.append({
                "business": name,
                "website": tags.get("website", ""),
                "contact": tags.get("phone", "") or tags.get("email", ""),
                "city": city,
                "category": category,
                "source": "OpenStreetMap",
            })

            if len(results) >= limit:
                break

        return results

    except Exception:
        return []


# -----------------------------
# DATABASE HELPERS
# -----------------------------
def save_lead(lead):
    conn = db()

    conn.execute("""
        INSERT INTO leads
        (business, website, city, country, category, contact,
         source, problem, service, score, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead["business"],
        lead.get("website", ""),
        lead.get("city", ""),
        lead.get("country", ""),
        lead.get("category", ""),
        lead.get("contact", ""),
        lead.get("source", ""),
        lead.get("problem", ""),
        lead.get("service", ""),
        lead.get("score", 0),
        lead.get("status", "NEW"),
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def get_leads():
    conn = db()
    rows = conn.execute("""
        SELECT *
        FROM leads
        ORDER BY id DESC
    """).fetchall()
    conn.close()
    return rows


def update_status(lead_id, status):
    conn = db()
    conn.execute(
        "UPDATE leads SET status=? WHERE id=?",
        (status, lead_id),
    )
    conn.commit()
    conn.close()


# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:
    st.title("🎯 Client Hunter")

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Lead Finder",
            "Leads",
            "Outreach",
            "AI Inbox",
            "Deal Alerts",
            "Analytics",
            "Settings",
        ],
    )

    st.divider()

    if st.button("⏸ Pause Automations"):
        st.session_state["paused"] = True
        st.warning("Automations paused.")

    if APP_PASSWORD and st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()


# -----------------------------
# DASHBOARD
# -----------------------------
if page == "Dashboard":

    st.title("🎯 AI Client Hunter")
    st.caption("Find better clients. Qualify them with AI. Take over when they are ready to buy.")

    conn = db()

    total = conn.execute(
        "SELECT COUNT(*) FROM leads"
    ).fetchone()[0]

    qualified = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE score >= 70"
    ).fetchone()[0]

    interested = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status='INTERESTED'"
    ).fetchone()[0]

    deals = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status='DEAL'"
    ).fetchone()[0]

    contacted = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status='CONTACTED'"
    ).fetchone()[0]

    replies = conn.execute(
        "SELECT COUNT(*) FROM replies"
    ).fetchone()[0]

    conn.close()

    cols = st.columns(6)

    metrics = [
        ("New Leads", total),
        ("Qualified", qualified),
        ("Contacted", contacted),
        ("Replies", replies),
        ("Interested", interested),
        ("Deals", deals),
    ]

    for col, (name, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="card">
                    <div class="small">{name}</div>
                    <div class="metric">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### 🚀 Workflow")

    st.info(
        "1️⃣ Find leads → "
        "2️⃣ AI audits → "
        "3️⃣ AI qualifies → "
        "4️⃣ Generate outreach → "
        "5️⃣ Reply analysis → "
        "6️⃣ Deal alert → "
        "7️⃣ You negotiate and close"
    )


# -----------------------------
# LEAD FINDER
# -----------------------------
elif page == "Lead Finder":

    st.title("🔎 Lead Finder")

    c1, c2 = st.columns(2)

    with c1:
        city = st.text_input(
            "City",
            placeholder="Ambala",
        )

        country = st.text_input(
            "Country",
            value="India",
        )

    with c2:
        category = st.text_input(
            "Business category",
            placeholder="restaurant",
        )

        limit = st.slider(
            "Number of leads",
            1,
            30,
            10,
        )

    min_score = st.slider(
        "Minimum AI score",
        0,
        100,
        50,
    )

    if st.button(
        "🚀 Find & Qualify Leads",
        use_container_width=True,
    ):

        if not city or not category:
            st.warning("City और business category डालो.")
            st.stop()

        with st.spinner("Public business data खोज रहा हूँ..."):

            businesses = find_businesses(
                city,
                category,
                limit,
            )

        if not businesses:
            st.warning(
                "इस search से leads नहीं मिले. "
                "दूसरी city/category try करो."
            )
            st.stop()

        progress = st.progress(0)
        saved = 0

        for index, business in enumerate(businesses):

            audit = audit_website(
                business.get("website", "")
            )

            qualification = qualify_lead(
                business["business"],
                business["category"],
                business["city"],
                business.get("website", ""),
                audit["details"],
            )

            if qualification["score"] >= min_score:

                lead = {
                    **business,
                    "country": country,
                    "problem": qualification["problem"],
                    "service": qualification["service"],
                    "score": qualification["score"],
                    "status": "QUALIFIED",
                }

                save_lead(lead)
                saved += 1

            progress.progress(
                (index + 1) / len(businesses)
            )

        st.success(
            f"{saved} qualified leads save हो गईं."
        )


# -----------------------------
# LEADS
# -----------------------------
elif page == "Leads":

    st.title("📋 Lead Database")

    rows = get_leads()

    if not rows:
        st.info("अभी कोई lead नहीं है.")
    else:

        for row in rows:

            (
                lead_id,
                business,
                website,
                city,
                country,
                category,
                contact,
                source,
                problem,
                service,
                score,
                status,
                created,
            ) = row

            with st.expander(
                f"{business}  •  Score {score}  •  {status}"
            ):

                st.write(
                    f"**Category:** {category}"
                )

                st.write(
                    f"**Location:** {city}, {country}"
                )

                st.write(
                    f"**Website:** {website or 'Not available'}"
                )

                st.write(
                    f"**Public contact:** {contact or 'Not available'}"
                )

                st.write(
                    f"**Detected opportunity:** {problem}"
                )

                st.write(
                    f"**Recommended service:** {service}"
                )

                new_status = st.selectbox(
                    "Status",
                    [
                        "NEW",
                        "QUALIFIED",
                        "CONTACTED",
                        "REPLIED",
                        "INTERESTED",
                        "CALL REQUESTED",
                        "NEGOTIATING",
                        "DEAL",
                        "NOT INTERESTED",
                        "DO NOT CONTACT",
                    ],
                    index=[
                        "NEW",
                        "QUALIFIED",
                        "CONTACTED",
                        "REPLIED",
                        "INTERESTED",
                        "CALL REQUESTED",
                        "NEGOTIATING",
                        "DEAL",
                        "NOT INTERESTED",
                        "DO NOT CONTACT",
                    ].index(status)
                    if status in [
                        "NEW",
                        "QUALIFIED",
                        "CONTACTED",
                        "REPLIED",
                        "INTERESTED",
                        "CALL REQUESTED",
                        "NEGOTIATING",
                        "DEAL",
                        "NOT INTERESTED",
                        "DO NOT CONTACT",
                    ]
                    else 0,
                    key=f"status_{lead_id}",
                )

                if st.button(
                    "Save Status",
                    key=f"save_{lead_id}",
                ):
                    update_status(
                        lead_id,
                        new_status,
                    )
                    st.success("Status updated.")
                    st.rerun()


# -----------------------------
# OUTREACH
# -----------------------------
elif page == "Outreach":

    st.title("✉️ AI Outreach")

    rows = get_leads()

    if not rows:
        st.info("पहले leads खोजो.")
    else:

        options = {
            f"{r[1]} — Score {r[10]}": r
            for r in rows
        }

        selected = st.selectbox(
            "Lead चुनें",
            list(options.keys()),
        )

        row = options[selected]

        lead = {
            "business": row[1],
            "website": row[2],
            "city": row[3],
            "category": row[5],
            "problem": row[8],
            "service": row[9],
        }

        st.write(
            f"**Opportunity:** {lead['problem']}"
        )

        if st.button(
            "✨ Generate Personalized Message",
            use_container_width=True,
        ):

            with st.spinner("AI message बना रहा है..."):
                message = create_message(lead)

            st.text_area(
                "Ready-to-send message",
                message,
                height=220,
            )

            st.warning(
                "MANUAL ACTION REQUIRED: "
                "इस version में automatic WhatsApp/LinkedIn/email sending enabled नहीं है."
            )


# -----------------------------
# AI INBOX
# -----------------------------
elif page == "AI Inbox":

    st.title("🤖 AI Inbox")

    reply = st.text_area(
        "Client का reply यहाँ paste करें",
        height=180,
        placeholder="Yes, I would like to know more...",
    )

    if st.button(
        "Analyze Reply",
        use_container_width=True,
    ):

        if not reply.strip():
            st.warning("Reply डालो.")
            st.stop()

        with st.spinner("AI reply analyze कर रहा है..."):

            result = classify_reply(reply)

        classification = result.get(
            "classification",
            "UNKNOWN",
        )

        if classification in [
            "INTERESTED",
            "WANTS PRICE",
            "WANTS CALL",
        ]:
            st.success(
                f"🔥 DEAL SIGNAL: {classification}"
            )
        else:
            st.info(
                f"Classification: {classification}"
            )

        st.write(
            f"**Summary:** {result.get('summary', '')}"
        )

        st.write(
            f"**Next action:** {result.get('next_action', '')}"
        )


# -----------------------------
# DEAL ALERTS
# -----------------------------
elif page == "Deal Alerts":

    st.title("🔥 Deal Alerts")

    conn = db()

    rows = conn.execute("""
        SELECT id, business, contact, service, status
        FROM leads
        WHERE status IN (
            'INTERESTED',
            'CALL REQUESTED',
            'NEGOTIATING',
            'DEAL'
        )
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    if not rows:
        st.info("अभी कोई deal alert नहीं है.")
    else:

        for row in rows:

            st.markdown(
                f"""
                <div class="card">
                    <h3>🔥 {row[1]}</h3>
                    <p><b>Status:</b> {row[4]}</p>
                    <p><b>Service:</b> {row[3]}</p>
                    <p><b>Contact:</b> {row[2] or 'Not available'}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.warning(
            "अब negotiation, pricing, call और payment manually handle करें."
        )


# -----------------------------
# ANALYTICS
# -----------------------------
elif page == "Analytics":

    st.title("📊 Analytics")

    conn = db()

    total = conn.execute(
        "SELECT COUNT(*) FROM leads"
    ).fetchone()[0]

    qualified = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE score >= 70"
    ).fetchone()[0]

    contacted = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status='CONTACTED'"
    ).fetchone()[0]

    interested = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status='INTERESTED'"
    ).fetchone()[0]

    deals = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status='DEAL'"
    ).fetchone()[0]

    conn.close()

    cols = st.columns(5)

    values = [
        ("Leads", total),
        ("Qualified", qualified),
        ("Contacted", contacted),
        ("Interested", interested),
        ("Deals", deals),
    ]

    for col, (label, value) in zip(cols, values):
        with col:
            st.metric(label, value)

    if total:
        st.metric(
            "Lead → Deal conversion",
            f"{(deals / total) * 100:.1f}%",
        )


# -----------------------------
# SETTINGS
# -----------------------------
elif page == "Settings":

    st.title("⚙️ Settings")

    st.subheader("🔐 Security")

    st.write(
        "APP_PASSWORD Streamlit Secrets से लिया जाता है."
    )

    st.subheader("🤖 AI")

    if GEMINI_KEY:
        st.success("Gemini API configured.")
    else:
        st.error(
            "GEMINI_API_KEY अभी configured नहीं है."
        )

    st.write(
        f"Model: `{GEMINI_MODEL}`"
    )

    st.subheader("📨 Automation")

    st.warning(
        "Automatic messaging केवल officially authorised APIs "
        "के साथ implement किया जाना चाहिए."
    )

    st.write(
        "Current mode: MANUAL ACTION REQUIRED"
    )

    st.subheader("🛡️ Safety")

    st.write(
        "यह app CAPTCHA, login protection, rate limits, "
        "anti-spam systems या private data access को bypass नहीं करता."
    )

    if st.button(
        "🗑️ Clear Local Database",
        type="secondary",
    ):
        st.session_state["confirm_delete"] = True

    if st.session_state.get("confirm_delete"):

        st.error(
            "क्या सच में local lead database delete करना है?"
        )

        if st.button(
            "YES — DELETE DATABASE",
            type="primary",
        ):

            conn = db()

            conn.execute("DELETE FROM leads")
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM replies")

            conn.commit()
            conn.close()

            st.session_state["confirm_delete"] = False

            st.success("Database cleared.")
            st.rerun()
