import json
from pathlib import Path

from src.services.occurrence.infer_mmd import MMDInferenceService


def _log(start, end, depth, activity="drilling"):
    return {
        "start_time": start,
        "end_time": end,
        "duration_hours": 1.0,
        "activity": activity,
        "depth_md": depth,
        "comment": None,
    }


def test_uses_problem_line_depth_when_present():
    logs = [_log("06:00", "07:00", 1400.0), _log("07:00", "08:00", 1455.0, "stuck pipe")]
    assert MMDInferenceService.infer_mmd(1, logs) == 1455.0


def test_backward_scan_one_row():
    logs = [_log("06:00", "07:00", 1430.0), _log("07:00", "08:00", None, "stuck pipe")]
    assert MMDInferenceService.infer_mmd(1, logs) == 1430.0


def test_backward_scan_multiple_rows():
    logs = [
        _log("05:00", "06:00", 2300.0),
        _log("06:00", "07:00", None),
        _log("07:00", "08:00", None, "kick"),
    ]
    assert MMDInferenceService.infer_mmd(2, logs) == 2300.0


def test_returns_none_when_no_depth_anywhere():
    logs = [_log("07:00", "08:00", None, "stuck pipe")]
    assert MMDInferenceService.infer_mmd(0, logs) is None


def test_problem_line_skips_later_rows():
    logs = [_log("07:00", "08:00", None, "stuck pipe"), _log("08:00", "09:00", 1500.0)]
    assert MMDInferenceService.infer_mmd(0, logs) is None


def test_returns_float_not_int():
    logs = [_log("07:00", "08:00", 1450, "stuck pipe")]
    result = MMDInferenceService.infer_mmd(0, logs)
    assert result == 1450.0
    assert isinstance(result, float)


def test_problem_line_first_row_with_depth():
    logs = [
        _log("00:00", "01:00", 980.0, "washout detected"),
        _log("01:00", "02:00", 990.0),
    ]
    assert MMDInferenceService.infer_mmd(0, logs) == 980.0


def test_problem_line_first_row_no_depth_returns_none():
    logs = [
        _log("00:00", "01:00", None, "kick"),
        _log("01:00", "02:00", 1000.0),
    ]
    assert MMDInferenceService.infer_mmd(0, logs) is None


def test_problem_line_depth_priority_over_earlier():
    logs = [_log("05:00", "06:00", 1000.0), _log("06:00", "07:00", 1050.0, "stuck pipe")]
    assert MMDInferenceService.infer_mmd(1, logs) == 1050.0


def test_backward_scan_stops_at_first_non_null():
    logs = [
        _log("00:00", "01:00", 1200.0),
        _log("01:00", "02:00", 1250.0),
        _log("02:00", "03:00", None, "kick"),
    ]
    assert MMDInferenceService.infer_mmd(2, logs) == 1250.0


def test_depth_zero_treated_as_valid():
    logs = [_log("08:00", "09:00", 0.0, "surface blowout")]
    result = MMDInferenceService.infer_mmd(0, logs)
    assert result == 0.0
    assert isinstance(result, float)


def test_all_null_multiple_rows():
    logs = [
        _log("00:00", "01:00", None),
        _log("01:00", "02:00", None),
        _log("02:00", "03:00", None, "wellhead issue"),
    ]
    assert MMDInferenceService.infer_mmd(2, logs) is None


def test_out_of_bounds_index_raises():
    import pytest
    logs = [_log("06:00", "07:00", 1450.0)]
    with pytest.raises(ValueError):
        MMDInferenceService.infer_mmd(1, logs)


def test_negative_index_raises():
    import pytest
    logs = [_log("06:00", "07:00", 1450.0)]
    with pytest.raises(ValueError):
        MMDInferenceService.infer_mmd(-1, logs)


def test_non_numeric_depth_on_problem_line_falls_through_to_scan():
    logs = [_log("06:00", "07:00", 1430.0), {"start_time": "07:00", "end_time": "08:00",
            "duration_hours": 1.0, "activity": "stuck pipe", "depth_md": "N/A", "comment": None}]
    assert MMDInferenceService.infer_mmd(1, logs) == 1430.0


def test_non_numeric_depth_in_scan_skipped():
    logs = [
        _log("05:00", "06:00", 1200.0),
        {"start_time": "06:00", "end_time": "07:00", "duration_hours": 1.0,
         "activity": "reaming", "depth_md": "unknown", "comment": None},
        _log("07:00", "08:00", None, "kick"),
    ]
    assert MMDInferenceService.infer_mmd(2, logs) == 1200.0


def test_non_dict_element_returns_none():
    logs = [None, _log("07:00", "08:00", 1450.0)]
    assert MMDInferenceService.infer_mmd(0, logs) is None


def test_fixture_accuracy():
    cases = json.loads(
        (Path(__file__).parent / "fixtures" / "expected_mmd_inference.json").read_text()
    )
    correct = 0
    for c in cases:
        result = MMDInferenceService.infer_mmd(c["problem_index"], c["time_logs"])
        expected = c["expected_mmd"]
        if expected is None:
            if result is None:
                correct += 1
        elif result is not None and abs(result - expected) <= 10.0:
            correct += 1
    accuracy = correct / len(cases)
    assert accuracy >= 0.85, (
        f"mMD inference accuracy {accuracy:.1%} below 85% ({correct}/{len(cases)})"
    )
