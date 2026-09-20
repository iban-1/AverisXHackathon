from pathlib import Path

from sdoc.pipeline import build_submission, process_email

DATA = Path(__file__).resolve().parents[1] / "data"


def test_process_email_non_comparison_defaults_to_ok():
    email = {
        "email_id": "x",
        "subject": "Bitcoin investment opportunity - guaranteed 300% returns",
        "body": "",
        "from": "x@secure-mailbox.org",
        "attachments": [],
    }
    result = process_email(email, DATA)
    assert result == {
        "category": "SPAM",
        "status": "OK",
        "review_reason": None,
        "has_defect": False,
        "defect_fields": [],
    }


def test_process_email_compares_real_txt_pair_email_004():
    import json

    email = json.loads((DATA / "inbox" / "email_004.json").read_text())
    result = process_email(email, DATA)
    assert result["category"] == "BL_COMPARISON"
    assert result["status"] == "MISMATCH"
    assert set(result["defect_fields"]) == {"consignee", "notify_party"}


def test_process_email_ok_bl_comparison_no_attachment_yet():
    email = {
        "email_id": "x",
        "subject": "RE_ TO CONFIRM DOCS _ 5AAT-03056 _ AQABA_JORDAN",
        "body": "Please assist to send the draft BL for checking asap.",
        "from": "x@aprilasia.com",
        "attachments": [],
    }
    result = process_email(email, DATA)
    assert result["category"] == "BL_COMPARISON"
    assert result["status"] == "OK"


def test_process_email_escalates_unsupported_attachment_format_instead_of_guessing():
    import json

    email = json.loads((DATA / "inbox" / "email_512.json").read_text())  # pdf+pdf pair
    assert len(email["attachments"]) == 2
    result = process_email(email, DATA)
    assert result["category"] == "BL_COMPARISON"
    assert result["status"] == "NEEDS_REVIEW"
    assert result["review_reason"] == "unreadable"
    assert result["has_defect"] is False


def test_build_submission_covers_every_email():
    import json

    emails = [json.loads(p.read_text()) for p in sorted((DATA / "inbox").glob("email_*.json"))]
    submission = build_submission(DATA, emails)
    assert len(submission) == len(emails) == 520
    for result in submission.values():
        assert set(result.keys()) == {"category", "status", "review_reason", "has_defect", "defect_fields"}
