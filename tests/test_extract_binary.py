"""M7: PDF/DOCX/XLSX extraction."""
import glob
import json
import re
from pathlib import Path

from sdoc.extract import extract_fields, extract_fields_docx, extract_fields_pdf, extract_fields_xlsx
from sdoc.synonyms import FIELDS

DATA = Path(__file__).resolve().parents[1] / "data"


def test_pdf_pair_email_059_matches_exactly():
    si = extract_fields_pdf(DATA / "attachments" / "email_059_SI.pdf")
    bl = extract_fields_pdf(DATA / "attachments" / "email_059_BL.pdf")
    for f in FIELDS:
        assert f in si, f
        assert f in bl, f
    assert si["shipper"] == bl["shipper"] == "APRIL FINE PAPER TRADING"
    assert si["port_of_loading"] == bl["port_of_loading"] == "BUATAN, INDONESIA"
    assert si["gross_weight_kg"] == bl["gross_weight_kg"] == "131,322 KG"


def test_docx_bilingual_labels():
    fields = extract_fields_docx(DATA / "attachments" / "email_055_BL.docx")
    assert fields["shipper"] == "APRIL FINE PAPER TRADING"
    assert fields["consignee"] == "AL GURG STATIONERY LLC"
    assert fields["port_of_loading"] == "SINGAPORE"
    assert fields["container_count"] == "12 x 20'FCL"
    assert fields["gross_weight_kg"] == "243,588"


def test_xlsx_pipe_joined_address_and_numeric_weight():
    fields = extract_fields_xlsx(DATA / "attachments" / "email_005_SI.xlsx")
    assert fields["shipper"] == "ASIA PACIFIC PAPERBOARD TRADING PTE LTD"
    assert fields["consignee"] == "BALL & DOGGETT AUSTRALIA PTY LTD"
    assert fields["gross_weight_kg"] == "341715"  # raw numeric cell, no "KG" suffix


def test_dispatcher_picks_extractor_by_suffix():
    assert extract_fields(DATA / "attachments" / "email_059_SI.pdf")["shipper"]
    assert extract_fields(DATA / "attachments" / "email_055_BL.docx")["shipper"]
    assert extract_fields(DATA / "attachments" / "email_005_SI.xlsx")["shipper"]


def test_label_leakage_in_garbled_pdf_text_is_treated_as_missing_not_guessed():
    # email_407_SI.pdf's own text layer is corrupted: "Notify
    # Party/Intermediate ConsNigAnGeAePPA EXPORTS" (the long label
    # visually overlaps its own value in the source PDF). The exact label
    # match fails, and without a leakage guard a shorter "notify"
    # alternative would capture the leftover label fragments as a bogus
    # value -- worse than just not extracting it.
    fields = extract_fields(DATA / "attachments" / "email_407_SI.pdf")
    assert "notify_party" not in fields


# Attachment sides where the PDF's own text layer is corrupted enough that
# a field is deliberately left unextracted rather than guessed (see
# test_label_leakage_in_garbled_pdf_text_is_treated_as_missing_not_guessed).
# The email still resolves correctly overall -- to NEEDS_REVIEW/missing_value
# via pipeline.py -- rather than a false-positive mismatch.
_KNOWN_CORRUPTED_SIDES = {
    ("email_208", "attachments/email_208_SI.pdf"): {"notify_party"},
    ("email_351", "attachments/email_351_BL.pdf"): {"notify_party"},
    ("email_407", "attachments/email_407_SI.pdf"): {"notify_party"},
}


def test_full_coverage_on_all_main_set_binary_pairs():
    """Every main-set (email_001-500) SI+BL pair — of any supported format,
    same or mixed — should yield all 7 fields on both sides, except the
    known-corrupted sides above."""
    gaps = []
    for f in sorted(glob.glob(str(DATA / "inbox" / "email_*.json"))):
        e = json.loads(Path(f).read_text())
        num = int(e["email_id"].split("_")[1])
        if num > 500:
            continue
        atts = e.get("attachments", [])
        if len(atts) != 2:
            continue
        si = [a for a in atts if re.search(r"_SI\.\w+$", a)]
        bl = [a for a in atts if re.search(r"_BL\.\w+$", a)]
        if len(si) != 1 or len(bl) != 1:
            continue
        for att in atts:
            fields = extract_fields(DATA / att)
            allowed = _KNOWN_CORRUPTED_SIDES.get((e["email_id"], att), set())
            missing = [f2 for f2 in FIELDS if f2 not in fields and f2 not in allowed]
            if missing:
                gaps.append((e["email_id"], att, missing))
    assert gaps == []
