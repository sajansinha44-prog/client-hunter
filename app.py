import streamlit as st
import sqlite3
import requests
import json
import re
import hmac
from datetime import datetime
from urllib.parse import urlparse

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="AI Client Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB = "client_hunter.db"

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
.stApp {
    background: #080b12;
    color: #f5f7fb;
}
.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
}
.card {
    background: #111620;
    border: 1px solid #252d3b;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 14px;
}
.metric {
    font-size: 28px;
    font-weight: 800;
}
.small {
    color: #8f9bad;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE
# =========================================================
def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business TEXT NOT NULL,
            website TEXT DEFAULT '',
            city TEXT DEFAULT '',
            country TEXT DEFAULT '',
            category TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            source TEXT DEFAULT '',
            problem TEXT DEFAULT '',
            service TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            reason TEXT DEFAULT '',
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
            next_action TEXT DEFAULT '',
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
        return str(st.secrets.get(name, default))
    except Exception:
        return default


APP_PASSWORD = secret("APP_PASSWORD")
GEMINI_KEY = secret("GEMINI_API_KEY")
GEMINI_MODEL = secret("GEMINI_MODEL", "gemini-2.5-flash")

# =========================================================
# LOGIN
# =========================================================
def login():
    st.title("🎯 AI Client Hunter")
    st.caption("Find → Qualify → Personalize → Close")

    if not APP_PASSWORD:
        st.warning(
            "APP_PASSWORD Streamlit Secrets में configured नहीं है."
        )
        st.info(
            "App को public करने से पहले APP_PASSWORD और GEMINI_API_KEY "
            "Streamlit Secrets में configure करें."
        )
        return

    password = st.text_input(
        "App Password",
        type="password"
    )

    if st.button(
        "🔐 Login",
        use_container_width=True
    ):
        if hmac.compare_digest(password, APP_PASSWORD):
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("गलत password.")


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if APP_PASSWORD and not st.session_state["logged_in"]:
    login()
    st.stop()

# =========================================================
# GEMINI
# =========================================================
def gemini(prompt):

    if not GEMINI_KEY:
        return None, "GEMINI_API_KEY configured नहीं है."

    model = GEMINI_MODEL.strip() or "gemini-2.5-flash"

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
            "temperature": 0.4,
            "maxOutputTokens": 1200
        }
    }

    try:

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_KEY
            },
            json=payload,
            timeout=45
        )

        if response.status_code != 200:
            return None, (
                f"Gemini API returned HTTP "
                f"{response.status_code}."
            )

        data = response.json()

        text = (
            data
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        return text.strip(), None

    except requests.RequestException:
        return None, "Gemini से connection नहीं हो पाया."

    except Exception:
        return None, "Gemini response पढ़ने में समस्या हुई."

# =========================================================
# JSON PARSER
# =========================================================
def parse_json(text):

    if not text:
        return None

    try:
        return json.loads(text)

    except Exception:

        match = re.search(
            r"\{.*\}",
            text,
            re.S
        )

        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

    return None

# =========================================================
# CITY NORMALIZATION
# =========================================================
def normalize_city(city):

    aliases = {
        "dehli": "Delhi",
        "delhi": "Delhi",
        "new delhi": "Delhi",
        "mumbai": "Mumbai",
        "bombay": "Mumbai",
        "bangalore": "Bengaluru",
        "bengaluru": "Bengaluru",
        "calcutta": "Kolkata",
        "calcutta city": "Kolkata",
    }

    key = re.sub(
        r"\s+",
        " ",
        city.strip().lower()
    )

    return aliases.get(
        key,
        city.strip()
    )

# =========================================================
# URL HELPERS
# =========================================================
def valid_url(url):

    if not url:
        return False

    candidate = url.strip()

    if not candidate.startswith(
        ("http://", "https://")
    ):
        candidate = "https://" + candidate

    try:

        parsed = urlparse(candidate)

        return (
            parsed.scheme in
            ("http", "https")
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def clean_url(url):

    if not url:
        return ""

    if url.startswith(
        ("http://", "https://")
    ):
        return url

    return "https://" + url

# =========================================================
# WEBSITE AUDIT
# =========================================================
def audit_website(url):

    if not valid_url(url):

        return {
            "reachable": False,
            "status": "No public website",
            "details": "No public website URL was supplied."
        }

    try:

        response = requests.get(
            clean_url(url),
            timeout=12,
            allow_redirects=True,
            headers={
                "User-Agent":
                "Mozilla/5.0 AIClientHunter/1.0"
            }
        )

        html = response.text[:500000]

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            re.I | re.S
        )

        description_match = re.search(
            r'<meta[^>]+name=["\']description["\']'
            r'[^>]+content=["\'](.*?)["\']',
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

        lower_html = html.lower()

        problems = []

        if response.status_code >= 400:
            problems.append(
                f"HTTP status {response.status_code}"
            )

        if not title:
            problems.append(
                "Page title missing."
            )

        if not description:
            problems.append(
                "Meta description missing."
            )

        if "viewport" not in lower_html:
            problems.append(
                "Mobile viewport was not detected."
            )

        if not re.search(
            r"(contact|book|quote|appointment|"
            r"schedule|get started)",
            lower_html
        ):
            problems.append(
                "No clear contact/CTA signal detected."
            )

        if not problems:
            problems.append(
                "No obvious issue was verified by this basic audit."
            )

        return {
            "reachable":
                200 <= response.status_code < 400,
            "status":
                f"HTTP {response.status_code}",
            "title":
                title,
            "description":
                description,
            "details":
                " ".join(problems)
        }

    except requests.RequestException:

        return {
            "reachable": False,
            "status": "Audit unavailable",
            "details":
                "Public website could not be reached."
        }

# =========================================================
# AI QUALIFICATION
# =========================================================
def qualify_lead(
    business,
    category,
    city,
    country,
    website,
    audit
):

    if not GEMINI_KEY:

        score = 45 if website else 35

        return {
            "score": score,
            "problem":
                audit.get(
                    "details",
                    "No verified website issue."
                ),
            "service":
                "Website improvement / AI automation",
            "reason":
                "AI unavailable until GEMINI_API_KEY is configured."
        }, None

    prompt = f"""
You are a professional B2B lead qualification assistant.

Business: {business}
Category: {category}
City: {city}
Country: {country}
Website: {website}

Verified website audit:
{json.dumps(audit, ensure_ascii=False)}

Return ONLY JSON:

{{
  "score": 0,
  "problem": "",
  "service": "",
  "reason": ""
}}

Rules:
- score must be 0-100.
- Do not invent facts.
- Only mention opportunities supported by supplied data.
- Recommend a realistic website, AI or automation service.
- Keep reason concise.
"""

    text, error = gemini(prompt)

    data = parse_json(text)

    if error or not data:

        return {
            "score": 0,
            "problem":
                audit.get("details", ""),
            "service":
                "Website improvement / AI automation",
            "reason":
                "AI qualification failed; review manually."
        }, error

    try:
        score = int(
            data.get(
                "score",
                0
            )
        )

        score = max(
            0,
            min(100, score)
        )

    except Exception:
        score = 0

    return {
        "score": score,
        "problem":
            str(data.get("problem", ""))[:500],
        "service":
            str(data.get("service", ""))[:250],
        "reason":
            str(data.get("reason", ""))[:500]
    }, None

# =========================================================
# GENERIC PUBLIC BUSINESS SEARCH
# =========================================================
def find_businesses(
    city,
    country,
    category,
    limit
):

    city = normalize_city(city)

    category = category.strip()

    if not category:
        return [], "Business category required."

    # Search many common OSM tags.
    # This is intentionally generic rather than Gym-specific.
    query = f"""
[out:json][timeout:50];

area["name"="{city}"]["boundary"="administrative"]->.searchArea;

(
    nwr["name"]["amenity"](area.searchArea);
    nwr["name"]["shop"](area.searchArea);
    nwr["name"]["office"](area.searchArea);
    nwr["name"]["leisure"](area.searchArea);
    nwr["name"]["tourism"](area.searchArea);
    nwr["name"]["craft"](area.searchArea);
    nwr["name"]["healthcare"](area.searchArea);
);

out center tags;
"""

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    wanted_words = [
        word.lower()
        for word in re.findall(
            r"[A-Za-z0-9]+",
            category
        )
        if len(word) >= 3
    ]

    for endpoint in endpoints:

        try:

            response = requests.post(
                endpoint,
                data=query,
                timeout=60,
                headers={
                    "User-Agent":
                    "Mozilla/5.0 AIClientHunter/1.0"
                }
            )

            if response.status_code != 200:
                continue

            data = response.json()

            results = []

            seen = set()

            for item in data.get(
                "elements",
                []
            ):

                tags = item.get(
                    "tags",
                    {}
                )

                name = tags.get(
                    "name",
                    ""
                ).strip()

                if not name:
                    continue

                searchable = " ".join(
                    str(
                        tags.get(key, "")
                    )
                    for key in [
                        "name",
                        "amenity",
                        "shop",
                        "office",
                        "leisure",
                        "tourism",
                        "craft",
                        "healthcare",
                        "sport",
                        "description",
                    ]
                ).lower()

                # If category is specific,
                # require at least one category word.
                if wanted_words:

                    if not any(
                        word in searchable
                        for word in wanted_words
                    ):
                        continue

                key = name.lower()

                if key in seen:
                    continue

                seen.add(key)

                website = (
                    tags.get("website")
                    or tags.get(
                        "contact:website"
                    )
                    or ""
                )

                contact = (
                    tags.get("phone")
                    or tags.get(
                        "contact:phone"
                    )
                    or tags.get("email")
                    or tags.get(
                        "contact:email"
                    )
                    or ""
                )

                results.append(
                    {
                        "business": name,
                        "website": website,
                        "contact": contact,
                        "city": city,
                        "country": country,
                        "category": category,
                        "source":
                            "https://www.openstreetmap.org/"
                    }
                )

                if len(results) >= limit:
                    break

            return results, None

        except Exception:
            continue

    return [], (
        "Public business search returned no matching "
        "results or the service is temporarily unavailable."
    )

# =========================================================
# DATABASE HELPERS
# =========================================================
def save_lead(lead):

    conn = db()

    conn.execute(
        """
        INSERT INTO leads
        (
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
            reason,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
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
            lead.get("reason", ""),
            lead.get("status", "NEW"),
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )

    conn.commit()
    conn.close()


def get_leads():

    conn = db()

    rows = conn.execute(
        """
        SELECT *
        FROM leads
        ORDER BY score DESC, id DESC
        """
    ).fetchall()

    conn.close()

    return rows


def update_status(
    lead_id,
    status
):

    conn = db()

    conn.execute(
        """
        UPDATE leads
        SET status=?
        WHERE id=?
        """,
        (
            status,
            lead_id
        )
    )

    conn.commit()
    conn.close()


def save_message(
    lead_id,
    channel,
    message
):

    conn = db()

    conn.execute(
        """
        INSERT INTO messages
        (
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
            "DRAFT",
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )

    conn.commit()
    conn.close()

# =========================================================
# OUTREACH
# =========================================================
def create_message(lead):

    if not GEMINI_KEY:

        return (
            f"Hi, I came across {lead['business']} "
            f"in {lead['city']}. "
            f"I noticed an opportunity around "
            f"{lead['problem'] or 'the online customer journey'}. "
            f"I work on "
            f"{lead['service'] or 'websites and AI automation'}. "
            f"Would you like me to share a quick idea?",
            "AI unavailable; fallback draft created."
        )

    prompt = f"""
Write one concise professional B2B outreach message.

Business:
{lead['business']}

Category:
{lead['category']}

City:
{lead['city']}

Country:
{lead['country']}

Website:
{lead['website']}

Verified opportunity:
{lead['problem']}

Recommended service:
{lead['service']}

Rules:
- Maximum 80 words.
- Natural and human.
- No fake claims.
- No fake urgency.
- No guarantees.
- Do not pretend previous contact.
- Mention only supplied facts.
- Offer a quick useful idea/demo.
"""

    text, error = gemini(prompt)

    return (
        text or "",
        error
    )

# =========================================================
# AI REPLY CLASSIFIER
# =========================================================
def classify_reply(reply):

    if not GEMINI_KEY:

        return {
            "classification":
                "UNKNOWN",
            "summary":
                "AI unavailable because GEMINI_API_KEY is missing.",
            "next_action":
                "Review the reply manually."
        }, "GEMINI_API_KEY missing."

    prompt = f"""
Classify this business reply.

Reply:
{reply}

Return ONLY JSON.

Allowed classifications:
INTERESTED
WANTS PRICE
WANTS CALL
NEEDS INFORMATION
MAYBE LATER
NOT INTERESTED
SPAM
UNKNOWN

JSON:

{{
    "classification": "UNKNOWN",
    "summary": "",
    "next_action": ""
}}
"""

    text, error = gemini(prompt)

    data = parse_json(text)

    if error or not data:

        return {
            "classification":
                "UNKNOWN",
            "summary":
                "AI classification failed.",
            "next_action":
                "Review manually."
        }, error

    allowed = {
        "INTERESTED",
        "WANTS PRICE",
        "WANTS CALL",
        "NEEDS INFORMATION",
        "MAYBE LATER",
        "NOT INTERESTED",
        "SPAM",
        "UNKNOWN"
    }

    classification = str(
        data.get(
            "classification",
            "UNKNOWN"
        )
    ).upper().strip()

    if classification not in allowed:
        classification = "UNKNOWN"

    return {
        "classification":
            classification,
        "summary":
            str(
                data.get(
                    "summary",
                    ""
                )
            )[:500],
        "next_action":
            str(
                data.get(
                    "next_action",
                    ""
                )
            )[:500]
    }, None


def save_reply(
    lead_id,
    reply,
    result
):

    conn = db()

    classification = result[
        "classification"
    ]

    if classification in {
        "INTERESTED",
        "WANTS PRICE",
        "WANTS CALL"
    }:

        status = "INTERESTED"

    elif classification in {
        "SPAM",
        "NOT INTERESTED"
    }:

        status = classification

    else:

        status = "REPLIED"

    conn.execute(
        """
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
        """,
        (
            lead_id,
            reply,
            classification,
            result["summary"],
            result["next_action"],
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )

    conn.execute(
        """
        UPDATE leads
        SET status=?
        WHERE id=?
        """,
        (
            status,
            lead_id
        )
    )

    conn.commit()
    conn.close()

# =========================================================
# DASHBOARD COUNTS
# =========================================================
def counts():

    conn = db()

    data = {
        "total":
            conn.execute(
                "SELECT COUNT(*) FROM leads"
            ).fetchone()[0],

        "qualified":
            conn.execute(
                """
                SELECT COUNT(*)
                FROM leads
                WHERE score >= 70
                """
            ).fetchone()[0],

        "high":
            conn.execute(
                """
                SELECT COUNT(*)
                FROM leads
                WHERE score >= 85
                """
            ).fetchone()[0],

        "contacted":
            conn.execute(
                """
                SELECT COUNT(*)
                FROM leads
                WHERE status='CONTACTED'
                """
            ).fetchone()[0],

        "replies":
            conn.execute(
                "SELECT COUNT(*) FROM replies"
            ).fetchone()[0],

        "interested":
            conn.execute(
                """
                SELECT COUNT(*)
                FROM leads
                WHERE status='INTERESTED'
                """
            ).fetchone()[0],

        "deals":
            conn.execute(
                """
                SELECT COUNT(*)
                FROM leads
                WHERE status='DEAL'
                """
            ).fetchone()[0]
    }

    conn.close()

    return data

# =========================================================
# SESSION
# =========================================================
if "paused" not in st.session_state:
    st.session_state["paused"] = False

# =========================================================
# SIDEBAR
# =========================================================
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
            "Settings"
        ]
    )

    st.divider()

    if st.button(
        "⏸ Pause Automations",
        use_container_width=True
    ):
        st.session_state[
            "paused"
        ] = True

    if st.session_state["paused"]:
        st.warning(
            "Automations paused."
        )

    if st.button(
        "▶ Resume Automations",
        use_container_width=True
    ):
        st.session_state[
            "paused"
        ] = False

    if APP_PASSWORD:

        if st.button(
            "Logout",
            use_container_width=True
        ):
            st.session_state[
                "logged_in"
            ] = False

            st.rerun()

# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":

    st.title(
        "🎯 AI Client Hunter"
    )

    st.caption(
        "Find legitimate public business leads → "
        "AI qualify → personalize → "
        "take over when they are ready to buy."
    )

    c = counts()

    metrics = [
        ("All Leads", c["total"]),
        ("Qualified", c["qualified"]),
        ("High Value", c["high"]),
        ("Contacted", c["contacted"]),
        ("Replies", c["replies"]),
        ("Interested", c["interested"]),
        ("Deals", c["deals"])
    ]

    cols = st.columns(4)

    for i, (
        label,
        value
    ) in enumerate(metrics):

        with cols[i % 4]:

            st.markdown(
                f"""
                <div class="card">
                    <div class="small">
                        {label}
                    </div>
                    <div class="metric">
                        {value}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.info(
        "1️⃣ Find public leads → "
        "2️⃣ Audit → "
        "3️⃣ AI qualify → "
        "4️⃣ Create outreach → "
        "5️⃣ Analyze replies → "
        "6️⃣ Deal alert → "
        "7️⃣ You negotiate and close."
    )

    if not GEMINI_KEY:

        st.warning(
            "GEMINI_API_KEY missing. "
            "Lead search can still work, but "
            "AI features will use safe fallbacks."
        )

# =========================================================
# LEAD FINDER
# =========================================================
elif page == "Lead Finder":

    st.title(
        "🔎 Lead Finder"
    )

    st.caption(
        "Any country • Any city • Any business category"
    )

    c1, c2 = st.columns(2)

    with c1:

        city = st.text_input(
            "City",
            value="Delhi"
        )

        country = st.text_input(
            "Country",
            value="India"
        )

    with c2:

        category = st.text_input(
            "Business category",
            value="restaurant",
            placeholder=(
                "restaurant, hotel, lawyer, "
                "real estate, agency, dentist..."
            )
        )

        limit = st.slider(
            "Number of leads",
            1,
            30,
            10
        )

    min_score = st.slider(
        "Minimum AI score",
        0,
        100,
        40
    )

    if st.button(
        "🚀 Find & Qualify Leads",
        use_container_width=True
    ):

        if not city.strip():
            st.warning(
                "City डालो."
            )
            st.stop()

        if not country.strip():
            st.warning(
                "Country डालो."
            )
            st.stop()

        if not category.strip():
            st.warning(
                "Business category डालो."
            )
            st.stop()

        if st.session_state["paused"]:

            st.error(
                "Automation paused है. "
                "पहले Resume Automations दबाओ."
            )

            st.stop()

        with st.spinner(
            "Public business data खोज रहा हूँ..."
        ):

            businesses, source_error = find_businesses(
                city,
                country,
                category,
                limit
            )

        if not businesses:

            st.error(
                source_error or
                "कोई matching public business नहीं मिला."
            )

            st.info(
                "उदाहरण: Delhi + restaurant, "
                "London + dentist, "
                "Toronto + real estate."
            )

            st.stop()

        progress = st.progress(0)

        saved = 0

        for i, business in enumerate(
            businesses
        ):

            audit = audit_website(
                business.get(
                    "website",
                    ""
                )
            )

            qualification, _ = qualify_lead(
                business["business"],
                business["category"],
                business["city"],
                business["country"],
                business.get(
                    "website",
                    ""
                ),
                audit
            )

            if qualification[
                "score"
            ] >= min_score:

                save_lead(
                    {
                        **business,
                        "problem":
                            qualification[
                                "problem"
                            ],
                        "service":
                            qualification[
                                "service"
                            ],
                        "score":
                            qualification[
                                "score"
                            ],
                        "reason":
                            qualification[
                                "reason"
                            ],
                        "status":
                            (
                                "QUALIFIED"
                                if qualification[
                                    "score"
                                ] >= 70
                                else "NEW"
                            )
                    }
                )

                saved += 1

            progress.progress(
                (i + 1) /
                len(businesses)
            )

        st.success(
            f"{saved} leads database में save हो गईं."
        )

        if saved == 0:

            st.info(
                "Minimum AI score कम करके "
                "फिर search करो."
            )

# =========================================================
# LEADS
# =========================================================
elif page == "Leads":

    st.title(
        "📋 Lead Database"
    )

    rows = get_leads()

    if not rows:

        st.info(
            "अभी कोई lead नहीं है. "
            "Lead Finder चलाओ."
        )

    for row in rows:

        with st.expander(
            f"{row['business']} • "
            f"Score {row['score']} • "
            f"{row['status']}"
        ):

            st.write(
                f"**Category:** "
                f"{row['category']}"
            )

            st.write(
                f"**Location:** "
                f"{row['city']}, "
                f"{row['country']}"
            )

            st.write(
                f"**Website:** "
                f"{row['website'] or 'Not available'}"
            )

            st.write(
                f"**Public contact:** "
                f"{row['contact'] or 'Not available'}"
            )

            st.write(
                f"**Opportunity:** "
                f"{row['problem'] or 'Not available'}"
            )

            st.write(
                f"**Recommended service:** "
                f"{row['service'] or 'Not available'}"
            )

            st.write(
                f"**AI reason:** "
                f"{row['reason'] or 'Not available'}"
            )

            if row["source"]:

                st.link_button(
                    "Open source",
                    row["source"]
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
                row["status"]
                if row["status"] in statuses
                else "NEW"
            )

            new_status = st.selectbox(
                "Status",
                statuses,
                index=statuses.index(
                    current
                ),
                key=f"status_{row['id']}"
            )

            if st.button(
                "Save Status",
                key=f"save_{row['id']}"
            ):

                update_status(
                    row["id"],
                    new_status
                )

                st.rerun()

# =========================================================
# OUTREACH
# =========================================================
elif page == "Outreach":

    st.title(
        "✉️ AI Outreach"
    )

    rows = get_leads()

    if not rows:

        st.info(
            "पहले Lead Finder चलाओ."
        )

    else:

        labels = {
            f"{r['business']} — Score {r['score']}":
            r
            for r in rows
        }

        selected = st.selectbox(
            "Lead चुनें",
            list(labels.keys())
        )

        row = labels[selected]

        lead = dict(row)

        channel = st.selectbox(
            "Channel",
            [
                "Email",
                "Manual WhatsApp",
                "Manual LinkedIn"
            ]
        )

        if st.button(
            "✨ Generate Personalized Message",
            use_container_width=True
        ):

            with st.spinner(
                "Personalized message बना रहा हूँ..."
            ):

                message, error = create_message(
                    lead
                )

            if error:
                st.info(error)

            st.text_area(
                "Ready-to-send message",
                message,
                height=220
            )

            save_message(
                row["id"],
                channel,
                message
            )

            st.warning(
                "MANUAL ACTION REQUIRED — "
                "इस version में automatic "
                "WhatsApp/LinkedIn/email sending "
                "enabled नहीं है."
            )

# =========================================================
# AI INBOX
# =========================================================
elif page == "AI Inbox":

    st.title(
        "🤖 AI Inbox"
    )

    rows = get_leads()

    if not rows:

        st.info(
            "पहले leads बनाओ."
        )

    else:

        labels = {
            f"{r['business']} — {r['status']}":
            r
            for r in rows
        }

        selected = st.selectbox(
            "Business चुनें",
            list(labels.keys())
        )

        row = labels[selected]

        reply = st.text_area(
            "Client का reply यहाँ paste करें",
            height=180,
            placeholder=(
                "Yes, I would like to know more..."
            )
        )

        if st.button(
            "Analyze Reply",
            use_container_width=True
        ):

            if not reply.strip():

                st.warning(
                    "Client reply डालो."
                )

                st.stop()

            with st.spinner(
                "AI reply analyze कर रहा है..."
            ):

                result, error = classify_reply(
                    reply
                )

            save_reply(
                row["id"],
                reply.strip(),
                result
            )

            if error:
                st.info(error)

            classification = result[
                "classification"
            ]

            if classification in {
                "INTERESTED",
                "WANTS PRICE",
                "WANTS CALL"
            }:

                st.success(
                    f"🔥 DEAL ALERT — "
                    f"{classification}"
                )

                st.warning(
                    "अब automated sales action रोकें. "
                    "Pricing, call, negotiation और payment "
                    "आप manually handle करें."
                )

            else:

                st.info(
                    f"Classification: "
                    f"{classification}"
                )

            st.write(
                f"**Summary:** "
                f"{result['summary']}"
            )

            st.write(
                f"**Next action:** "
                f"{result['next_action']}"
            )

# =========================================================
# DEAL ALERTS
# =========================================================
elif page == "Deal Alerts":

    st.title(
        "🔥 Deal Alerts"
    )

    conn = db()

    rows = conn.execute(
        """
        SELECT
            l.*,
            r.reply,
            r.classification,
            r.summary,
            r.next_action
        FROM leads l
        JOIN replies r
        ON r.id = (
            SELECT MAX(r2.id)
            FROM replies r2
            WHERE r2.lead_id = l.id
        )
        WHERE r.classification IN
        (
            'INTERESTED',
            'WANTS PRICE',
            'WANTS CALL'
        )
        ORDER BY r.id DESC
        """
    ).fetchall()

    conn.close()

    if not rows:

        st.info(
            "अभी कोई strong buying-intent reply नहीं है."
        )

    for row in rows:

        st.markdown(
            f"""
            <div class="card">
                <h3>
                    🔥 DEAL ALERT — {row['business']}
                </h3>

                <p>
                    <b>Classification:</b>
                    {row['classification']}
                </p>

                <p>
                    <b>Last message:</b>
                    {row['reply']}
                </p>

                <p>
                    <b>AI summary:</b>
                    {row['summary']}
                </p>

                <p>
                    <b>Next action:</b>
                    {row['next_action']}
                </p>

                <p>
                    <b>Contact:</b>
                    {row['contact'] or 'Not available'}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if row["website"]:

            st.link_button(
                "Open website",
                clean_url(
                    row["website"]
                )
            )

# =========================================================
# ANALYTICS
# =========================================================
elif page == "Analytics":

    st.title(
        "📊 Analytics"
    )

    conn = db()

    total = conn.execute(
        "SELECT COUNT(*) FROM leads"
    ).fetchone()[0]

    qualified = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE score >= 70
        """
    ).fetchone()[0]

    contacted = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE status='CONTACTED'
        """
    ).fetchone()[0]

    replies = conn.execute(
        "SELECT COUNT(*) FROM replies"
    ).fetchone()[0]

    interested = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE status='INTERESTED'
        """
    ).fetchone()[0]

    deals = conn.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE status='DEAL'
        """
    ).fetchone()[0]

    messages = conn.execute(
        """
        SELECT COUNT(*)
        FROM messages
        """
    ).fetchone()[0]

    conn.close()

    metrics = [
        ("Leads", total),
        ("Qualified", qualified),
        ("Messages", messages),
        ("Replies", replies),
        ("Interested", interested),
        ("Deals", deals)
    ]

    cols = st.columns(3)

    for i, (
        label,
        value
    ) in enumerate(metrics):

        with cols[i % 3]:

            st.metric(
                label,
                value
            )

    conversion = (
        deals / total * 100
        if total
        else 0
    )

    st.metric(
        "Lead → Deal conversion",
        f"{conversion:.1f}%"
    )

# =========================================================
# SETTINGS
# =========================================================
elif page == "Settings":

    st.title(
        "⚙️ Settings"
    )

    st.subheader(
        "🔐 Security"
    )

    if APP_PASSWORD:

        st.success(
            "App password protection enabled."
        )

    else:

        st.warning(
            "APP_PASSWORD configured नहीं है."
        )

    st.subheader(
        "🤖 AI"
    )

    if GEMINI_KEY:

        st.success(
            "Gemini API configured."
        )

    else:

        st.error(
            "GEMINI_API_KEY configured नहीं है."
        )

    st.write(
        f"Model: `{GEMINI_MODEL}`"
    )

    st.subheader(
        "🌎 Lead Search"
    )

    st.write(
        "Any country + any city + "
        "any business category/custom category."
    )

    st.subheader(
        "📨 Automation"
    )

    st.warning(
        "Automatic messaging केवल officially "
        "authorised APIs/integrations के साथ "
        "implement किया जाना चाहिए."
    )

    st.write(
        "Current messaging mode: "
        "MANUAL ACTION REQUIRED"
    )

    st.subheader(
        "🛡️ Safety"
    )

    st.write(
        "No CAPTCHA bypass, private-data scraping, "
        "fake accounts, anti-spam bypass, "
        "or rate-limit bypass."
    )

    st.subheader(
        "🗑️ Data"
    )

    if st.button(
        "Clear Local Database"
    ):

        st.session_state[
            "confirm_delete"
        ] = True

    if st.session_state.get(
        "confirm_delete"
    ):

        st.error(
            "क्या सच में पूरा local database delete करना है?"
        )

        if st.button(
            "YES — DELETE DATABASE",
            type="primary"
        ):

            conn = db()

            conn.execute(
                "DELETE FROM leads"
            )

            conn.execute(
                "DELETE FROM messages"
            )

            conn.execute(
                "DELETE FROM replies"
            )

            conn.commit()
            conn.close()

            st.session_state[
                "confirm_delete"
            ] = False

            st.success(
                "Database cleared."
            )

            st.rerun()
