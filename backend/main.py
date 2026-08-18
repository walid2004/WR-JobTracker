from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import time
import database as db
import extractor
import matchmaker
import email_fetcher
from models import (
    ApplicationResponse,
    CreateApplicationRequest,
    UpdateApplicationRequest,
    RawEmailInput,
    ProcessEmailResponse
)

class ImapCredentialsRequest(BaseModel):
    email_address: Optional[str] = None
    password: Optional[str] = None
    imap_server: Optional[str] = "imap.gmail.com"
    max_emails: Optional[int] = 50

app = FastAPI(
    title="WR JobTracker API",
    description="Local AI-powered Job Application Tracking Engine",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    db.init_db()
    saved_interval = db.get_setting("auto_sync_interval", "0")
    try:
        email_fetcher.set_auto_sync_interval(int(saved_interval))
    except Exception:
        pass

@app.get("/api/health")
def health_check():
    account = db.get_active_email_account()
    return {
        "status": "healthy",
        "app_name": "WR JobTracker",
        "database": "sqlite_ready",
        "model": extractor.get_active_model(),
        "available_models": extractor.get_installed_ollama_models(),
        "auto_sync_interval_mins": email_fetcher.get_auto_sync_interval(),
        "email_connected": bool(account and account.get("status") == "CONNECTED"),
        "connected_email": account.get("email_address") if account else None
    }

@app.get("/api/models")
def list_models():
    return {
        "active_model": extractor.get_active_model(),
        "available_models": extractor.get_installed_ollama_models()
    }

class SetModelRequest(BaseModel):
    model_name: str

@app.post("/api/models/active")
def change_active_model(req: SetModelRequest):
    updated = extractor.set_active_model(req.model_name)
    return {"success": True, "active_model": updated}

class TestCustomApiRequest(BaseModel):
    api_url: str
    api_key: Optional[str] = ""
    model_name: str

@app.post("/api/models/test-custom-api")
def test_custom_api(req: TestCustomApiRequest):
    test_config = {
        "custom_api_url": req.api_url,
        "custom_api_key": req.api_key or "",
        "custom_model_name": req.model_name
    }
    sample_sender = "recruiting@spotify.com"
    sample_subject = "Interview Invitation: Frontend Engineer at Spotify"
    sample_body = "Hi candidate, we were impressed with your application and would like to schedule a 45-minute technical screen next Tuesday. Please reply with your availability."
    
    t0 = time.time()
    try:
        res = extractor.extract_via_custom_api(sample_sender, sample_subject, sample_body, test_config)
        elapsed = round(time.time() - t0, 2)
        if not res or not res.is_job_related:
            return {
                "success": False,
                "error": "The model responded, but did not extract the expected job schema.",
                "elapsed": elapsed
            }
        return {
            "success": True,
            "message": f"Successfully connected to {req.model_name}. Response parsed in {elapsed}s.",
            "extracted_sample": res.model_dump(),
            "elapsed": elapsed
        }
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return {
            "success": False,
            "error": str(e),
            "elapsed": elapsed
        }

class SettingsRequest(BaseModel):
    auto_sync_interval: Optional[int] = None
    scan_depth: Optional[int] = None
    active_model: Optional[str] = None
    ai_provider: Optional[str] = None
    custom_api_url: Optional[str] = None
    custom_api_key: Optional[str] = None
    custom_model_name: Optional[str] = None

@app.get("/api/settings")
def get_app_settings():
    ai_cfg = extractor.get_ai_config()
    return {
        "auto_sync_interval": email_fetcher.get_auto_sync_interval(),
        "scan_depth": int(db.get_setting("scan_depth", "50")),
        "ai_provider": ai_cfg["ai_provider"],
        "active_model": ai_cfg["active_model"],
        "custom_api_url": ai_cfg["custom_api_url"],
        "custom_api_key": ai_cfg["custom_api_key"],
        "custom_model_name": ai_cfg["custom_model_name"],
        "available_models": extractor.get_installed_ollama_models()
    }

@app.post("/api/settings")
def update_app_settings(req: SettingsRequest):
    if req.auto_sync_interval is not None:
        email_fetcher.set_auto_sync_interval(req.auto_sync_interval)
    if req.scan_depth is not None:
        db.set_setting("scan_depth", str(req.scan_depth))
    if req.ai_provider is not None:
        db.set_setting("ai_provider", req.ai_provider)
    if req.active_model:
        db.set_setting("active_model", req.active_model)
    if req.custom_api_url is not None:
        db.set_setting("custom_api_url", req.custom_api_url)
    if req.custom_api_key is not None:
        db.set_setting("custom_api_key", req.custom_api_key)
    if req.custom_model_name is not None:
        db.set_setting("custom_model_name", req.custom_model_name)
        
    ai_cfg = extractor.get_ai_config()
    return {
        "success": True,
        "settings": {
            "auto_sync_interval": email_fetcher.get_auto_sync_interval(),
            "scan_depth": int(db.get_setting("scan_depth", "50")),
            "ai_provider": ai_cfg["ai_provider"],
            "active_model": ai_cfg["active_model"],
            "custom_api_url": ai_cfg["custom_api_url"],
            "custom_api_key": ai_cfg["custom_api_key"],
            "custom_model_name": ai_cfg["custom_model_name"]
        }
    }

@app.get("/api/email/account")
def get_email_account():
    account = db.get_active_email_account()
    if not account:
        return {"connected": False, "account": None}
    return {"connected": account["status"] == "CONNECTED", "account": account}

@app.post("/api/email/test-connection")
def test_connection(req: ImapCredentialsRequest):
    if not req.email_address or not req.password:
        raise HTTPException(status_code=400, detail="Please provide both email_address and password.")
    res = email_fetcher.test_imap_credentials(
        imap_server=req.imap_server or "imap.gmail.com",
        email_address=req.email_address,
        password=req.password
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Connection failed"))
    return res

@app.post("/api/email/connect")
def connect_and_save_account(req: ImapCredentialsRequest):
    if not req.email_address or not req.password:
        raise HTTPException(status_code=400, detail="Please provide both email_address and password.")
    
    server = req.imap_server or "imap.gmail.com"
    test_res = email_fetcher.test_imap_credentials(
        imap_server=server,
        email_address=req.email_address,
        password=req.password
    )
    if not test_res.get("success"):
        raise HTTPException(status_code=400, detail=test_res.get("error", "Invalid credentials"))
    
    clean_pwd = req.password.strip().replace(" ", "")
    account_id = db.save_email_account(
        email_address=req.email_address.strip(),
        imap_server=server,
        password=clean_pwd,
        status="CONNECTED"
    )
    return {
        "success": True,
        "message": f"Connected to {req.email_address} successfully",
        "account": db.get_active_email_account()
    }

@app.post("/api/email/disconnect")
def disconnect_account():
    db.disconnect_email_account()
    return {"success": True, "message": "Email account disconnected."}

@app.post("/api/sync-start")
def start_sync(req: Optional[ImapCredentialsRequest] = None):
    if email_fetcher.tracker.is_syncing:
        return {"success": True, "message": "Sync already in progress.", "progress": email_fetcher.tracker.to_dict()}
    
    email_addr = None
    pwd = None
    server = "imap.gmail.com"
    max_emails = 50

    if req and req.email_address and req.password:
        email_addr = req.email_address
        pwd = req.password
        server = req.imap_server or "imap.gmail.com"
        max_emails = req.max_emails or 50
    else:
        saved = db.get_active_email_account()
        if not saved:
            raise HTTPException(status_code=400, detail="No email account connected. Please connect an inbox first.")
        conn = db.get_db_connection()
        row = conn.execute("SELECT password FROM email_accounts WHERE id = ?", (saved["id"],)).fetchone()
        conn.close()
        if not row or not row["password"]:
            raise HTTPException(status_code=400, detail="Saved credentials missing. Please reconnect.")
        email_addr = saved["email_address"]
        pwd = row["password"]
        server = saved["imap_server"]
        if req and req.max_emails:
            max_emails = req.max_emails
        else:
            max_emails = int(db.get_setting("scan_depth", "50"))

    email_fetcher.run_sync_in_background(
        imap_server=server,
        email_address=email_addr,
        password=pwd,
        max_emails=max_emails
    )
    return {"success": True, "message": "Sync started.", "progress": email_fetcher.tracker.to_dict()}

@app.get("/api/sync-progress")
def get_sync_progress():
    return email_fetcher.tracker.to_dict()

@app.get("/api/applications")
def list_applications():
    return db.get_all_applications()

@app.get("/api/applications/{app_id}")
def get_application(app_id: int):
    app_data = db.get_application_by_id(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application not found")
    return app_data

@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
def create_manual_application(req: CreateApplicationRequest):
    company_slug = matchmaker.normalize_company_name(req.company_name)
    app_id = db.create_application(
        company_name=req.company_name,
        company_slug=company_slug,
        job_title=req.job_title,
        job_reference_id=req.job_reference_id,
        status=req.status or "APPLIED",
        action_required=req.action_required,
        next_step_deadline=req.next_step_deadline,
        location=req.location,
        notes=req.notes
    )
    created = db.get_application_by_id(app_id)
    return created

@app.patch("/api/applications/{app_id}")
def update_application(app_id: int, req: UpdateApplicationRequest):
    fields = req.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    if "company_name" in fields and fields["company_name"]:
        fields["company_slug"] = matchmaker.normalize_company_name(fields["company_name"])
        
    updated = db.update_application(app_id, **fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found or no changes made")
    
    return db.get_application_by_id(app_id)

@app.delete("/api/applications/{app_id}")
def delete_application(app_id: int):
    deleted = db.delete_application(app_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "message": f"Application #{app_id} deleted"}

@app.post("/api/process-email", response_model=ProcessEmailResponse)
def process_single_email(email_input: RawEmailInput):
    extracted = extractor.extract_job_details(
        sender=email_input.sender,
        subject=email_input.subject,
        body=email_input.body
    )
    
    if not extracted:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to extract job details via {extractor.get_active_model()}."
        )
    
    result = matchmaker.process_and_match_email(email_input, extracted)
    return result

@app.get("/api/stats")
def get_dashboard_stats():
    apps = db.get_all_applications()
    total = len(apps)
    
    applied = sum(1 for a in apps if a.get("status") == "APPLIED")
    under_review = sum(1 for a in apps if a.get("status") == "UNDER_REVIEW")
    interviews = sum(1 for a in apps if a.get("status") in ("INTERVIEW_INVITED", "ASSESSMENT_INVITED", "ACTION_REQUIRED"))
    offers = sum(1 for a in apps if a.get("status") == "OFFER_RECEIVED")
    rejections = sum(1 for a in apps if a.get("status") in ("REJECTED", "ARCHIVED"))
    action_needed = sum(1 for a in apps if a.get("action_required") is not None and a.get("status") not in ("REJECTED", "OFFER_RECEIVED", "ARCHIVED"))

    response_rate = round(((total - applied) / total * 100), 1) if total > 0 else 0.0

    return {
        "total_applications": total,
        "applied": applied,
        "under_review": under_review,
        "interviews_assessments": interviews,
        "offers": offers,
        "rejections": rejections,
        "action_needed": action_needed,
        "response_rate_percent": response_rate
    }

@app.post("/api/reset-db")
def reset_database():
    conn = db.get_db_connection()
    conn.execute("DELETE FROM email_events;")
    conn.execute("DELETE FROM applications;")
    conn.commit()
    conn.close()
    return {"success": True, "message": "Database reset successfully."}
