import sqlite3
import os
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "job_tracker.db")

KNOWN_DOMAINS = {
    "bmw": "bmwgroup.com",
    "google": "google.com",
    "siemens": "siemens.com",
    "mercor": "mercor.com",
    "mirker": "mirker.com",
    "turing": "turing.com",
    "indeed": "indeed.com",
    "knorr-bremse": "knorr-bremse.com",
    "bsh": "bsh-group.com",
    "bsh home appliances group": "bsh-group.com",
    "sercanto": "sercanto.com",
    "praml": "praml.de",
    "microsoft": "microsoft.com",
    "amazon": "amazon.com",
    "apple": "apple.com",
    "meta": "meta.com",
    "stripe": "stripe.com",
    "spotify": "spotify.com",
    "netflix": "netflix.com"
}

def extract_domain_from_email(email_str: Optional[str]) -> Optional[str]:
    if not email_str:
        return None
    match = re.search(r'@([a-zA-Z0-9.\-_]+)', email_str)
    if match:
        domain = match.group(1).lower().strip()
        if domain not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"):
            return domain
    return None

def get_logo_url(company_name: str, company_slug: str, domain: Optional[str] = None) -> str:
    clean_domain = domain
    if not clean_domain:
        clean_domain = KNOWN_DOMAINS.get(company_slug) or KNOWN_DOMAINS.get(company_name.lower().strip())
    if not clean_domain:
        clean_domain = f"{company_slug}.com"
    return f"https://www.google.com/s2/favicons?domain={clean_domain}&sz=128"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        company_slug TEXT NOT NULL,
        job_title TEXT NOT NULL,
        job_reference_id TEXT,
        company_domain TEXT,
        status TEXT NOT NULL DEFAULT 'APPLIED',
        action_required TEXT,
        next_step_deadline TEXT,
        interview_date TEXT,
        location TEXT,
        salary TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        email_message_id TEXT,
        email_thread_id TEXT,
        sender TEXT NOT NULL,
        subject TEXT NOT NULL,
        received_at TEXT NOT NULL,
        summary TEXT NOT NULL,
        extracted_status TEXT NOT NULL,
        email_deep_link TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_address TEXT NOT NULL UNIQUE,
        imap_server TEXT NOT NULL,
        password TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'CONNECTED',
        last_error TEXT,
        last_synced_at TEXT,
        total_synced_cards INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_slug ON applications(company_slug);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_ref_id ON applications(job_reference_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_thread ON email_events(email_thread_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_app_id ON email_events(application_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_msg_id ON email_events(email_message_id);")

    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN company_domain TEXT;")
    except Exception:
        pass

    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def is_email_already_recorded(email_message_id: Optional[str], subject: str, application_id: Optional[int] = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    if email_message_id and len(email_message_id.strip()) > 3:
        cursor.execute("SELECT id FROM email_events WHERE email_message_id = ? LIMIT 1", (email_message_id.strip(),))
        if cursor.fetchone():
            conn.close()
            return True
            
    if application_id and subject:
        cursor.execute("SELECT id FROM email_events WHERE application_id = ? AND subject = ? LIMIT 1", (application_id, subject.strip()))
        if cursor.fetchone():
            conn.close()
            return True

    conn.close()
    return False

def get_active_email_account() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_accounts WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["has_password"] = bool(data.get("password"))
    data["password_masked"] = "••••••••••••••••" if data["has_password"] else ""
    return data

def save_email_account(email_address: str, imap_server: str, password: str, status: str = "CONNECTED", error: Optional[str] = None) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE email_accounts SET is_active = 0")
    cursor.execute("""
        INSERT INTO email_accounts (email_address, imap_server, password, status, last_error, last_synced_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(email_address) DO UPDATE SET
            imap_server = excluded.imap_server,
            password = excluded.password,
            status = excluded.status,
            last_error = excluded.last_error,
            is_active = 1
    """, (email_address, imap_server, password, status, error, now))
    account_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return account_id

def update_email_account_status(email_address: str, status: str, last_error: Optional[str] = None, new_cards_count: int = 0):
    now = datetime.utcnow().isoformat() + "Z"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE email_accounts 
        SET status = ?, last_error = ?, last_synced_at = ?, total_synced_cards = total_synced_cards + ?
        WHERE email_address = ?
    """, (status, last_error, now, new_cards_count, email_address))
    conn.commit()
    conn.close()

def disconnect_email_account() -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_accounts")
    conn.commit()
    conn.close()
    return True

def get_company_insights(company_slug: str, current_app_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.job_title, a.status, a.created_at, a.updated_at, COUNT(e.id) as email_count
        FROM applications a
        LEFT JOIN email_events e ON a.id = e.application_id
        WHERE a.company_slug = ?
        GROUP BY a.id
        ORDER BY a.created_at DESC
    """, (company_slug,))
    apps = [dict(r) for r in cursor.fetchall()]

    total_apps = len(apps)
    other_apps = [a for a in apps if a["id"] != current_app_id]

    responded_count = sum(1 for a in apps if a["status"] != "APPLIED")
    offers_count = sum(1 for a in apps if a["status"] == "OFFER_RECEIVED")
    rejections_count = sum(1 for a in apps if a["status"] in ("REJECTED", "ARCHIVED"))
    interviews_count = sum(1 for a in apps if a["status"] in ("INTERVIEW_INVITED", "ASSESSMENT_INVITED", "ACTION_REQUIRED"))

    company_response_rate = round((responded_count / total_apps * 100), 1) if total_apps > 0 else 0.0

    days_list = []
    for a in apps:
        if a["status"] != "APPLIED" and a.get("created_at") and a.get("updated_at"):
            try:
                t0 = datetime.fromisoformat(a["created_at"].replace("Z", ""))
                t1 = datetime.fromisoformat(a["updated_at"].replace("Z", ""))
                diff = (t1 - t0).total_seconds() / 86400.0
                if diff >= 0:
                    days_list.append(diff)
            except Exception:
                pass
    
    avg_turnaround_days = round(sum(days_list) / len(days_list), 1) if days_list else None

    conn.close()

    return {
        "company_slug": company_slug,
        "total_applications_to_company": total_apps,
        "active_roles_count": sum(1 for a in apps if a["status"] not in ("REJECTED", "ARCHIVED")),
        "company_response_rate_percent": company_response_rate,
        "interviews_count": interviews_count,
        "offers_count": offers_count,
        "rejections_count": rejections_count,
        "avg_turnaround_days": avg_turnaround_days,
        "other_applications": other_apps
    }

def get_all_applications() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, COUNT(DISTINCT e.id) as email_count, MAX(e.received_at) as last_email_date
        FROM applications a
        LEFT JOIN email_events e ON a.id = e.application_id
        GROUP BY a.id
        ORDER BY a.updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        d = dict(row)
        d["logo_url"] = get_logo_url(d["company_name"], d["company_slug"], d.get("company_domain"))
        results.append(d)
    return results

def get_application_by_id(app_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    app_data = dict(row)
    app_data["logo_url"] = get_logo_url(app_data["company_name"], app_data["company_slug"], app_data.get("company_domain"))
    
    cursor.execute("SELECT * FROM email_events WHERE application_id = ? ORDER BY received_at DESC", (app_id,))
    events = cursor.fetchall()
    app_data["timeline"] = [dict(e) for e in events]
    conn.close()

    app_data["company_insights"] = get_company_insights(app_data["company_slug"], app_id)

    return app_data

def create_application(
    company_name: str,
    company_slug: str,
    job_title: str,
    job_reference_id: Optional[str] = None,
    company_domain: Optional[str] = None,
    status: str = "APPLIED",
    action_required: Optional[str] = None,
    next_step_deadline: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications (
            company_name, company_slug, job_title, job_reference_id, company_domain,
            status, action_required, next_step_deadline, location, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_name, company_slug, job_title, job_reference_id, company_domain,
        status, action_required, next_step_deadline, location, notes,
        now, now
    ))
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return app_id

def update_application(app_id: int, **fields) -> bool:
    if not fields:
        return False
    fields["updated_at"] = datetime.utcnow().isoformat() + "Z"
    set_clauses = [f"{k} = ?" for k in fields.keys()]
    values = list(fields.values()) + [app_id]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE applications SET {', '.join(set_clauses)} WHERE id = ?", values)
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def delete_application(app_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    cursor.execute("DELETE FROM email_events WHERE application_id = ?", (app_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def add_email_event(
    application_id: int,
    sender: str,
    subject: str,
    summary: str,
    extracted_status: str,
    email_message_id: Optional[str] = None,
    email_thread_id: Optional[str] = None,
    email_deep_link: Optional[str] = None,
    received_at: Optional[str] = None
) -> int:
    if is_email_already_recorded(email_message_id, subject, application_id):
        return 0

    now = datetime.utcnow().isoformat() + "Z"
    received_time = received_at or now
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO email_events (
            application_id, email_message_id, email_thread_id, sender,
            subject, received_at, summary, extracted_status, email_deep_link, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        application_id, email_message_id, email_thread_id, sender,
        subject, received_time, summary, extracted_status, email_deep_link, now
    ))
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return event_id

def find_app_by_thread_id(thread_id: str) -> Optional[int]:
    if not thread_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT application_id FROM email_events 
        WHERE email_thread_id = ? 
        ORDER BY id DESC LIMIT 1
    """, (thread_id,))
    row = cursor.fetchone()
    conn.close()
    return row["application_id"] if row else None

def find_app_by_reference_id(job_ref_id: str) -> Optional[int]:
    if not job_ref_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM applications 
        WHERE job_reference_id = ? 
        ORDER BY id DESC LIMIT 1
    """, (job_ref_id,))
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None
