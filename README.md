# WR JobTracker

Local-first, AI-driven Applicant Tracking System (ATS) that synchronizes with your email inbox over IMAP, extracts structured job application metadata using local or cloud LLMs, and organizes applications across an automated state machine.

---

## System Architecture

### High-Level Ingestion and Processing Pipeline

```
+-------------------------------------------------------------------------+
|                              EMAIL INBOX                                |
|           (Gmail, Outlook, Custom IMAP via TLS / SSL Port 993)          |
+-------------------------------------------------------------------------+
                                     |
                                     | [IMAP Fetcher Worker]
                                     v
+-------------------------------------------------------------------------+
|                       PRE-PROCESSING & FILTERING                        |
|  - MIME Header Decoding                                                 |
|  - HTML to Plaintext Conversion                                         |
|  - Negative Filter: Newsletters, Digests, Job Alerts (LinkedIn/Indeed)  |
|  - Positive Keyword Matcher (Candidate, Interview, Offer, Status)      |
|  - Message-ID / Subject Deduplication Check                             |
+-------------------------------------------------------------------------+
                                     |
                                     | [Candidate Email Body]
                                     v
+-------------------------------------------------------------------------+
|                         DUAL AI EXTRACTION ENGINE                       |
|                                                                         |
|  [Provider A: Local Ollama]               [Provider B: Cloud API]       |
|  - Model: qwen3:8b / qwen2.5:3b          - Endpoints: GitHub Models,    |
|  - Endpoint: http://localhost:11434/api/chat          OpenAI, Groq,     |
|  - Strict JSON Schema constraint                      Mistral, etc.     |
|  - 100% Offline & Private                - JSON Object response_format  |
+-------------------------------------------------------------------------+
                                     |
                                     | [Structured JSON Output]
                                     v
+-------------------------------------------------------------------------+
|                        APPLICATION MATCHMAKER                           |
|  - Strategy 1: Thread ID & References Header Match                      |
|  - Strategy 2: Job Requisition / Reference Code Match                   |
|  - Strategy 3: Normalized Company Slug + Role Jaccard Similarity        |
|                                                                         |
|  [Existing Application Matched]            [No Previous Match Found]    |
|  -> Update Card Stage & Action Items       -> Create New Application    |
|  -> Append Event to Audit Timeline         -> Create Initial Event      |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         SQLITE DATABASE ENGINE                          |
|  - applications (id, company, role, slug, status, deadline, dates)      |
|  - email_events (id, app_id, message_id, thread_id, raw_summary)       |
|  - email_accounts (id, email, imap_server, password_encrypted, status)  |
|  - app_settings (key, value)                                            |
+-------------------------------------------------------------------------+
                                     ^
                                     | REST API (FastAPI)
                                     v
+-------------------------------------------------------------------------+
|                            REACT FRONTEND                               |
|  - Kanban Board (Applied, Review, Assessment/Interview, Offer, Reject)  |
|  - Real-time Sync Progress & Polling Tracker                            |
|  - Company Intelligence (Historical Applications, Response Rates)       |
|  - Dual AI Model Switcher & Live Handshake Verification Modal           |
|  - Light / Dark Architectural Surface Tokens                            |
+-------------------------------------------------------------------------+
```

---

## Technical Specifications

### Backend Stack
- **Framework**: FastAPI (Python 3.10+)
- **Server**: Uvicorn ASGI
- **Database**: SQLite3 with indexing on company slug, job reference ID, and email thread IDs
- **Validation**: Pydantic v2
- **Protocol**: IMAP4 over SSL

### Frontend Stack
- **Library**: React 19
- **Build Tool**: Vite 8
- **Styling**: Pure CSS Design System (Custom variables, zero utility overhead)
- **Icons**: Lucide React

---

## Requirements

### Software Prerequisites
1. **Python**: Version `3.10` or higher
2. **Node.js**: Version `18.0.0` or higher with `npm`
3. **Git**: Installed and available in PATH

### AI Inference (Select at least one):
- **Option 1 (Local GPU / CPU - Recommended)**:
  - [Ollama](https://ollama.com/) running locally (`http://localhost:11434`).
  - Model: `qwen3:8b`, `qwen2.5:3b`, `llama3.1:8b`, or `mistral`.
- **Option 2 (Cloud API)**:
  - API Token from any OpenAI-compatible provider:
    - GitHub Models Personal Access Token (Free tier available)
    - OpenAI API Key
    - Groq Cloud API Key
    - Mistral AI API Key
    - OpenRouter API Key

### Email Provider (For Live Sync):
- Gmail, Outlook, or custom IMAP provider.
- For Gmail: A **16-character Google App Password** generated under Google Account Security (Requires 2-Step Verification enabled).

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/walid2004/WR-JobApplicant.git
cd WR-JobApplicant
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Start the FastAPI backend server:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
The API documentation and Swagger UI will be available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
The frontend interface will be available at `http://localhost:5173`.

---

## Configuration

### Connecting Email Inbox (IMAP)
1. Open the application at `http://localhost:5173`.
2. Click **Connect Inbox** in the upper right.
3. Provide your email credentials:
   - **Email Address**: Your email (e.g., `user@gmail.com`)
   - **IMAP Server**: `imap.gmail.com` (Default for Gmail)
   - **Password**: Your 16-character App Password (e.g., `abcd efgh ijkl mnop`)
4. Click **Test Connection** to verify handshake, then click **Connect Account**.

### Configuring the AI Engine
1. Click the **Settings** icon in the header.
2. Select your AI provider:
   - **Local GPU (Ollama)**: Select any downloaded Ollama model from the dropdown.
   - **Cloud API / GitHub Models**: Select a preset (GitHub Models, OpenAI, Groq, Mistral, OpenRouter) or enter a custom endpoint, paste your API token, and click **Test Connection**.
3. Set your preferred **Scan Depth** (number of recent emails to inspect per sync) and **Auto-Sync Interval**.

---

## Data Schema & Deduplication Logic

### Structured JSON Extraction Schema
Every candidate email is parsed into this schema:
```json
{
  "is_job_related": true,
  "company_name": "Spotify",
  "job_title": "Frontend Engineer",
  "job_reference_id": "REQ-10492",
  "status": "INTERVIEW_INVITED",
  "summary": "Invitation to 45-minute technical screen next Tuesday.",
  "action_required": "Reply with availability for technical screen.",
  "next_step_deadline": "2026-08-25T00:00:00Z"
}
```

### Application Matching Rules
When a new email is processed, the matchmaker resolves the target application card using three sequential strategies:
1. **Thread ID Match**: Resolves against `In-Reply-To` and `References` RFC822 headers.
2. **Requisition ID Match**: Exact match on extracted job requisition or reference code.
3. **Company Slug + Role Match**: Normalizes company name into a canonical slug (e.g. `Bayerische Motoren Werke` -> `bmw`) and calculates Jaccard token overlap between job titles to differentiate separate roles at the same company (e.g., `Frontend Engineer` vs `Backend Engineer`).

---

## API Endpoints

### Applications
- `GET /api/applications` - Retrieve all tracked application cards with latest email counts and logo URLs.
- `GET /api/applications/{id}` - Retrieve detailed card with complete email event history and company intelligence.
- `POST /api/applications` - Manually create an application card.
- `PATCH /api/applications/{id}` - Update application card fields (status, title, notes, deadlines).
- `DELETE /api/applications/{id}` - Delete application card and associated event history.

### Email & Sync
- `POST /api/email/test-connection` - Test IMAP credentials without persisting.
- `POST /api/email/connect` - Validate and persist IMAP credentials in local SQLite database.
- `POST /api/email/disconnect` - Clear active email account credentials.
- `POST /api/sync-start` - Trigger asynchronous inbox synchronization worker.
- `GET /api/sync-progress` - Poll current synchronization state and metrics.
- `POST /api/process-email` - Process a single raw email payload through the parser.

### Models & Settings
- `GET /api/models` - List local Ollama models and active extraction model.
- `POST /api/models/test-custom-api` - Test endpoint connectivity and response format for cloud AI models.
- `GET /api/settings` - Retrieve system configuration (auto-sync, scan depth, active AI provider).
- `POST /api/settings` - Update system configuration.
- `GET /api/stats` - Retrieve dashboard analytics and response rate metrics.

---

## Security and Privacy Model

- **Local Storage**: All credentials, tokens, application records, and email event summaries are stored locally in `backend/job_tracker.db`.
- **Zero External Telemetry**: The application communicates only with your configured IMAP server and selected AI provider.
- **Git Ignore**: Database files (`*.db`), log files, node modules, and environment configurations are excluded from version control.

---

## License
MIT License.
