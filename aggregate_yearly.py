"""
Aggregate monthly data into yearly summaries.

The issue: the same yield value is repeated across all months in a year.
Solution: create one row per site and year with features aggregated over
the growing season, then split the result chronologically.

Usage:
    python aggregate_yearly.py
"""

import pandas as pd

# Growing season months (May-September)
GROWING_SEASON = [5, 6, 7, 8, 9]

# Last year that goes to the training set
LAST_TRAIN_YEAR = 2020

LAG_COLUMNS = ['yield_lag_1', 'yield_lag_2', 'yield_lag_3', 'yield_rolling_3yr']


def aggregate_site_year(site, year, group):
    """Collapse the monthly rows of one site and year into a single row."""
    row = {
        'site_name': site,
        'year': year,
        'latitude': group['latitude'].iloc[0],
        'longitude': group['longitude'].iloc[0],
        'yield_tha': group['yield_tha'].iloc[0]  # Same for all months
    }

    # Growing season subset
    gs_data = group[group['month'].isin(GROWING_SEASON)]

    # Temperature features - mean across growing season
    row['temp_max_gs_mean'] = gs_data['temp_max'].mean()
    row['temp_min_gs_mean'] = gs_data['temp_min'].mean()
    row['temp_mean_gs_mean'] = gs_data['temp_mean'].mean()
    row['temp_range_gs_mean'] = gs_data['temp_range'].mean()

    # Precipitation - sum across growing season
    row['precip_total_gs_sum'] = gs_data['precip_total_mm'].sum()
    row['precip_days_gs_sum'] = gs_data['precip_days_gt1mm'].sum()
    row['precip_max_daily_gs_max'] = gs_data['precip_max_daily_mm'].max()

    # Radiation - mean across growing season
    row['radiation_gs_mean'] = gs_data['radiation_avg_mjm2'].mean()

    # Humidity - mean across growing season
    row['humidity_max_gs_mean'] = gs_data['humidity_max'].mean()
    row['humidity_min_gs_mean'] = gs_data['humidity_min'].mean()

    # Wind - mean across growing season
    row['wind_max_gs_mean'] = gs_data['wind_max_kmh'].mean()

    # ET0 - sum across growing season
    row['et0_gs_sum'] = gs_data['et0_mm'].sum()

    # GDD - sum across growing season
    row['gdd_base5_gs_sum'] = gs_data['gdd_base5'].sum()

    # Stress indicators - max/sum across growing season
    row['heat_stress_days_gs_sum'] = gs_data['heat_stress_days_30c'].sum()
    row['frost_days_gs_sum'] = gs_data['frost_days'].sum()
    row['dry_spell_gs_max'] = gs_data['dry_spell_max_days'].max()

    # NDVI - max across growing season
    row['ndvi_max_gs'] = gs_data['ndvi_max'].max()
    row['ndvi_mean_gs'] = gs_data['ndvi_mean'].mean()

    # EVI - max across growing season
    row['evi_max_gs'] = gs_data['evi_max'].max()
    row['evi_mean_gs'] = gs_data['evi_mean'].mean()

    # Soil features - static (take first value)
    row['soil_phh2o'] = group['soil_phh2o_avg_0_30cm'].iloc[0]
    row['soil_clay'] = group['soil_clay_avg_0_30cm'].iloc[0]
    row['soil_sand'] = group['soil_sand_avg_0_30cm'].iloc[0]
    row['soil_silt'] = group['soil_silt_avg_0_30cm'].iloc[0]
    row['soil_soc'] = group['soil_soc_avg_0_30cm'].iloc[0]
    row['soil_nitrogen'] = group['soil_nitrogen_avg_0_30cm'].iloc[0]
    row['soil_cec'] = group['soil_cec_avg_0_30cm'].iloc[0]
    row['soil_bdod'] = group['soil_bdod_avg_0_30cm'].iloc[0]
    row['soil_moisture_mean'] = group['soil_moisture_mean'].mean()

    # Cumulative features - take December value (or last month)
    dec_data = group[group['month'] == 12]
    if len(dec_data) > 0:
        row['precip_cumulative'] = dec_data['precip_cumulative_mm'].iloc[0]
        row['gdd_cumulative'] = dec_data['gdd_cumulative'].iloc[0]
    else:
        # If December not available, take last month
        row['precip_cumulative'] = group['precip_cumulative_mm'].iloc[-1]
        row['gdd_cumulative'] = group['gdd_cumulative'].iloc[-1]

    # Derived features
    row['aridity_index'] = row['precip_total_gs_sum'] / row['et0_gs_sum'] if row['et0_gs_sum'] > 0 else 0

    # Lag features - these should be kept
    if 'yield_lag_1' in group.columns:
        for col in LAG_COLUMNS:
            row[col] = group[col].iloc[0]

    return row


def aggregate_yearly(monthly_df):
    """Return one row per site and year. Missing values are filled with 0."""
    rows = [
        aggregate_site_year(site, year, group)
        for (site, year), group in monthly_df.groupby(['site_name', 'year'])
    ]
    agg_df = pd.DataFrame(rows)

    nan_cols = agg_df.columns[agg_df.isna().any()].tolist()
    if nan_cols:
        print(f"\nWarning: Columns with NaN: {nan_cols}")
        print("Filling NaN with 0...")
        agg_df = agg_df.fillna(0)

    return agg_df


def split_by_year(agg_df, last_train_year=LAST_TRAIN_YEAR):
    """Chronological split: years up to last_train_year go to train."""
    train = agg_df[agg_df['year'] <= last_train_year].copy()
    test = agg_df[agg_df['year'] > last_train_year].copy()
    return train, test


def main():
    print("=" * 80)
    print("YEARLY AGGREGATION PIPELINE")
    print("=" * 80)

    # Load original data
    train_df = pd.read_csv('train_shortandy.csv')
    test_df = pd.read_csv('test_shortandy.csv')
    all_data = pd.concat([train_df, test_df], ignore_index=True)

    print(f"\nOriginal data: {len(all_data)} rows")
    print(f"Unique yields: {all_data['yield_tha'].nunique()}")
    print(f"Years: {all_data['year'].unique()}")
    print(f"Months per year: {all_data.groupby('year').size().unique()}")

    agg_df = aggregate_yearly(all_data)

    print(f"\nAggregated data: {len(agg_df)} rows")
    print(f"Unique yields: {agg_df['yield_tha'].nunique()}")
    print(f"Features: {len(agg_df.columns)}")

    train_agg, test_agg = split_by_year(agg_df)

    print(f"\nTrain: {len(train_agg)} rows ({train_agg['year'].min()}-{train_agg['year'].max()})")
    print(f"Test: {len(test_agg)} rows ({test_agg['year'].min()}-{test_agg['year'].max()})")

    # Save
    train_agg.to_csv('train_shortandy_yearly.csv', index=False)
    test_agg.to_csv('test_shortandy_yearly.csv', index=False)

    print("\n✅ Yearly aggregated data saved:")
    print("  - train_shortandy_yearly.csv")
    print("  - test_shortandy_yearly.csv")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Reduction: {len(all_data)} rows → {len(agg_df)} rows")
    print(f"Train samples: {len(train_agg)}")
    print(f"Test samples: {len(test_agg)}")
    print(f"Features: {len(agg_df.columns) - 5} (excluding ID columns)")


if __name__ == '__main__':
    main()
