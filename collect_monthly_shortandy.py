#!/usr/bin/env python3
"""
=============================================================================
MONTHLY RESOLUTION — Shortandy, Akmola Oblast, Kazakhstan
=============================================================================
Multimodal crop yield prediction dataset — 100% real, monthly temporal resolution.

Structure: Each row = 1 site × 1 month × 1 year
  → 8 sites × 21 years × 12 months = 2,016 rows

Data sources (ALL REAL):
  ✅ Weather  → Open-Meteo Archive API (monthly aggregates, free)
  ✅ NDVI/EVI → NASA ORNL DAAC MODIS MOD13Q1 (monthly composites, free)
  ✅ Soil     → ISRIC SoilGrids 2.0 (static per site, free)
  ✅ Yield    → stat.gov.kz Bureau of National Statistics (annual target)

Target variable: yield_tha (annual wheat yield for Shortandy district)
  → Same for all 12 months of a year (district-level annual statistic)
  → ML model learns which months are most important for yield

How to run:
  pip install requests pandas numpy
  python collect_monthly_shortandy.py

  Faster test (3 years only):
  python collect_monthly_shortandy.py --year-start 2020 --year-end 2022

Output: data/monthly/shortandy_monthly_dataset.csv
  Expected: ~2,016 rows × 40+ columns
=============================================================================
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from calendar import monthrange

import requests
import pandas as pd
import numpy as np

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("monthly_collection.log")]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data") / "monthly"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# FIELD SITES — spatially distributed across Shortandy district (~40km span)
# =============================================================================
FIELD_SITES = {
    "Shortandy_SPCGF":  {"lat": 51.6025, "lon": 71.0400, "desc": "Barayev Research Center"},
    "Shortandy_North":   {"lat": 51.65,   "lon": 71.05,   "desc": "Northern fields"},
    "Shortandy_South":   {"lat": 51.55,   "lon": 71.00,   "desc": "Southern fields"},
    "Shortandy_West":    {"lat": 51.60,   "lon": 70.90,   "desc": "Western fields"},
    "Shortandy_East":    {"lat": 51.60,   "lon": 71.15,   "desc": "Eastern fields"},
    "Shortandy_NW":      {"lat": 51.67,   "lon": 70.95,   "desc": "Northwest elevated"},
    "Shortandy_SE":      {"lat": 51.53,   "lon": 71.10,   "desc": "Southeast lowland"},
    "Shortandy_Center":  {"lat": 51.59,   "lon": 71.02,   "desc": "Central district"},
}

YEAR_START = 2004
YEAR_END = 2024

# =============================================================================
# REAL YIELD — stat.gov.kz (Shortandy district, wheat, ц/га)
# =============================================================================
YIELD_WHEAT_CHA = {
    2004: 8.5,  2005: 9.1,  2006: 10.4,  2007: 9.3,  2008: 6.8,
    2009: 11.9, 2010: 4.2,  2011: 11.5,  2012: 5.6,  2013: 10.2,
    2014: 8.9,  2015: 10.9, 2016: 12.3,  2017: 9.6,
    2018: 14.3, 2019: 10.2, 2020: 14.9,  2021: 11.8538,
    2022: 12.1711, 2023: 6.5, 2024: 14.9,
}

YIELD_CEREALS_CHA = {
    2004: 8.3,  2005: 9.3,  2006: 10.4,  2007: 9.6,  2008: 6.9,
    2009: 12.5, 2010: 4.2,  2011: 11.8,  2012: 5.8,  2013: 11.1,
    2014: 9.5,  2015: 10.6687, 2016: 13.0876, 2017: 9.896,
    2018: 15.0, 2019: 10.7,    2020: 15.5,    2021: 11.9972,
    2022: 12.2959, 2023: 6.4,  2024: 15.4,
}


# =============================================================================
# MODULE 1: MONTHLY WEATHER — Open-Meteo Archive API
# =============================================================================

def collect_monthly_weather(sites, year_start, year_end):
    """
    ✅ 100% REAL monthly weather from Open-Meteo Archive API.
    Each row = 1 site × 1 month with aggregated weather features.
    """
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    all_records = []
    total_calls = len(sites) * (year_end - year_start + 1) * 12
    call_count = 0

    for site_name, site_info in sites.items():
        logger.info(f"Weather: {site_name}...")

        for year in range(year_start, year_end + 1):
            for month in range(1, 13):
                call_count += 1
                
                # Skip future months
                today = datetime.now()
                if year > today.year or (year == today.year and month > today.month):
                    continue

                last_day = monthrange(year, month)[1]
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day:02d}"

                # Don't go past today
                if end_date > today.strftime("%Y-%m-%d"):
                    end_date = today.strftime("%Y-%m-%d")

                params = {
                    "latitude": site_info["lat"],
                    "longitude": site_info["lon"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": ",".join([
                        "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
                        "precipitation_sum", "shortwave_radiation_sum",
                        "relative_humidity_2m_max", "relative_humidity_2m_min",
                        "wind_speed_10m_max", "et0_fao_evapotranspiration",
                    ]),
                    "timezone": "Asia/Almaty",
                }

                try:
                    resp = requests.get(BASE_URL, params=params, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()

                    if "daily" not in data:
                        continue

                    df = pd.DataFrame(data["daily"])

                    record = {
                        "site_name": site_name,
                        "year": year,
                        "month": month,
                        "latitude": site_info["lat"],
                        "longitude": site_info["lon"],
                        # Temperature
                        "temp_max": round(df["temperature_2m_max"].mean(), 2),
                        "temp_min": round(df["temperature_2m_min"].mean(), 2),
                        "temp_mean": round(df["temperature_2m_mean"].mean(), 2),
                        "temp_range": round((df["temperature_2m_max"] - df["temperature_2m_min"]).mean(), 2),
                        "temp_max_absolute": round(df["temperature_2m_max"].max(), 1),
                        "temp_min_absolute": round(df["temperature_2m_min"].min(), 1),
                        # Precipitation
                        "precip_total_mm": round(df["precipitation_sum"].sum(), 1),
                        "precip_days_gt1mm": int((df["precipitation_sum"] > 1.0).sum()),
                        "precip_max_daily_mm": round(df["precipitation_sum"].max(), 1),
                        # Radiation
                        "radiation_avg_mjm2": round(df["shortwave_radiation_sum"].mean(), 2),
                        # Humidity
                        "humidity_max": round(df["relative_humidity_2m_max"].mean(), 1),
                        "humidity_min": round(df["relative_humidity_2m_min"].mean(), 1),
                        # Wind
                        "wind_max_kmh": round(df["wind_speed_10m_max"].mean(), 1),
                        # Evapotranspiration
                        "et0_mm": round(df["et0_fao_evapotranspiration"].sum(), 1),
                        # Growing degree days (base 5°C)
                        "gdd_base5": round(df["temperature_2m_mean"].apply(
                            lambda x: max(0, x - 5) if pd.notna(x) else 0).sum(), 1),
                        # Stress days
                        "heat_stress_days_30c": int((df["temperature_2m_max"] > 30).sum()),
                        "frost_days": int((df["temperature_2m_min"] < 0).sum()),
                        # Dry spell
                        "dry_spell_max_days": _max_dry_spell(df["precipitation_sum"]),
                    }

                    all_records.append(record)

                except Exception as e:
                    logger.debug(f"  Weather {start_date} failed: {e}")

                # Progress every 100 calls
                if call_count % 100 == 0:
                    logger.info(f"  Progress: {call_count}/{total_calls} ({100*call_count/total_calls:.0f}%)")

                time.sleep(0.15)  # Rate limiting

    df_out = pd.DataFrame(all_records)
    logger.info(f"Weather: {len(df_out)} monthly records")
    return df_out


def _max_dry_spell(precip_series):
    dry = (precip_series < 1.0).astype(int)
    max_spell = current = 0
    for v in dry:
        if v == 1:
            current += 1
            max_spell = max(max_spell, current)
        else:
            current = 0
    return max_spell


# =============================================================================
# MODULE 2: MONTHLY NDVI — ORNL DAAC MODIS
# =============================================================================

def collect_monthly_ndvi(sites, year_start, year_end):
    """
    ✅ 100% REAL monthly NDVI from NASA MODIS MOD13Q1.
    16-day composites aggregated to monthly mean/max.
    Available from 2000 onwards.
    """
    BASE_URL = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
    all_records = []
    effective_start = max(year_start, 2000)

    for site_name, site_info in sites.items():
        logger.info(f"NDVI: {site_name}...")

        for year in range(effective_start, year_end + 1):
            # Fetch entire year at once (DOY 1 to 365)
            latest = datetime.now() - timedelta(days=60)
            if datetime(year, 1, 1) > latest:
                continue

            start_date = f"A{year}001"
            end_doy = min(365, int(latest.strftime("%j"))) if year == latest.year else 365
            end_date = f"A{year}{end_doy:03d}"

            ndvi_raw = _fetch_modis_year(BASE_URL, site_info["lat"], site_info["lon"],
                                          start_date, end_date, "250m_16_days_NDVI")
            evi_raw = _fetch_modis_year(BASE_URL, site_info["lat"], site_info["lon"],
                                         start_date, end_date, "250m_16_days_EVI")

            if not ndvi_raw:
                continue

            # Group by month
            for month in range(1, 13):
                # DOY ranges for each month (approximate)
                month_start_doy = datetime(year, month, 1).timetuple().tm_yday
                if month == 12:
                    month_end_doy = 365
                else:
                    month_end_doy = datetime(year, month + 1, 1).timetuple().tm_yday - 1

                # Filter NDVI values for this month
                month_ndvi = [v for doy, v in ndvi_raw if month_start_doy <= doy <= month_end_doy]
                month_evi = [v for doy, v in evi_raw if month_start_doy <= doy <= month_end_doy] if evi_raw else []

                if not month_ndvi:
                    continue

                record = {
                    "site_name": site_name,
                    "year": year,
                    "month": month,
                    "ndvi_max": round(max(month_ndvi), 4),
                    "ndvi_mean": round(np.mean(month_ndvi), 4),
                    "ndvi_min": round(min(month_ndvi), 4),
                }

                if month_evi:
                    record["evi_max"] = round(max(month_evi), 4)
                    record["evi_mean"] = round(np.mean(month_evi), 4)

                all_records.append(record)

            time.sleep(0.3)

    df_out = pd.DataFrame(all_records)
    logger.info(f"NDVI: {len(df_out)} monthly records")
    return df_out


def _fetch_modis_year(base_url, lat, lon, start_date, end_date, band):
    """Fetch MODIS band for a year, return list of (doy, scaled_value)."""
    params = {
        "latitude": lat, "longitude": lon,
        "startDate": start_date, "endDate": end_date,
        "kmAboveBelow": 0, "kmLeftRight": 0,
    }
    try:
        resp = requests.get(base_url, params=params,
                          headers={"Accept": "application/json"}, timeout=90)
        resp.raise_for_status()
        data = resp.json()

        results = []
        if "subset" in data:
            for item in data["subset"]:
                # Parse date from calendar_date or modis_date
                cal_date = item.get("calendar_date", "")
                if cal_date:
                    try:
                        dt = datetime.strptime(cal_date, "%Y-%m-%d")
                        doy = dt.timetuple().tm_yday
                    except ValueError:
                        continue
                else:
                    # Try modis_date format AYYYYDDD
                    md = item.get("modis_date", "")
                    if md and len(md) == 8:
                        doy = int(md[5:])
                    else:
                        continue

                if "data" in item:
                    for val in item["data"]:
                        try:
                            v = int(val)
                            if -2000 < v < 10000:
                                results.append((doy, v / 10000.0))
                        except (ValueError, TypeError):
                            pass
        return results if results else None

    except Exception as e:
        logger.debug(f"  MODIS {band} error: {e}")
        return None


# =============================================================================
# MODULE 3: SOIL — ISRIC SoilGrids 2.0 (static per site)
# =============================================================================

def collect_soil(sites):
    """✅ 100% REAL soil from ISRIC SoilGrids 2.0."""
    BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    PROPERTIES = ["phh2o", "clay", "sand", "silt", "soc", "nitrogen", "cec", "bdod"]
    DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]
    all_records = []

    for site_name, site_info in sites.items():
        logger.info(f"Soil: {site_name}...")
        record = {"site_name": site_name}

        params = {
            "lon": site_info["lon"], "lat": site_info["lat"],
            "property": PROPERTIES, "depth": DEPTHS,
            "value": ["mean"],
        }
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "properties" in data and "layers" in data["properties"]:
                for layer in data["properties"]["layers"]:
                    prop = layer["name"]
                    factor = layer.get("unit_measure", {}).get("mapped_units_factor", 1) or 1
                    for d_item in layer.get("depths", []):
                        mean_val = d_item.get("values", {}).get("mean")
                        if mean_val is not None:
                            record[f"soil_{prop}_{d_item['label']}_mean"] = round(mean_val * factor, 3)

                # Averaged top-30cm
                for prop in PROPERTIES:
                    vals = [record[f"soil_{prop}_{d}_mean"] for d in DEPTHS
                            if f"soil_{prop}_{d}_mean" in record]
                    if vals:
                        record[f"soil_{prop}_avg_0_30cm"] = round(np.mean(vals), 3)

                all_records.append(record)
        except requests.exceptions.ConnectionError:
            logger.warning("SoilGrids API down. Try later.")
            break
        except Exception as e:
            logger.warning(f"SoilGrids error: {e}")
        time.sleep(1.5)

    df = pd.DataFrame(all_records)
    logger.info(f"Soil: {len(df)} records")
    return df


# =============================================================================
# MERGE ALL + DERIVED FEATURES
# =============================================================================

def merge_all(weather_df, ndvi_df, soil_df):
    """Merge monthly weather + NDVI + soil + yield into ML-ready dataset."""

    merged = weather_df.copy()

    # NDVI (site + year + month)
    if ndvi_df is not None and not ndvi_df.empty:
        merged = merged.merge(ndvi_df, on=["site_name", "year", "month"], how="left")

    # Soil (site only — static)
    if soil_df is not None and not soil_df.empty:
        merged = merged.merge(soil_df, on="site_name", how="left")

    # ── Yield target (annual → assigned to each month of that year) ──
    merged["yield_wheat_tha"] = merged["year"].map(
        {y: round(v / 10.0, 4) for y, v in YIELD_WHEAT_CHA.items()}
    )
    merged["yield_cereals_tha"] = merged["year"].map(
        {y: round(v / 10.0, 4) for y, v in YIELD_CEREALS_CHA.items()}
    )
    merged["yield_tha"] = merged["yield_wheat_tha"]  # Primary target
    merged["crop"] = "spring_wheat"

    # ══════════════════════════════════════════════════════════════════
    # DERIVED FEATURES
    # ══════════════════════════════════════════════════════════════════
    logger.info("Computing derived features...")

    # Season indicator (important for model to know which month)
    merged["month_sin"] = round(np.sin(2 * np.pi * merged["month"] / 12), 4)
    merged["month_cos"] = round(np.cos(2 * np.pi * merged["month"] / 12), 4)

    # Growing season flag (May=5 to Sep=9)
    merged["is_growing_season"] = ((merged["month"] >= 5) & (merged["month"] <= 9)).astype(int)

    # Season category: winter(12,1,2), spring(3,4,5), summer(6,7,8), autumn(9,10,11)
    merged["season"] = merged["month"].map({
        12: 0, 1: 0, 2: 0,   # winter
        3: 1, 4: 1, 5: 1,    # spring
        6: 2, 7: 2, 8: 2,    # summer
        9: 3, 10: 3, 11: 3,  # autumn
    })

    # Aridity index
    if "et0_mm" in merged.columns and "precip_total_mm" in merged.columns:
        merged["aridity_index"] = round(merged["et0_mm"] / (merged["precip_total_mm"] + 0.1), 3)

    # VPD proxy
    if "humidity_min" in merged.columns and "temp_max" in merged.columns:
        merged["vpd_proxy"] = round(
            (100 - merged["humidity_min"]) * merged["temp_max"] / 100, 2)

    # Interactions
    if "precip_total_mm" in merged.columns and "soil_clay_avg_0_30cm" in merged.columns:
        merged["precip_clay_interaction"] = round(
            merged["precip_total_mm"] * merged["soil_clay_avg_0_30cm"], 2)

    if "gdd_base5" in merged.columns and "soil_nitrogen_avg_0_30cm" in merged.columns:
        merged["gdd_nitrogen_interaction"] = round(
            merged["gdd_base5"] * merged["soil_nitrogen_avg_0_30cm"], 2)

    if "radiation_avg_mjm2" in merged.columns and "ndvi_max" in merged.columns:
        merged["radiation_ndvi_interaction"] = round(
            merged["radiation_avg_mjm2"] * merged["ndvi_max"], 4)

    if "ndvi_max" in merged.columns and "soil_soc_avg_0_30cm" in merged.columns:
        merged["ndvi_soc_interaction"] = round(
            merged["ndvi_max"] * merged["soil_soc_avg_0_30cm"], 4)

    # ── Cumulative features within each site-year ──
    merged = merged.sort_values(["site_name", "year", "month"]).reset_index(drop=True)

    for site in merged["site_name"].unique():
        for year in merged["year"].unique():
            mask = (merged["site_name"] == site) & (merged["year"] == year)
            if mask.sum() == 0:
                continue
            # Cumulative precipitation from January
            merged.loc[mask, "precip_cumulative_mm"] = merged.loc[mask, "precip_total_mm"].cumsum()
            # Cumulative GDD
            merged.loc[mask, "gdd_cumulative"] = merged.loc[mask, "gdd_base5"].cumsum()
            # Cumulative ET0
            if "et0_mm" in merged.columns:
                merged.loc[mask, "et0_cumulative_mm"] = merged.loc[mask, "et0_mm"].cumsum()

    # ── Lag yield (previous years) ──
    yield_by_year = {y: round(v / 10.0, 4) for y, v in YIELD_WHEAT_CHA.items()}
    merged["yield_lag_1"] = merged["year"].map(lambda y: yield_by_year.get(y - 1, np.nan))
    merged["yield_lag_2"] = merged["year"].map(lambda y: yield_by_year.get(y - 2, np.nan))
    merged["yield_lag_3"] = merged["year"].map(lambda y: yield_by_year.get(y - 3, np.nan))

    # Rolling 3-year mean
    merged["yield_rolling_3yr"] = merged["year"].map(
        lambda y: round(np.nanmean([yield_by_year.get(y - i, np.nan) for i in range(1, 4)]), 4)
        if any(yield_by_year.get(y - i) is not None for i in range(1, 4)) else np.nan
    )

    # Year normalized
    merged["year_normalized"] = round(
        (merged["year"] - YEAR_START) / max(1, YEAR_END - YEAR_START), 4)

    return merged


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Monthly real data for Shortandy")
    parser.add_argument("--year-start", type=int, default=YEAR_START)
    parser.add_argument("--year-end", type=int, default=YEAR_END)
    parser.add_argument("--skip-weather", action="store_true")
    parser.add_argument("--skip-ndvi", action="store_true")
    parser.add_argument("--skip-soil", action="store_true")
    args = parser.parse_args()

    print("=" * 72)
    print("  MONTHLY REAL DATA — Shortandy, Akmola Oblast, Kazakhstan")
    print("=" * 72)
    n_years = args.year_end - args.year_start + 1
    expected = len(FIELD_SITES) * n_years * 12
    print(f"  Years:    {args.year_start}-{args.year_end} ({n_years} years)")
    print(f"  Sites:    {len(FIELD_SITES)}")
    print(f"  Expected: ~{expected} rows (sites × years × 12 months)")
    print(f"  Sources:  ALL REAL")
    print(f"    Weather:  Open-Meteo Archive API (monthly)")
    print(f"    NDVI/EVI: NASA MODIS MOD13Q1 (monthly)")
    print(f"    Soil:     ISRIC SoilGrids 2.0 (static)")
    print(f"    Yield:    stat.gov.kz (annual target)")
    print("=" * 72)

    # Estimate time
    weather_calls = len(FIELD_SITES) * n_years * 12
    ndvi_calls = len(FIELD_SITES) * n_years
    print(f"\n  Estimated time:")
    print(f"    Weather: {weather_calls} API calls (~{weather_calls * 0.3 / 60:.0f} min)")
    print(f"    NDVI:    {ndvi_calls} API calls (~{ndvi_calls * 1.0 / 60:.0f} min)")
    print(f"    Soil:    {len(FIELD_SITES)} API calls (~0.5 min)")
    print(f"    Total:   ~{(weather_calls * 0.3 + ndvi_calls * 1.0 + 30) / 60:.0f} min\n")

    # 1. Weather
    weather_df = pd.DataFrame()
    if not args.skip_weather:
        print("--- STEP 1/3: Monthly Weather (Open-Meteo) ---")
        weather_df = collect_monthly_weather(FIELD_SITES, args.year_start, args.year_end)
        if not weather_df.empty:
            weather_df.to_csv(DATA_DIR / "weather_monthly.csv", index=False)
            print(f"  ✅ {len(weather_df)} records saved")
    else:
        p = DATA_DIR / "weather_monthly.csv"
        if p.exists():
            weather_df = pd.read_csv(p)
            print(f"  Loaded: {len(weather_df)} weather records")

    # 2. NDVI
    ndvi_df = pd.DataFrame()
    if not args.skip_ndvi:
        print("\n--- STEP 2/3: Monthly NDVI (NASA MODIS) ---")
        ndvi_df = collect_monthly_ndvi(FIELD_SITES, args.year_start, args.year_end)
        if not ndvi_df.empty:
            ndvi_df.to_csv(DATA_DIR / "ndvi_monthly.csv", index=False)
            print(f"  ✅ {len(ndvi_df)} records saved")
    else:
        p = DATA_DIR / "ndvi_monthly.csv"
        if p.exists():
            ndvi_df = pd.read_csv(p)
            print(f"  Loaded: {len(ndvi_df)} NDVI records")

    # 3. Soil
    soil_df = pd.DataFrame()
    if not args.skip_soil:
        print("\n--- STEP 3/3: Soil (ISRIC SoilGrids) ---")
        soil_df = collect_soil(FIELD_SITES)
        if not soil_df.empty:
            soil_df.to_csv(DATA_DIR / "soil.csv", index=False)
            print(f"  ✅ {len(soil_df)} records saved")
    else:
        p = DATA_DIR / "soil.csv"
        if p.exists():
            soil_df = pd.read_csv(p)
            print(f"  Loaded: {len(soil_df)} soil records")

    # 4. Merge
    print("\n--- MERGING ---")
    if not weather_df.empty:
        merged = merge_all(weather_df, ndvi_df, soil_df)
        out_path = DATA_DIR / "shortandy_monthly_dataset.csv"
        merged.to_csv(out_path, index=False)

        print(f"\n{'=' * 72}")
        print(f"  FINAL ML-READY DATASET (MONTHLY)")
        print(f"{'=' * 72}")
        print(f"  File:    {out_path}")
        print(f"  Rows:    {len(merged)}")
        print(f"  Columns: {len(merged.columns)}")
        print(f"  Sites:   {merged['site_name'].nunique()}")
        print(f"  Years:   {merged['year'].min()}-{merged['year'].max()}")
        print(f"  Months:  {merged['month'].min()}-{merged['month'].max()}")

        if "yield_tha" in merged.columns:
            v = merged["yield_tha"].dropna()
            print(f"\n  Target: yield_tha (annual wheat yield)")
            print(f"    Valid:  {len(v)} / {len(merged)} rows")
            print(f"    Range:  {v.min():.3f} - {v.max():.3f} t/ha")
            print(f"    Mean:   {v.mean():.3f}   Std: {v.std():.3f}")

        # Feature count by modality
        w = [c for c in merged.columns if any(c.startswith(p) for p in
             ["temp_", "precip_", "radiation_", "humidity_", "wind_", "et0_",
              "gdd_", "heat_", "frost_", "dry_"])]
        n = [c for c in merged.columns if c.startswith(("ndvi_", "evi_"))]
        s = [c for c in merged.columns if c.startswith("soil_")]
        d = [c for c in merged.columns if any(c.startswith(p) for p in
             ["aridity", "vpd", "precip_clay", "gdd_nitrogen", "radiation_ndvi",
              "ndvi_soc", "precip_cumulative", "gdd_cumulative", "et0_cumulative",
              "month_sin", "month_cos", "is_growing", "season",
              "yield_lag", "yield_rolling", "year_norm"])]

        print(f"\n  Features:")
        print(f"    Weather:     {len(w)}")
        print(f"    Vegetation:  {len(n)}")
        print(f"    Soil:        {len(s)}")
        print(f"    Derived:     {len(d)}")
        print(f"    Total:       {len(w)+len(n)+len(s)+len(d)}")

        print(f"\n  ✅ ALL DATA IS 100% REAL")
        print(f"  ✅ Ready for ML training")
        print(f"{'=' * 72}")
    else:
        print("  No weather data. Check internet connection.")


if __name__ == "__main__":
    main()
