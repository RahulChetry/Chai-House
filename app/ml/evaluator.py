"""
Model evaluation utilities for Chai House AI.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    confusion_matrix,
    classification_report,
)
import json


def compute_regression_metrics(y_true, y_pred) -> dict:
    """
    Compute and return regression metrics.
    Returns: dict with MAE, RMSE, R2, and MAPE (where applicable).
    """
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    # MAPE — guard against zero denominators
    nonzero_mask = y_true != 0
    if nonzero_mask.sum() > 0:
        mape = float(
            np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100
        )
    else:
        mape = None

    return {
        "MAE": round(float(mae), 4),
        "RMSE": round(float(rmse), 4),
        "R2": round(float(r2), 4),
        "MAPE": round(mape, 2) if mape is not None else None,
    }


def compute_classification_metrics(y_true, y_pred, class_names=None) -> dict:
    """
    Compute classification metrics.
    Returns: accuracy, precision (weighted), recall (weighted),
             f1 (weighted), confusion_matrix as list of lists.
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    rec = recall_score(y_true, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    cm = confusion_matrix(y_true, y_pred).tolist()

    return {
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "confusion_matrix": cm,
        "class_names": class_names or [],
    }


def format_confusion_matrix_for_json(cm: np.ndarray, class_names: list) -> dict:
    """
    Convert confusion matrix to JSON-serializable dict suitable for Chart.js.

    Returns:
    {
        "labels": [...],
        "datasets": [{"label": "Predicted X", "data": [...]}]
    }
    """
    cm_list = cm.tolist() if isinstance(cm, np.ndarray) else cm

    datasets = []
    for i, row in enumerate(cm_list):
        datasets.append({
            "label": f"Actual: {class_names[i] if i < len(class_names) else i}",
            "data": row,
        })

    return {
        "labels": class_names,
        "datasets": datasets,
        "raw": cm_list,
    }


def interpret_regression_results(results: list) -> str:
    """
    Return a plain-English summary of which model performed best and why.
    """
    if not results:
        return "No regression results available."

    # Sort by test MAE ascending
    sorted_results = sorted(results, key=lambda r: r.get("test_mae", float("inf")))
    best = sorted_results[0]
    worst = sorted_results[-1]

    name = best.get("model_name", "Unknown")
    mae = best.get("test_mae", 0)
    rmse = best.get("test_rmse", 0)
    r2 = best.get("test_r2", 0)
    cv_mean = best.get("cv_mean", 0)
    cv_std = best.get("cv_std", 0)

    interpretation = (
        f"**{name}** performed best with a Test MAE of {mae:.2f}, meaning predictions "
        f"are off by about {mae:.0f} cups on average. "
        f"RMSE = {rmse:.2f}, R² = {r2:.3f}. "
    )

    if r2 >= 0.8:
        interpretation += f"The R² of {r2:.3f} indicates a strong model fit. "
    elif r2 >= 0.5:
        interpretation += f"The R² of {r2:.3f} indicates a moderate model fit. "
    else:
        interpretation += (
            f"The R² of {r2:.3f} is relatively low — more data or better features may improve results. "
        )

    interpretation += (
        f"Cross-validation (TimeSeriesSplit) MAE: {cv_mean:.2f} ± {cv_std:.2f}. "
        f"The weakest performer was **{worst.get('model_name', 'Unknown')}** "
        f"with MAE = {worst.get('test_mae', 0):.2f}."
    )

    if best.get("best_params"):
        params_str = ", ".join(f"{k}={v}" for k, v in best["best_params"].items())
        interpretation += f" Best hyperparameters: {params_str}."

    return interpretation


def interpret_classification_results(result: dict) -> str:
    """Return plain-English summary of SVM classifier performance."""
    if not result:
        return "No classification results available."

    if "error" in result:
        return f"Classification error: {result['error']}"

    acc = result.get("accuracy", 0)
    f1 = result.get("f1", 0)
    prec = result.get("precision", 0)
    rec = result.get("recall", 0)
    thresholds = result.get("class_thresholds", {})
    best_params = result.get("best_params", {})

    low = thresholds.get("low", "?")
    high = thresholds.get("high", "?")

    interpretation = (
        f"**SVM Classifier** achieved an accuracy of {acc * 100:.1f}% on the test set. "
        f"Weighted F1-score = {f1:.3f}, Precision = {prec:.3f}, Recall = {rec:.3f}. "
        f"Demand was classified as: Low (≤ {low} cups), Medium ({low}–{high} cups), "
        f"High (> {high} cups). "
    )

    if acc >= 0.85:
        interpretation += "The classifier performs excellently — reliable for operational decisions. "
    elif acc >= 0.70:
        interpretation += "The classifier performs adequately for indicative demand planning. "
    else:
        interpretation += (
            "Accuracy is below 70%. Consider collecting more diverse data before relying on this model. "
        )

    if best_params:
        params_str = ", ".join(f"{k}={v}" for k, v in best_params.items())
        interpretation += f"Best SVM hyperparameters: {params_str}."

    return interpretation


def check_data_leakage_risks(feature_names: list, target_name: str) -> list:
    """
    Return list of warning strings if any feature name suggests data leakage.
    Checks for: 'revenue', 'profit', 'price', 'cost', and the target name itself.
    """
    warnings = []
    leakage_keywords = ["revenue", "profit", "price", "cost"]

    for feat in feature_names:
        feat_lower = feat.lower()

        for kw in leakage_keywords:
            if kw in feat_lower:
                warnings.append(
                    f"⚠️ Potential data leakage: feature '{feat}' contains '{kw}'. "
                    f"Financial quantities derived from sales targets should not be used as predictors."
                )
                break

        if feat_lower == target_name.lower():
            warnings.append(
                f"⚠️ Severe data leakage: feature '{feat}' is the same as the target '{target_name}'. "
                f"Remove it immediately."
            )

    return warnings
