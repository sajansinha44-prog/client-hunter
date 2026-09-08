You are working directly inside my GitHub repository:

Repository: sajansinha44-prog/client-hunter
Branch: main

I want you to FIX and COMPLETE this project directly in the repository.

IMPORTANT:
- Do NOT just explain what to do.
- Do NOT give me code in chat.
- Inspect the existing files first.
- Make the required changes directly in the repository.
- Preserve anything useful from the existing project.
- Do not create duplicate/merged app.py code.
- Replace broken code cleanly where necessary.
- Make sure the final Python files pass syntax checks.

PROJECT:
Build a premium, mobile-friendly AI Client Hunter web app using Streamlit.

CORE FEATURES:
1. Secure app login using APP_PASSWORD from Streamlit Secrets.
2. Premium dark, clean, responsive dashboard.
3. Dashboard metrics:
   - New Leads
   - Qualified Leads
   - High Value Leads
   - Contacted
   - Replies
   - Interested
   - Calls
   - Deals
4. Lead Finder:
   - Country
   - City
   - Business category
   - Number of leads
   - Minimum lead score
5. Find legitimate public business information using permitted/public sources only.
6. Lead database using SQLite:
   - Business name
   - Website
   - City
   - Country
   - Category
   - Public contact information when available
   - Source URL
   - Detected problem
   - Recommended service
   - Lead score
   - Status
7. Website audit:
   - Check publicly accessible websites.
   - Detect only issues that can actually be verified.
   - Do not invent problems.
8. Gemini AI integration through the official Gemini API:
   - GEMINI_API_KEY from Streamlit Secrets
   - GEMINI_MODEL optional
   - Never expose API keys in frontend or source code.
9. AI lead qualification:
   - Is this a genuine business?
   - Website quality
   - Potential need
   - Recommended service
   - Value score 0–100
   - Short reason
10. AI outreach generator:
   - Generate short personalized professional messages.
   - Mention a real business detail when available.
   - No fake claims.
   - No spam.
11. AI Inbox:
   Classify replies as:
   - INTERESTED
   - WANTS PRICE
   - WANTS CALL
   - NEEDS INFORMATION
   - MAYBE LATER
   - NOT INTERESTED
   - SPAM
   - UNKNOWN
12. Deal Alert:
   When a reply indicates strong buying intent, show:
   - DEAL ALERT
   - Business
   - Last message
   - AI summary
   - Suggested next action
   - Contact/source link
   Then stop automated sales actions and let the owner handle negotiation, pricing, calls and payment.
13. Outreach automation:
   - NEVER bypass CAPTCHA, login protections, rate limits, platform restrictions or anti-spam systems.
   - NEVER create fake accounts.
   - NEVER scrape private information.
   - Only auto-send through officially authorized APIs/integrations.
   - If automatic sending is unavailable, show MANUAL ACTION REQUIRED with a ready-to-send message.
14. Analytics:
   - Leads found
   - Qualified
   - Messages
   - Replies
   - Interested
   - Calls
   - Deals
   - Conversion rate
15. Settings:
   - Security
   - AI
   - Lead filters
   - Automation
   - Notifications
   - Data management
   - Pause all automations
   - Logout
16. Error handling:
   - User-friendly errors.
   - Detailed technical errors only in logs.
17. Performance:
   - Avoid unnecessary dependencies.
   - Use pagination/caching where useful.
   - Keep the app lightweight and fast.
18. Security:
   - Server-side secrets.
   - Input validation.
   - Safe database queries.
   - No hard-coded API keys.
   - No hidden admin/backdoor accounts.
   - Do not claim the app is 100% hack-proof.

FILES:
- Inspect the existing app.py and requirements.txt.
- Clean up broken/duplicate code.
- Update requirements.txt to contain only required packages.
- If README is missing, optionally create a short setup README.
- Keep the project simple enough for Streamlit deployment.

STREAMLIT SECRETS EXPECTED:
APP_PASSWORD
GEMINI_API_KEY
GEMINI_MODEL (optional)

IMPORTANT FINAL CHECK:
Before committing:
1. Run Python syntax validation on app.py.
2. Check imports.
3. Check database initialization.
4. Check that missing API keys show a clear message instead of crashing.
5. Check login flow.
6. Check all Streamlit pages/buttons for obvious runtime errors.
7. Do not leave partially pasted code.
8. Do not duplicate functions or imports unnecessarily.

Then commit all fixes directly to the main branch with a clear commit message:

"Fix Client Hunter app and complete AI lead workflow"

Do the work directly. Do not merely describe the solution.
