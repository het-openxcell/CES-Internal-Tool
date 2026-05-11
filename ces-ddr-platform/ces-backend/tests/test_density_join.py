from src.services.occurrence.density_join import density_join


def _mud(depth, weight):
    return {"depth_md": depth, "mud_weight": weight, "viscosity": None, "ph": None, "comment": None}


def test_nearest_depth_exact_match():
    records = [_mud(1400.0, 1.80), _mud(1450.0, 1.85), _mud(1500.0, 1.90)]
    assert density_join(1450.0, records) == 1.85


def test_nearest_depth_between_records():
    records = [_mud(1400.0, 1.80), _mud(1500.0, 1.90)]
    assert density_join(1430.0, records) == 1.80


def test_nearest_depth_above_all():
    records = [_mud(1000.0, 1.75), _mud(1200.0, 1.80)]
    assert density_join(2000.0, records) == 1.80


def test_nearest_depth_below_all():
    records = [_mud(1000.0, 1.75), _mud(1200.0, 1.80)]
    assert density_join(500.0, records) == 1.75


def test_none_mmd_returns_deepest_record():
    records = [_mud(1000.0, 1.75), _mud(1200.0, 1.80), _mud(1400.0, 1.85)]
    assert density_join(None, records) == 1.85


def test_none_mmd_unsorted_returns_deepest_not_last():
    records = [_mud(1400.0, 1.85), _mud(1000.0, 1.75), _mud(1200.0, 1.80)]
    assert density_join(None, records) == 1.85


def test_empty_records_returns_none_with_mmd():
    assert density_join(1450.0, []) is None


def test_empty_records_returns_none_without_mmd():
    assert density_join(None, []) is None


def test_single_record_always_selected():
    records = [_mud(1000.0, 1.82)]
    assert density_join(5000.0, records) == 1.82


def test_returns_float():
    records = [_mud(1450, 2)]
    result = density_join(1450.0, records)
    assert isinstance(result, float)


def test_single_record_with_none_mmd():
    records = [_mud(800.0, 1.78)]
    assert density_join(None, records) == 1.78


def test_equidistant_picks_first_via_min():
    records = [_mud(1400.0, 1.80), _mud(1600.0, 1.90)]
    result = density_join(1500.0, records)
    assert result in (1.80, 1.90)


def test_three_records_picks_middle():
    records = [_mud(1000.0, 1.70), _mud(1450.0, 1.85), _mud(2000.0, 1.95)]
    assert density_join(1460.0, records) == 1.85


def test_missing_mud_weight_record_skipped_in_nearest_join():
    records = [
        {"depth_md": 1450.0, "mud_weight": None, "viscosity": None, "ph": None, "comment": None},
        _mud(1500.0, 1.90),
    ]
    assert density_join(1450.0, records) == 1.90


def test_missing_depth_md_record_skipped_in_nearest_join():
    records = [
        {"depth_md": None, "mud_weight": 1.80, "viscosity": None, "ph": None, "comment": None},
        _mud(1500.0, 1.90),
    ]
    assert density_join(1450.0, records) == 1.90


def test_all_records_missing_depth_md_returns_none():
    records = [
        {"depth_md": None, "mud_weight": 1.80, "viscosity": None, "ph": None, "comment": None},
        {"depth_md": None, "mud_weight": 1.85, "viscosity": None, "ph": None, "comment": None},
    ]
    assert density_join(1450.0, records) is None


def test_missing_depth_md_key_absent_entirely():
    records = [{"mud_weight": 1.80}, _mud(1500.0, 1.90)]
    assert density_join(1450.0, records) == 1.90


def test_none_mmd_all_records_missing_depth_md_falls_back_to_last_mud_weight():
    records = [
        {"depth_md": None, "mud_weight": 1.80, "viscosity": None, "ph": None, "comment": None},
    ]
    assert density_join(None, records) == 1.80


def test_none_mmd_all_records_missing_both_depth_and_weight_returns_none():
    records = [{"depth_md": None, "mud_weight": None}]
    assert density_join(None, records) is None
