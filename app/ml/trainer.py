"""
Model training and evaluation for Chai House AI.
Implements: Linear Regression, Multiple Linear Regression, Polynomial Regression,
Ridge, Lasso, SVR for regression.
SVM (SVC) for demand classification.
"""
import numpy as np
import pandas as pd
import joblib
import os

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.svm import SVR, SVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import (
    train_test_split, cross_val_score, GridSearchCV, TimeSeriesSplit
)
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)
from sklearn.impute import SimpleImputer

from app.ml.features import engineer_features, prepare_regression_data, prepare_classification_data, get_next_day_features

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")


def _ensure_models_dir():
    os.makedirs(MODELS_DIR, exist_ok=True)


def _regression_metrics(pipeline, X, y):
    """Return MAE, RMSE, R2 for a fitted pipeline on given data."""
    y_pred = pipeline.predict(X)
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    return mae, rmse, r2


def _build_base_pipeline(model):
    """Standard pipeline: impute -> scale -> model."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler()),
        ("model", model),
    ])


def train_all_regression_models(X_train, X_test, y_train, y_test, feature_names):
    """
    Train and evaluate all regression models.

    Returns list of result dicts:
    {
        model_name, pipeline,
        train_mae, train_rmse, train_r2,
        test_mae, test_rmse, test_r2,
        cv_scores (list of MAE scores from TimeSeriesSplit),
        cv_mean, cv_std,
        best_params (if tuned),
        n_train, n_test
    }
    """
    _ensure_models_dir()
    results = []
    tscv = TimeSeriesSplit(n_splits=5)

    # ── Helper ──────────────────────────────────────────────────────────────

    def _evaluate(name, pipeline, X_tr, X_te, y_tr, y_te, best_params=None):
        pipeline.fit(X_tr, y_tr)

        tr_mae, tr_rmse, tr_r2 = _regression_metrics(pipeline, X_tr, y_tr)
        te_mae, te_rmse, te_r2 = _regression_metrics(pipeline, X_te, y_te)

        # TimeSeriesSplit CV on training data
        cv_scores = -cross_val_score(
            pipeline, X_tr, y_tr,
            cv=tscv, scoring="neg_mean_absolute_error"
        )

        return {
            "model_name": name,
            "pipeline": pipeline,
            "train_mae": round(float(tr_mae), 4),
            "train_rmse": round(float(tr_rmse), 4),
            "train_r2": round(float(tr_r2), 4),
            "test_mae": round(float(te_mae), 4),
            "test_rmse": round(float(te_rmse), 4),
            "test_r2": round(float(te_r2), 4),
            "cv_scores": [round(float(s), 4) for s in cv_scores],
            "cv_mean": round(float(cv_scores.mean()), 4),
            "cv_std": round(float(cv_scores.std()), 4),
            "best_params": best_params or {},
            "n_train": len(y_tr),
            "n_test": len(y_te),
        }

    # ── 1. Simple Linear Regression (single best feature) ───────────────────
    best_single_feat = "rolling_7_mean"
    feat_idx = feature_names.index(best_single_feat) if best_single_feat in feature_names else 0
    X_tr_single = X_train.iloc[:, [feat_idx]]
    X_te_single = X_test.iloc[:, [feat_idx]]

    pipe_simple = _build_base_pipeline(LinearRegression())
    results.append(_evaluate("Simple Linear Regression", pipe_simple, X_tr_single, X_te_single, y_train, y_test))

    # ── 2. Multiple Linear Regression ────────────────────────────────────────
    pipe_mlr = _build_base_pipeline(LinearRegression())
    results.append(_evaluate("Multiple Linear Regression", pipe_mlr, X_train, X_test, y_train, y_test))

    # ── 3. Polynomial Regression degree=2 ─────────────────────────────────
    pipe_poly2 = Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler()),
        ("poly", PolynomialFeatures(degree=2, include_bias=False)),
        ("model", LinearRegression()),
    ])
    results.append(_evaluate("Polynomial Regression (deg=2)", pipe_poly2, X_train, X_test, y_train, y_test))

    # ── 4. Polynomial Regression degree=3 ─────────────────────────────────
    pipe_poly3 = Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler()),
        ("poly", PolynomialFeatures(degree=3, include_bias=False)),
        ("model", LinearRegression()),
    ])
    results.append(_evaluate("Polynomial Regression (deg=3)", pipe_poly3, X_train, X_test, y_train, y_test))

    # ── 5. Ridge Regression with GridSearchCV ─────────────────────────────
    ridge_pipe = _build_base_pipeline(Ridge())
    ridge_grid = GridSearchCV(
        ridge_pipe,
        param_grid={"model__alpha": [0.01, 0.1, 1, 10, 100]},
        cv=3, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    ridge_grid.fit(X_train, y_train)
    best_ridge = ridge_grid.best_estimator_
    results.append(_evaluate("Ridge Regression", best_ridge, X_train, X_test, y_train, y_test,
                              best_params=ridge_grid.best_params_))

    # ── 6. Lasso Regression with GridSearchCV ─────────────────────────────
    lasso_pipe = _build_base_pipeline(Lasso(max_iter=10000))
    lasso_grid = GridSearchCV(
        lasso_pipe,
        param_grid={"model__alpha": [0.001, 0.01, 0.1, 1, 10]},
        cv=3, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    lasso_grid.fit(X_train, y_train)
    best_lasso = lasso_grid.best_estimator_
    results.append(_evaluate("Lasso Regression", best_lasso, X_train, X_test, y_train, y_test,
                              best_params=lasso_grid.best_params_))

    # ── 7. SVR with GridSearchCV ────────────────────────────────────────────
    svr_pipe = _build_base_pipeline(SVR())
    svr_grid = GridSearchCV(
        svr_pipe,
        param_grid={
            "model__C": [0.1, 1, 10],
            "model__epsilon": [0.1, 0.5, 1],
            "model__kernel": ["rbf", "linear"],
        },
        cv=3, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    svr_grid.fit(X_train, y_train)
    best_svr = svr_grid.best_estimator_
    results.append(_evaluate("SVR", best_svr, X_train, X_test, y_train, y_test,
                              best_params=svr_grid.best_params_))

    # ── Save best model ──────────────────────────────────────────────────────
    best_result = min(results, key=lambda r: r["test_mae"])
    joblib.dump(best_result["pipeline"], os.path.join(MODELS_DIR, "best_regression.pkl"))
    best_result["is_best"] = True

    return results


def train_svm_classifier(X_train, X_test, y_train, y_test, thresholds=None, class_names=None):
    """
    Train SVM classifier for demand classification.
    GridSearchCV over C, kernel, gamma.

    Returns dict with accuracy, precision, recall, f1, confusion_matrix,
    classification_report, best_params, cv scores.
    Saves to MODELS_DIR/best_classifier.pkl
    """
    _ensure_models_dir()

    if class_names is None:
        class_names = ["Low", "Medium", "High"]

    # Check for single-class edge case
    unique_classes = np.unique(y_train)
    if len(unique_classes) < 2:
        return {
            "model_name": "SVM Classifier",
            "error": "Only one demand class present in training data. Need more varied data.",
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "confusion_matrix": [],
            "classification_report": "",
            "best_params": {},
            "cv_accuracy_scores": [],
            "n_train": len(y_train),
            "n_test": len(y_test),
            "class_thresholds": thresholds or {},
        }

    svc_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler()),
        ("model", SVC(probability=True, random_state=42)),
    ])

    param_grid = {
        "model__C": [0.1, 1, 10, 100],
        "model__kernel": ["rbf", "linear"],
        "model__gamma": ["scale", "auto"],
    }

    grid_search = GridSearchCV(
        svc_pipe, param_grid, cv=3, scoring="accuracy", n_jobs=-1
    )
    grid_search.fit(X_train, y_train)
    best_pipe = grid_search.best_estimator_

    # Evaluate
    y_pred = best_pipe.predict(X_test)
    y_pred_train = best_pipe.predict(X_train)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    cm = confusion_matrix(y_test, y_pred, labels=sorted(unique_classes))
    cr = classification_report(y_test, y_pred, zero_division=0)

    # CV accuracy scores
    cv_scores = cross_val_score(best_pipe, X_train, y_train, cv=3, scoring="accuracy")

    result = {
        "model_name": "SVM Classifier",
        "pipeline": best_pipe,
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "confusion_matrix": cm.tolist(),
        "classification_report": cr,
        "best_params": grid_search.best_params_,
        "cv_accuracy_scores": [round(float(s), 4) for s in cv_scores],
        "cv_mean": round(float(cv_scores.mean()), 4),
        "cv_std": round(float(cv_scores.std()), 4),
        "n_train": len(y_train),
        "n_test": len(y_test),
        "class_thresholds": thresholds or {},
        "class_names": class_names,
    }

    joblib.dump(best_pipe, os.path.join(MODELS_DIR, "best_classifier.pkl"))

    return result


def run_full_training_pipeline(sales_data: list) -> dict:
    """
    Main entry point.
    Input: list of sale dicts (product_name, date, quantity, revenue, product_id)
    1. Convert to DataFrame
    2. Aggregate by date + product
    3. Engineer features
    4. Split chronologically (80% train, 20% test)
    5. Train all regression models
    6. Train SVM classifier
    7. Return summary dict with all results

    Returns {error: ...} if dataset < 30 rows.
    """
    if len(sales_data) < 30:
        return {
            "error": "Insufficient data for reliable training. Need at least 30 sales records."
        }

    # ── 1. Build DataFrame ─────────────────────────────────────────────────
    df = pd.DataFrame(sales_data)
    df["date"] = pd.to_datetime(df["date"])
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)

    # ── 2. Aggregate by date + product ─────────────────────────────────────
    agg_df = (
        df.groupby(["date", "product_id"])
        .agg(quantity=("quantity", "sum"), revenue=("revenue", "sum"))
        .reset_index()
    )

    # ── 3. Engineer features ────────────────────────────────────────────────
    feat_df = engineer_features(agg_df)

    # ── 4. Prepare regression data ─────────────────────────────────────────
    X, y, feature_names = prepare_regression_data(feat_df)

    if len(X) < 30:
        return {
            "error": "Insufficient data after feature engineering. Need at least 30 usable rows."
        }

    # Chronological split (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # ── 5. Regression models ───────────────────────────────────────────────
    regression_results = train_all_regression_models(X_train, X_test, y_train, y_test, feature_names)

    # ── 6. Classification ──────────────────────────────────────────────────
    X_cls, y_cls, thresholds, class_names = prepare_classification_data(feat_df)

    split_cls = int(len(X_cls) * 0.8)
    X_cls_train = X_cls.iloc[:split_cls]
    X_cls_test = X_cls.iloc[split_cls:]
    y_cls_train = y_cls.iloc[:split_cls]
    y_cls_test = y_cls.iloc[split_cls:]

    classification_result = train_svm_classifier(
        X_cls_train, X_cls_test, y_cls_train, y_cls_test,
        thresholds=thresholds, class_names=class_names
    )

    # ── 7. Compose summary ─────────────────────────────────────────────────
    best_reg = min(regression_results, key=lambda r: r["test_mae"])

    return {
        "regression_results": [
            {k: v for k, v in r.items() if k != "pipeline"}
            for r in regression_results
        ],
        "classification_result": {
            k: v for k, v in classification_result.items() if k != "pipeline"
        },
        "best_regression_model": best_reg["model_name"],
        "best_regression_mae": best_reg["test_mae"],
        "best_regression_r2": best_reg["test_r2"],
        "n_total_samples": len(X),
        "n_train": len(y_train),
        "n_test": len(y_test),
        "feature_names": feature_names,
        "thresholds": thresholds,
        "class_names": class_names,
    }


def load_best_regression_model():
    """Load best_regression.pkl if exists, else return None."""
    path = os.path.join(MODELS_DIR, "best_regression.pkl")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def load_best_classifier():
    """Load best_classifier.pkl if exists, else return None."""
    path = os.path.join(MODELS_DIR, "best_classifier.pkl")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def predict_demand(product_id: int, forecast_date: str, sales_data: list) -> dict:
    """
    Make prediction for a specific product and date.
    Returns {predicted_cups, expected_revenue, model_name, model_used, warning_message}
    """
    pipeline = load_best_regression_model()
    warning_message = None

    if pipeline is None:
        return {
            "predicted_cups": None,
            "expected_revenue": None,
            "model_name": None,
            "model_used": False,
            "warning_message": "No trained regression model found. Please run training first.",
        }

    # Build product-specific DataFrame
    df = pd.DataFrame(sales_data)
    df["date"] = pd.to_datetime(df["date"])
    product_df = df[df["product_id"] == product_id].sort_values("date")

    if product_df.empty:
        return {
            "predicted_cups": None,
            "expected_revenue": None,
            "model_name": None,
            "model_used": False,
            "warning_message": f"No historical data found for product_id={product_id}.",
        }

    last_known_date = product_df["date"].max()
    target_date = pd.to_datetime(forecast_date)

    if target_date <= last_known_date:
        warning_message = "Forecast date is not in the future; features may be approximate."

    X_pred = get_next_day_features(last_known_date, product_df)

    try:
        predicted_cups = float(pipeline.predict(X_pred)[0])
        predicted_cups = max(0.0, round(predicted_cups, 2))
    except Exception as e:
        return {
            "predicted_cups": None,
            "expected_revenue": None,
            "model_name": str(pipeline.named_steps.get("model", "Unknown")),
            "model_used": True,
            "warning_message": f"Prediction failed: {e}",
        }

    # Estimate revenue using average unit price from historical data
    avg_unit_price = 0.0
    if "revenue" in product_df.columns and "quantity" in product_df.columns:
        total_qty = product_df["quantity"].sum()
        if total_qty > 0:
            avg_unit_price = product_df["revenue"].sum() / total_qty

    expected_revenue = round(predicted_cups * avg_unit_price, 2)

    model_name = type(pipeline.named_steps.get("model", "Unknown")).__name__

    return {
        "predicted_cups": predicted_cups,
        "expected_revenue": expected_revenue,
        "model_name": model_name,
        "model_used": True,
        "warning_message": warning_message,
    }


def classify_demand(features_dict: dict) -> dict:
    """
    Classify demand level for given features.
    Returns {predicted_class, class_name, model_name, probabilities_if_available}
    """
    pipeline = load_best_classifier()

    if pipeline is None:
        return {
            "predicted_class": None,
            "class_name": "Unknown",
            "model_name": None,
            "probabilities_if_available": None,
            "error": "No trained classifier found. Please run training first.",
        }

    class_names = ["Low", "Medium", "High"]

    feature_order = [
        "day_of_week", "is_weekend", "month", "day_of_month",
        "week_of_year", "lag_1_qty", "lag_7_qty", "rolling_7_mean",
    ]

    row = {k: features_dict.get(k, np.nan) for k in feature_order}
    X = pd.DataFrame([row])

    try:
        pred = int(pipeline.predict(X)[0])
        class_name = class_names[pred] if 0 <= pred < len(class_names) else str(pred)

        probabilities = None
        if hasattr(pipeline, "predict_proba"):
            proba = pipeline.predict_proba(X)[0]
            probabilities = {class_names[i]: round(float(p), 4) for i, p in enumerate(proba)
                            if i < len(class_names)}

        model_name = type(pipeline.named_steps.get("model", "Unknown")).__name__

        return {
            "predicted_class": pred,
            "class_name": class_name,
            "model_name": model_name,
            "probabilities_if_available": probabilities,
        }

    except Exception as e:
        return {
            "predicted_class": None,
            "class_name": "Unknown",
            "model_name": None,
            "probabilities_if_available": None,
            "error": str(e),
        }
