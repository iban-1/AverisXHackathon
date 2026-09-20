"""M3: parse a plain-text SI/BL attachment into the 7 canonical fields.

Attachments render as "Label: value" lines (see synonyms.py for the label
survey this was built from). Address/description continuation lines that
follow a name field are indented and are intentionally not folded into the
value — the compared identity is the name on the label's own line.
"""
import re

from .synonyms import field_for_label

# Label text itself is unconstrained (some documents mix in CJK characters,
# e.g. "Gross Weight毛重(KGS):") — synonyms.normalize_label() strips those
# before dictionary lookup. Only the ":" separator anchors the split.
_LABEL_LINE = re.compile(r"^([^:\n]{1,60}):\s*(.*)$")

# Placeholder values used by the "missing_value" edge cases (blank fields
# that are uncertainty, not a discrepancy) — extraction treats these as if
# the field were absent so downstream comparison/reliability logic (M6) can
# tell "not present" from "present but blank".
_PLACEHOLDER_RE = re.compile(r"^(?:\?+|_+|TBA)$", re.IGNORECASE)


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
