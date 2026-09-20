import glob
import json
from pathlib import Path

from sdoc.extract import extract_fields_txt, parse_container_count, parse_gross_weight_kg
from sdoc.synonyms import FIELDS

DATA = Path(__file__).resolve().parents[1] / "data"

SI_001 = """SHIPPING INSTRUCTION
========================================

Shipper/Exporter: APRIL FAR EAST (M) SDN BHD
  TOWER 2, AVENUE 5, LEVEL 6; BANGSAR SOUTH CITY, NO. 8 JALAN KERINCHI; 59200 KUALA LUMPUR, MALAYSIA
CONSIGNEE: MOORIM SP CO., LTD
  656, GANGNAM-DAERO, GANGNAM-GU; SEOUL, SOUTH KOREA; T. 82-2-3485-1500
NOTIFY PARTY: UAB NOVAKOPA
Port of Loading: PORT KLANG (WESTPORT), MALAYSIA (MYPKG)
Discharge Port: CALLAO, PERU (PECLL)
No. of Containers or Packages: 1 x 40'HC
Gross Weight (KG): 21,577 KG
Freight: PREPAID
"""


def test_extract_email_001_si():
    fields = extract_fields_txt(SI_001)
    assert fields["shipper"] == "APRIL FAR EAST (M) SDN BHD"
    assert fields["consignee"] == "MOORIM SP CO., LTD"
    assert fields["notify_party"] == "UAB NOVAKOPA"
    assert fields["port_of_loading"] == "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)"
    assert fields["port_of_discharge"] == "CALLAO, PERU (PECLL)"
    assert fields["container_count"] == "1 x 40'HC"
    assert fields["gross_weight_kg"] == "21,577 KG"
    assert "freight" not in fields  # not one of the 7 compared fields


def test_bilingual_label_is_handled():
    text = "Gross Weight毛重(KGS): 67,311 KG\n"
    fields = extract_fields_txt(text)
    assert fields["gross_weight_kg"] == "67,311 KG"


def test_placeholder_values_are_treated_as_absent():
    text = "Consignee: ???\nNotify Party: _______\nPort of Loading: TBA\n"
    fields = extract_fields_txt(text)
    assert fields == {}


def test_parse_container_count():
    assert parse_container_count("1 x 40'HC") == 1
    assert parse_container_count("6 x 40'HC") == 6


def test_parse_gross_weight_kg():
    assert parse_gross_weight_kg("21,577 KG") == 21577.0
    assert parse_gross_weight_kg("131,058 KG") == 131058.0


def test_full_coverage_on_all_main_set_txt_pairs():
    """Every non-edge-case (email_001-500) txt/txt SI+BL pair should yield
    all 7 fields on both sides — extraction gaps should only ever occur on
    the deliberately messy edge cases (email_501-520)."""
    gaps = []
    for f in sorted(glob.glob(str(DATA / "inbox" / "email_*.json"))):
        e = json.loads(Path(f).read_text())
        num = int(e["email_id"].split("_")[1])
        if num > 500:
            continue
        atts = e.get("attachments", [])
        if len(atts) != 2 or not all(a.endswith(".txt") for a in atts):
            continue
        for att in atts:
            text = (DATA / att).read_text(encoding="utf-8")
            fields = extract_fields_txt(text)
            missing = [f2 for f2 in FIELDS if f2 not in fields]
            if missing:
                gaps.append((e["email_id"], att, missing))
    assert gaps == []
