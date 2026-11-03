"""Deliberately failing tests to show that the pipeline stops on a broken commit.

Delete this file to make the pipeline green again.
"""
import pandas as pd


def test_train_includes_2021():
    # Wrong on purpose: 2021 belongs to the test set, not the training set
    train_df = pd.read_csv('train_shortandy_yearly.csv')
    assert train_df['year'].max() == 2021


def test_yield_in_centners():
    # Wrong on purpose: yield is stored in t/ha (about 1), not centners/ha (about 10)
    train_df = pd.read_csv('train_shortandy_yearly.csv')
    assert train_df['yield_tha'].mean() > 5
