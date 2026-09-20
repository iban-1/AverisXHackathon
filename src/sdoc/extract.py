"""M3: parse a plain-text SI/BL attachment into the 7 canonical fields.

Attachments render as "Label: value" lines (see synonyms.py for the label
survey this was built from). Address/description continuation lines that
follow a name field are indented and are intentionally not folded into the
value — the compared identity is the name on the label's own line.
"""
import re

from .synonyms import field_for_label, is_other_doc_type_label

# Label text itself is unconstrained (some documents mix in CJK characters,
# e.g. "Gross Weight毛重(KGS):") — synonyms.normalize_label() strips those
# before dictionary lookup. Only the ":" separator anchors the split.
_LABEL_LINE = re.compile(r"^([^:\n]{1,60}):\s*(.*)$")

# Placeholder values used by the "missing_value" edge cases (blank fields
# that are uncertainty, not a discrepancy) — extraction treats these as if
# the field were absent so downstream comparison/reliability logic (M6) can
# tell "not present" from "present but blank". Covers bare "???"/"_______",
# a blank with a stray leftover unit ("____MT"), and word placeholders
# (N/A, TBA, NIL, PENDING) — the full set observed across the dataset.
_PLACEHOLDER_RE = re.compile(
    r"^(?:[_?]+\s*(?:MTS?|KGS?)?|N/?A|TBA|NIL|PENDING)$", re.IGNORECASE
)


def extract_fields_txt(text: str) -> dict[str, str]:
    """Return {field_name: raw_value_string} for the 7 fields found in a
    plain-text SI/BL attachment. A field with only a placeholder value
    (`???`, `_______`, `TBA`) or no attachment text at all is omitted."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        m = _LABEL_LINE.match(line)
        if not m:
            continue
        label, value = m.group(1), m.group(2).strip()
        field = field_for_label(label)
        if not field or field in fields:
            continue
        if not value or _PLACEHOLDER_RE.match(value):
            continue
        fields[field] = value
    return fields


_EXPECTED_HEADERS = ("SHIPPING INSTRUCTION", "BILL OF LADING")


def looks_like_other_doc_type(text: str) -> bool:
    """True if a "BL"/"SI" attachment is actually some other document type
    (Commercial Invoice, Packing List, Certificate of Origin). Primary
    signal: the document's own header line doesn't name it as either an SI
    or a BL. Secondary/defense-in-depth signal: labels from that other
    document family (invoice/certificate fields — see
    synonyms.OTHER_DOC_TYPE_LABELS) rather than any of the 7 compared ones."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and not any(h in lines[0].upper() for h in _EXPECTED_HEADERS):
        return True
    for line in text.splitlines():
        m = _LABEL_LINE.match(line)
        if m and is_other_doc_type_label(m.group(1)):
            return True
    return False


def normalize_text_value(value: str) -> str:
    """Case/whitespace-insensitive form for comparing name/port fields."""
    return " ".join(value.strip().split()).upper()


_LEADING_INT_RE = re.compile(r"(\d+)")


def parse_container_count(value: str) -> int | None:
    """'1 x 40'HC' -> 1"""
    m = _LEADING_INT_RE.search(value)
    return int(m.group(1)) if m else None


_NUMBER_RE = re.compile(r"([\d,]+(?:\.\d+)?)")


def parse_gross_weight_kg(value: str) -> float | None:
    """'21,577 KG' -> 21577.0"""
    m = _NUMBER_RE.search(value)
    return float(m.group(1).replace(",", "")) if m else None
