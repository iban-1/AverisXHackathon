"""Export the real dataset (emails + attachments flattened to text) for the
browser-side live-demo artifact. Reuses the project's own extractors so the
demo sees exactly the text the Python pipeline itself works from.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pdfplumber
import docx as docx_lib
import openpyxl

DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "demo_data.js"


def flatten_pdf(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def flatten_docx(path: Path) -> str:
    document = docx_lib.Document(path)
    lines = []
    for para in document.paragraphs:
        if para.text.strip():
            lines.append(para.text.strip())
    for table in document.tables:
        for row in table.rows:
            if len(row.cells) < 2:
                continue
            label = row.cells[0].text.strip()
            value_lines = [l for l in row.cells[1].text.splitlines() if l.strip()]
            if not label or not value_lines:
                continue
            lines.append(f"{label}: {value_lines[0].strip()}")
            for extra in value_lines[1:]:
                lines.append(f"  {extra.strip()}")
    return "\n".join(lines)


def flatten_xlsx(path: Path) -> str:
    workbook = openpyxl.load_workbook(path, data_only=True)
    lines = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            if len(row) < 2 or row[0] is None or row[1] is None:
                continue
            label = str(row[0]).strip()
            raw_value = row[1]
            # Multi-part values are "|"-joined ("NAME | ADDRESS ..."); keep
            # only the compared identity, same as extract_fields_xlsx does.
            value = raw_value.split("|")[0].strip() if isinstance(raw_value, str) else raw_value
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def flatten(path: Path) -> str | None:
    suffix = path.suffix.lower()
    try:
        if suffix == ".txt":
            return path.read_text(encoding="utf-8")
        if suffix == ".pdf":
            return flatten_pdf(path)
        if suffix == ".docx":
            return flatten_docx(path)
        if suffix == ".xlsx":
            return flatten_xlsx(path)
    except Exception:
        return None  # genuinely unreadable -> None, same as the real pipeline
    return None


def main():
    emails = []
    attachment_text = {}

    for f in sorted((DATA / "inbox").glob("email_*.json")):
        e = json.loads(f.read_text(encoding="utf-8"))
        emails.append({
            "email_id": e["email_id"],
            "from": e.get("from", ""),
            "subject": e.get("subject", ""),
            "body": e.get("body", ""),
            "attachments": e.get("attachments", []),
        })
        for att in e.get("attachments", []):
            path = DATA / att
            if att in attachment_text:
                continue
            if not path.exists():
                attachment_text[att] = {"ok": False, "text": None, "size": 0}
                continue
            size = path.stat().st_size
            text = flatten(path) if size > 0 else None
            attachment_text[att] = {"ok": text is not None, "text": text, "size": size}

    bundle = {"emails": emails, "attachments": attachment_text}
    OUT.write_text(
        "window.SDOC_DEMO_DATA = " + json.dumps(bundle, ensure_ascii=True) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB) - {len(emails)} emails, {len(attachment_text)} attachments")


if __name__ == "__main__":
    main()
