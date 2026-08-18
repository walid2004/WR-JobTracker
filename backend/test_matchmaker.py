import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import database as db
import matchmaker
from models import RawEmailInput, ExtractedJobDetails

def run_test():
    print("=" * 70)
    print("🧪 Testing Step 2 Matchmaker & Database State Machine")
    print("=" * 70)

    # 1. Initialize DB
    db.init_db()
    
    # Clear any previous test data
    conn = db.get_db_connection()
    conn.execute("DELETE FROM email_events;")
    conn.execute("DELETE FROM applications;")
    conn.commit()
    conn.close()
    print("[1] Database initialized & cleaned.")

    # 2. Test Email 1: BMW Initial Application
    email1 = RawEmailInput(
        sender="career@bmwgroup.com",
        subject="Confirmation of your application: Working Student Software Engineering (Ref #DE-89211)",
        body="Thank you for applying to BMW Group.",
        email_thread_id="thread_bmw_01",
        email_message_id="msg_001",
        received_at="2026-08-01T10:00:00Z"
    )
    ext1 = ExtractedJobDetails(
        is_job_related=True,
        company_name="BMW Group",
        job_title="Working Student - Software Engineering",
        job_reference_id="DE-89211",
        status="APPLIED",
        summary="Confirmation of application receipt at BMW Group.",
        action_required=None,
        next_step_deadline=None
    )
    res1 = matchmaker.process_and_match_email(email1, ext1)
    print(f"\n[Email 1 Processed] -> {res1.message}")
    assert res1.matched_existing_application is False
    assert res1.application_id == 1

    # 3. Test Email 2: TechCorp Interview
    email2 = RawEmailInput(
        sender="recruiter@techcorp.io",
        subject="TechCorp - Interview Invitation",
        body="We invite you to interview.",
        email_thread_id="thread_techcorp_01",
        email_message_id="msg_002",
        received_at="2026-08-05T12:00:00Z"
    )
    ext2 = ExtractedJobDetails(
        is_job_related=True,
        company_name="TechCorp",
        job_title="Full Stack Engineer",
        job_reference_id=None,
        status="INTERVIEW_INVITED",
        summary="Invitation to 1st round technical interview.",
        action_required="Schedule slot by Aug 20",
        next_step_deadline="2026-08-20T00:00:00Z"
    )
    res2 = matchmaker.process_and_match_email(email2, ext2)
    print(f"\n[Email 2 Processed] -> {res2.message}")
    assert res2.matched_existing_application is False
    assert res2.application_id == 2

    # 4. Test Email 3: BMW Rejection (2 Weeks Later on same thread)
    email3 = RawEmailInput(
        sender="no-reply@bmwgroup-jobs.com",
        subject="Update on your application for Ref #DE-89211",
        body="We regret to inform you that we will proceed with other candidates.",
        email_thread_id="thread_bmw_01", # Matches thread!
        email_message_id="msg_003",
        received_at="2026-08-15T15:30:00Z"
    )
    ext3 = ExtractedJobDetails(
        is_job_related=True,
        company_name="BMW",
        job_title="Working Student",
        job_reference_id="DE-89211",
        status="REJECTED",
        summary="Rejection letter for Working Student position.",
        action_required=None,
        next_step_deadline=None
    )
    res3 = matchmaker.process_and_match_email(email3, ext3)
    print(f"\n[Email 3 Processed] -> {res3.message}")
    assert res3.matched_existing_application is True
    assert res3.application_id == 1 # Must update existing BMW card!

    # 5. Verify Database Records & Timeline
    print("\n" + "-" * 50)
    print("📊 Verifying Persisted Cards & Timelines in SQLite:")
    apps = db.get_all_applications()
    for app in apps:
        details = db.get_application_by_id(app["id"])
        print(f"\n🏷️  Card #{details['id']}: {details['company_name']} | Role: {details['job_title']} | Status: [{details['status']}]")
        print(f"   Action: {details['action_required']} | Deadline: {details['next_step_deadline']}")
        print(f"   Email History ({len(details['timeline'])} emails):")
        for ev in details['timeline']:
            print(f"     - [{ev['received_at']}] [{ev['extracted_status']}] {ev['subject']}")

    print("\n" + "=" * 70)
    print("✅ All State Machine and Database Tests Passed Successfully!")
    print("=" * 70)

if __name__ == "__main__":
    run_test()
