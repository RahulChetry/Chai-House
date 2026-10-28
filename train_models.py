#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone script to train all ML models for Chai House AI.
Usage: python train_models.py
Run from ChaiHouseAI/ directory.
"""
import sys
import os

# Fix Windows console unicode issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models import Sale, Product, db
from app.ml.trainer import run_full_training_pipeline
from app.ml.evaluator import interpret_regression_results, interpret_classification_results, check_data_leakage_risks
import pandas as pd


def main():
    app = create_app()
    with app.app_context():
        # ── Load sales from DB ─────────────────────────────────────────────
        sales = Sale.query.join(Product).all()

        if len(sales) < 30:
            print(f"\n[!] Only {len(sales)} sales records found. Need at least 30 for training.")
            print("    Run 'flask seed-demo' first to load demo data.")
            sys.exit(1)

        print(f"\n[OK] Loaded {len(sales)} sales records from database.")

        sales_data = [
            {
                "id": s.id,
                "product_id": s.product_id,
                "product_name": s.product.name,
                "date": s.date.strftime("%Y-%m-%d"),
                "quantity": s.quantity,
                "revenue": float(s.revenue) if s.revenue else 0.0,
                "gross_profit": float(s.gross_profit) if hasattr(s, "gross_profit") and s.gross_profit else 0.0,
            }
            for s in sales
        ]

        # ── Data leakage check ─────────────────────────────────────────────
        feature_names = [
            "day_of_week", "is_weekend", "month", "day_of_month",
            "week_of_year", "lag_1_qty", "lag_7_qty", "rolling_7_mean",
        ]
        leakage_warnings = check_data_leakage_risks(feature_names, "quantity")
        if leakage_warnings:
            print("\n[!] Data leakage warnings:")
            for w in leakage_warnings:
                print(f"    {w}")
        else:
            print("[OK] No data leakage risks detected in feature set.")

        # ── Run pipeline ───────────────────────────────────────────────────
        print(f"\n[...] Training on {len(sales_data)} records. This may take a moment...\n")
        results = run_full_training_pipeline(sales_data)

        if "error" in results:
            print(f"\n[✗] Training failed: {results['error']}")
            sys.exit(1)

        # ── Print regression results ───────────────────────────────────────
        print("=" * 65)
        print(" REGRESSION RESULTS")
        print("=" * 65)
        print(f"{'Model':<35} {'MAE':>6} {'RMSE':>7} {'R²':>7}")
        print("-" * 65)

        reg_results = results.get("regression_results", [])
        for r in sorted(reg_results, key=lambda x: x["test_mae"]):
            marker = " ◄ BEST" if r.get("is_best") else ""
            # is_best may not survive the dict copy — fall back to minimum check
            print(
                f"{r['model_name']:<35} "
                f"{r['test_mae']:>6.2f} "
                f"{r['test_rmse']:>7.2f} "
                f"{r['test_r2']:>7.3f}"
                f"{marker}"
            )

        print()
        print("[Interpretation]")
        print(interpret_regression_results(reg_results))

        # ── Print classification results ───────────────────────────────────
        print("\n" + "=" * 65)
        print(" CLASSIFICATION RESULTS (SVM Demand Classifier)")
        print("=" * 65)
        cr = results.get("classification_result", {})

        if "error" in cr:
            print(f"[!] {cr['error']}")
        else:
            print(f"  Accuracy  : {cr.get('accuracy', 0):.4f}")
            print(f"  Precision : {cr.get('precision', 0):.4f}")
            print(f"  Recall    : {cr.get('recall', 0):.4f}")
            print(f"  F1 Score  : {cr.get('f1', 0):.4f}")
            print(f"  Best params: {cr.get('best_params', {})}")
            print(f"  CV Accuracy: {cr.get('cv_mean', 0):.4f} ± {cr.get('cv_std', 0):.4f}")
            print()
            print("[Interpretation]")
            print(interpret_classification_results(cr))
            print()
            print("[Classification Report]")
            print(cr.get("classification_report", ""))

        # ── Summary ────────────────────────────────────────────────────────
        print("=" * 65)
        print(f"  Best regression model : {results.get('best_regression_model')}")
        print(f"  Best regression MAE   : {results.get('best_regression_mae')}")
        print(f"  Training samples      : {results.get('n_train')}")
        print(f"  Test samples          : {results.get('n_test')}")
        print("=" * 65)
        print("\n[OK] Models saved to models/ directory.")
        print("[OK] Training complete!\n")


if __name__ == "__main__":
    main()
