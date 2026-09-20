import glob
import json
from collections import Counter
from pathlib import Path

from sdoc.classify import classify

DATA = Path(__file__).resolve().parents[1] / "data"


def _load_all():
    return [json.loads(Path(f).read_text()) for f in sorted(glob.glob(str(DATA / "inbox" / "email_*.json")))]


def test_category_distribution_matches_documented_mix():
    # data_v2/README.md documents the main-500 mix; the 20 edge cases
    # (email_501-520) are all BL_COMPARISON on top of that.
    counts = Counter(classify(e) for e in _load_all())
    assert counts["BL_COMPARISON"] == 220
    assert counts["SI_REQUEST"] == 125
    assert counts["INVOICE_QUERY"] == 75
    assert counts["GENERAL"] == 60
    assert counts["SPAM"] == 40


def test_edge_cases_are_all_bl_comparison():
    for f in sorted(glob.glob(str(DATA / "inbox" / "email_5[0-2][0-9].json"))):
        e = json.loads(Path(f).read_text())
        if e["email_id"] == "email_500":
            continue  # part of the main 500, not an edge case
        assert classify(e) == "BL_COMPARISON", e["email_id"]


def test_attachments_always_imply_bl_comparison():
    for e in _load_all():
        if e.get("attachments"):
            assert classify(e) == "BL_COMPARISON", e["email_id"]


def test_spam_examples():
    assert classify({"subject": "Bitcoin investment opportunity - guaranteed 300% returns",
                      "body": "", "from": "x@secure-mailbox.org", "attachments": []}) == "SPAM"
    assert classify({"subject": "URGENT: Your email storage is full - verify account immediately",
                      "body": "", "from": "x@webmail-verify.co", "attachments": []}) == "SPAM"


def test_coded_bl_comparison_reply_subject():
    e = {"subject": "RE_ AIE - JEBEL ALI_UAE - ONE(SINF21158693) - 5ALT-87937 - 5250074160 - CLIFFORD PAPER INC",
         "body": "", "from": "x@aprilasia.com", "attachments": []}
    assert classify(e) == "BL_COMPARISON"


def test_si_request_examples():
    for subject in [
        "SI - EGLV754781291428 - DIRECT(EVER) - 5RUS-80996 - MOMBASA_KENYA",
        "REQUEST SI _ 5RSG-76553 _ APAPA_NIGERIA",
        "SI NEEDED_ 5RCY-63982 _ 3S PAPER PRODUCTS SDN BHD",
        "RE_ CUST SI _ MEA _ 5ALT-48877",
    ]:
        e = {"subject": subject, "body": "", "from": "x@aprilasia.com", "attachments": []}
        assert classify(e) == "SI_REQUEST", subject


def test_invoice_query_examples():
    for subject in [
        "2100 RAK BILLING 5070146623 MISSING GR",
        "Total Freight - INDIA - 5RUS-24161",
        "REQUEST TO CANCEL INVOICE -5250070084 - PACIFIC OFFICE (M) SDN BHD",
        "RE_ LOCAL CHARGES FOB - KARGOSMAR - 5AKR-61849 - TELEX RELEASE CHARGES",
        "Mill D & D charges - 6437419879",
    ]:
        e = {"subject": subject, "body": "", "from": "x@aprilasia.com", "attachments": []}
        assert classify(e) == "INVOICE_QUERY", subject


def test_general_examples_including_rpa_billing_wording():
    for subject in [
        "15_01_2026 - UPDATE SUMMARY LE HAVRE V.QI540A",
        "daily Berthing Report - 01 JAN 2026",
        "_RPA_ India HSS SD Billing Process Completed - LE HAVRE V.QI540A",
        "_Approval Required_ Time Off Request",
    ]:
        e = {"subject": subject, "body": "", "from": "x@aprilasia.com", "attachments": []}
        assert classify(e) == "GENERAL", subject


def test_body_document_checklist_does_not_trigger_invoice_query():
    # A real SI_REQUEST/BL_COMPARISON email body often lists "Original
    # invoice" as a required document — that must not flip the category.
    e = {
        "subject": "REQUEST SI _ 5RCY-60883",
        "body": "Documents Required:\n1) 3 Original invoice\n2) 3 Packing list\n3) 3 Original BL + 3 N/N",
        "from": "x@aprilasia.com",
        "attachments": [],
    }
    assert classify(e) == "SI_REQUEST"
