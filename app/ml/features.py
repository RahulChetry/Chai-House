"""
Feature engineering for Chai House AI ML pipeline.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features from sales DataFrame.
    Input df must have columns: date (datetime), product_id, quantity, revenue
    Output: df with additional features for ML

    Features added:
    - day_of_week (0=Mon, 6=Sun)
    - is_weekend (bool)
    - month (1-12)
    - day_of_month (1-31)
    - week_of_year (1-53)
    - lag_1_qty: previous day total quantity for that product
    - lag_7_qty: 7 days ago quantity for that product
    - rolling_7_mean: 7-day rolling mean quantity
    - rolling_14_mean: 14-day rolling mean

    Returns engineered DataFrame sorted by date.
    """
    if df.empty:
        return df

    df = df.copy()

    # Ensure date column is datetime
    df["date"] = pd.to_datetime(df["date"])

    # Sort by product and date for proper lag calculation
    df = df.sort_values(["product_id", "date"]).reset_index(drop=True)

    # Calendar features
    df["day_of_week"] = df["date"].dt.dayofweek          # 0=Mon, 6=Sun
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = df["date"].dt.month
    df["day_of_month"] = df["date"].dt.day
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

    # Lag and rolling features per product to avoid data bleed across products
    lag_1_list = []
    lag_7_list = []
    rolling_7_list = []
    rolling_14_list = []

    for product_id, grp in df.groupby("product_id"):
        grp = grp.sort_values("date")
        qty = grp["quantity"]

        lag_1 = qty.shift(1)
        lag_7 = qty.shift(7)
        roll_7 = qty.shift(1).rolling(window=7, min_periods=1).mean()
        roll_14 = qty.shift(1).rolling(window=14, min_periods=1).mean()

        lag_1_list.append(pd.Series(lag_1.values, index=grp.index))
        lag_7_list.append(pd.Series(lag_7.values, index=grp.index))
        rolling_7_list.append(pd.Series(roll_7.values, index=grp.index))
        rolling_14_list.append(pd.Series(roll_14.values, index=grp.index))

    df["lag_1_qty"] = pd.concat(lag_1_list).sort_index()
    df["lag_7_qty"] = pd.concat(lag_7_list).sort_index()
    df["rolling_7_mean"] = pd.concat(rolling_7_list).sort_index()
    df["rolling_14_mean"] = pd.concat(rolling_14_list).sort_index()

    # Final sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df


def prepare_regression_data(df: pd.DataFrame, target_product_id: int = None):
    """
    Prepare X, y for regression.
    Target: quantity (cups sold)
    Features: day_of_week, is_weekend, month, day_of_month, week_of_year,
              lag_1_qty, lag_7_qty, rolling_7_mean

    IMPORTANT: No data leakage — revenue, profit, and target-derived fields
    are excluded from features.

    Returns: X (DataFrame), y (Series), feature_names (list)
    """
    df = df.copy()

    if target_product_id is not None:
        df = df[df["product_id"] == target_product_id]

    feature_names = [
        "day_of_week",
        "is_weekend",
        "month",
        "day_of_month",
        "week_of_year",
        "lag_1_qty",
        "lag_7_qty",
        "rolling_7_mean",
    ]

    # Keep only rows where all features are present (lag features need prior data)
    df = df.dropna(subset=feature_names)

    X = df[feature_names].copy()
    y = df["quantity"].copy()

    return X, y, feature_names


def prepare_classification_data(df: pd.DataFrame, low_threshold=None, high_threshold=None):
    """
    Classify demand: Low (0), Medium (1), High (2).
    Thresholds computed from 33rd and 67th percentiles of training data if not provided.

    Returns: X, y, thresholds dict, class_names list
    """
    df = df.copy()

    if low_threshold is None:
        low_threshold = df["quantity"].quantile(0.33)
    if high_threshold is None:
        high_threshold = df["quantity"].quantile(0.67)

    def _label(q):
        if q <= low_threshold:
            return 0   # Low
        elif q <= high_threshold:
            return 1   # Medium
        else:
            return 2   # High

    df["demand_class"] = df["quantity"].apply(_label)

    feature_names = [
        "day_of_week",
        "is_weekend",
        "month",
        "day_of_month",
        "week_of_year",
        "lag_1_qty",
        "lag_7_qty",
        "rolling_7_mean",
    ]

    df = df.dropna(subset=feature_names)

    X = df[feature_names].copy()
    y = df["demand_class"].copy()

    thresholds = {"low": float(low_threshold), "high": float(high_threshold)}
    class_names = ["Low", "Medium", "High"]

    return X, y, thresholds, class_names


def get_next_day_features(last_known_date: datetime, product_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature row for the next day prediction.
    Uses last known sales data to compute lag features.

    Args:
        last_known_date: The most recent date we have data for
        product_df: DataFrame of historical data for a single product,
                    must contain columns: date, quantity (already sorted)

    Returns:
        Single-row DataFrame with all regression features
    """
    next_date = last_known_date + timedelta(days=1)

    product_df = product_df.copy()
    product_df["date"] = pd.to_datetime(product_df["date"])
    product_df = product_df.sort_values("date").reset_index(drop=True)

    # Compute lag features from historical data
    if len(product_df) >= 1:
        lag_1 = float(product_df.iloc[-1]["quantity"])
    else:
        lag_1 = np.nan

    if len(product_df) >= 7:
        lag_7 = float(product_df.iloc[-7]["quantity"])
    else:
        lag_7 = float(product_df["quantity"].mean()) if len(product_df) > 0 else np.nan

    recent_7 = product_df["quantity"].tail(7)
    rolling_7_mean = float(recent_7.mean()) if len(recent_7) > 0 else np.nan

    features = {
        "day_of_week": next_date.weekday(),
        "is_weekend": int(next_date.weekday() >= 5),
        "month": next_date.month,
        "day_of_month": next_date.day,
        "week_of_year": int(next_date.isocalendar()[1]),
        "lag_1_qty": lag_1,
        "lag_7_qty": lag_7,
        "rolling_7_mean": rolling_7_mean,
    }

    return pd.DataFrame([features])
