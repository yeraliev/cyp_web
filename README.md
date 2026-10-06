# Dataset Preparation Tool for Wheat Yield Prediction

[![CI](https://github.com/yeraliev/cyp_web/actions/workflows/ci.yml/badge.svg)](https://github.com/yeraliev/cyp_web/actions/workflows/ci.yml)

A small data processing tool written for a Master's thesis on predicting spring wheat yield in Shortandy district, Akmola region, Kazakhstan. It converts a monthly dataset of climate, vegetation and soil variables into a yearly dataset that is ready for modelling.

## Why the tool is needed

The official wheat yield is published once per year, but the source dataset has one row per site and month. The same yield value is repeated in all twelve monthly rows, so a model trained on them sees many copies of one observation. The tool removes this repetition by producing one row per site and year.

## What it does

For every site and year, [aggregate_yearly.py](aggregate_yearly.py) aggregates the monthly values over the growing season (May–September) and then splits the result chronologically.

| Variables | Rule |
|---|---|
| Temperature, radiation, humidity, wind | Mean over the growing season |
| Precipitation, rainy days, ET0, growing degree days, heat stress days, frost days | Sum over the growing season |
| Maximum daily precipitation, longest dry spell, maximum NDVI and EVI | Maximum over the growing season |
| Soil properties | Constant for a site; the first value is taken |
| Cumulative precipitation and degree days | Value of December, or of the last available month |
| Aridity index | Precipitation sum divided by ET0 sum |
| Yield | Kept unchanged |

Years up to 2020 go to the training set, later years to the test set.

## Files

| File | Size | Content |
|---|---|---|
| `train_shortandy.csv`, `test_shortandy.csv` | 2,015 rows, 50 columns | Input: monthly data, 8 sites, 2004–2024 |
| `train_shortandy_yearly.csv` | 136 rows, 41 columns | Output: training set, 8 sites × 17 years (2004–2020) |
| `test_shortandy_yearly.csv` | 32 rows, 41 columns | Output: test set, 8 sites × 4 years (2021–2024) |

## Installation

Requires Python 3.11 or higher.

```bash
git clone https://github.com/yeraliev/cyp_web.git
cd cyp_web
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python aggregate_yearly.py
```

This reads the two monthly files and rewrites the two yearly files.

The functions can also be used from Python:

```python
import pandas as pd
from aggregate_yearly import aggregate_yearly, split_by_year

monthly = pd.read_csv('train_shortandy.csv')
yearly = aggregate_yearly(monthly)
train, test = split_by_year(yearly, last_train_year=2018)
```

## Testing and continuous integration

```bash
pip install -r requirements-dev.txt
pytest -v
```

- `tests/test_aggregate.py` checks the aggregation rules, the chronological split, and that the tool reproduces the yearly files in this repository.
- `tests/test_data.py` checks the yearly files: sizes, years, sites per year, missing values and the yield range.

Every push and pull request to `main` runs the GitHub Actions workflow in [.github/workflows/ci.yml](.github/workflows/ci.yml), which installs the pinned dependencies, lints the code with flake8 and runs the tests.

## Limitations

- The yield is a statistic for the whole district, so all eight sites share the same yield value in a given year. The yearly dataset has 168 rows but only 21 independent yield observations.
- Missing aggregated values, if any appear, are filled with 0.

## Data sources

| Data | Source |
|---|---|
| Climate (temperature, precipitation, radiation, humidity, wind, ET0) | [Open-Meteo Historical Weather API](https://open-meteo.com/) |
| Vegetation indices (NDVI, EVI) | [NASA MODIS Terra MOD13Q1 v061](https://lpdaac.usgs.gov/products/mod13q1v061/) |
| Soil properties | [ISRIC SoilGrids v2.0](https://soilgrids.org/) |
| Wheat yield | [Bureau of National Statistics of Kazakhstan](https://stat.gov.kz/) |

## License

Released under the [MIT License](LICENSE).
