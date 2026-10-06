"""Tests for the data preparation tool (aggregate_yearly.py)."""
import pandas as pd
import pytest

from aggregate_yearly import aggregate_yearly, split_by_year

MONTHLY_COLUMNS = [
    'temp_max', 'temp_min', 'temp_mean', 'temp_range', 'precip_total_mm',
    'precip_days_gt1mm', 'precip_max_daily_mm', 'radiation_avg_mjm2',
    'humidity_max', 'humidity_min', 'wind_max_kmh', 'et0_mm', 'gdd_base5',
    'heat_stress_days_30c', 'frost_days', 'dry_spell_max_days',
    'ndvi_max', 'ndvi_mean', 'evi_max', 'evi_mean',
    'soil_phh2o_avg_0_30cm', 'soil_clay_avg_0_30cm', 'soil_sand_avg_0_30cm',
    'soil_silt_avg_0_30cm', 'soil_soc_avg_0_30cm', 'soil_nitrogen_avg_0_30cm',
    'soil_cec_avg_0_30cm', 'soil_bdod_avg_0_30cm', 'soil_moisture_mean',
    'precip_cumulative_mm', 'gdd_cumulative',
]


def make_site_year(site='A', year=2010, months=range(1, 13)):
    """Monthly rows for one site and year; every feature equals the month number."""
    df = pd.DataFrame({'month': list(months)})
    df['site_name'] = site
    df['year'] = year
    df['latitude'] = 51.7
    df['longitude'] = 71.0
    df['yield_tha'] = 1.0
    for col in MONTHLY_COLUMNS:
        df[col] = df['month'].astype(float)
    return df


def test_one_row_per_site_and_year():
    monthly = pd.concat([
        make_site_year('A', 2010), make_site_year('A', 2011), make_site_year('B', 2010),
    ])
    result = aggregate_yearly(monthly)
    assert len(result) == 3
    assert not result.duplicated(['site_name', 'year']).any()


def test_only_growing_season_months_are_aggregated():
    row = aggregate_yearly(make_site_year()).iloc[0]
    # Months 5-9: sum = 35, mean = 7, max = 9
    assert row['precip_total_gs_sum'] == 35
    assert row['temp_mean_gs_mean'] == 7
    assert row['precip_max_daily_gs_max'] == 9
    assert row['ndvi_max_gs'] == 9


def test_cumulative_features_use_december():
    row = aggregate_yearly(make_site_year()).iloc[0]
    assert row['precip_cumulative'] == 12
    assert row['gdd_cumulative'] == 12


def test_cumulative_features_fall_back_to_last_month():
    row = aggregate_yearly(make_site_year(months=range(1, 12))).iloc[0]
    assert row['precip_cumulative'] == 11


def test_aridity_index_is_precipitation_over_et0():
    monthly = make_site_year()
    monthly['et0_mm'] = 10.0
    row = aggregate_yearly(monthly).iloc[0]
    assert row['aridity_index'] == pytest.approx(35 / 50)


def test_aridity_index_is_zero_when_et0_is_zero():
    monthly = make_site_year()
    monthly['et0_mm'] = 0.0
    assert aggregate_yearly(monthly).iloc[0]['aridity_index'] == 0


def test_yield_is_kept_unchanged():
    assert aggregate_yearly(make_site_year()).iloc[0]['yield_tha'] == 1.0


def test_split_is_chronological():
    monthly = pd.concat([make_site_year(year=y) for y in (2019, 2020, 2021)])
    train, test = split_by_year(aggregate_yearly(monthly), last_train_year=2020)
    assert sorted(train['year']) == [2019, 2020]
    assert sorted(test['year']) == [2021]


def test_reproduces_published_yearly_datasets():
    """Running the tool on the monthly data must give the yearly files in the repository."""
    monthly = pd.concat(
        [pd.read_csv('train_shortandy.csv'), pd.read_csv('test_shortandy.csv')],
        ignore_index=True,
    )
    train, test = split_by_year(aggregate_yearly(monthly))

    for result, path in ((train, 'train_shortandy_yearly.csv'), (test, 'test_shortandy_yearly.csv')):
        expected = pd.read_csv(path)
        pd.testing.assert_frame_equal(
            result.reset_index(drop=True), expected, check_exact=False, check_dtype=False,
        )
