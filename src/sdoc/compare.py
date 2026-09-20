"""M4: compare extracted SI vs BL fields and decide the outcome.

Field-level comparison only — attachment-count issues (missing/extra
attachments) and document-type/readability issues are handled by the
caller (pipeline.py) before it gets this far; see M5/M6.
"""
from .extract import normalize_text_value, parse_container_count, parse_gross_weight_kg
from .synonyms import FIELDS

_NUMERIC_PARSERS = {
    "container_count": parse_container_count,
    "gross_weight_kg": parse_gross_weight_kg,
}


def _normalized_value(field: str, raw_value: str):
    parser = _NUMERIC_PARSERS.get(field)
    return parser(raw_value) if parser else normalize_text_value(raw_value)


def compare_fields(si_fields: dict[str, str], bl_fields: dict[str, str]) -> dict:
    """Compare two {field: raw_value} dicts (from extract_fields_txt or an
    equivalent extractor) across the 7 canonical fields.

    A field absent on either side (extraction couldn't find it, or it was
    only a placeholder like "???") is NOT treated as a mismatch — the system
    genuinely can't decide — and the whole result escalates to
    NEEDS_REVIEW / missing_value instead of guessing.
    """
    missing = [f for f in FIELDS if f not in si_fields or f not in bl_fields]
    if missing:
        return {
            "status": "NEEDS_REVIEW",
            "has_defect": False,
            "defect_fields": [],
            "review_reason": "missing_value",
        }

    defect_fields = [
        field
        for field in FIELDS
        if _normalized_value(field, si_fields[field]) != _normalized_value(field, bl_fields[field])
    ]

    if defect_fields:
        return {
            "status": "MISMATCH",
            "has_defect": True,
            "defect_fields": defect_fields,
            "review_reason": None,
        }
    return {
        "status": "OK",
        "has_defect": False,
        "defect_fields": [],
        "review_reason": None,
    }
