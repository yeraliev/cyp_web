"""Tests for the data collection tool (collect_monthly_shortandy.py).

The API is replaced by a fake response, so the tests need no network.
"""
import pandas as pd
import pytest

import collect_monthly_shortandy as collect

SITE = {"Test_Site": {"lat": 51.6, "lon": 71.0}}

# Four days of fake daily weather
DAILY = {
    "temperature_2m_max": [31.0, 20.0, 10.0, -1.0],
    "temperature_2m_min": [15.0, 10.0, 0.0, -5.0],
    "temperature_2m_mean": [25.0, 15.0, 5.0, -3.0],
    "precipitation_sum": [0.0, 5.0, 0.5, 2.0],
    "shortwave_radiation_sum": [20.0, 20.0, 20.0, 20.0],
    "relative_humidity_2m_max": [80.0, 80.0, 80.0, 80.0],
    "relative_humidity_2m_min": [40.0, 40.0, 40.0, 40.0],
    "wind_speed_10m_max": [10.0, 10.0, 10.0, 10.0],
    "et0_fao_evapotranspiration": [4.0, 3.0, 2.0, 1.0],
}


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"daily": DAILY}


@pytest.fixture
def api_calls(monkeypatch):
    """Replace requests.get with a fake and record the request parameters."""
    calls = []

    def fake_get(url, params=None, **kwargs):
        calls.append(params)
        return FakeResponse()

    monkeypatch.setattr(collect.requests, "get", fake_get)
    monkeypatch.setattr(collect.time, "sleep", lambda seconds: None)
    return calls


def test_max_dry_spell():
    precipitation = pd.Series([0.0, 0.5, 5.0, 0.0, 0.0, 0.9, 2.0])
    assert collect._max_dry_spell(precipitation) == 3


def test_one_weather_record_per_month(api_calls):
    df = collect.collect_monthly_weather(SITE, 2020, 2020)
    assert len(df) == 12
    assert list(df["month"]) == list(range(1, 13))


def test_weather_features_are_computed_from_daily_values(api_calls):
    row = collect.collect_monthly_weather(SITE, 2020, 2020).iloc[0]
    assert row["precip_total_mm"] == 7.5
    assert row["precip_days_gt1mm"] == 2
    assert row["et0_mm"] == 10.0
    assert row["gdd_base5"] == 30.0  # (25-5) + (15-5) + 0 + 0
    assert row["heat_stress_days_30c"] == 1
    assert row["frost_days"] == 1
    assert row["dry_spell_max_days"] == 1


def test_request_covers_the_whole_month(api_calls):
    collect.collect_monthly_weather(SITE, 2020, 2020)
    february = api_calls[1]
    assert february["start_date"] == "2020-02-01"
    assert february["end_date"] == "2020-02-29"  # leap year
    assert february["latitude"] == 51.6


def test_failed_request_is_skipped(monkeypatch):
    def failing_get(*args, **kwargs):
        raise collect.requests.exceptions.ConnectionError("no network")

    monkeypatch.setattr(collect.requests, "get", failing_get)
    monkeypatch.setattr(collect.time, "sleep", lambda seconds: None)
    assert collect.collect_monthly_weather(SITE, 2020, 2020).empty


def make_weather(years):
    rows = [
        {"site_name": "Test_Site", "year": year, "month": month,
         "precip_total_mm": 10.0, "gdd_base5": 100.0, "et0_mm": 50.0}
        for year in years for month in range(1, 13)
    ]
    return pd.DataFrame(rows)


def test_merge_converts_yield_to_tonnes_per_hectare():
    merged = collect.merge_all(make_weather([2010]), pd.DataFrame(), pd.DataFrame())
    # 4.2 centners per hectare in the statistics = 0.42 t/ha
    assert (merged["yield_tha"] == 0.42).all()


def test_merge_adds_cumulative_and_lag_features():
    merged = collect.merge_all(make_weather([2010, 2011]), pd.DataFrame(), pd.DataFrame())
    december = merged[(merged["year"] == 2010) & (merged["month"] == 12)].iloc[0]
    assert december["precip_cumulative_mm"] == 120.0
    assert december["gdd_cumulative"] == 1200.0
    assert (merged.loc[merged["year"] == 2011, "yield_lag_1"] == 0.42).all()
