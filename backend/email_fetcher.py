import imaplib
import email
from email.header import decode_header
from html.parser import HTMLParser
import re
import datetime
import threading
import urllib.parse
import time
from typing import List, Dict, Any, Optional
import extractor
import matchmaker
from models import RawEmailInput, ProcessEmailResponse
import database as db
import logging

logger = logging.getLogger(__name__)

NEWSLETTER_SENDERS = [
    "jobalerts-noreply@linkedin.com",
    "newsletters-noreply@linkedin.com",
    "invitations@linkedin.com",
    "messages-noreply@linkedin.com",
    "jobs-noreply@linkedin.com",
    "alert@indeed.com",
    "jobalerts@indeed.com",
    "noreply@glassdoor.com",
    "updates@stepstone.de",
    "newsletter@",
    "news@",
    "promotions@",
    "marketing@",
    "no-reply@bebee.com",
    "notifications@bebee.com",
    "job-alerts@",
    "dailyalerts@"
]

NEWSLETTER_SUBJECT_KEYWORDS = [
    "job alert",
    "jobs you may be interested in",
    "recommended jobs",
    "new jobs in",
    "stellenangebote für",
    "stellenangebote matching",
    "top job picks",
    "jobs matching your alert",
    "see who's hiring",
    "jobs for you",
    "neue jobs für",
    "haben sie interesse an",
    "offene stellen für",
    "suggested jobs",
    "weekly job digest",
    "daily job digest",
    "top picks for you"
]

def generate_gmail_deep_link(message_id: str, subject: str, sender: str) -> str:
    clean_id = re.sub(r'[<>]', '', (message_id or '')).strip()
    if clean_id and len(clean_id) > 5 and not clean_id.startswith("msg_"):
        encoded_id = urllib.parse.quote(clean_id)
        return f"https://mail.google.com/mail/u/0/#search/rfc822msgid%3A{encoded_id}"
    clean_sub = re.sub(r'[\r\n]', ' ', subject or '').strip()
    encoded_query = urllib.parse.quote(f'"{clean_sub}"')
    return f"https://mail.google.com/mail/u/0/#search/{encoded_query}"

def is_job_alert_or_newsletter(sender: str, subject: str, body: str) -> bool:
    s_lower = sender.lower()
    sub_lower = subject.lower()

    for bad_sender in NEWSLETTER_SENDERS:
        if bad_sender in s_lower:
            return True

    for bad_sub in NEWSLETTER_SUBJECT_KEYWORDS:
        if bad_sub in sub_lower:
            return True

    body_snippet = body[:1000].lower()
    if "you have 1 new alert" in body_snippet or ("unsubscribe from job alerts" in body_snippet and "thank you for applying" not in body_snippet):
        if "recommended jobs" in body_snippet or "jobs matching your preferences" in body_snippet:
            return True

    return False

# Global Sync Progress State
class SyncTracker:
    def __init__(self):
        self.is_syncing = False
        self.current_step = "Idle"
        self.current_email = ""
        self.emails_checked = 0
        self.total_candidates = 0
        self.cards_updated = 0
        self.early_stopped = False
        self.last_error = None
        self.started_at = None
        self.completed_at = None

    def start(self, step="Connecting to email server..."):
        self.is_syncing = True
        self.current_step = step
        self.current_email = ""
        self.emails_checked = 0
        self.total_candidates = 0
        self.cards_updated = 0
        self.early_stopped = False
        self.last_error = None
        self.started_at = datetime.datetime.utcnow().isoformat() + "Z"
        self.completed_at = None

    def update(self, step, email_subject="", checked=None, total=None, cards=None):
        self.current_step = step
        if email_subject:
            self.current_email = email_subject
        if checked is not None:
            self.emails_checked = checked
        if total is not None:
            self.total_candidates = total
        if cards is not None:
            self.cards_updated = cards

    def finish(self, message="Sync complete!", early_stopped=False):
        self.is_syncing = False
        self.current_step = message
        self.early_stopped = early_stopped
        self.completed_at = datetime.datetime.utcnow().isoformat() + "Z"

    def fail(self, error):
        self.is_syncing = False
        self.current_step = f"Failed: {error}"
        self.last_error = error
        self.completed_at = datetime.datetime.utcnow().isoformat() + "Z"

    def to_dict(self):
        return {
            "is_syncing": self.is_syncing,
            "current_step": self.current_step,
            "current_email": self.current_email,
            "emails_checked": self.emails_checked,
            "total_candidates": self.total_candidates,
            "cards_updated": self.cards_updated,
            "early_stopped": self.early_stopped,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }

tracker = SyncTracker()

# --- Auto-Sync Background Scheduler ---
AUTO_SYNC_INTERVAL_MINUTES = 0
_auto_sync_timer = None

def get_auto_sync_interval() -> int:
    global AUTO_SYNC_INTERVAL_MINUTES
    return AUTO_SYNC_INTERVAL_MINUTES

def set_auto_sync_interval(minutes: int):
    global AUTO_SYNC_INTERVAL_MINUTES, _auto_sync_timer
    AUTO_SYNC_INTERVAL_MINUTES = max(0, minutes)
    db.set_setting("auto_sync_interval", str(AUTO_SYNC_INTERVAL_MINUTES))
    
    if _auto_sync_timer:
        _auto_sync_timer.cancel()
        _auto_sync_timer = None
        
    if AUTO_SYNC_INTERVAL_MINUTES > 0:
        _schedule_next_auto_sync()
        logger.info(f"Auto-sync scheduled every {AUTO_SYNC_INTERVAL_MINUTES} minutes")

def _schedule_next_auto_sync():
    global _auto_sync_timer
    if AUTO_SYNC_INTERVAL_MINUTES <= 0:
        return
    _auto_sync_timer = threading.Timer(AUTO_SYNC_INTERVAL_MINUTES * 60, _run_auto_sync_tick)
    _auto_sync_timer.daemon = True
    _auto_sync_timer.start()

def _run_auto_sync_tick():
    try:
        account = db.get_active_email_account()
        if account and not tracker.is_syncing:
            conn = db.get_db_connection()
            row = conn.execute("SELECT password FROM email_accounts WHERE id = ?", (account["id"],)).fetchone()
            conn.close()
            if row and row["password"]:
                run_sync_in_background(
                    imap_server=account["imap_server"],
                    email_address=account["email_address"],
                    password=row["password"],
                    max_emails=50
                )
    except Exception as e:
        logger.error(f"Auto-sync tick error: {e}")
    finally:
        _schedule_next_auto_sync()

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()

    def handle_endtag(self, tag):
        if self.current_tag == tag.lower():
            self.current_tag = None
        if tag.lower() in {'p', 'br', 'div', 'tr', 'h1', 'h2', 'h3', 'li'}:
            self.result.append('\n')

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.result.append(text + ' ')

    def get_text(self) -> str:
        raw_text = "".join(self.result)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', raw_text)
        return cleaned.strip()

def decode_mime_header(header_value: Optional[str]) -> str:
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    text_parts = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            try:
                text_parts.append(fragment.decode(encoding or 'utf-8', errors='ignore'))
            except Exception:
                text_parts.append(fragment.decode('latin-1', errors='ignore'))
        else:
            text_parts.append(str(fragment))
    return "".join(text_parts)

def extract_email_body(msg: email.message.Message) -> str:
    plain_text = ""
    html_text = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or 'utf-8'
                decoded_str = payload.decode(charset, errors='ignore')

                if content_type == "text/plain":
                    plain_text += decoded_str + "\n"
                elif content_type == "text/html":
                    html_text += decoded_str + "\n"
            except Exception as e:
                logger.warning(f"Error parsing email part: {e}")
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            decoded_str = payload.decode(charset, errors='ignore')
            if msg.get_content_type() == "text/html":
                html_text = decoded_str
            else:
                plain_text = decoded_str
        except Exception as e:
            logger.warning(f"Error parsing single-part email: {e}")

    if plain_text.strip():
        return plain_text.strip()
    elif html_text.strip():
        parser = HTMLTextExtractor()
        parser.feed(html_text)
        return parser.get_text()
    
    return ""

def test_imap_credentials(imap_server: str, email_address: str, password: str) -> Dict[str, Any]:
    clean_email = email_address.strip()
    clean_password = password.strip().replace(" ", "")

    try:
        mail = imaplib.IMAP4_SSL(imap_server, timeout=10)
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not connect to {imap_server}. Please check your server address and internet connection."
        }

    try:
        mail.login(clean_email, clean_password)
        res, data = mail.select("INBOX", readonly=True)
        total_msgs = int(data[0].decode('utf-8')) if data and data[0] else 0
        mail.logout()

        return {
            "success": True,
            "message": f"Successfully connected to {clean_email}!",
            "email_address": clean_email,
            "imap_server": imap_server,
            "total_inbox_messages": total_msgs
        }
    except imaplib.IMAP4.error as e:
        err_msg = str(e)
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            return {
                "success": False,
                "error": (
                    "Authentication Failed. For Gmail:\n"
                    "1. You must use a 16-character Google App Password (not your normal Google account password).\n"
                    "2. Generate one at https://myaccount.google.com/apppasswords\n"
                    "3. Ensure IMAP is enabled in Gmail Settings > Forwarding and POP/IMAP."
                )
            }
        return {"success": False, "error": f"Login failed: {err_msg}"}
    except Exception as e:
        return {"success": False, "error": f"Connection test failed: {e}"}

def run_sync_in_background(imap_server: str, email_address: str, password: str, max_emails: int = 50):
    thread = threading.Thread(
        target=_sync_imap_worker,
        args=(imap_server, email_address, password, max_emails),
        daemon=True
    )
    thread.start()

def _sync_imap_worker(imap_server: str, email_address: str, password: str, max_emails: int):
    tracker.start(f"Connecting to IMAP server (Scan limit: {max_emails} emails)...")
    clean_email = email_address.strip()
    clean_password = password.strip().replace(" ", "")

    try:
        mail = imaplib.IMAP4_SSL(imap_server, timeout=20)
        mail.login(clean_email, clean_password)
        mail.select("INBOX", readonly=True)

        tracker.update("Searching for recent candidate emails...")
        status, messages = mail.search(None, "ALL")
        if status != "OK" or not messages or not messages[0]:
            tracker.finish("No emails found in INBOX.")
            mail.logout()
            return

        email_ids = messages[0].split()
        target_limit = min(max(max_emails, 10), 250)
        recent_ids = email_ids[-target_limit:] if len(email_ids) > target_limit else email_ids
        recent_ids.reverse()

        tracker.update("Filtering and inspecting emails...", total=len(recent_ids))

        positive_keywords = [
            "application", "applied", "candidate", "interview", "offer", 
            "assessment", "status update", "bewerbung", "vorstellungsgespräch", 
            "absage", "angebot", "working student", "internship", "hiring team", 
            "recruiting team", "talent acquisition", "greenhouse", "workday", "lever"
        ]

        checked = 0
        cards_updated = 0
        consecutive_already_synced = 0

        for e_id in recent_ids:
            try:
                checked += 1
                res, data = mail.fetch(e_id, "(RFC822)")
                if res != "OK" or not data or not data[0]:
                    continue

                raw_email_bytes = data[0][1]
                msg = email.message_from_bytes(raw_email_bytes)

                subject = decode_mime_header(msg.get("Subject", "No Subject"))
                sender = decode_mime_header(msg.get("From", "Unknown Sender"))
                message_id = msg.get("Message-ID", "")
                thread_id = msg.get("In-Reply-To") or msg.get("References") or message_id

                body = extract_email_body(msg)

                # 1. Drop job alerts & newsletters
                if is_job_alert_or_newsletter(sender, subject, body):
                    tracker.update(f"Skipping alert ({checked}/{len(recent_ids)})", checked=checked)
                    continue

                # 2. Positive Keyword Check
                combined_text = f"{subject} {body} {sender}".lower()
                is_candidate = any(kw in combined_text for kw in positive_keywords)
                if not is_candidate:
                    tracker.update(f"Inspecting email {checked}/{len(recent_ids)}...", checked=checked)
                    continue

                # 3. Checkpoint & Deduplication
                if db.is_email_already_recorded(message_id, subject):
                    consecutive_already_synced += 1
                    tracker.update(f"Already synced: '{subject[:28]}...' ({checked}/{len(recent_ids)})", checked=checked)
                    if consecutive_already_synced >= 2:
                        mail.close()
                        mail.logout()
                        db.update_email_account_status(clean_email, "CONNECTED", None, cards_updated)
                        tracker.finish(f"✓ Checkpoint reached: Older emails already synced! Scanned {checked} emails, updated {cards_updated} cards.", early_stopped=True)
                        return
                    continue
                else:
                    consecutive_already_synced = 0

                # 4. Extract with active local AI model
                active_m = extractor.get_active_model()
                tracker.update(
                    f"⚡ Extracting with {active_m}: '{subject[:30]}...' ({checked}/{len(recent_ids)})",
                    email_subject=subject,
                    checked=checked
                )

                deep_link = generate_gmail_deep_link(message_id, subject, sender)

                raw_input = RawEmailInput(
                    sender=sender,
                    subject=subject,
                    body=body[:1500],
                    email_message_id=message_id,
                    email_thread_id=thread_id,
                    email_deep_link=deep_link,
                    received_at=datetime.datetime.utcnow().isoformat() + "Z"
                )

                extracted = extractor.extract_job_details(
                    sender=raw_input.sender,
                    subject=raw_input.subject,
                    body=raw_input.body
                )

                if extracted and extracted.is_job_related and extracted.status != "NOT_JOB_RELATED":
                    match_res = matchmaker.process_and_match_email(raw_input, extracted)
                    if match_res.is_job_related:
                        cards_updated += 1
                        tracker.update(
                            f"✓ Logged Card for '{extracted.company_name}'!",
                            checked=checked,
                            cards=cards_updated
                        )

            except Exception as e:
                logger.error(f"Error processing email ID {e_id}: {e}")
                continue

        mail.close()
        mail.logout()

        db.update_email_account_status(clean_email, "CONNECTED", None, cards_updated)
        tracker.finish(f"Sync complete! Scanned {checked} emails, updated {cards_updated} job cards.")

    except Exception as e:
        logger.error(f"IMAP Sync Worker Error: {e}")
        db.update_email_account_status(clean_email, "ERROR", str(e))
        tracker.fail(str(e))
