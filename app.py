
import streamlit as st
import requests
import sqlite3
import json
import re
from datetime import datetime
from urllib.parse import urlparse

# =========================================================
# NEXUS AI — CLIENT HUNTER
# SINGLE FILE APP
# =========================================================

st.set_page_config(
    page_title="NEXUS AI — Client Hunter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "nexus_client_hunter.db"


# =========================================================
# PREMIUM UI
# =========================================================

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top right, #172033 0%, #080b12 35%),
        #080b12;
    color: #f4f7fb;
}

section[data-testid="stSidebar"] {
    background: #0b1018;
    border-right: 1px solid #202b3c;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
}

.nexus-title {
    font-size: 38px;
    font-weight: 900;
    letter-spacing: -1.5px;
}

.nexus-sub {
    color: #8e9caf;
    font-size: 15px;
}

.card {
    background: linear-gradient(145deg, #121925, #0c1119);
    border: 1px solid #222d3f;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 16px;
}

.metric {
    background: #101722;
    border: 1px solid #222d3f;
    border-radius: 16px;
    padding: 18px;
    min-height: 105px;
}

.metric-number {
    font-size: 30px;
    font-weight: 900;
}

.metric-label {
    color: #8c98aa;
    font-size: 13px;
}

.hot {
    background: #241b0d;
    border: 1px solid #69511c;
    border-radius: 18px;
    padding: 20px;
}

.green {
    color: #63e6a5;
    font-weight: 800;
}

.yellow {
    color: #ffd166;
    font-weight: 800;
}

.red {
    color: #ff7777;
    font-weight: 800;
}

.muted {
    color: #8995a8;
    font-size: 12px;
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
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT,
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
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            channel TEXT,
            message TEXT,
            status TEXT DEFAULT 'DRAFT',
            created_at TEXT
        )
    """)

    cur.execute("""
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
# BASIC HELPERS
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value, limit=1000):
    if value is None:
        return ""
    return str(value).strip()[:limit]


def clean_url(url):
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def valid_url(url):
    try:
        parsed = urlparse(clean_url(url))
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )
    except Exception:
        return False


def score_class(score):
    if score >= 75:
        return "green"
    if score >= 50:
        return "yellow"
    return "red"


def get_gemini_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


# =========================================================
# GEMINI AI
# =========================================================

def gemini(prompt):
    key = get_gemini_key()

    if not key:
        return None, "GEMINI_API_KEY is not configured."

    model = "gemini-3.7-flash"

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
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
            "temperature": 0.7,
            "maxOutputTokens": 1400
        }
    }

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": key
            },
            json=payload,
            timeout=40
        )

        if response.status_code != 200:
            return None, f"Gemini API error: {response.status_code}"

        data = response.json()

        text = (
            data
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not text:
            return None, "Gemini returned an empty response."

        return text.strip(), None

    except Exception as e:
        return None, f"AI connection error: {e}"


def gemini_json(prompt):

    text, error = gemini(
        prompt + """

IMPORTANT:
Return ONLY valid JSON.
Do not use markdown.
Do not use ```json.
Do not add explanations outside JSON.
"""
    )

    if error:
        return None, error

    try:
        text = text.strip()

        text = re.sub(
            r"^```json\s*",
            "",
            text,
            flags=re.I
        )

        text = re.sub(
            r"^```\s*",
            "",
            text
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        return json.loads(text), None

    except Exception:
        return None, "AI returned invalid JSON."


# =========================================================
# WEBSITE AUDIT
# =========================================================

def audit_website(url):

    if not valid_url(url):
        return {
            "reachable": False,
            "status": None,
            "title": "",
            "description": "",
            "problems": [
                "No valid public website URL."
            ]
        }

    url = clean_url(url)

    try:

        response = requests.get(
            url,
            timeout=12,
            allow_redirects=True,
            headers={
                "User-Agent":
                    "Mozilla/5.0 NEXUS-AI-Client-Hunter"
            }
        )

        html = response.text[:500000]

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            re.I | re.S
        )

        description_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html,
            re.I | re.S
        )

        title = ""

        if title_match:
            title = re.sub(
                r"\s+",
                " ",
                title_match.group(1)
            ).strip()

        description = ""

        if description_match:
            description = re.sub(
                r"\s+",
                " ",
                description_match.group(1)
            ).strip()

        lower = html.lower()

        problems = []

        if len(title) < 5:
            problems.append(
                "Website title appears missing or weak."
            )

        if not description:
            problems.append(
                "Meta description was not detected."
            )

        if "viewport" not in lower:
            problems.append(
                "Mobile viewport tag was not detected."
            )

        if not re.search(
            r"(contact|book|quote|call|appointment|get started|schedule)",
            lower
        ):
            problems.append(
                "Clear contact/CTA signal was not detected."
            )

        if not problems:
            problems.append(
                "No obvious basic issue detected."
            )

        return {
            "reachable": True,
            "status": response.status_code,
            "title": title,
            "description": description,
            "problems": problems
        }

    except Exception as e:

        return {
            "reachable": False,
            "status": None,
            "title": "",
            "description": "",
            "problems": [
                f"Website audit failed: {e}"
            ]
        }


# =========================================================
# AI LEAD QUALIFICATION
# =========================================================

def qualify_lead(lead):

    prompt = f"""
You are an expert B2B sales qualification AI.

Business:
{lead.get("business_name", "")}

Category:
{lead.get("category", "")}

Country:
{lead.get("country", "")}

City:
{lead.get("city", "")}

Website:
{lead.get("website", "")}

Website audit:
{json.dumps(lead.get("audit", {}))}

Evaluate whether this business could reasonably need:

1. Website creation
2. Website redesign
3. AI automation
4. Lead generation
5. Business automation

Never invent information.

Return exactly:

{{
    "score": 0,
    "problem": "short factual opportunity",
    "service": "best recommended service",
    "reason": "short explanation"
}}
"""

    data, error = gemini_json(prompt)

    if error or not data:

        return {
            "score": 50,
            "problem":
                "Potential website or automation opportunity.",
            "service":
                "Website + AI automation",
            "reason":
                "AI qualification unavailable; manual review recommended."
        }

    try:
        score = int(data.get("score", 50))
    except Exception:
        score = 50

    score = max(0, min(100, score))

    return {
        "score": score,
        "problem":
            clean(data.get("problem"), 500),
        "service":
            clean(data.get("service"), 250),
        "reason":
            clean(data.get("reason"), 600)
    }


# =========================================================
# AI OUTREACH
# =========================================================

def create_message(lead, channel):

    prompt = f"""
Create a concise, natural B2B outreach message.

Business:
{lead.get("business_name")}

Category:
{lead.get("category")}

City:
{lead.get("city")}

Website:
{lead.get("website")}

Detected opportunity:
{lead.get("detected_problem")}

Recommended service:
{lead.get("recommended_service")}

Channel:
{channel}

Rules:
- Maximum 100 words.
- Human and professional.
- Personalize using only supplied information.
- Mention one real opportunity.
- No fake claims.
- No guaranteed results.
- No fake urgency.
- No spam language.
- Offer a quick idea/demo.
"""

    text, error = gemini(prompt)

    if error:

        return (
            f"Hi, I came across "
            f"{lead.get('business_name', 'your business')} "
            f"and noticed a possible opportunity around "
            f"{lead.get('detected_problem', 'your website')}. "
            f"I help businesses with "
            f"{lead.get('recommended_service', 'websites and automation')}. "
            f"I'd be happy to share a quick idea if you're interested."
        )

    return text


# =========================================================
# AI REPLY ANALYSIS
# =========================================================

def analyze_reply(reply):

    prompt = f"""
Analyze this business reply.

Reply:
{reply}

Choose ONE classification:

INTERESTED
WANTS PRICE
WANTS A CALL
NEEDS MORE INFORMATION
MAYBE LATER
NOT INTERESTED
SPAM
UNKNOWN

Return:

{{
    "classification": "ONE OF THE ABOVE",
    "summary": "short summary",
    "next_action": "short recommended next step"
}}
"""

    data, error = gemini_json(prompt)

    if error or not data:

        return {
            "classification": "UNKNOWN",
            "summary": "AI analysis unavailable.",
            "next_action": "Review the reply manually."
        }

    return {
        "classification":
            clean(data.get("classification"), 80),
        "summary":
            clean(data.get("summary"), 500),
        "next_action":
            clean(data.get("next_action"), 500)
    }


# =========================================================
# PUBLIC LEAD FINDER
# =========================================================

def find_public_businesses(
    city,
    category,
    country=""
):

    safe_city = city.replace('"', '\\"')

    query = f"""
[out:json][timeout:30];

area["name"="{safe_city}"]["boundary"="administrative"]->.searchArea;

(
    nwr["name"]["shop"](area.searchArea);
    nwr["name"]["amenity"](area.searchArea);
    nwr["name"]["office"](area.searchArea);
);

out center tags;
"""

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    last_error = ""

    for endpoint in endpoints:

        try:

            response = requests.post(
                endpoint,
                data=query,
                timeout=40,
                headers={
                    "User-Agent":
                        "NEXUS-AI-Client-Hunter"
                }
            )

            if response.status_code != 200:

                last_error = (
                    f"Overpass HTTP "
                    f"{response.status_code}"
                )

                continue

            data = response.json()

            results = []

            wanted = category.lower().strip()

            for element in data.get(
                "elements",
                []
            ):

                tags = element.get(
                    "tags",
                    {}
                )

                name = tags.get("name")

                if not name:
                    continue

                searchable = " ".join([
                    str(name),
                    str(tags.get("shop", "")),
                    str(tags.get("amenity", "")),
                    str(tags.get("office", "")),
                    str(tags.get("description", ""))
                ]).lower()

                if wanted:

                    words = [
                        w for w in wanted.split()
                        if len(w) >= 4
                    ]

                    match = (
                        wanted in searchable
                        or any(
                            w in searchable
                            for w in words
                        )
                    )

                    if not match:
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

                if phone:
                    contact = phone
                elif email:
                    contact = email
                elif website:
                    contact = website
                else:
                    contact = ""

                results.append({
                    "business_name":
                        clean(name, 200),
                    "person_name":
                        "",
                    "country":
                        country,
                    "city":
                        city,
                    "category":
                        category,
                    "website":
                        clean(website, 500),
                    "source_url":
                        "https://www.openstreetmap.org/",
                    "contact_method":
                        clean(contact, 500)
                })

                if len(results) >= 50:
                    break

            return results, None

        except Exception as e:

            last_error = str(e)

    return [], last_error or "Lead source unavailable."


# =========================================================
# DATABASE OPERATIONS
# =========================================================

def save_lead(lead):

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
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
        VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (
        lead.get("business_name"),
        lead.get("person_name"),
        lead.get("country"),
        lead.get("city"),
        lead.get("category"),
        lead.get("website"),
        lead.get("source_url"),
        lead.get("contact_method"),
        lead.get("detected_problem"),
        lead.get("recommended_service"),
        lead.get("lead_score", 0),
        lead.get("ai_reason"),
        "QUALIFIED",
        now(),
        now()
    ))

    lead_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return lead_id


def get_leads():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM leads
        ORDER BY lead_score DESC, id DESC
    """).fetchall()

    conn.close()

    return rows


def update_status(lead_id, status):

    conn = get_db()

    conn.execute("""
        UPDATE leads
        SET status = ?, updated_at = ?
        WHERE id = ?
    """, (
        status,
        now(),
        lead_id
    ))

    conn.commit()
    conn.close()


def save_message(
    lead_id,
    channel,
    message,
    status="DRAFT"
):

    conn = get_db()

    conn.execute("""
        INSERT INTO messages (
            lead_id,
            channel,
            message,
            status,
            created_at
        )
        VALUES (?,?,?,?,?)
    """, (
        lead_id,
        channel,
        message,
        status,
        now()
    ))

    conn.commit()
    conn.close()


def save_reply(
    lead_id,
    reply,
    analysis
):

    conn = get_db()

    conn.execute("""
        INSERT INTO replies (
            lead_id,
            reply,
            classification,
            summary,
            next_action,
            created_at
        )
        VALUES (?,?,?,?,?,?)
    """, (
        lead_id,
        reply,
        analysis["classification"],
        analysis["summary"],
        analysis["next_action"],
        now()
    ))

    conn.commit()
    conn.close()


def get_stats():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM leads"
    ).fetchone()[0]

    qualified = conn.execute(
        "SELECT COUNT(*) FROM leads "
        
