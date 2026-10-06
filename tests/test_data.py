"""Tests for the yearly datasets produced by the tool."""
import pandas as pd
import pytest


@pytest.fixture(scope='module')
def train_df():
    return pd.read_csv('train_shortandy_yearly.csv')


@pytest.fixture(scope='module')
def test_df():
    return pd.read_csv('test_shortandy_yearly.csv')


def test_dataset_shapes(train_df, test_df):
    # 8 sites x 17 years and 8 sites x 4 years
    assert len(train_df) == 136
    assert len(test_df) == 32
    assert list(train_df.columns) == list(test_df.columns)


def test_split_is_chronological(train_df, test_df):
    assert train_df['year'].max() < test_df['year'].min()
    assert (train_df['year'].min(), train_df['year'].max()) == (2004, 2020)
    assert (test_df['year'].min(), test_df['year'].max()) == (2021, 2024)


def test_every_year_has_eight_sites(train_df, test_df):
    for df in (train_df, test_df):
        assert (df.groupby('year')['site_name'].nunique() == 8).all()


def test_no_missing_values(train_df, test_df):
    for df in (train_df, test_df):
        assert not df.isnull().any().any()


def test_yield_in_plausible_range(train_df, test_df):
    for df in (train_df, test_df):
        assert df['yield_tha'].between(0.1, 5.0).all()
