import json
import re
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

import requests
import streamlit as st

st.set_page_config(
    page_title="NEXUS AI Client Hunter",
    page_icon="⚡",
    layout="wide",
)

DB = "client_hunter.db"

STATUSES = [
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


def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def clean(value, max_len=1000):
    if value is None:
        return ""
    return str(value).strip()[:max_len]


def valid_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def init_db():
    conn = sqlite3.connect(DB, check_same_thread=False)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            person_name TEXT,
            country TEXT,
            city TEXT,
            category TEXT,
            website TEXT,
            source_url TEXT,
            contact_method TEXT,
            detected_problem TEXT,
            recommended_service TEXT,
            lead_score INTEGER DEFAULT 0,
            ai_reason TEXT,
            status TEXT DEFAULT 'NEW',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            channel TEXT,
            message TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            reply TEXT,
            classification TEXT,
            summary TEXT,
            next_action TEXT,
            created_at TEXT
        )
        """
    )

    conn.commit()
    return conn


conn = init_db()


def get_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


def get_model():
    try:
        return st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    except Exception:
        return "gemini-2.5-flash"


def gemini(prompt):
    key = get_key()

    if not key:
        return ""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{get_model()}:generateContent?key={key}"
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
            "temperature": 0.4,
            "maxOutputTokens": 1200,
        },
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    except Exception as exc:
        st.session_state["last_ai_error"] = str(exc)
        return ""


def gemini_json(prompt):
    text = gemini(prompt)

    if not text:
        return {}

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text.strip(),
        flags=re.I,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text.strip(),
    )

    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, flags=re.S)

        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass

    return {}


def audit_website(url):
    if not valid_url(url):
        return "No valid public website provided."

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 ClientHunter/1.0"
            },
            allow_redirects=True,
        )

        html = response.text[:300000]

        text = re.sub(
            r"<[^>]+>",
            " ",
            html,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        problems = []

        if response.status_code >= 400:
            problems.append(
                f"website returned HTTP {response.status_code}"
            )

        if len(text) < 300:
            problems.append(
                "very little readable public content detected"
            )

        if "viewport" not in html.lower():
            problems.append(
                "mobile viewport meta tag was not detected"
            )

        if not re.search(
            r"contact|book|quote|call|appointment|demo",
            text,
            re.I,
        ):
            problems.append(
                "clear contact/conversion wording was not detected"
            )

        if not problems:
            return (
                "No obvious issue detected by the basic public audit."
            )

        return "; ".join(problems[:4])

    except Exception as exc:
        return f"Audit unavailable: {str(exc)[:160]}"


def qualify_lead(
    business,
    category,
    city,
    website,
    audit,
):
    prompt = f"""
You are a B2B lead qualification assistant.

Return ONLY valid JSON with these keys:

lead_score
detected_problem
recommended_service
ai_reason

Score must be 0-100.

Be conservative.
Never invent facts.

Business: {business}
Category: {category}
City: {city}
Website: {website or "none"}

Public audit:
{audit}

Possible services:
- website redesign
- landing page
- booking system
- CRM automation
- AI chatbot
- lead follow-up automation
"""

    data = gemini_json(prompt)

    if data:
        try:
            score = int(data.get("lead_score", 0))
            score = max(0, min(100, score))
        except Exception:
            score = 0

        return {
            "lead_score": score,
            "detected_problem": clean(
                data.get("detected_problem", ""),
                500,
            ),
            "recommended_service": clean(
                data.get("recommended_service", ""),
                300,
            ),
            "ai_reason": clean(
                data.get("ai_reason", ""),
                700,
            ),
        }

    score = 40 if website else 55

    problem = (
        audit
        if audit
        else "No public website supplied; website/automation opportunity may exist."
    )

    service = (
        "Website + lead capture automation"
        if not website
        else "Website conversion improvement"
    )

    return {
        "lead_score": score,
        "detected_problem": problem,
        "recommended_service": service,
        "ai_reason": (
            "Fallback qualification used because AI analysis is unavailable."
        ),
    }


def create_message(lead, channel="Email"):
    prompt = f"""
Write one short, natural B2B outreach message.

Do not lie.
Do not claim you already spoke to them.
Do not guarantee results.

Mention one specific opportunity from the supplied data.

Keep it under 90 words.

End with a low-pressure question about a quick idea or demo.

Business:
{lead["business_name"]}

Category:
{lead["category"]}

City:
{lead["city"]}

Website:
{lead["website"]}

Problem:
{lead["detected_problem"]}

Recommended service:
{lead["recommended_service"]}

Channel:
{channel}
"""

    result = gemini(prompt)

    if result:
        return result

    return (
        f"Hi, I came across {lead['business_name']} and noticed "
        f"a possible opportunity around "
        f"{lead['recommended_service'].lower() or 'lead capture'}. "
        "I have a quick idea that may help improve enquiries. "
        "Would you like me to send it over?"
    )


def analyze_reply(reply):
    prompt = f"""
Classify this B2B reply.

Return ONLY valid JSON with:

classification
summary
next_action

Allowed classification values:

INTERESTED
WANTS PRICE
WANTS A CALL
NEEDS MORE INFORMATION
MAYBE LATER
NOT INTERESTED
SPAM
UNKNOWN

Reply:
{reply}
"""

    data = gemini_json(prompt)

    if data:
        return {
            "classification": clean(
                data.get("classification", "UNKNOWN"),
                80,
            ).upper(),
            "summary": clean(
                data.get("summary", ""),
                500,
            ),
            "next_action": clean(
                data.get("next_action", ""),
                500,
            ),
        }

    low = reply.lower()

    if any(
        x in low
        for x in ["price", "cost", "how much"]
    ):
        classification = "WANTS PRICE"

    elif any(
        x in low
        for x in ["call", "phone", "meeting"]
    ):
        classification = "WANTS A CALL"

    elif any(
        x in low
        for x in ["yes", "interested", "sure", "tell me more"]
    ):
        classification = "INTERESTED"

    elif any(
        x in low
        for x in ["no thanks", "not interested", "remove me"]
    ):
        classification = "NOT INTERESTED"

    else:
        classification = "UNKNOWN"

    return {
        "classification": classification,
        "summary": "Rule-based analysis used.",
        "next_action": "Review reply manually.",
    }


def find_public_businesses(
    city,
    country,
    category,
    limit=20,
):
    query = f"""
[out:json][timeout:25];

area["name"="{city}"][boundary=administrative]->.a;

(
    nwr["name"]["shop"](area.a);
    nwr["name"]["amenity"](area.a);
    nwr["name"]["office"](area.a);
);

out center tags {max(1, min(limit, 50))};
"""

    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=35,
            headers={
                "User-Agent": "NEXUS-AI-Client-Hunter/1.0"
            },
        )

        response.raise_for_status()

        elements = response.json().get(
            "elements",
            [],
        )

    except Exception as exc:
        st.session_state["finder_error"] = str(exc)
        return []

    wanted = category.lower().strip()

    results = []

    for element in elements:
        tags = element.get("tags", {})

        name = clean(
            tags.get("name", ""),
            200,
        )

        if not name:
            continue

        blob = " ".join(
            str(value)
            for value in tags.values()
        ).lower()

        if (
            wanted
            and wanted not in blob
            and wanted not in name.lower()
        ):
            continue

        website = (
            tags.get("website")
            or tags.get("contact:website")
            or ""
        )

        phone = (
            tags.get("phone")
            or tags.get("contact:phone")
            or ""
        )

        email = (
            tags.get("email")
            or tags.get("contact:email")
            or ""
        )

        contact = (
            phone
            or email
            or website
            or "Public source page"
        )

        results.append(
            {
                "business_name": name,
                "city": city,
                "country": country,
                "category": category,
                "website": website,
                "contact_method": contact,
                "source_url": (
                    "https://www.openstreetmap.org/"
                ),
            }
        )

        if len(results) >= limit:
            break

    return results


def save_lead(item):
    created = now()

    cursor = conn.execute(
        """
        INSERT INTO leads (
            business_name,
            person_name,
            country,
            city,
            category,
            website,
            source_url,
            contact_method,
            detected_problem,
            recommended_service,
            lead_score,
            ai_reason,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.get("business_name", ""),
            item.get("person_name", ""),
            item.get("country", ""),
            item.get("city", ""),
            item.get("category", ""),
            item.get("website", ""),
            item.get("source_url", ""),
            item.get("contact_method", ""),
            item.get("detected_problem", ""),
            item.get("recommended_service", ""),
            int(item.get("lead_score", 0)),
            item.get("ai_reason", ""),
            item.get("status", "NEW"),
            created,
            created,
        ),
    )

    conn.commit()

    return cursor.lastrowid


def get_leads(
    status=None,
    min_score=0,
):
    if status and status != "ALL":
        return conn.execute(
            """
            SELECT *
            FROM leads
            WHERE status=?
            AND lead_score>=?
            ORDER BY lead_score DESC, id DESC
            """,
            (
                status,
                min_score,
            ),
        ).fetchall()

    return conn.execute(
        """
        SELECT *
        FROM leads
        WHERE lead_score>=?
        ORDER BY lead_score DESC, id DESC
        """,
        (min_score,),
    ).fetchall()


def lead_dict(row):
    columns = [
        "id",
        "business_name",
        "person_name",
        "country",
        "city",
        "category",
        "website",
        "source_url",
        "contact_method",
        "detected_problem",
        "recommended_service",
        "lead_score",
        "ai_reason",
        "status",
        "created_at",
        "updated_at",
    ]

    return dict(zip(columns, row))


def update_status(
    lead_id,
    status,
):
    conn.execute(
        """
        UPDATE leads
        SET status=?,
            updated_at=?
        WHERE id=?
        """,
        (
            status,
            now(),
            lead_id,
        ),
    )

    conn.commit()


def save_message(
    lead_id,
    channel,
    message,
    status,
):
    conn.execute(
        """
        INSERT INTO messages (
            lead_id,
            channel,
            message,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            channel,
            message,
            status,
            now(),
        ),
    )

    conn.commit()


def save_reply(
    lead_id,
    reply,
    analysis,
):
    conn.execute(
        """
        INSERT INTO replies (
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
            analysis["classification"],
            analysis["summary"],
            analysis["next_action"],
            now(),
        ),
    )

    conn.commit()


def stats():
    total = conn.execute(
        "SELECT COUNT(*) FROM leads"
    ).fetchone()[0]

    qualified = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE status IN (
            'QUALIFIED',
            'CONTACTED',
            'REPLIED',
            'INTERESTED',
            'CALL REQUESTED',
            'NEGOTIATING',
            'DEAL'
        )
        """
    ).fetchone()[0]

    interested = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE status IN (
            'INTERESTED',
            'CALL REQUESTED',
            'NEGOTIATING',
            'DEAL'
        )
        """
    ).fetchone()[0]

    deals = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE status='DEAL'
        """
    ).fetchone()[0]

    sent = conn.execute(
        """
        SELECT COUNT(*)
        FROM messages
        WHERE status='SENT'
        """
    ).fetchone()[0]

    replies = conn.execute(
        "SELECT COUNT(*) FROM replies"
    ).fetchone()[0]

    return (
        total,
        qualified,
        interested,
        deals,
        sent,
        replies,
    )


def apply_css():
    st.markdown(
        """
        <style>

        .stApp {
            background: #080b12;
        }

        [data-testid="stSidebar"] {
            background: #0d111a;
        }

        .hero {
            padding: 20px 24px;
            border: 1px solid #202838;
            border-radius: 18px;
            background:
                linear-gradient(
                    135deg,
                    #111827,
                    #0b1220
                );
            margin-bottom: 18px;
        }

        .hero h1 {
            margin: 0;
            font-size: 32px;
        }

        .muted {
            color: #9aa5b5;
        }

        .card {
            padding: 18px;
            border: 1px solid #202838;
            border-radius: 16px;
            background: #0d121c;
            margin-bottom: 12px;
        }

        .alert {
            padding: 16px;
            border: 1px solid #634b1d;
            border-radius: 14px;
            background: #19140a;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


apply_css()


with st.sidebar:
    st.markdown("## ⚡ NEXUS AI")
    st.caption("AI Client Hunter")

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

    if st.button(
        "⏸ PAUSE ALL AUTOMATIONS",
        use_container_width=True,
    ):
        st.session_state["paused"] = True
        st.warning(
            "Automations paused for this session."
        )

    st.caption(
        "Auto-send works only through authorized official APIs. "
        "No CAPTCHA, login bypass, spam, or private-data scraping."
    )


st.markdown(
    """
    <div class="hero">
        <h1>⚡ NEXUS AI Client Hunter</h1>
        <div class="muted">
            Find → Qualify → Personalize → Follow up → Deal Alert
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


if page == "Dashboard":

    total, qualified, interested, deals, sent, replies = stats()

    a, b, c, d, e, f = st.columns(6)

    a.metric("New Leads", total)
    b.metric("Qualified", qualified)
    c.metric("Interested", interested)
    d.metric("Deals", deals)
    e.metric("Messages", sent)
    f.metric("Replies", replies)

    st.subheader("🔥 High-value leads")

    rows = get_leads(min_score=70)[:10]

    if not rows:
        st.info(
            "No high-score leads yet. Use Lead Finder."
        )

    for row in rows:
        lead = lead_dict(row)

        with st.container(border=True):

            st.write(
                f"**{lead['business_name']}** · "
                f"Score **{lead['lead_score']}** · "
                f"{lead['status']}"
            )

            st.caption(
                f"{lead['category']} · "
                f"{lead['city']} · "
                f"{lead['recommended_service']}"
            )

            if lead["detected_problem"]:
                st.write(
                    lead["detected_problem"]
                )


elif page == "Lead Finder":

    st.subheader("🔎 Public Lead Finder")

    c1, c2, c3 = st.columns(3)

    country = c1.text_input(
        "Country",
        "United States",
    )

    city = c2.text_input(
        "City",
        "New York",
    )

    category = c3.text_input(
        "Business category",
       
