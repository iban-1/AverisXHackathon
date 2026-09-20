from sdoc.synonyms import field_for_label, is_other_doc_type_label, FIELDS


def test_all_seven_fields_have_at_least_one_label():
    covered = set()
    from sdoc.synonyms import LABEL_TO_FIELD

    covered.update(LABEL_TO_FIELD.values())
    assert covered == set(FIELDS)


def test_label_variants_resolve_to_the_same_field():
    assert field_for_label("Port of Loading") == "port_of_loading"
    assert field_for_label("Load Port") == "port_of_loading"
    assert field_for_label("POL") == "port_of_loading"
    assert field_for_label("Port of Loading (POL)") == "port_of_loading"

    assert field_for_label("Consignee") == "consignee"
    assert field_for_label("Consignee (Non-Negotiable)") == "consignee"
    assert field_for_label("To the Order of") == "consignee"

    assert field_for_label("Gross Wt (kgs)") == "gross_weight_kg"
    assert field_for_label("Gross Weight (KG)") == "gross_weight_kg"


def test_unrelated_labels_do_not_match():
    assert field_for_label("Freight") is None
    assert field_for_label("HS Code") is None
    assert field_for_label("Bill of Lading No.") is None
    assert field_for_label("Vessel Name") is None


def test_other_doc_type_labels():
    assert is_other_doc_type_label("Invoice No.")
    assert is_other_doc_type_label("Buyer")
    assert not is_other_doc_type_label("Shipper")
