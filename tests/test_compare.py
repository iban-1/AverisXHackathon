from sdoc.compare import compare_fields

OK_SI = {
    "shipper": "APRIL FAR EAST (M) SDN BHD",
    "consignee": "MOORIM SP CO., LTD",
    "notify_party": "UAB NOVAKOPA",
    "port_of_loading": "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)",
    "port_of_discharge": "CALLAO, PERU (PECLL)",
    "container_count": "1 x 40'HC",
    "gross_weight_kg": "21,577 KG",
}


def test_identical_fields_are_ok():
    result = compare_fields(OK_SI, dict(OK_SI))
    assert result == {
        "status": "OK",
        "has_defect": False,
        "defect_fields": [],
        "review_reason": None,
    }


def test_case_and_whitespace_differences_are_not_a_mismatch():
    bl = dict(OK_SI)
    bl["shipper"] = "  april far east (m)   sdn bhd "
    result = compare_fields(OK_SI, bl)
    assert result["status"] == "OK"


def test_container_count_mismatch_matches_problem_statement_example():
    # SI: 3 containers / 22,000 kg. BL: 4 containers / 22,000 kg -> only
    # container_count flagged (from the hackathon problem statement's own
    # worked example).
    si = dict(OK_SI, container_count="3 x 40'HC", gross_weight_kg="22,000 KG")
    bl = dict(OK_SI, container_count="4 x 40'HC", gross_weight_kg="22,000 KG")
    result = compare_fields(si, bl)
    assert result["status"] == "MISMATCH"
    assert result["defect_fields"] == ["container_count"]
    assert result["has_defect"] is True


def test_multiple_field_mismatch_email_004():
    si = dict(OK_SI, consignee="EAST BRIGHT FZ-LLC", notify_party="EAST BRIGHT FZ-LLC")
    bl = dict(OK_SI, consignee="UAB NOVAKOPA", notify_party="UAB NOVAKOPA")
    result = compare_fields(si, bl)
    assert result["status"] == "MISMATCH"
    assert set(result["defect_fields"]) == {"consignee", "notify_party"}


def test_missing_field_on_either_side_escalates_instead_of_guessing():
    si_incomplete = dict(OK_SI)
    del si_incomplete["gross_weight_kg"]
    result = compare_fields(si_incomplete, dict(OK_SI))
    assert result == {
        "status": "NEEDS_REVIEW",
        "has_defect": False,
        "defect_fields": [],
        "review_reason": "missing_value",
    }


def test_gross_weight_numeric_normalization():
    bl = dict(OK_SI)
    bl["gross_weight_kg"] = "21577 KG"  # no thousands separator
    result = compare_fields(OK_SI, bl)
    assert result["status"] == "OK"
