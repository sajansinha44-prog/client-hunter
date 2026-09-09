import streamlit as st

import sqlite3

import requests

import json

import re

from datetime import datetime

# =========================

# APP CONFIG

# =========================

st.set_page_config(

    page_title="NEXUS AI",

    page_icon="🤖",

    layout="wide"

)

DB = "nexus_ai.db"

# =========================

# DATABASE

# =========================

def connect():

    conn = sqlite3.connect(DB, check_same_thread=False)

    conn.row_factory = sqlite3.Row

    return conn

def init_db():

    conn = connect()

    conn.execute("""

        CREATE TABLE IF NOT EXISTS leads (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            business TEXT,

            category TEXT,

            city TEXT,

            country TEXT,

            website TEXT,

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

            status TEXT,

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

# =========================

# SECRETS

# =========================

def get_secret(name, default=""):

    try:

        return st.secrets.get(name, default)

    except Exception:

        return default

GEMINI_KEY = get_secret("GEMINI_API_KEY")

GEMINI_MODEL = get_secret(

    "GEMINI_MODEL",

    "gemini-2.5-flash"

)

# =========================

# GEMINI

# =========================

def ask_ai(prompt):

    if not GEMINI_KEY:

        return None

    url = (

        "https://generativelanguage.googleapis.com/"

        "v1beta/models/"

        + GEMINI_MODEL

        + ":generateContent?key="

        + GEMINI_KEY

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

            "temperature": 0.3,

            "maxOutputTokens": 1000

        }

    }

    try:

        response = requests.post(

            url,

            json=payload,

            timeout=40

        )

        if response.status_code != 200:

            return None

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:

            return None

        parts = candidates[0].get(

            "content",

            {}

        ).get(

            "parts",

            []

        )

        if not parts:

            return None

        return parts[0].get("text", "")

    except Exception:

        return None

def get_json(text):

    if not text:

        return None

    try:

        return json.loads(text)

    except Exception:

        pass

    match = re.search(

        r"\{.*\}",

        text,

        re.S

    )

    if match:

        try:

            return json.loads(match.group())

        except Exception:

            return None

    return None

# =========================

# LEAD FUNCTIONS

# =========================

def save_lead(data):

    conn = connect()

    conn.execute("""

        INSERT INTO leads (

            business,

            category,

            city,

            country,

            website,

            contact,

            source,

            problem,

            service,

            reason,

            score,

            status,

            created_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        data.get("business", ""),

        data.get("category", ""),

        data.get("city", ""),

        data.get("country", ""),

        data.get("website", ""),

        data.get("contact", ""),

        data.get("source", ""),

        data.get("problem", ""),

        data.get("service", ""),

        data.get("reason", ""),

        int(data.get("score", 0)),

        data.get("status", "NEW"),

        datetime.utcnow().isoformat()

    ))

    conn.commit()

    conn.close()

def get_leads():

    conn = connect()

    rows = conn.execute("""

        SELECT *

        FROM leads

        ORDER BY id DESC

    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]

def get_lead(lead_id):

    conn = connect()

    row = conn.execute(

        "SELECT * FROM leads WHERE id = ?",

        (lead_id,)

    ).fetchone()

    conn.close()

    if row is None:

        return None

    return dict(row)

def change_status(lead_id, status):

    conn = connect()

    conn.execute(

        "UPDATE leads SET status = ? WHERE id = ?",

        (status, lead_id)

    )

    conn.commit()

    conn.close()

# =========================

# AI QUALIFICATION

# =========================

def qualify(lead):

    if not GEMINI_KEY:

        return {

            "score": 50,

            "problem": "Manual review required",

            "service": "Website / AI automation",

            "reason": "Gemini API is not connected."

        }

    prompt = f"""

Analyze this business prospect for B2B services.

Business: {lead.get("business")}

Category: {lead.get("category")}

City: {lead.get("city")}

Country: {lead.get("country")}

Website: {lead.get("website")}

Contact: {lead.get("contact")}

Services available:

- Website development

- Lead generation

- CRM

- AI chatbot

- Lead follow-up automation

- Booking automation

- WhatsApp/email automation

Return ONLY JSON:

{{

  "score": 0,

  "problem": "",

  "service": "",

  "reason": ""

}}

Score 0-100.

Do not invent facts.

If evidence is weak, say manual review.

"""

    result = ask_ai(prompt)

    data = get_json(result)

    if not data:

        return {

            "score": 50,

            "problem": "Manual review required",

            "service": "Website / AI automation",

            "reason": "AI response could not be parsed."

        }

    try:

        score = int(data.get("score", 50))

    except Exception:

        score = 50

    return {

        "score": max(0, min(score, 100)),

        "problem": str(

            data.get(

                "problem",

                "Manual review required"

            )

        ),

        "service": str(

            data.get(

                "service",

                "Website / AI automation"

            )

        ),

        "reason": str(

            data.get(

                "reason",

                "AI qualification completed."

            )

        )

    }

# =========================

# AI MESSAGE

# =========================

def generate_message(lead, channel):

    if not GEMINI_KEY:

        return (

            "Hi "

            + lead.get("business", "there")

            + " 👋\n\n"

            "I came across your business and wanted "

            "to reach out.\n\n"

            "I help businesses improve their website "

            "and automate lead follow-up.\n\n"

            "Would you be open to seeing a quick demo?"

        )

    prompt = f"""

Write a short natural B2B outreach message.

Business: {lead.get("business")}

Category: {lead.get("category")}

Country: {lead.get("country")}

Problem: {lead.get("problem")}

Service: {lead.get("service")}

Channel: {channel}

Rules:

- Under 90 words.

- Human and polite.

- No fake claims.

- No spam.

- Mention the business naturally.

- Offer a quick demo.

"""

    result = ask_ai(prompt)

    if result:

        return result.strip()

    return (

        "Hi "

        + lead.get("business", "there")

        + " 👋\n\n"

        "I help businesses improve their website "

        "and automate lead follow-up.\n\n"

        "Would you be interested in a quick demo?"

    )

# =========================

# REPLY AI

# =========================

def analyze_reply(reply):

    if not GEMINI_KEY:

        text = reply.lower()

        if "price" in text or "cost" in text:

            kind = "WANTS PRICE"

        elif "call" in text or "meeting" in text:

            kind = "WANTS A CALL"

        elif "interested" in text or "yes" in text:

            kind = "INTERESTED"

        elif "not interested" in text:

            kind = "NOT INTERESTED"

        else:

            kind = "UNKNOWN"

        return {

            "classification": kind,

            "summary": "Fallback classification.",

            "next_action": "Review manually."

        }

    prompt = f"""

Classify this business reply:

{reply}

Return ONLY JSON:

{{

  "classification": "",

  "summary": "",

  "next_action": ""

}}

Allowed:

INTERESTED

WANTS PRICE

WANTS A CALL

NEEDS MORE INFORMATION

MAYBE LATER

NOT INTERESTED

SPAM

UNKNOWN

"""

    result = ask_ai(prompt)

    data = get_json(result)

    if not data:

        return {

            "classification": "UNKNOWN",

            "summary": "Could not classify.",

            "next_action": "Review manually."

        }

    return {

        "classification": str(

            data.get(

                "classification",

                "UNKNOWN"

            )

        ).upper(),

        "summary": str(

            data.get(

                "summary",

                ""

            )

        ),

        "next_action": str(

            data.get(

                "next_action",

                "Review manually."

            )

        )

    }

# =========================

# PUBLIC LEAD SEARCH

# =========================

CATEGORY_TAGS = {

    "gym": ["gym", "fitness_centre"],

    "restaurant": ["restaurant", "cafe"],

    "cafe": ["cafe"],

    "hotel": ["hotel"],

    "dentist": ["dentist"],

    "doctor": ["clinic", "doctors"],

    "salon": ["hairdresser", "beauty"],

    "real estate": ["estate_agent"]

}

def find_leads(city, category, limit):

    category_key = category.lower().strip()

    tags = CATEGORY_TAGS.get(

        category_key,

        [category_key]

    )

    results = []

    for tag in tags:

        query = f"""

        [out:json][timeout:25];

        area["name"="{city}"]->.a;

        (

          nwr["amenity"="{tag}"](area.a);

          nwr["shop"="{tag}"](area.a);

          nwr["office"="{tag}"](area.a);

        );

        out center tags;

        """

        try:

            response = requests.post(

                "https://overpass-api.de/api/interpreter",

                data=query,

                timeout=35

            )

            if response.status_code != 200:

                continue

            data = response.json()

            for item in data.get(

                "elements",

                []

            ):

                tags_data = item.get(

                    "tags",

                    {}

                )

                business = tags_data.get(

                    "name",

                    ""

                )

                if not business:

                    continue

                website = (

                    tags_data.get("website")

                    or tags_data.get(

                        "contact:website",

                        ""

                    )

                )

                phone = (

                    tags_data.get("phone")

                    or tags_data.get(

                        "contact:phone",

                        ""

                    )

                )

                email = (

                    tags_data.get("email")

                    or tags_data.get(

                        "contact:email",

                        ""

                    )

                )

                results.append({

                    "business": business,

                    "category": category,

                    "city": city,

                    "country": "",

                    "website": website,

                    "contact": email or phone,

                    "source": "OpenStreetMap"

                })

                if len(results) >= limit:

                    break

        except Exception:

            continue

        if len(results) >= limit:

            break

    unique = {}

    for item in results:

        key = item["business"].lower()

        if key not in unique:

            unique[key] = item

    return list(unique.values())[:limit]

# =========================================================

# SIDEBAR

# =========================================================

st.sidebar.title("🤖 NEXUS AI")

st.sidebar.caption("Your AI + Client Hunter")

page = st.sidebar.radio(

    "Navigation",

    [

        "Dashboard",

        "Lead Finder",

        "Database",

        "AI Outreach",

        "AI Inbox",

        "Deal Alerts",

        "Analytics",

        "Settings"

    ]

)

# =========================================================

# DASHBOARD

# =========================================================

if page == "Dashboard":

    st.title("🤖 NEXUS AI")

    st.caption("Your AI + Client Hunter")

    leads = get_leads()

    total = len(leads)

    qualified = len([

        x for x in leads

        if x["score"] >= 70

    ])

    contacted = len([

        x for x in leads

        if x["status"] == "CONTACTED"

    ])

    interested = len([

        x for x in leads

        if x["status"] in [

            "INTERESTED",

            "CALL REQUESTED",

            "NEGOTIATING"

        ]

    ])

    deals = len([

        x for x in leads

        if x["status"] == "DEAL"

    ])

    a, b, c, d, e = st.columns(5)

    a.metric("New Leads", total)

    b.metric("Qualified", qualified)

    c.metric("Contacted", contacted)

    d.metric("Interested", interested)

    e.metric("Deals", deals)

    st.divider()

    st.subheader("🔥 High-value Leads")

    high = [

        x for x in leads

        if x["score"] >= 70

    ]

    if not high:

        st.info(

            "No high-value leads yet. "

            "Use Lead Finder."

        )

    for lead in high[:10]:

        with st.container(border=True):

            st.subheader(

                f"🔥 {lead['business']} "

                f"— {lead['score']}/100"

            )

            st.write(

                f"{lead['category']} • "

                f"{lead['city']}, "

                f"{lead['country']}"

            )

            st.write(

                "**Problem:** "

                + lead["problem"]

            )

            st.write(

                "**Service:** "

                + lead["service"]

            )

# =========================================================

# LEAD FINDER

# =========================================================

elif page == "Lead Finder":

    st.title("🔎 Lead Finder")

    city = st.text_input(

        "City",

        placeholder="London"

    )

    country = st.text_input(

        "Country",

        placeholder="United Kingdom"

    )

    category = st.text_input(

        "Business category",

        placeholder="Hotel, dentist, gym..."

    )

    limit = st.number_input(

        "Number of leads",

        1,

        50,

        10

    )

    min_score = st.slider(

        "Minimum AI score",

        0,

        100,

        50

    )

    if st.button(

        "🚀 Find Leads",

        type="primary"

    ):

        if not city or not category:

            st.error(

                "Enter city and business category."

            )

            st.stop()

        with st.spinner(

            "Finding public businesses..."

        ):

            found = find_leads(

                city,

                category,

                int(limit)

            )

        if not found:

            st.warning(

                "No public businesses found. "

                "Try another city/category."

            )

        else:

            saved = 0

            progress = st.progress(0)

            for i, lead in enumerate(found):

                lead["country"] = country

                ai = qualify(lead)

                lead.update(ai)

                lead["status"] = "QUALIFIED"

                if lead["score"] >= min_score:

                    save_lead(lead)

                    saved += 1

                progress.progress(

                    (i + 1) / len(found)

                )

            st.success(

                f"Found {len(found)} businesses. "

                f"Saved {saved} qualified leads."

            )

# =========================================================

# DATABASE

# =========================================================

elif page == "Database":

    st.title("🗄️ Database")

    leads = get_leads()

    if not leads:

        st.info(

            "No leads yet."

        )

        st.stop()

    for lead in leads:

        with st.expander(

            f"{lead['business']} — "

            f"Score {lead['score']}"

        ):

            st.write(

                f"**Category:** {lead['category']}"

            )

            st.write(

                f"**Location:** "

                f"{lead['city']}, "

                f"{lead['country']}"

            )

            st.write(

                f"**Website:** "

                f"{lead['website'] or 'None'}"

            )

            st.write(

                f"**Contact:** "

                f"{lead['contact'] or 'None'}"

            )

            st.write(

                f"**Problem:** {lead['problem']}"

            )

            st.write(

                f"**Service:** {lead['service']}"

            )

            st.write(

                f"**Reason:** {lead['reason']}"

            )

            statuses = [

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

            current = (

                lead["status"]

                if lead["status"] in statuses

                else "NEW"

            )

            new_status = st.selectbox(

                "Status",

                statuses,

                index=statuses.index(current),

                key=f"db_status_{lead['id']}"

            )

            if st.button(

                "Save",

                key=f"db_save_{lead['id']}"

            ):

                change_status(

                    lead["id"],

                    new_status

                )

                st.success(

                    "Status updated."

                )

                st.rerun()

# =========================================================

# AI OUTREACH

# =========================================================

elif page == "AI Outreach":

    st.title("✍️ AI Outreach")

    leads = get_leads()

    if not leads:

        st.info(

            "Find leads first."

        )

        st.stop()

    # IMPORTANT:

    # selectbox receives simple integers,

    # NOT SQLite Row/dict objects.

    lead_ids = [

        lead["id"]

        for lead in leads

    ]

    selected_id = st.selectbox(

        "Choose lead",

        lead_ids,

        format_func=lambda x: (

            get_lead(x)["business"]

            + " — "

            + str(get_lead(x)["score"])

        ),

        key="outreach_select"

    )

    lead = get_lead(selected_id)

    st.write(

        f"**Business:** {lead['business']}"

    )

    st.write(

        f"**Problem:** {lead['problem']}"

    )

    st.write(

        f"**Recommended service:** "

        f"{lead['service']}"

    )

    channel = st.selectbox(

        "Channel",

        [

            "Email",

            "LinkedIn",

            "WhatsApp",

            "Manual"

        ]

    )

    if st.button(

        "✨ Generate Message",

        type="primary"

    ):

        st.session_state[

            "outreach_message"

        ] = generate_message(

            lead,

            channel

        )

    message = st.text_area(

        "Message",

        st.session_state.get(

            "outreach_message",

            ""

        ),

        height=220

    )

    if st.button("💾 Save Draft"):

        conn = connect()

        conn.execute("""

            INSERT INTO messages

            (

                lead_id,

                channel,

                message,

                status,

                created_at

            )

            VALUES (?, ?, ?, ?, ?)

        """, (

            lead["id"],

            channel,

            message,

            "DRAFT",

            datetime.utcnow().isoformat()

        ))

        conn.commit()

        conn.close()

        change_status(

            lead["id"],

            "CONTACTED"

        )

        st.success(

            "Draft saved."

        )

# =========================================================

# AI INBOX

# =========================================================

elif page == "AI Inbox":

    st.title("📥 AI Inbox")

    leads = get_leads()

    if not leads:

        st.info(

            "No leads available."

        )

        st.stop()

    # Again: IDs only.

    lead_ids = [

        lead["id"]

        for lead in leads

    ]

    selected_id = st.selectbox(

        "Client",

        lead_ids,

        format_func=lambda x: (

            get_lead(x)["business"]

        ),

        key="inbox_select"

    )

    lead = get_lead(selected_id)

    reply = st.text_area(

        "Paste client's reply",

        height=180,

        placeholder=(

            "Yes, I'm interested. "

            "How much does it cost?"

        )

    )

    if st.button(

        "🤖 Analyze Reply",

        type="primary"

    ):

        if not reply.strip():

            st.warning(

                "Paste the reply first."

            )

            st.stop()

        result = analyze_reply(reply)

        classification = result[

            "classification"

        ]

        conn = connect()

        conn.execute("""

            INSERT INTO replies

            (

                lead_id,

                reply,

                classification,

                summary,

                next_action,

                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?)

        """, (

            lead["id"],

            reply,

            classification,

            result["summary"],

            result["next_action"],

            datetime.utcnow().isoformat()

        ))

        conn.commit()

        conn.close()

        if classification in [

            "INTERESTED",

            "WANTS PRICE",

            "WANTS A CALL"

        ]:

            change_status(

                lead["id"],

                "INTERESTED"

            )

        st.success(

            "Classification: "

            + classification

        )

        st.write(

            "**Summary:** "

            + result["summary"]

        )

        st.write(

            "**Next action:** "

            + result["next_action"]

        )

        if classification in [

            "INTERESTED",

            "WANTS PRICE",

            "WANTS A CALL"

        ]:

            st.warning(

                "🔥 High-intent client. "

                "Take over manually for pricing, "

                "negotiation and payment."

            )

# =========================================================

# DEAL ALERTS

# =========================================================

elif page == "Deal Alerts":

    st.title("🔥 Deal Alerts")

    leads = get_leads()

    hot = [

        x for x in leads

        if x["status"] in [

            "INTERESTED",

            "CALL REQUESTED",

            "NEGOTIATING"

        ]

    ]

    if not hot:

        st.info(

            "No active deal alerts."

        )

        st.stop()

    for lead in hot:

        with st.container(border=True):

            st.subheader(

                "🔥 "

                + lead["business"]

            )

            st.write(

                f"Score: {lead['score']}/100"

            )

            st.write(

                f"Problem: {lead['problem']}"

            )

            st.write(

                f"Service: {lead['service']}"

            )

            c1, c2, c3 = st.columns(3)

            if c1.button(

                "📞 Call",

                key=f"call_{lead['id']}"

            ):

                change_status(

                    lead["id"],

                    "CALL REQUESTED"

                )

                st.rerun()

            if c2.button(

                "🤝 Negotiating",

                key=f"neg_{lead['id']}"

            ):

                change_status(

                    lead["id"],

                    "NEGOTIATING"

                )

                st.rerun()

            if c3.button(

                "💰 Deal",

                key=f"deal_{lead['id']}"

            ):

                change_status(

                    lead["id"],

                    "DEAL"

                )

                st.rerun()

# =========================================================

# ANALYTICS

# =========================================================

elif page == "Analytics":

    st.title("📊 Analytics")

    leads = get_leads()

    total = len(leads)

    qualified = len([

        x for x in leads

        if x["score"] >= 70

    ])

    interested = len([

        x for x in leads

        if x["status"] in [

            "INTERESTED",

            "CALL REQUESTED",

            "NEGOTIATING"

        ]

    ])

    deals = len([

        x for x in leads

        if x["status"] == "DEAL"

    ])

    a, b, c, d = st.columns(4)

    a.metric(

        "Leads",

        total

    )

    b.metric(

        "Qualified",

        qualified

    )

    c.metric(

        "Interested",

        interested

    )

    d.metric(

        "Deals",

        deals

    )

    if total:

        st.write(

            "Qualification rate: "

            f"{qualified / total * 100:.1f}%"

        )

        st.write(

            "Lead → Deal rate: "

            f"{deals / total * 100:.1f}%"

        )

# =========================================================

# SETTINGS

# =========================================================

elif page == "Settings":

    st.title("⚙️ Settings")

    st.subheader("🤖 AI Engine")

    if GEMINI_KEY:

        st.success(

            "Gemini API: Connected"

        )

    else:

        st.warning(

            "Gemini API: Not connected"

        )

        st.code("""

GEMINI_API_KEY = "YOUR_KEY"

GEMINI_MODEL = "gemini-2.5-flash"

""")

        st.info(

            "Add the Gemini key in "

            "Streamlit Secrets."

        )

    st.write(

        "Model: "

        + GEMINI_MODEL

    )

    st.divider()

    st.subheader("🔐 Security")

    st.success(

        "Password/login is disabled."

    )

    st.divider()

    st.subheader("🛑 Automation")

    st.warning(

        "Automatic external messaging is disabled. "

        "Use official authorized APIs only."

    )

    st.divider()

    st.subheader("💾 Database")

    st.write(

        "Database: "

        + DB

    )
