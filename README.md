# 💼 WR JobTracker

> **Privacy-First, AI-Powered Job Application Tracking System.**  
> Automatically parses, organizes, and tracks your job applications directly from your inbox using **Local GPU Models (Ollama)** or **Cloud AI APIs** (GitHub Models, OpenAI, Groq, Mistral).

---

## ✨ Features

- 📬 **Live Gmail / IMAP Inbox Sync**: Automatically scans and monitors candidate confirmation emails, coding assessments, interview invitations, offers, and rejections.
- 🧠 **Dual AI Extraction Engine**:
  - **Local Offline GPU Mode**: Powered by Ollama (`qwen2.5:3b`, `qwen3:8b`, etc.) running 100% locally on your machine with zero API costs.
  - **Cloud / OpenAI-Compatible Mode**: 1-click presets for **GitHub Models**, **OpenAI ChatGPT**, **Groq**, **Mistral AI**, and **OpenRouter** with live connection handshake testing.
- 🎯 **ATS Entity & Stage Extraction**: Automatically extracts company names, job titles, requisition IDs, deadline dates, and action items with structured JSON schema validation.
- 📊 **Company Intelligence & Analytics**:
  - Track response rates, average response times, and historic application logs across individual companies.
  - Kanban board with stage management (`Applied`, `Under Review`, `Interviews & Assessments`, `Offers`, `Rejected`).
- 🎨 **Disciplined, Human-Crafted SaaS UI**:
  - Built with clean geometric typography, high density, and subtle micro-states.
  - Full **Light Mode (Default)** and **Dark Mode** support.
  - Instant `/` keyboard shortcut for search.
  - Live auto-sync countdown timer.

---

## 🛠️ Architecture

```
WR-JobTracker/
├── backend/                  # FastAPI Application
│   ├── database.py           # SQLite persistence layer
│   ├── email_fetcher.py      # IMAP SSL client & email synchronizer
│   ├── extractor.py          # Dual AI parser (Ollama + Cloud API)
│   ├── matchmaker.py         # Application correlation & deduplication
│   ├── models.py             # Pydantic data schemas
│   ├── main.py               # REST API endpoints & WebSockets/polling
│   └── requirements.txt      # Python dependencies
│
└── frontend/                 # React 19 + Vite Frontend
    ├── src/
    │   ├── App.jsx           # Main Dashboard & Kanban Board
    │   ├── index.css         # High-density SaaS design system
    │   └── main.jsx          # React DOM root & ErrorBoundary
    ├── index.html
    └── package.json
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`
- *(Optional for Local AI)*: [Ollama](https://ollama.com/) with `qwen2.5:3b` or `qwen3:8b` (`ollama run qwen2.5:3b`)

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API will be available at `http://127.0.0.1:8000`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend dashboard will be available at `http://localhost:5173`.

---

## 🔒 Security & Privacy

- **Zero Third-Party Data Leakage**: In local mode, email contents are processed solely inside your local GPU/RAM.
- **Local Credentials**: IMAP App Passwords and API tokens are stored strictly in your local SQLite database on your machine and are never transmitted to external telemetry.
- **Protected Secrets**: SQLite databases and logs are strictly ignored by `.gitignore`.

---

## 📄 License
MIT License. Created by [walid2004](https://github.com/walid2004).
