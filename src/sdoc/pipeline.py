"""M5: tie classify + extract + compare together into a full submission.json.

Usage: python -m sdoc.pipeline [--data DIR] [--out FILE]
"""
import argparse
import json
from pathlib import Path

from .classify import classify
from .compare import compare_fields
from .extract import extract_fields_txt

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
        # Nothing to compare yet (0/1 attachments) -> defaults to
        # OK/no-defect, matching the ground-truth convention for
        # non-comparable emails. M6 refines this for the deliberate
        # missing_attachment edge cases.
        return result

    pair = _txt_pair(attachments)
    if pair is None:
        # Two attachments are present but not a parseable .txt SI+BL pair
        # (PDF/DOCX/XLSX -> M7/M8 not built yet, or unexpected naming). We
        # genuinely can't compare them -- escalate instead of silently
        # reporting OK, which would hide any real discrepancy.
        result["status"] = "NEEDS_REVIEW"
        result["has_defect"] = False
        result["defect_fields"] = []
        result["review_reason"] = "unreadable"
        return result

    si_path, bl_path = pair
    si_text = (data_dir / si_path).read_text(encoding="utf-8")
    bl_text = (data_dir / bl_path).read_text(encoding="utf-8")
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
