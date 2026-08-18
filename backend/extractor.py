import json
import urllib.request
import urllib.error
import logging
import time
import re
from typing import Optional, Dict, Any, List
from models import ExtractedJobDetails
import database as db

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://localhost:11434"
DEFAULT_LOCAL_MODEL = "qwen3:8b"

JOB_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_job_related": {
            "type": "boolean",
            "description": "TRUE ONLY for direct job application updates (confirmations, interviews, assessments, offers, rejections) regarding a role the candidate applied for. FALSE for job alert newsletters, job recommendations, marketing, or general job postings."
        },
        "company_name": {
            "type": "string",
            "description": "Normalized hiring company name (e.g., 'BMW Group', 'Google', 'Siemens', 'Spotify')."
        },
        "job_title": {
            "type": "string",
            "description": "The specific position or role applied for (e.g. 'Software Engineer', 'Working Student')."
        },
        "job_reference_id": {
            "type": ["string", "null"],
            "description": "Job ID, Requisition number, or reference code if mentioned, else null."
        },
        "status": {
            "type": "string",
            "enum": [
                "APPLIED",
                "UNDER_REVIEW",
                "ASSESSMENT_INVITED",
                "INTERVIEW_INVITED",
                "OFFER_RECEIVED",
                "REJECTED",
                "ACTION_REQUIRED",
                "NOT_JOB_RELATED"
            ],
            "description": "The application stage."
        },
        "summary": {
            "type": "string",
            "description": "A crisp 1-sentence summary of what this email says."
        },
        "action_required": {
            "type": ["string", "null"],
            "description": "Action the candidate must take (e.g. 'Schedule interview slot by Aug 20') or null."
        },
        "next_step_deadline": {
            "type": ["string", "null"],
            "description": "Any deadline date/time mentioned, or null."
        }
    },
    "required": [
        "is_job_related",
        "company_name",
        "job_title",
        "job_reference_id",
        "status",
        "summary",
        "action_required",
        "next_step_deadline"
    ]
}

SYSTEM_INSTRUCTION = """You are an expert ATS (Applicant Tracking System) parser.
Extract structured metadata from candidate emails into JSON according to the schema.

STRICT CLASSIFICATION RULES:
1. ONLY mark is_job_related as TRUE if this email is a DIRECT update regarding an application the candidate submitted:
   - Application confirmations ("Thank you for applying to...", "We have received your application...") -> status: APPLIED
   - Online Assessment invitations ("Complete your coding test on HackerRank...") -> status: ASSESSMENT_INVITED
   - Interview invitations ("We'd love to schedule an interview...") -> status: INTERVIEW_INVITED
   - Job offers ("Congratulations! We are offering you the role...") -> status: OFFER_RECEIVED
   - Rejections ("We decided to proceed with other candidates...") -> status: REJECTED

2. CRITICAL NEGATIVE RULES - Mark is_job_related: FALSE and status: NOT_JOB_RELATED for:
   - Automated job alerts, digests, and recommendations (e.g. "30 new Software Engineer jobs", "Jobs you might like from LinkedIn/Indeed/beBee", "See who is hiring").
   - Marketing emails, newsletter digests, or company announcements.
   - Job alerts where the user did NOT actually apply.

3. Extract clean company name (e.g. 'BMW Group', 'Google', 'Spotify').
"""

def get_installed_ollama_models() -> List[str]:
    """Fetches list of all locally downloaded models from Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            return models if models else [DEFAULT_LOCAL_MODEL]
    except Exception as e:
        logger.warning(f"Could not query Ollama tags: {e}")
        return [DEFAULT_LOCAL_MODEL]

def get_ai_config() -> Dict[str, Any]:
    """Returns the current AI provider configuration from DB settings."""
    provider = db.get_setting("ai_provider", "local")
    active_model = db.get_setting("active_model", DEFAULT_LOCAL_MODEL)
    custom_api_url = db.get_setting("custom_api_url", "https://models.inference.ai.azure.com")
    custom_api_key = db.get_setting("custom_api_key", "")
    custom_model_name = db.get_setting("custom_model_name", "gpt-4o-mini")
    
    return {
        "ai_provider": provider,
        "active_model": active_model,
        "custom_api_url": custom_api_url,
        "custom_api_key": custom_api_key,
        "custom_model_name": custom_model_name
    }

def set_active_model(model_name: str) -> str:
    db.set_setting("active_model", model_name.strip())
    db.set_setting("ai_provider", "local")
    return model_name.strip()

def get_active_model() -> str:
    config = get_ai_config()
    if config["ai_provider"] == "custom_api":
        return f"cloud:{config['custom_model_name']}"
    return config["active_model"]

def normalize_chat_endpoint(url: str) -> str:
    """Normalizes various user-provided API base URLs to chat/completions endpoint."""
    u = url.strip().rstrip("/")
    if u.endswith("/chat/completions"):
        return u
    if u.endswith("/v1"):
        return f"{u}/chat/completions"
    return f"{u}/chat/completions"

def clean_json_response(raw_text: str) -> str:
    """Strips Markdown code fences and whitespace from model output."""
    t = raw_text.strip()
    if t.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
        if match:
            return match.group(1).strip()
    return t

def extract_via_custom_api(sender: str, subject: str, body: str, config: Dict[str, Any]) -> Optional[ExtractedJobDetails]:
    """Sends email to custom OpenAI-compatible API endpoint (GitHub Models, OpenAI, Mistral, Groq, etc.)."""
    endpoint = normalize_chat_endpoint(config.get("custom_api_url", "https://models.inference.ai.azure.com"))
    api_key = config.get("custom_api_key", "").strip()
    model = config.get("custom_model_name", "gpt-4o-mini").strip()

    prompt = f"""Sender: {sender}
Subject: {subject}

Email Content:
{body}
"""

    system_content = f"{SYSTEM_INSTRUCTION}\n\nCRITICAL OUTPUT FORMAT: You must respond ONLY with a valid JSON object strictly matching this schema:\n{json.dumps(JOB_EXTRACTION_SCHEMA, indent=2)}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        # Also pass api-key header for Azure / GitHub Models compatibility
        headers["api-key"] = api_key

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content_str = res_data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            elapsed = round(time.time() - t0, 2)
            logger.info(f"Custom API ({model} @ {endpoint}) returned JSON in {elapsed}s")
            
            cleaned = clean_json_response(content_str)
            parsed_json = json.loads(cleaned)
            return ExtractedJobDetails(**parsed_json)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.error(f"HTTP {e.code} from Custom API ({endpoint}): {err_body}")
        raise RuntimeError(f"API Error ({e.code}): {err_body}")
    except Exception as e:
        logger.error(f"Error calling Custom API ({endpoint}): {e}")
        raise

def extract_via_ollama(sender: str, subject: str, body: str, model_name: str) -> Optional[ExtractedJobDetails]:
    """Sends email to active local Ollama model."""
    prompt = f"""Sender: {sender}
Subject: {subject}

Email Content:
{body}
"""

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt}
        ],
        "format": JOB_EXTRACTION_SCHEMA,
        "think": False,
        "keep_alive": "10m",
        "stream": False
    }

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content_str = res_data.get("message", {}).get("content", "{}")
            elapsed = round(time.time() - t0, 2)
            logger.info(f"Ollama ({model_name}) extracted JSON in {elapsed}s")
            parsed_json = json.loads(clean_json_response(content_str))
            return ExtractedJobDetails(**parsed_json)
    except urllib.error.URLError as e:
        logger.error(f"Error connecting to Ollama with model {model_name}: {e}")
        raise RuntimeError(f"Could not connect to Ollama at {OLLAMA_BASE}. Make sure Ollama is running.")
    except Exception as e:
        logger.error(f"Error parsing Ollama output for {model_name}: {e}")
        raise

def extract_job_details(sender: str, subject: str, body: str) -> Optional[ExtractedJobDetails]:
    """
    Main extraction pipeline. Routes automatically between Local Ollama and Custom Cloud API.
    """
    config = get_ai_config()
    if config["ai_provider"] == "custom_api":
        return extract_via_custom_api(sender, subject, body, config)
    else:
        return extract_via_ollama(sender, subject, body, config["active_model"])
