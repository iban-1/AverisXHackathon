"""M6: the 20 reliability edge cases (email_501-520) should all escalate to
NEEDS_REVIEW with the right review_reason, without hurting the main set."""
import json
from pathlib import Path

from sdoc.pipeline import process_email

DATA = Path(__file__).resolve().parents[1] / "data"


def _process(email_id):
    email = json.loads((DATA / "inbox" / f"{email_id}.json").read_text())
    return process_email(email, DATA)


def test_wrong_doc_type_edge_cases():
    for eid in ["email_501", "email_502", "email_503", "email_504", "email_505"]:
        result = _process(eid)
        assert result["status"] == "NEEDS_REVIEW", eid
        assert result["review_reason"] == "wrong_doc_type", eid


def test_missing_attachment_edge_cases():
    for eid in ["email_506", "email_507", "email_508", "email_509", "email_510"]:
        result = _process(eid)
        assert result["status"] == "NEEDS_REVIEW", eid
        assert result["review_reason"] == "missing_attachment", eid


def test_missing_value_edge_cases():
    for eid in ["email_516", "email_517", "email_518", "email_519", "email_520"]:
        result = _process(eid)
        assert result["status"] == "NEEDS_REVIEW", eid
        assert result["review_reason"] == "missing_value", eid


def test_ordinary_no_attachment_request_stays_ok_not_review():
    # "Please assist to send the draft BL ... for checking asap" -- a normal
    # request, not a claim that documents were dropped -- must NOT escalate.
    result = _process("email_003")
    assert result["status"] == "OK"
    assert result["review_reason"] is None
