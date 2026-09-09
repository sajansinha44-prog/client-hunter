import streamlit as st
import requests
import sqlite3
import json
import re
import hmac
from datetime import datetime
from urllib.parse import urlparse
from html import unescape

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="NEXUS AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "nexus_ai.db"

# Local Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2:3b"

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, system-ui, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, #172033 0%, #090d14 38%, #05070b 100%);
    color: #f5f7fb;
}

.block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] {
    background: #080b11;
    border-right: 1px solid #202633;
}

.card {
    background: rgba(18, 23, 34, 0.88);
    border: 1px solid #252d3b;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 15px;
}

.metric-card {
    background: linear-gradient(145deg, #121925, #0c111a);
    border: 1px solid #273143;
    border-radius: 18px;
    padding: 18px;
    min-height: 110px;
}

.metric-number {
    font-size: 30px;
    font-weight: 800;
}

.metric-label {
    color: #9ca7b8;
    font-size: 13px;
}

.chat-user {
    background: #182235;
    border-radius: 18px;
    padding: 15px;
    margin: 8px 0 8px 15%;
}

.chat-ai {
    background: #101722;
    border: 1px solid #263142;
    border-radius: 18px;
    padding: 15px;
    margin: 8px 15% 8px 0;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #202a3a;
    color: #dce5f5;
    font-size: 12px;
    margin-right: 5px;
}

.small {
    color: #9ca7b8;
    font-size: 13px;
}

h1, h2, h3 {
    letter-spacing: -0.02em;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        role TEXT,
        content TEXT,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business TEXT,
        city TEXT,
        country TEXT,
        category TEXT,
        website TEXT,
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
# AUTH
# =========================================================

def check_password():
    """
    Set APP_PASSWORD in Streamlit secrets for real deployment.
    If not configured, local development password is nexus.
    """

    if st.session_state.get("authenticated"):
        return True

    try:
        expected = st.secrets.get("APP_PASSWORD", "nexus")
    except Exception:
        expected = "nexus"

    st.markdown("""
    <div style="max-width:520px;margin:100px auto;text-align:center">
        <h1>🤖 NEXUS AI</h1>
        <p class="small">Your private AI workspace</p>
    </div>
    """, unsafe_allow_html=True)

    password = st.text_input(
        "Password",
        type="password",
        key="login_password"
    )

    if st.button("🔐 Enter AI", use_container_width=True):
        if hmac.compare_digest(password, expected):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password.")

    return False


if not check_password():
    st.stop()


# =========================================================
# OLLAMA AI
# =========================================================

def get_model():
    try:
        return st.session_state.get(
            "model",
            st.secrets.get("OLLAMA_MODEL", DEFAULT_MODEL)
        )
    except Exception:
        return DEFAULT_MODEL


def ollama_chat(messages, temperature=0.7):
    """
    Calls a locally running Ollama model.

    Example:
        ollama pull llama3.2:3b
        ollama serve
    """

    payload = {
        "model": get_model(),
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        return data.get("message", {}).get(
            "content",
            "AI returned no response."
        )

    except requests.exceptions.ConnectionError:
        return (
            "⚠️ AI engine is not running.\n\n"
            "Start Ollama and make sure the selected model is installed."
        )

    except Exception as e:
        return f"⚠️ AI error: {str(e)}"


# =========================================================
# AI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are NEXUS AI, a helpful general-purpose AI assistant.

You can:
- answer questions
- explain concepts
- write content
- analyze information
- help with business
- help find legitimate customer opportunities
- generate marketing ideas
- write outreach messages
- analyze customer replies
- help with websites and automation
- write and explain code

Rules:
1. Be accurate and honest.
2. Never pretend an action happened if it did not.
3. Never claim to have contacted someone unless an authorized integration actually did it.
4. Never bypass CAPTCHA, authentication, rate limits, anti-spam systems, or platform restrictions.
5. Never expose secrets, passwords, tokens, or private information.
6. If an action requires a human, clearly say so.
7. Keep answers practical.
"""


# =========================================================
# CHAT MEMORY
# =========================================================

def new_conversation(title="New Chat"):
    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO conversations(title, created_at)
        VALUES (?, ?)
        """,
        (title, datetime.utcnow().isoformat())
    )

    conversation_id = cur.lastrowid
    conn.commit()
    conn.close()

    return conversation_id


def save_message(conversation_id, role, content):
    conn = get_db()

    conn.execute(
        """
        INSERT INTO messages(
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()
    conn.close()


def load_messages(conversation_id):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id
        """,
        (conversation_id,)
    ).fetchall()

    conn.close()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]


def list_conversations():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM conversations
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


# =========================================================
# WEBSITE AUDIT
# =========================================================

def normalize_url(url):
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def audit_website(url):
    url = normalize_url(url)

    if not url:
        return {
            "success": False,
            "reason": "No website provided."
        }

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return {
                "success": False,
                "reason": "Invalid URL."
            }

        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "NexusAIWebsiteAudit/1.0"
            }
        )

        html = response.text

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            re.I | re.S
        )

        title = (
            unescape(title_match.group(1)).strip()
            if title_match
            else ""
        )

        description_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html,
            re.I | re.S
        )

        description = (
            unescape(description_match.group(1)).strip()
            if description_match
            else ""
        )

        viewport = bool(
            re.search(
                r'name=["\']viewport["\']',
                html,
                re.I
            )
        )

        cta_words = [
            "contact",
            "book",
            "call",
            "buy",
            "get started",
            "appointment",
            "quote"
        ]

        lower_html = html.lower()

        ctas = [
            word for word in cta_words
            if word in lower_html
        ]

        return {
            "success": True,
            "status": response.status_code,
            "title": title,
            "description": description,
            "mobile_viewport": viewport,
            "cta_detected": ctas,
            "length": len(html)
        }

    except Exception as e:
        return {
            "success": False,
            "reason": str(e)
        }


# =========================================================
# AI LEAD QUALIFICATION
# =========================================================

def qualify_lead(business, category, website, audit=None):
    prompt = f"""
Analyze this business as a potential website/automation client.

Business:
{business}

Category:
{category}

Website:
{website or "No website"}

Website audit:
{json.dumps(audit or {}, indent=2)}

Return JSON only:

{{
  "score": 0,
  "problem": "short specific problem",
  "service": "recommended service",
  "reason": "why this could be a valuable client"
}}

Score from 0 to 100.

Do not invent facts.
"""

    result = ollama_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    try:
        match = re.search(
            r"\{.*\}",
            result,
            re.S
        )

        data = json.loads(match.group(0))

        return {
            "score": int(data.get("score", 0)),
            "problem": data.get("problem", ""),
            "service": data.get("service", ""),
            "reason": data.get("reason", "")
        }

    except Exception:
        return {
            "score": 50,
            "problem": "Needs manual review",
            "service": "Website / AI automation",
            "reason": result[:300]
        }


# =========================================================
# LEADS
# =========================================================

def save_lead(data):
    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO leads(
            business,
            city,
            country,
            category,
            website,
            contact,
            source,
            problem,
            service,
            score,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("business", ""),
            data.get("city", ""),
            data.get("country", ""),
            data.get("category", ""),
            data.get("website", ""),
            data.get("contact", ""),
            data.get("source", ""),
            data.get("problem", ""),
            data.get("service", ""),
            data.get("score", 0),
            data.get("status", "NEW"),
            datetime.utcnow().isoformat()
        )
    )

    lead_id = cur.lastrowid

    conn.commit()
    conn.close()

    return lead_id


def get_leads():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM leads
        ORDER BY score DESC, id DESC
        """
    ).fetchall()

    conn.close()

    return rows


def update_lead_status(lead_id, status):
    conn = get_db()

    conn.execute(
        """
        UPDATE leads
        SET status = ?
        WHERE id = ?
        """,
        (status, lead_id)
    )

    conn.commit()
    conn.close()


# =========================================================
# OUTREACH
# =========================================================

def generate_outreach(lead, channel="Email"):
    prompt = f"""
Write a short, natural business outreach message.

Business:
{lead["business"]}

Category:
{lead["category"]}

City:
{lead["city"]}

Website:
{lead["website"] or "No website"}

Detected opportunity:
{lead["problem"]}

Recommended service:
{lead["service"]}

Channel:
{channel}

Requirements:
- personalized
- human sounding
- concise
- no fake claims
- no spammy language
- no guaranteed results
- mention a useful improvement
- finish with a simple question
"""

    return ollama_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )


# =========================================================
# REPLY ANALYSIS
# =========================================================

def analyze_reply(reply):
    prompt = f"""
Analyze this potential client reply.

Reply:
{reply}

Return JSON only:

{{
  "classification":
    "INTERESTED" |
    "WANTS PRICE" |
    "WANTS A CALL" |
    "NEEDS INFORMATION" |
    "MAYBE LATER" |
    "NOT INTERESTED" |
    "SPAM" |
    "UNKNOWN",

  "summary": "short summary",
  "next_action": "what the human owner should do next"
}}
"""

    result = ollama_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    try:
        match = re.search(
            r"\{.*\}",
            result,
            re.S
        )

        return json.loads(match.group(0))

    except Exception:
        return {
            "classification": "UNKNOWN",
            "summary": result[:300],
            "next_action": "Review manually."
        }


def save_reply(lead_id, reply, analysis):
    conn = get_db()

    conn.execute(
        """
        INSERT INTO replies(
            lead_id,
            reply,
            classification,
            summary,
            next_action,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            reply,
            analysis.get("classification", "UNKNOWN"),
            analysis.get("summary", ""),
            analysis.get("next_action", ""),
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()
    conn.close()

    classification = analysis.get("classification")

    if classification in (
        "INTERESTED",
        "WANTS PRICE",
        "WANTS A CALL"
    ):
        update_lead_status(
            lead_id,
            "INTERESTED"
        )


# =========================================================
# DASHBOARD COUNTS
# =========================================================

def count_leads(status=None):
    conn = get_db()

    if status:
        value = conn.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE status = ?
            """,
            (status,)
        ).fetchone()[0]
    else:
        value = conn.execute(
            "SELECT COUNT(*) FROM leads"
        ).fetchone()[0]

    conn.close()

    return value


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown("# 🤖 NEXUS AI")
st.sidebar.caption("Your AI + Client Hunter")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = new_conversation()

pages = [
    "🏠 Dashboard",
    "🤖 AI Chat",
    "🔎 Lead Finder",
    "👥 Leads",
    "✍️ Outreach",
    "📥 AI Inbox",
    "🔥 Deal Alerts",
    "📊 Analytics",
    "⚙️ Settings"
]

page = st.sidebar.radio(
    "Navigation",
    pages
)

if st.sidebar.button(
    "➕ New Chat",
    use_container_width=True
):
    st.session_state.conversation_id = new_conversation()
    st.rerun()

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):
    st.session_state.authenticated = False
    st.rerun()


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.title("🎯 NEXUS AI")

    st.markdown(
        "### Your personal AI assistant + client acquisition workspace."
    )

    metrics = [
        ("New Leads", count_leads("NEW")),
        ("Qualified", count_leads("QUALIFIED")),
        ("Contacted", count_leads("CONTACTED")),
        ("Interested", count_leads("INTERESTED")),
        ("Deals", count_leads("DEAL")),
    ]

    cols = st.columns(len(metrics))

    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    st.markdown("## 🚀 Workflow")

    st.markdown("""
    <div class="card">

    **1️⃣ Find leads**  
    ↓  
    **2️⃣ Audit website**  
    ↓  
    **3️⃣ AI qualifies business**  
    ↓  
    **4️⃣ Generate personalized outreach**  
    ↓  
    **5️⃣ Analyze replies**  
    ↓  
    **6️⃣ Detect buying intent**  
    ↓  
    **7️⃣ 🔥 Deal Alert**  
    ↓  
    **8️⃣ You negotiate and close**

    </div>
    """, unsafe_allow_html=True)

    st.info(
        "AI handles research, analysis and drafts. "
        "You take over when a client is ready to buy."
    )


# =========================================================
# AI CHAT
# =========================================================

elif page == "🤖 AI Chat":

    st.title("🤖 AI Chat")

    conversations = list_conversations()

    if conversations:

        selected = st.selectbox(
            "Conversation",
            conversations,
            format_func=lambda x: x["title"] or f"Chat #{x['id']}"
        )

        if selected:
            st.session_state.conversation_id = selected["id"]

    messages = load_messages(
        st.session_state.conversation_id
    )

    for message in messages:

        if message["role"] == "user":

            st.markdown(
                f"""
                <div class="chat-user">
                    <b>👤 You</b><br><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                f"""
                <div class="chat-ai">
                    <b>🤖 NEXUS AI</b><br><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True
            )

    prompt = st.chat_input(
        "Ask NEXUS anything..."
    )

    if prompt:

        save_message(
            st.session_state.conversation_id,
            "user",
            prompt
        )

        history = load_messages(
            st.session_state.conversation_id
        )

        ai_messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ] + history[-20:]

        answer = ollama_chat(
            ai_messages
        )

        save_message(
            st.session_state.conversation_id,
            "assistant",
            answer
        )

        st.rerun()


# =========================================================
# LEAD FINDER
# =========================================================

elif page == "🔎 Lead Finder":

    st.title("🔎 Lead Finder")

    st.write(
        "Find legitimate public business opportunities and qualify them with AI."
    )

    c1, c2 = st.columns(2)

    with c1:
        business = st.text_input(
            "Business name"
        )

        category = st.text_input(
            "Business category",
            placeholder="Restaurant, dentist, agency, gym..."
        )

        city = st.text_input(
            "City",
            placeholder="Delhi"
        )

    with c2:
        country = st.text_input(
            "Country",
            placeholder="India / USA / UK..."
        )

        website = st.text_input(
            "Website",
            placeholder="example.com"
        )

        contact = st.text_input(
            "Public contact",
            placeholder="Public email / website contact page"
        )

    if st.button(
        "🧠 Analyze & Save Lead",
        use_container_width=True
    ):

        if not business:
            st.warning(
                "Enter a business name."
            )

        else:

            with st.spinner("Auditing website + qualifying..."):

                audit = {}

                if website:
                    audit = audit_website(
                        website
                    )

                qualification = qualify_lead(
                    business=business,
                    category=category,
                    website=website,
                    audit=audit
                )

                lead = {
                    "business": business,
                    "city": city,
                    "country": country,
                    "category": category,
                    "website": normalize_url(website),
                    "contact": contact,
                    "source": "Manual/Public",
                    "problem": qualification["problem"],
                    "service": qualification["service"],
                    "score": qualification["score"],
                    "status": "QUALIFIED"
                    if qualification["score"] >= 60
                    else "NEW"
                }

                lead_id = save_lead(
                    lead
                )

            st.success(
                f"Lead saved. ID: {lead_id}"
            )

            st.metric(
                "AI Score",
                qualification["score"]
            )

            st.write(
                "**Problem:**",
                qualification["problem"]
            )

            st.write(
                "**Recommended service:**",
                qualification["service"]
            )

            st.write(
                "**Reason:**",
                qualification["reason"]
            )


# =========================================================
# LEADS
# =========================================================

elif page == "👥 Leads":

    st.title("👥 Lead Database")

    leads = get_leads()

    if not leads:

        st.info(
            "No leads yet. Use Lead Finder."
        )

    else:

        for lead in leads:

            with st.expander(
                f"🔥 {lead['business']} — Score {lead['score']}"
            ):

                c1, c2 = st.columns(2)

                with c1:

                    st.write(
                        f"**Category:** {lead['category']}"
                    )

                    st.write(
                        f"**Location:** {lead['city']}, {lead['country']}"
                    )

                    st.write(
                        f"**Website:** {lead['website'] or 'None'}"
                    )

                    st.write(
                        f"**Contact:** {lead['contact'] or 'None'}"
                    )

                with c2:

                    st.write(
                        f"**Problem:** {lead['problem']}"
                    )

                    st.write(
                        f"**Service:** {lead['service']}"
                    )

                    st.write(
                        f"**Status:** {lead['status']}"
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
                        "DO NOT CONTACT"
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
                        "DO NOT CONTACT"
                    ].index(lead["status"])
                    if lead["status"] in [
                        "NEW",
                        "QUALIFIED",
                        "CONTACTED",
                        "REPLIED",
                        "INTERESTED",
                        "CALL REQUESTED",
                        "NEGOTIATING",
                        "DEAL",
                        "NOT INTERESTED",
                        "DO NOT CONTACT"
                    ]
                    else 0,
                    key=f"status_{lead['id']}"
                )

                if st.button(
                    "Save status",
                    key=f"save_status_{lead['id']}"
                ):
                    update_lead_status(
                        lead["id"],
                        new_status
                    )
                    st.success("Updated.")
                    st.rerun()


# =========================================================
# OUTREACH
# =========================================================

elif page == "✍️ Outreach":

    st.title("✍️ AI Outreach")

    leads = get_leads()

    if not leads:

        st.info(
            "Create a lead first."
        )

    else:

        lead = st.selectbox(
            "Choose lead",
            leads,
            format_func=lambda x:
                f"{x['business']} — {x['score']}"
        )

        channel = st.selectbox(
            "Channel",
            [
                "Email",
                "WhatsApp",
                "LinkedIn",
                "Instagram DM",
                "SMS"
            ]
        )

        if st.button(
            "✨ Generate Personalized Message",
            use_container_width=True
        ):

            with st.spinner(
                "Writing personalized outreach..."
            ):

                message = generate_outreach(
                    lead,
                    channel
                )

            st.text_area(
                "Message",
                message,
                height=250
            )

            st.warning(
                "⚠️ Sending is not automatic here. "
                "Use only authorized official integrations and respect platform rules."
            )


# =========================================================
# AI INBOX
# =========================================================

elif page == "📥 AI Inbox":

    st.title("📥 AI Inbox")

    leads = get_leads()

    if not leads:

        st.info(
            "Create a lead first."
        )

    else:

        lead = st.selectbox(
            "Client",
            leads,
            format_func=lambda x:
                x["business"]
        )

        reply = st.text_area(
            "Paste client's reply",
            height=180,
            placeholder="Example: Sounds interesting. How much do you charge?"
        )

        if st.button(
            "🧠 Analyze Reply",
            use_container_width=True
        ):

            if not reply.strip():

                st.warning(
                    "Paste a reply first."
                )

            else:

                with st.spinner(
                    "AI is analyzing..."
                ):

                    analysis = analyze_reply(
                        reply
                    )

                    save_reply(
                        lead["id"],
                        reply,
                        analysis
                    )

                classification = analysis.get(
                    "classification",
                    "UNKNOWN"
                )

                if classification in (
                    "INTERESTED",
                    "WANTS PRICE",
                    "WANTS A CALL"
                ):

                    st.error(
                        f"🔥 DEAL SIGNAL: {classification}"
                    )

                else:

                    st.info(
                        classification
                    )

                st.write(
                    "**Summary:**",
                    analysis.get("summary")
                )

                st.write(
                    "**Next action:**",
                    analysis.get("next_action")
                )


# =========================================================
# DEAL ALERTS
# =========================================================

elif page == "🔥 Deal Alerts":

    st.title("🔥 Deal Alerts")

    conn = get_db()

    replies = conn.execute(
        """
        SELECT
            replies.*,
            leads.business
        FROM replies
        JOIN leads
        ON replies.lead_id = leads.id
        WHERE classification IN (
            'INTERESTED',
            'WANTS PRICE',
            'WANTS A CALL'
        )
        ORDER BY replies.id DESC
        """
    ).fetchall()

    conn.close()

    if not replies:

        st.success(
            "No new deal alerts."
        )

    else:

        for item in replies:

            st.markdown(
                f"""
                <div class="card">

                <h3>🔥 DEAL ALERT — {item['business']}</h3>

                <span class="badge">
                {item['classification']}
                </span>

                <br><br>

                <b>AI Summary</b><br>
                {item['summary']}

                <br><br>

                <b>Recommended Action</b><br>
                {item['next_action']}

                </div>
                """,
                unsafe_allow_html=True
            )

        st.warning(
            "Automation stops at strong buying intent. "
            "You handle pricing, negotiation, calls and payment."
        )


# =========================================================
# ANALYTICS
# =========================================================

elif page == "📊 Analytics":

    st.title("📊 Analytics")

    total = count_leads()

    qualified = count_leads(
        "QUALIFIED"
    )

    contacted = count_leads(
        "CONTACTED"
    )

    interested = count_leads(
        "INTERESTED"
    )

    deals = count_leads(
        "DEAL"
    )

    cols = st.columns(5)

    values = [
        ("Total Leads", total),
        ("Qualified", qualified),
        ("Contacted", contacted),
        ("Interested", interested),
        ("Deals", deals)
    ]

    for col, (label, value) in zip(
        cols,
        values
    ):

        with col:

            st.metric(
                label,
                value
            )

    if total:

        qualification_rate = (
            qualified / total
        ) * 100

        deal_rate = (
            deals / total
        ) * 100

        st.write(
            f"Qualification rate: **{qualification_rate:.1f}%**"
        )

        st.write(
            f"Deal rate: **{deal_rate:.1f}%**"
        )


# =========================================================
# SETTINGS
# =========================================================

elif page == "⚙️ Settings":

    st.title("⚙️ Settings")

    st.subheader(
        "🤖 AI Engine"
    )

    model = st.text_input(
        "Ollama Model",
        value=get_model()
    )

    if st.button(
        "Save AI model"
    ):

        st.session_state.model = model

        st.success(
            f"Model set to {model}"
        )

    st.divider()

    st.subheader(
        "🔐 Security"
    )

    st.write(
        "For deployment, store APP_PASSWORD in secrets."
    )

    st.code("""
APP_PASSWORD = "your-strong-password"
OLLAMA_MODEL = "llama3.2:3b"
""")

    st.divider()

    st.subheader(
        "🛑 Automation Safety"
    )

    st.checkbox(
        "Allow automated actions",
        value=False,
        disabled=True
    )

    st.caption(
        "Automatic external messaging should only be enabled "
        "through official authorized APIs with appropriate limits."
    )

    st.divider()

    st.subheader(
        "💾 Database"
    )

    st.write(
        f"Database: `{DB_FILE}`"
    )

    if st.button(
        "🧹 Clear all local data"
    ):

        st.warning(
            "This option intentionally requires manual confirmation "
            "in a production version."
        )
