#!/usr/bin/env python3
"""
Standalone script to evaluate saved ML models for Chai House AI.
Loads best_regression.pkl and best_classifier.pkl from models/ and
prints a detailed evaluation report using test data rebuilt from the DB.

Usage: python evaluate_models.py
Run from ChaiHouseAI/ directory.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd

from app import create_app
from app.models import Sale, Product, db
from app.ml.trainer import load_best_regression_model, load_best_classifier
from app.ml.features import engineer_features, prepare_regression_data, prepare_classification_data
from app.ml.evaluator import (
    compute_regression_metrics,
    compute_classification_metrics,
    format_confusion_matrix_for_json,
    interpret_regression_results,
    interpret_classification_results,
    check_data_leakage_risks,
)


def _section(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def _hr():
    print("-" * 65)


def evaluate_regression(pipeline, X_test, y_test, X_train, y_train):
    """Print a detailed regression evaluation report."""
    _section("REGRESSION MODEL EVALUATION")

    model_name = type(pipeline.named_steps.get("model", object())).__name__
    print(f"  Model       : {model_name}")
    print(f"  Train rows  : {len(y_train)}")
    print(f"  Test rows   : {len(y_test)}")
    _hr()

    # Training metrics
    train_metrics = compute_regression_metrics(y_train, pipeline.predict(X_train))
    print("  [Training Set Metrics]")
    for k, v in train_metrics.items():
        print(f"    {k:<8}: {v}")

    _hr()

    # Test metrics
    test_metrics = compute_regression_metrics(y_test, pipeline.predict(X_test))
    print("  [Test Set Metrics]")
    for k, v in test_metrics.items():
        print(f"    {k:<8}: {v}")

    _hr()

    # Residual analysis
    y_pred = pipeline.predict(X_test)
    residuals = np.array(y_test) - y_pred
    print("  [Residual Analysis]")
    print(f"    Mean residual : {residuals.mean():.4f}  (near 0 = unbiased)")
    print(f"    Std residual  : {residuals.std():.4f}")
    print(f"    Max over-pred : {(-residuals).max():.2f} cups")
    print(f"    Max under-pred: {residuals.max():.2f} cups")

    _hr()

    # Sample predictions
    print("  [Sample Predictions vs Actual (first 10 test rows)]")
    print(f"    {'Actual':>8}  {'Predicted':>10}  {'Error':>8}")
    for actual, pred in zip(list(y_test)[:10], y_pred[:10]):
        print(f"    {actual:>8.1f}  {pred:>10.2f}  {actual - pred:>+8.2f}")

    return test_metrics


def evaluate_classifier(pipeline, X_test, y_test, X_train, y_train, class_names=None):
    """Print a detailed classification evaluation report."""
    _section("CLASSIFICATION MODEL EVALUATION")

    if class_names is None:
        class_names = ["Low", "Medium", "High"]

    model_name = type(pipeline.named_steps.get("model", object())).__name__
    print(f"  Model       : {model_name}")
    print(f"  Train rows  : {len(y_train)}")
    print(f"  Test rows   : {len(y_test)}")
    _hr()

    metrics = compute_classification_metrics(y_test, pipeline.predict(X_test), class_names)
    print("  [Test Set Metrics]")
    print(f"    Accuracy  : {metrics['accuracy']:.4f}")
    print(f"    Precision : {metrics['precision']:.4f}  (weighted)")
    print(f"    Recall    : {metrics['recall']:.4f}  (weighted)")
    print(f"    F1 Score  : {metrics['f1']:.4f}  (weighted)")

    _hr()

    # Confusion matrix
    from sklearn.metrics import confusion_matrix, classification_report
    cm = confusion_matrix(y_test, pipeline.predict(X_test))
    cm_dict = format_confusion_matrix_for_json(cm, class_names)

    print("  [Confusion Matrix]")
    header = "         " + "  ".join(f"{c:>8}" for c in class_names)
    print(f"    {header}")
    for i, (label, row) in enumerate(zip(class_names, cm.tolist())):
        row_str = "  ".join(f"{v:>8}" for v in row)
        print(f"    Actual {label:<9}{row_str}")

    _hr()

    print("  [Per-Class Classification Report]")
    cr = classification_report(y_test, pipeline.predict(X_test),
                               target_names=class_names, zero_division=0)
    for line in cr.split("\n"):
        print(f"    {line}")

    _hr()

    # Training metrics
    train_metrics = compute_classification_metrics(y_train, pipeline.predict(X_train), class_names)
    print("  [Training Set Metrics (overfitting check)]")
    print(f"    Train Accuracy : {train_metrics['accuracy']:.4f}")
    print(f"    Test Accuracy  : {metrics['accuracy']:.4f}")
    gap = train_metrics["accuracy"] - metrics["accuracy"]
    if gap > 0.15:
        print(f"    ⚠️  Accuracy gap = {gap:.3f} → possible overfitting")
    else:
        print(f"    ✓  Accuracy gap = {gap:.3f} → no significant overfitting")

    return metrics


def main():
    app = create_app()
    with app.app_context():

        # ── Check saved models exist ───────────────────────────────────────
        reg_pipeline = load_best_regression_model()
        cls_pipeline = load_best_classifier()

        if reg_pipeline is None and cls_pipeline is None:
            print("\n[✗] No saved models found in models/ directory.")
            print("    Run 'python train_models.py' first.")
            sys.exit(1)

        # ── Load data ──────────────────────────────────────────────────────
        sales = Sale.query.join(Product).all()
        if len(sales) < 10:
            print(f"\n[!] Only {len(sales)} sales records. Cannot evaluate reliably.")
            sys.exit(1)

        print(f"\n[✓] Loaded {len(sales)} sales records.")

        df = pd.DataFrame([
            {
                "product_id": s.product_id,
                "date": s.date.strftime("%Y-%m-%d"),
                "quantity": s.quantity,
                "revenue": float(s.revenue) if s.revenue else 0.0,
            }
            for s in sales
        ])

        df["date"] = pd.to_datetime(df["date"])

        agg_df = (
            df.groupby(["date", "product_id"])
            .agg(quantity=("quantity", "sum"), revenue=("revenue", "sum"))
            .reset_index()
        )

        feat_df = engineer_features(agg_df)

        # ── Data leakage check ─────────────────────────────────────────────
        feature_names = [
            "day_of_week", "is_weekend", "month", "day_of_month",
            "week_of_year", "lag_1_qty", "lag_7_qty", "rolling_7_mean",
        ]
        warnings = check_data_leakage_risks(feature_names, "quantity")
        if warnings:
            print("\n[!] Data leakage warnings:")
            for w in warnings:
                print(f"    {w}")
        else:
            print("[✓] Feature set: no data leakage risks detected.")

        # ── Regression evaluation ──────────────────────────────────────────
        if reg_pipeline is not None:
            X, y, _ = prepare_regression_data(feat_df)
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            reg_metrics = evaluate_regression(reg_pipeline, X_test, y_test, X_train, y_train)

            # Synthetic result dict for interpretation
            reg_result_for_interp = [{
                "model_name": type(reg_pipeline.named_steps.get("model", object())).__name__,
                "test_mae": reg_metrics["MAE"],
                "test_rmse": reg_metrics["RMSE"],
                "test_r2": reg_metrics["R2"],
                "cv_mean": 0.0,
                "cv_std": 0.0,
                "best_params": {},
            }]

            print("\n  [Plain-English Interpretation]")
            print(f"  {interpret_regression_results(reg_result_for_interp)}")
        else:
            print("\n[!] No regression model found — skipping regression evaluation.")

        # ── Classification evaluation ──────────────────────────────────────
        if cls_pipeline is not None:
            X_cls, y_cls, thresholds, class_names = prepare_classification_data(feat_df)
            split_cls = int(len(X_cls) * 0.8)
            X_cls_train = X_cls.iloc[:split_cls]
            X_cls_test = X_cls.iloc[split_cls:]
            y_cls_train = y_cls.iloc[:split_cls]
            y_cls_test = y_cls.iloc[split_cls:]

            cls_metrics = evaluate_classifier(
                cls_pipeline, X_cls_test, y_cls_test,
                X_cls_train, y_cls_train, class_names
            )

            cls_result_for_interp = {
                "accuracy": cls_metrics["accuracy"],
                "f1": cls_metrics["f1"],
                "precision": cls_metrics["precision"],
                "recall": cls_metrics["recall"],
                "class_thresholds": thresholds,
                "best_params": {},
            }

            print("\n  [Plain-English Interpretation]")
            print(f"  {interpret_classification_results(cls_result_for_interp)}")
        else:
            print("\n[!] No classifier found — skipping classification evaluation.")

        _section("EVALUATION COMPLETE")
        print("  See models/ for saved pipeline objects.")
        print("  Run 'python train_models.py' to retrain with updated data.\n")


if __name__ == "__main__":
    main()
