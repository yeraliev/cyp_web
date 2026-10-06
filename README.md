# Data Collection and Preparation Tools for Wheat Yield Prediction

[![CI](https://github.com/yeraliev/cyp_web/actions/workflows/ci.yml/badge.svg)](https://github.com/yeraliev/cyp_web/actions/workflows/ci.yml)

Tools written for a Master's thesis on predicting spring wheat yield in Shortandy district, Akmola region, Kazakhstan. They download climate, vegetation and soil data from open APIs and turn them into a yearly dataset that is ready for modelling.

## Pipeline

| Step | Script | Input | Output |
|---|---|---|---|
| 1. Collect | [collect_monthly_shortandy.py](collect_monthly_shortandy.py), [patch_ndvi_v2.py](patch_ndvi_v2.py) | Open APIs | `data/monthly/shortandy_monthly_dataset.csv` (2,015 rows, 87 columns) |
| 2. Clean | done once, result stored | Collected dataset | `train_shortandy.csv`, `test_shortandy.csv` (2,015 rows, 50 columns) |
| 3. Aggregate | [aggregate_yearly.py](aggregate_yearly.py) | Cleaned monthly data | `train_shortandy_yearly.csv` (136 rows), `test_shortandy_yearly.csv` (32 rows) |

The data cover 2004–2024 for eight points inside the district. Each monthly row is one site and one month.

## Data sources

| Data | Source | API |
|---|---|---|
| Climate and soil moisture | Open-Meteo Historical Weather API | `https://archive-api.open-meteo.com/v1/archive` |
| Vegetation indices (NDVI, EVI) | NASA MODIS MOD13Q1 via ORNL DAAC | `https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset` |
| Soil properties | ISRIC SoilGrids 2.0 | `https://rest.isric.org/soilgrids/v2.0/properties/query` |
| Wheat yield (target) | Bureau of National Statistics of Kazakhstan, [stat.gov.kz](https://stat.gov.kz/) | No API; yearly values are written in the script |

All three APIs are free and need no key.

## Step 1: collection

```bash
python collect_monthly_shortandy.py
```

- **Weather:** one request per site and month (2,016 requests). Daily values are reduced to monthly features: temperature, precipitation, radiation, humidity, wind, evapotranspiration, growing degree days (base 5 °C), heat stress days (above 30 °C), frost days and the longest dry spell.
- **Vegetation:** 16-day MODIS composites reduced to monthly maximum and mean NDVI and EVI.
- **Soil:** eight properties at three depths, averaged for the top 30 cm. Soil is constant for a site.
- **Yield:** converted from centners per hectare to tonnes per hectare and attached to every month of its year.

Intermediate files are saved after every source, so one source can be repeated without the others:

```bash
python collect_monthly_shortandy.py --skip-weather --skip-soil    # only vegetation
python collect_monthly_shortandy.py --year-start 2020 --year-end 2022    # quick trial
```

`patch_ndvi_v2.py` adds NDVI and EVI to an existing dataset with one request per month, because requests for a whole year did not return data. It also adds soil moisture from Open-Meteo.

## Step 2: cleaning

The collected dataset was cleaned once and the result is stored in this repository:

- 50 of the 87 columns were kept.
- NDVI and EVI are absent for November–March and were set to 0. These months are outside the growing season, so they do not affect the yearly dataset.
- Soil moisture is absent in 672 rows and was filled with the median.
- Yield of previous years is not known for 2004 and was filled with the median yield.

## Step 3: aggregation

The official yield is published once per year, so the same value is repeated in all twelve monthly rows. `aggregate_yearly.py` produces one row per site and year and splits the result chronologically (years up to 2020 for training, later years for testing).

```bash
python aggregate_yearly.py
```

| Variables | Rule |
|---|---|
| Temperature, radiation, humidity, wind | Mean over the growing season (May–September) |
| Precipitation, rainy days, ET0, growing degree days, heat stress days, frost days | Sum over the growing season |
| Maximum daily precipitation, longest dry spell, maximum NDVI and EVI | Maximum over the growing season |
| Soil properties | Constant for a site; the first value is taken |
| Cumulative precipitation and degree days | Value of December, or of the last available month |
| Aridity index | Precipitation sum divided by ET0 sum |
| Yield | Kept unchanged |

## Installation

Requires Python 3.11 or higher.

```bash
git clone https://github.com/yeraliev/cyp_web.git
cd cyp_web
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Testing and continuous integration

```bash
pip install -r requirements-dev.txt
pytest -v
```

- `tests/test_collect.py` checks the collection tool with a fake API response, so no network is needed.
- `tests/test_aggregate.py` checks the aggregation rules, the chronological split, and that the tool reproduces the yearly files in this repository.
- `tests/test_data.py` checks the yearly files: sizes, years, sites per year, missing values and the yield range.

Every push and pull request to `main` runs the GitHub Actions workflow in [.github/workflows/ci.yml](.github/workflows/ci.yml), which installs the dependencies, lints the code with flake8 and runs the tests.

## Limitations

- The yield is a statistic for the whole district, so all eight sites share the same yield value in a given year. The yearly dataset has 168 rows but only 21 independent yield observations.
- The cleaning step is not scripted; only its result is stored.
- One site-month (in 2019) is missing from the collected data.

## License

Released under the [MIT License](LICENSE).
