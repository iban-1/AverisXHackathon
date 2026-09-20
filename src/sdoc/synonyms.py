"""Canonical field names and the label variants SI/BL documents use for them.

Built by scanning every "Label: value" line across all attachments/*.txt
files in the participant dataset (data/) and clustering the distinct labels
by meaning. Same list applies to PDF/DOCX/XLSX once those extractors land
(M7) since the renderer reuses these labels regardless of file format.
"""
import re

# The 7 fields the comparison covers.
FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

# normalized label (lowercase, whitespace-collapsed) -> canonical field name.
# Only labels that identify one of the 7 fields belong here. Labels seen in
# the data that belong to OTHER concepts (freight, HS code, vessel/voyage,
# booking/BL numbers, commodity) are deliberately left out so they're never
# mistaken for a compared field.
LABEL_TO_FIELD = {
    # shipper
    "shipper": "shipper",
    "shipper/exporter": "shipper",
    "shipper (principal or seller)": "shipper",
    "exporter": "shipper",
    # consignee
    "consignee": "consignee",
    "consignee (non-negotiable)": "consignee",
    "to the order of": "consignee",
    # notify_party
    "notify": "notify_party",
    "notify party": "notify_party",
    "notify party/intermediate consignee": "notify_party",
    # port_of_loading
    "port of loading": "port_of_loading",
    "port of loading (pol)": "port_of_loading",
    "load port": "port_of_loading",
    "pol": "port_of_loading",
    # port_of_discharge
    "discharge port": "port_of_discharge",
    "port of discharge": "port_of_discharge",
    "port of discharge (pod)": "port_of_discharge",
    "pod": "port_of_discharge",
    # container_count
    "no. of containers": "container_count",
    "no. of containers or packages": "container_count",
    "total containers": "container_count",
    "container count": "container_count",
    # gross_weight_kg
    "gross wt (kgs)": "gross_weight_kg",
    "gross wt": "gross_weight_kg",
    "gross weight": "gross_weight_kg",
    "gross weight (kg)": "gross_weight_kg",
    "gross weight (kgs)": "gross_weight_kg",
    "total gross wt (kgs)": "gross_weight_kg",
    "total gross weight (kg)": "gross_weight_kg",
    "total gross weight": "gross_weight_kg",
}

# Labels seen in the data that mark a document as NOT an SI/BL at all
# (commercial invoice, packing list, certificate of origin) — used to detect
# the `wrong_doc_type` NEEDS_REVIEW case (M6).
OTHER_DOC_TYPE_LABELS = {
    "invoice no.",
    "invoice date",
    "seller",
    "buyer",
    "total amount",
    "certificate no.",
    "issuing authority",
    "country of origin",
}


_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]+")


def normalize_label(raw_label: str) -> str:
    # Some documents mix in CJK characters right before the value, e.g.
    # "Gross Weight毛重(KGS)" — drop anything outside ASCII before matching,
    # and make sure dropping them didn't glue "(KGS)" onto the previous word.
    ascii_only = _NON_ASCII_RE.sub(" ", raw_label)
    ascii_only = re.sub(r"(?<=[A-Za-z])\(", " (", ascii_only)
    return " ".join(ascii_only.strip().lower().split())


def _normalize_label_parens_stripped(raw_label: str) -> str:
    """Fallback for bilingual DOCX/XLSX labels where CJK text is glued
    *inside the same parens* as an English abbreviation, e.g.
    "Gross Wt (kgs) (毛重 KGS)" — normalize_label() alone leaves a stray
    "( kgs)" behind. Drops every parenthetical group entirely."""
    ascii_only = _NON_ASCII_RE.sub(" ", raw_label)
    no_parens = re.sub(r"\([^)]*\)", " ", ascii_only)
    return " ".join(no_parens.strip().lower().split())


def field_for_label(raw_label: str) -> str | None:
    """Return the canonical field name for a raw document label, or None."""
    field = LABEL_TO_FIELD.get(normalize_label(raw_label))
    if field:
        return field
    return LABEL_TO_FIELD.get(_normalize_label_parens_stripped(raw_label))


def is_other_doc_type_label(raw_label: str) -> bool:
    return normalize_label(raw_label) in OTHER_DOC_TYPE_LABELS
