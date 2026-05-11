import logging

from src.services.occurrence.dedup import dedup


def _occ(type_, mmd):
    return {"type": type_, "mmd": mmd, "notes": "test"}


def test_no_duplicates_returns_same():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Lost Circulation", 2300.0)]
    assert dedup(occs) == occs


def test_removes_exact_type_mmd_duplicate():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0)]
    result = dedup(occs)
    assert len(result) == 1
    assert result[0] is occs[0]


def test_same_type_different_mmd_not_deduped():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1460.0)]
    assert len(dedup(occs)) == 2


def test_same_mmd_different_type_not_deduped():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Lost Circulation", 1450.0)]
    assert len(dedup(occs)) == 2


def test_none_mmd_deduped_by_type():
    occs = [_occ("Stuck Pipe", None), _occ("Stuck Pipe", None)]
    assert len(dedup(occs)) == 1


def test_none_mmd_different_types_not_deduped():
    occs = [_occ("Stuck Pipe", None), _occ("Lost Circulation", None)]
    assert len(dedup(occs)) == 2


def test_preserves_first_insertion_order():
    occs = [
        {"type": "Stuck Pipe", "mmd": 1450.0, "notes": "first"},
        {"type": "Stuck Pipe", "mmd": 1450.0, "notes": "second"},
    ]
    result = dedup(occs)
    assert result[0]["notes"] == "first"


def test_empty_list_returns_empty():
    assert dedup([]) == []


def test_logs_removed_count(caplog):
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0)]
    with caplog.at_level(logging.INFO, logger="src.services.occurrence.dedup"):
        result = dedup(occs)
    assert len(result) == 1
    assert "removed 2" in caplog.text


def test_no_log_when_no_duplicates(caplog):
    occs = [_occ("Stuck Pipe", 1450.0)]
    with caplog.at_level(logging.INFO, logger="src.services.occurrence.dedup"):
        dedup(occs)
    assert caplog.text == ""


def test_three_duplicates_one_kept():
    occs = [_occ("Kick", 3000.0)] * 3
    result = dedup(occs)
    assert len(result) == 1


def test_mixed_duplicates_and_unique():
    occs = [
        _occ("Stuck Pipe", 1450.0),
        _occ("Stuck Pipe", 1450.0),
        _occ("Lost Circulation", 2300.0),
        _occ("Kick", None),
        _occ("Kick", None),
    ]
    result = dedup(occs)
    assert len(result) == 3


def test_malformed_dict_no_type_key():
    occs = [{"mmd": 1450.0, "notes": "no type"}, {"mmd": 1450.0, "notes": "no type 2"}]
    result = dedup(occs)
    assert len(result) == 1


def test_malformed_dict_no_mmd_key():
    occs = [{"type": "Stuck Pipe", "notes": "no mmd"}, {"type": "Stuck Pipe", "notes": "no mmd 2"}]
    result = dedup(occs)
    assert len(result) == 1


def test_same_type_mmd_different_ddr_date_not_deduped():
    occs = [
        {"type": "Stuck Pipe", "mmd": 1450.0, "ddr_date_id": 1},
        {"type": "Stuck Pipe", "mmd": 1450.0, "ddr_date_id": 2},
    ]
    assert len(dedup(occs)) == 2


def test_same_type_mmd_same_ddr_date_deduped():
    occs = [
        {"type": "Stuck Pipe", "mmd": 1450.0, "ddr_date_id": 1},
        {"type": "Stuck Pipe", "mmd": 1450.0, "ddr_date_id": 1},
    ]
    assert len(dedup(occs)) == 1


def test_no_ddr_date_id_key_backward_compat():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0)]
    assert len(dedup(occs)) == 1
