# Chai House AI — Intelligent Sales Forecasting & Demand Classification System

> **Har Sip Mein Ghar Ka Ehsaas** 🍵

A complete, professional web application built for a real tea stall to manage sales, forecast demand using Machine Learning, classify demand with SVMs, and analyse profitability.

---

## 📋 Project Abstract

Chai House AI is a full-stack web application that combines a Flask backend, SQLite database, and scikit-learn ML pipeline to help a small tea stall owner manage daily operations and make data-driven decisions. The system demonstrates all three modules of the ML syllabus through real, working implementations — not just theory.

---

## 🎯 Problem Statement

Small tea stall owners lack tools to:
- Track daily sales and profitability systematically
- Forecast how much tea to prepare the next day
- Identify demand trends across products and seasons
- Manage ingredient inventory proactively

---

## 🏆 Objectives

1. Record daily sales manually (cups sold per product)
2. Calculate revenue, cost, and gross profit automatically
3. Forecast next-day demand using 6 regression models
4. Classify demand as Low / Medium / High using SVM
5. Compare all ML models with proper evaluation (no data leakage)
6. Track ingredient inventory and alert when stock is low
7. Export reports as CSV for accounting

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Bootstrap 5, Chart.js, Bootstrap Icons |
| Backend | Python 3.14, Flask 3.1 |
| Database | SQLite via Flask-SQLAlchemy |
| ML | scikit-learn 1.8, pandas, numpy, joblib |
| Security | Flask-WTF CSRF protection |

---

## 📁 Project Structure

```
ChaiHouseAI/
├── app.py                      # Entry point
├── config.py                   # Configuration classes
├── requirements.txt            # Dependencies
├── train_models.py             # Standalone ML training script
├── evaluate_models.py          # Model evaluation script
├── generate_5000_dataset.py    # Synthetic dataset generator
├── healthcheck.py              # Page health checker
├── data/
│   └── chai_house_5000_dataset.csv   # Exported dataset (5450 rows)
├── models/
│   ├── best_regression.pkl     # Best trained regression model
│   └── best_classifier.pkl     # Trained SVM classifier
├── instance/
│   └── chai_house.db           # SQLite database
└── app/
    ├── __init__.py             # App factory
    ├── models.py               # SQLAlchemy models
    ├── ml/
    │   ├── features.py         # Feature engineering (lag, rolling, etc.)
    │   ├── trainer.py          # All 7 models + SVM training pipeline
    │   └── evaluator.py        # Metrics, interpretation, leakage checks
    ├── routes/
    │   ├── dashboard.py        # Dashboard + demo data loader
    │   ├── sales.py            # CRUD sales management
    │   ├── products.py         # Product management
    │   ├── inventory.py        # Ingredient stock tracking
    │   ├── reports.py          # Daily/weekly/monthly reports + CSV
    │   ├── ml_prediction.py    # Demand prediction page
    │   ├── ml_comparison.py    # Model comparison + SVM classification
    │   └── concepts.py         # Educational ML concepts page
    ├── services/
    │   ├── sales_service.py    # Dashboard stats calculations
    │   ├── demo_service.py     # Demo data seeder
    │   ├── inventory_service.py
    │   └── report_service.py
    ├── static/
    │   ├── css/main.css
    │   └── js/main.js
    └── templates/              # Jinja2 HTML templates
```

---

## 🗄️ Database Schema

### Products
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | VARCHAR | e.g. "Regular Tea" |
| selling_price | FLOAT | e.g. 20.0 |
| cost_price | FLOAT | e.g. 8.0 |
| is_active | BOOLEAN | Show in sales form |

### Sales
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| product_id | FK → Products | |
| date | DATETIME | Transaction timestamp |
| quantity | INTEGER | Cups sold |
| unit_price | FLOAT | Price at time of sale |
| unit_cost | FLOAT | Cost at time of sale |
| revenue | FLOAT | quantity × unit_price |
| gross_profit | FLOAT | quantity × (price − cost) |
| notes | TEXT | Source tag |

### Ingredients, Recipes, InventoryTransaction, ModelEvaluation
*(See `app/models.py` for full schema)*

---

## 🤖 ML Algorithms Implemented

### Regression Models (predict cups sold)
1. **Simple Linear Regression** — single feature (rolling_7_mean)
2. **Multiple Linear Regression** — all 8 features
3. **Polynomial Regression deg=2** — non-linear patterns
4. **Polynomial Regression deg=3** — higher complexity (shows overfitting)
5. **Ridge Regression** (L2) — alpha tuned via GridSearchCV
6. **Lasso Regression** (L1) — alpha tuned, automatic feature selection
7. **SVR** — C, epsilon, kernel tuned via GridSearchCV

### Classification (Low / Medium / High demand)
- **SVM Classifier (SVC)** — C, kernel, gamma tuned via GridSearchCV

### Features Used (NO data leakage)
```
day_of_week, is_weekend, month, day_of_month,
week_of_year, lag_1_qty, lag_7_qty, rolling_7_mean
```
Revenue, price, cost intentionally excluded — they would cause leakage.

### Evaluation Strategy
- **80/20 chronological split** (no random shuffle — sales data is time-series)
- **TimeSeriesSplit(n_splits=5)** cross-validation
- **GridSearchCV(cv=3)** for hyperparameter tuning
- Model selected by **lowest test MAE** (not training accuracy)

---

## 📊 Actual Results (5,450 training records)

### Regression
| Model | Test MAE | Test R² |
|-------|----------|---------|
| **Multiple Linear Regression** 🥇 | **6.47 cups** | **0.767** |
| Ridge Regression | 6.47 | 0.767 |
| Lasso Regression | 6.48 | 0.767 |
| Polynomial (deg=2) | 6.59 | 0.764 |
| Simple Linear | 7.26 | 0.729 |
| SVR | 8.15 | 0.529 |
| Polynomial (deg=3) | 8.81 | 0.435 ← **overfitting** |

### SVM Classifier
| Metric | Value |
|--------|-------|
| Accuracy | 73.2% |
| F1 Score | 73.4% |
| CV Accuracy | **82.9% ± 0.3%** |

---

## 🚀 Installation & Setup (Windows)

### 1. Prerequisites
- Python 3.10+ installed
- Internet connection (for first install)

### 2. Install dependencies
```cmd
cd "D:\1st Sem Math video\CHAI WEB\ChaiHouseAI"
pip install -r requirements.txt
```

### 3. Run the application
```cmd
python app.py
```

### 4. Open in browser
```
http://127.0.0.1:5000
```

### 5. Load demo data (first time)
Click **"Load Demo Data"** on the Dashboard, or run:
```cmd
python generate_5000_dataset.py
```

### 6. Train ML models
```cmd
python train_models.py
```
Or click **"Train All Models"** on the ML Comparison page.

---

## 🧪 Running Tests
```cmd
python -m pytest tests/ -v
```

---

## 🌐 Pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/` | Overview, charts, forecast |
| Sales | `/sales` | Add/edit/delete sales |
| Products | `/products` | Menu management |
| Inventory | `/inventory` | Stock tracking |
| Reports | `/reports` | Daily/weekly/monthly + CSV export |
| Prediction | `/predict` | ML demand forecast |
| Classification | `/ml-comparison/classify` | SVM demand class |
| Model Comparison | `/ml-comparison` | All 7 models compared |
| ML Concepts | `/concepts` | Syllabus study guide |

---

## ⚠️ Known Limitations

1. **Single user** — no login/authentication (local use only)
2. **Synthetic dataset** — 5,000 rows are generated, not real shop data
3. **No weather/holiday API** — these features use dummy values
4. **Forecast uncertainty** — MAE ~6 cups means ±6 cup error typical
5. **Local only** — not deployed to cloud; runs on localhost

---

## 🔮 Future Improvements

- User authentication & multi-user support
- Real weather API integration (OpenWeatherMap)
- WhatsApp/SMS daily report notifications
- Mobile app (Flutter or React Native)
- More advanced models (XGBoost, LSTM for time series)
- Automated retraining when new data accumulates

---

## 📚 Syllabus Coverage

| Module | Topic | Implementation |
|--------|-------|---------------|
| M1 | Model Selection | 7 models compared on test MAE |
| M1 | Overfitting | Poly deg=3 shows high test MAE |
| M1 | Bias-Variance | Shown in comparison table |
| M1 | Regularization | Ridge + Lasso with alpha tuning |
| M1 | Cross-Validation | TimeSeriesSplit(n=5) |
| M1 | Hyperparameter Tuning | GridSearchCV on Ridge/Lasso/SVR/SVM |
| M2 | Simple Linear Regression | Single feature model |
| M2 | Multiple Linear Regression | Best model (R²=0.767) |
| M2 | Polynomial Regression | deg=2 and deg=3 |
| M2 | Ridge Regression | L2 penalty, shrinks coefficients |
| M2 | Lasso Regression | L1 penalty, feature selection |
| M3 | SVM Classification | SVC with soft margin |
| M3 | Hyperplane | Linear/RBF kernel |
| M3 | Slack Variables | C parameter controls violations |
| M3 | SVR | Support Vector Regression |
| M3 | SVM Evaluation | Confusion matrix, F1, accuracy |

---

*Built with ❤️ for Chai House — Har Sip Mein Ghar Ka Ehsaas*
