import re
import logging
from typing import Optional, Tuple, List
from models import RawEmailInput, ExtractedJobDetails, ProcessEmailResponse
import database as db

logger = logging.getLogger(__name__)

STRIP_WORDS = {
    "ag", "gmbh", "se", "corp", "corporation", "inc", "incorporated", 
    "llc", "ltd", "limited", "group", "deutschland", "germany", "technologies",
    "technology", "solutions", "holdings", "co", "company"
}

CANONICAL_ALIASES = {
    "bayerische motoren werke": "bmw",
    "bmw": "bmw",
    "bmw group": "bmw",
    "alphabet": "google",
    "google": "google",
    "meta": "meta",
    "facebook": "meta",
    "microsoft": "microsoft",
    "amazon": "amazon",
    "aws": "amazon"
}

def normalize_company_name(name: Optional[str]) -> str:
    if not name:
        return "general-career"
    clean = str(name).lower().strip()
    if clean in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[clean]
    clean = re.sub(r"[^\w\s]", " ", clean)
    tokens = [w for w in clean.split() if w not in STRIP_WORDS and len(w) > 1]
    if not tokens:
        clean_sub = re.sub(r"[^\w]", "", str(name).lower())
        return clean_sub if clean_sub else "general-career"
    return "-".join(tokens)

def normalize_job_title_tokens(title: Optional[str]) -> set:
    if not title:
        return set()
    clean = str(title).lower()
    clean = re.sub(r'\(m/w/d\)|\(f/m/d\)|m/w/d|f/m/d|\(all genders\)', '', clean)
    clean = re.sub(r'[^a-z0-9\s]', ' ', clean)
    noise_title_words = {'the', 'a', 'an', 'in', 'at', 'for', 'of', 'and', 'bereich', 'im', 'und', 'position', 'role'}
    tokens = {w for w in clean.split() if len(w) > 2 and w not in noise_title_words}
    return tokens

def are_job_roles_similar(title_a: Optional[str], title_b: Optional[str]) -> bool:
    tokens_a = normalize_job_title_tokens(title_a)
    tokens_b = normalize_job_title_tokens(title_b)

    if not tokens_a or not tokens_b:
        return True

    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)

    distinguishing_keywords = {
        'frontend', 'backend', 'fullstack', 'mobile', 'ios', 'android', 
        'data', 'ai', 'ml', 'machine', 'qa', 'test', 'security', 'devops', 
        'cloud', 'product', 'design', 'hr', 'einkauf', 'procurement', 'sales', 'marketing'
    }
    
    special_a = tokens_a.intersection(distinguishing_keywords)
    special_b = tokens_b.intersection(distinguishing_keywords)

    if special_a and special_b and special_a != special_b:
        return False

    jaccard_sim = len(intersection) / len(union) if union else 0
    return jaccard_sim >= 0.35 or len(intersection) >= 2

def find_matching_app_for_company_and_role(company_slug: str, new_job_title: str) -> Optional[int]:
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, job_title, status FROM applications 
        WHERE company_slug = ? 
        ORDER BY updated_at DESC
    """, (company_slug,))
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        existing_title = row["job_title"]
        if are_job_roles_similar(existing_title, new_job_title):
            return row["id"]
            
    return None

def process_and_match_email(
    raw_email: RawEmailInput, 
    extracted: ExtractedJobDetails
) -> ProcessEmailResponse:
    if not extracted.is_job_related or extracted.status == "NOT_JOB_RELATED":
        return ProcessEmailResponse(
            success=True,
            is_job_related=False,
            matched_existing_application=False,
            message="Email scanned: not job-related, discarded.",
            extraction=extracted
        )

    safe_company_name = (extracted.company_name or "Unknown Company").strip()
    company_slug = normalize_company_name(safe_company_name)
    safe_job_title = (extracted.job_title or "Position Applied").strip()
    safe_status = extracted.status or "APPLIED"

    app_id: Optional[int] = None
    match_reason = ""

    if raw_email.email_thread_id:
        app_id = db.find_app_by_thread_id(raw_email.email_thread_id)
        if app_id:
            match_reason = f"Matched application #{app_id} via Thread ID"

    if not app_id and extracted.job_reference_id:
        app_id = db.find_app_by_reference_id(str(extracted.job_reference_id).strip())
        if app_id:
            match_reason = f"Matched application #{app_id} via Reference ID: {extracted.job_reference_id}"

    if not app_id and company_slug and company_slug != "general-career":
        app_id = find_matching_app_for_company_and_role(company_slug, safe_job_title)
        if app_id:
            match_reason = f"Matched application #{app_id} for '{safe_company_name}' ({safe_job_title})"

    if app_id:
        update_fields = {
            "status": safe_status,
            "action_required": extracted.action_required,
            "next_step_deadline": extracted.next_step_deadline,
        }
        if safe_job_title and safe_job_title.lower() not in ("unknown", "position applied", "not specified"):
            update_fields["job_title"] = safe_job_title
        if extracted.job_reference_id:
            update_fields["job_reference_id"] = str(extracted.job_reference_id)

        db.update_application(app_id, **update_fields)

        db.add_email_event(
            application_id=app_id,
            sender=raw_email.sender or "Unknown Sender",
            subject=raw_email.subject or "No Subject",
            summary=extracted.summary or "Email received.",
            extracted_status=safe_status,
            email_message_id=raw_email.email_message_id,
            email_thread_id=raw_email.email_thread_id,
            email_deep_link=raw_email.email_deep_link,
            received_at=raw_email.received_at
        )

        return ProcessEmailResponse(
            success=True,
            is_job_related=True,
            matched_existing_application=True,
            application_id=app_id,
            company_name=safe_company_name,
            status=safe_status,
            message=f"{match_reason}. Updated card status to {safe_status}.",
            extraction=extracted
        )

    else:
        new_app_id = db.create_application(
            company_name=safe_company_name,
            company_slug=company_slug,
            job_title=safe_job_title,
            job_reference_id=str(extracted.job_reference_id) if extracted.job_reference_id else None,
            status=safe_status,
            action_required=extracted.action_required,
            next_step_deadline=extracted.next_step_deadline
        )

        db.add_email_event(
            application_id=new_app_id,
            sender=raw_email.sender or "Unknown Sender",
            subject=raw_email.subject or "No Subject",
            summary=extracted.summary or "Application confirmation received.",
            extracted_status=safe_status,
            email_message_id=raw_email.email_message_id,
            email_thread_id=raw_email.email_thread_id,
            email_deep_link=raw_email.email_deep_link,
            received_at=raw_email.received_at
        )

        return ProcessEmailResponse(
            success=True,
            is_job_related=True,
            matched_existing_application=False,
            application_id=new_app_id,
            company_name=safe_company_name,
            status=safe_status,
            message=f"Created separate application card #{new_app_id} for '{safe_company_name} - {safe_job_title}'.",
            extraction=extracted
        )
