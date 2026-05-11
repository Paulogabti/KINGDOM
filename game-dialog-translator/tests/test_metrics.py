from src.utils import calc_lines_per_minute, calc_eta_seconds

def test_eta_metrics():
    lpm = calc_lines_per_minute(120, 120)
    assert round(lpm, 1) == 60.0
    assert int(calc_eta_seconds(60, lpm)) == 60
