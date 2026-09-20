"""M5/M6: tie classify + extract + compare together into a full
submission.json, with reliability escalation for the cases the pipeline
genuinely can't decide on its own.

Usage: python -m sdoc.pipeline [--data DIR] [--out FILE]
"""
import argparse
import json
import re
from pathlib import Path

from .classify import classify
from .compare import compare_fields
from .extract import extract_fields_txt, looks_like_other_doc_type

# The 20 reliability edge cases explicitly ask us to *perform* a comparison
# ("Please compare the SI and draft BL ... (attachments appear to have been
# dropped)"), unlike a normal "please send the draft BL" request. That's
# what distinguishes a genuine missing_attachment case from the ~45% of
# ordinary BL_COMPARISON emails that simply don't have a BL yet.
_ASKS_TO_COMPARE_RE = re.compile(r"\bcompare\b", re.IGNORECASE)

_DEFAULT_RESULT: dict[str, object] = {
    "category": "GENERAL",
    "status": "OK",
    "review_reason": None,
    "has_defect": False,
    "defect_fields": [],
}


def _txt_pair(attachments: list[str]):
    """Return (si_path, bl_path) if attachments are exactly one SI + one BL
    .txt file, else None (0/1 attachments, or a format we don't parse yet)."""
    if len(attachments) != 2:
        return None
    si = [a for a in attachments if a.endswith("_SI.txt")]
    bl = [a for a in attachments if a.endswith("_BL.txt")]
    if len(si) == 1 and len(bl) == 1:
        return si[0], bl[0]
    return None


def process_email(email: dict, data_dir: Path) -> dict:
    category = classify(email)
    result: dict[str, object] = dict(_DEFAULT_RESULT, category=category)

    if category != "BL_COMPARISON":
        return result

    attachments = email.get("attachments", [])
    if len(attachments) < 2:
        # Nothing to compare yet (0/1 attachments). The email explicitly
        # asking us to compare despite that ("...attachments appear to have
        # been dropped" / "...the draft BL is still missing") is the
        # reliability edge case -> escalate. A plain "please send the draft
        # BL" request is the ordinary case -> OK/no-defect, matching the
        # ground-truth convention for non-comparable emails.
        if _ASKS_TO_COMPARE_RE.search(email.get("body", "") or ""):
            result["status"] = "NEEDS_REVIEW"
            result["review_reason"] = "missing_attachment"
        return result

    pair = _txt_pair(attachments)
    if pair is None:
        # Two attachments are present but not a parseable .txt SI+BL pair
        # (PDF/DOCX/XLSX -> M7/M8 not built yet, or unexpected naming). We
        # genuinely can't compare them -- escalate instead of silently
        # reporting OK, which would hide any real discrepancy.
        result["status"] = "NEEDS_REVIEW"
        result["review_reason"] = "unreadable"
        return result

    si_path, bl_path = pair
    si_text = (data_dir / si_path).read_text(encoding="utf-8")
    bl_text = (data_dir / bl_path).read_text(encoding="utf-8")

    if looks_like_other_doc_type(bl_text) or looks_like_other_doc_type(si_text):
        result["status"] = "NEEDS_REVIEW"
        result["review_reason"] = "wrong_doc_type"
        return result

    si_fields = extract_fields_txt(si_text)
    bl_fields = extract_fields_txt(bl_text)
    result.update(compare_fields(si_fields, bl_fields))
    return result


def build_submission(data_dir: Path, emails: list[dict]) -> dict:
    return {email["email_id"]: process_email(email, data_dir) for email in emails}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="dataset folder (default: data)")
    ap.add_argument("--out", default="submission.json")
    args = ap.parse_args()

    data_dir = Path(args.data)
    emails = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((data_dir / "inbox").glob("email_*.json"))]
    submission = build_submission(data_dir, emails)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(submission, indent=2))
    print(f"wrote {len(submission)} entries to {out_path}")


if __name__ == "__main__":
    main()
