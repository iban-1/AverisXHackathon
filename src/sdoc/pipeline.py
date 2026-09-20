"""M5/M6/M7: tie classify + extract + compare together into a full
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
from .extract import extract_fields, looks_like_other_doc_type

# The 20 reliability edge cases explicitly ask us to *perform* a comparison
# ("Please compare the SI and draft BL ... (attachments appear to have been
# dropped)"), unlike a normal "please send the draft BL" request. That's
# what distinguishes a genuine missing_attachment case from the ~45% of
# ordinary BL_COMPARISON emails that simply don't have a BL yet.
_ASKS_TO_COMPARE_RE = re.compile(r"\bcompare\b", re.IGNORECASE)

_SUPPORTED_SUFFIXES = {".txt", ".pdf", ".docx", ".xlsx"}
_SI_BL_ROLE_RE = re.compile(r"_(SI|BL)\.\w+$", re.IGNORECASE)

_DEFAULT_RESULT: dict[str, object] = {
    "category": "GENERAL",
    "status": "OK",
    "review_reason": None,
    "has_defect": False,
    "defect_fields": [],
}


def _find_comparable_pair(attachments: list[str]):
    """Return (si_path, bl_path) if attachments are exactly one SI + one BL
    file, each in a format we can parse (txt/pdf/docx/xlsx — SI and BL need
    not share the same format, e.g. an xlsx SI with a docx BL), else None."""
    if len(attachments) != 2:
        return None
    si_path = bl_path = None
    for a in attachments:
        if Path(a).suffix.lower() not in _SUPPORTED_SUFFIXES:
            return None
        m = _SI_BL_ROLE_RE.search(a)
        if not m:
            return None
        if m.group(1).upper() == "SI":
            si_path = a
        else:
            bl_path = a
    return (si_path, bl_path) if si_path and bl_path else None


def _raw_text_for_doc_type_check(path: Path) -> str | None:
    """Flattened text for the wrong_doc_type header/label check — only
    meaningful for text-bearing formats (txt/PDF); no known wrong_doc_type
    cases use docx/xlsx in this dataset, so those are skipped."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
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

    pair = _find_comparable_pair(attachments)
    if pair is None:
        # Two attachments are present but not a recognizable SI+BL pair in
        # a format we support -- escalate instead of silently reporting OK,
        # which would hide any real discrepancy.
        result["status"] = "NEEDS_REVIEW"
        result["review_reason"] = "unreadable"
        return result

    si_path, bl_path = pair
    si_full = data_dir / si_path
    bl_full = data_dir / bl_path

    try:
        for path in (si_full, bl_full):
            doc_text = _raw_text_for_doc_type_check(path)
            if doc_text is not None and looks_like_other_doc_type(doc_text):
                result["status"] = "NEEDS_REVIEW"
                result["review_reason"] = "wrong_doc_type"
                return result

        si_fields = extract_fields(si_full)
        bl_fields = extract_fields(bl_full)
    except Exception:
        # Garbled/truncated/corrupt file (e.g. no /Root object in a PDF).
        result["status"] = "NEEDS_REVIEW"
        result["review_reason"] = "unreadable"
        return result

    if not si_fields or not bl_fields:
        # Nothing at all was extracted from one side -- most likely a
        # scanned/image-only document with no text layer (needs OCR, M8),
        # not a document that just happens to have every field blank.
        result["status"] = "NEEDS_REVIEW"
        result["review_reason"] = "unreadable"
        return result

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
