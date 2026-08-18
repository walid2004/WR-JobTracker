import json
import urllib.request
import urllib.error
import sys

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ollama REST API endpoint
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:8b"

# Define the JSON Schema for strict structured output
JOB_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_job_related": {
            "type": "boolean",
            "description": "True if this email is about a job application, interview, rejection, offer, or assessment."
        },
        "company_name": {
            "type": "string",
            "description": "Normalized company name, e.g., 'BMW Group', 'Google', 'Siemens'."
        },
        "job_title": {
            "type": "string",
            "description": "The specific position or role applied for."
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
            "description": "Current status of the application derived from this specific email."
        },
        "summary": {
            "type": "string",
            "description": "A crisp 1-sentence summary of what this email says."
        },
        "action_required": {
            "type": ["string", "null"],
            "description": "Action the candidate must take, e.g. 'Schedule interview by Friday' or null."
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

# 3 Real-World Test Emails
TEST_EMAILS = [
    {
        "id": "email_01",
        "sender": "career@bmwgroup.com",
        "subject": "Confirmation of your application: Working Student Software Engineering (Ref #DE-89211)",
        "body": """
Dear Applicant,

Thank you for your interest in the BMW Group. We hereby confirm the receipt of your application for the position:
Working Student - Software Engineering (Autonomous Driving Systems)
Reference Number: DE-89211

Our recruiting team will review your application documents carefully. We will get back to you as soon as possible regarding the next steps.

Kind regards,
BMW Group Recruiting Team
Munich, Germany
        """
    },
    {
        "id": "email_02",
        "sender": "no-reply@bmwgroup-jobs.com",
        "subject": "Update on your application for Ref #DE-89211 (Working Student)",
        "body": """
Dear Candidate,

Thank you for the time and effort you invested in applying for the Working Student - Software Engineering role (Ref #DE-89211) at the BMW Group.

After careful consideration of all applications, we regret to inform you that we have decided to proceed with other candidates whose profiles more closely match our current requirements for this specific role.

We wish you all the best in your ongoing career search.

Sincerely,
BMW Talent Acquisition
        """
    },
    {
        "id": "email_03",
        "sender": "recruiter@techcorp.io",
        "subject": "TechCorp - Invitation for 1st Round Technical Interview!",
        "body": """
Hi Alex,

Great news! The engineering team was very impressed by your background. We would like to invite you for a 45-minute Technical Screening interview next week.

Please choose a suitable time slot using this scheduling link by August 20, 2026: https://calendly.com/techcorp-interviews/alex

Looking forward to speaking with you!

Best,
Sarah Jenkins
TechCorp Talent Team
        """
    }
]

def parse_email_with_ollama(email_data):
    prompt = f"""You are an expert job application parser. Extract structured metadata from this email into JSON.
Sender: {email_data['sender']}
Subject: {email_data['subject']}

Body:
{email_data['body']}
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise data extraction system for job applications. Follow the JSON schema strictly without extra commentary."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "format": JOB_EXTRACTION_SCHEMA,
        "options": {
            "temperature": 0.0
        },
        "stream": False
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data.get("message", {}).get("content", "{}")
            return json.loads(content)
    except urllib.error.URLError as e:
        print(f"[Error] Could not connect to Ollama: {e}")
        print("Make sure Ollama is running (`ollama serve` or app active).")
        return None
    except json.JSONDecodeError as e:
        print(f"[Error] Failed to parse model output JSON: {e}")
        return None

def main():
    print("=" * 70)
    print(f"[TEST] Testing Job Application AI Engine on Local Ollama ({MODEL_NAME})")
    print("=" * 70)

    for idx, email in enumerate(TEST_EMAILS, 1):
        print(f"\n[Test {idx}/3] Processing: '{email['subject']}'...")
        result = parse_email_with_ollama(email)
        
        if result:
            print("[SUCCESS] Parsed Structured Card Output:")
            print(json.dumps(result, indent=2))
        else:
            print("[FAILED] Could not process email.")

    print("\n" + "=" * 70)
    print("[DONE] Test Complete!")

if __name__ == "__main__":
    main()
