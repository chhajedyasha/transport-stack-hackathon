"""Chronological train/validation/test split with leakage prevention invariants."""
from typing import Tuple
import pandas as pd


def chronological_split(
    df: pd.DataFrame,
    date_col: str = "trip_date",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits dataset strictly by date to ensure zero future-to-past data leakage.

    Invariant enforced: max(train_date) < min(val_date) < min(test_date)
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col]).dt.date
    
    unique_dates = sorted(df[date_col].unique())
    n_dates = len(unique_dates)
    
    if n_dates < 3:
        raise ValueError(f"Insufficient distinct dates for chronological split: {n_dates}")
        
    n_train = max(1, int(n_dates * train_ratio))
    n_val = max(1, int(n_dates * val_ratio))
    
    # Ensure all splits have at least 1 date
    if n_train + n_val >= n_dates:
        n_val = max(1, n_dates - n_train - 1)
        
    train_dates = set(unique_dates[:n_train])
    val_dates = set(unique_dates[n_train : n_train + n_val])
    test_dates = set(unique_dates[n_train + n_val :])
    
    df_train = df[df[date_col].isin(train_dates)].copy()
    df_val = df[df[date_col].isin(val_dates)].copy()
    df_test = df[df[date_col].isin(test_dates)].copy()
    
    max_train = df_train[date_col].max()
    min_val = df_val[date_col].min()
    max_val = df_val[date_col].max()
    min_test = df_test[date_col].min()
    
    # Invariant assertion
    assert max_train < min_val, f"Leakage detected: max train date {max_train} >= min val date {min_val}"
    assert max_val < min_test, f"Leakage detected: max val date {max_val} >= min test date {min_test}"
    
    return df_train, df_val, df_test
