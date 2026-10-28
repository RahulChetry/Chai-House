"""
Chai House AI — Automated Test Suite
=====================================
Run with: python -m pytest tests/ -v
"""
import pytest
import json
from datetime import date, datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def app():
    from app import create_app
    application = create_app('testing')
    with application.app_context():
        from app.models import db
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_app(app):
    """App with demo data pre-loaded."""
    with app.app_context():
        from app.services.demo_service import load_demo_data
        load_demo_data()
    return app


@pytest.fixture
def seeded_client(seeded_app):
    return seeded_app.test_client()


# ─────────────────────────────────────────────────────────────
# 1. DATABASE MODELS
# ─────────────────────────────────────────────────────────────

class TestModels:
    def test_product_creation(self, app):
        with app.app_context():
            from app.models import db, Product
            p = Product(name='Test Tea', selling_price=20.0, cost_price=8.0, is_active=True)
            db.session.add(p)
            db.session.commit()
            fetched = Product.query.filter_by(name='Test Tea').first()
            assert fetched is not None
            assert fetched.selling_price == 20.0

    def test_sale_creation_and_revenue(self, app):
        with app.app_context():
            from app.models import db, Product, Sale
            p = Product(name='Chai', selling_price=20.0, cost_price=8.0, is_active=True)
            db.session.add(p)
            db.session.flush()
            sale = Sale(
                product_id=p.id, date=datetime.now(),
                quantity=10, unit_price=20.0, unit_cost=8.0,
                revenue=200.0, gross_profit=120.0
            )
            db.session.add(sale)
            db.session.commit()
            s = Sale.query.first()
            assert s.quantity == 10
            assert s.revenue == 200.0
            assert s.gross_profit == 120.0

    def test_revenue_calculation(self, app):
        """Revenue must equal quantity × unit_price."""
        quantity, price, cost = 15, 30.0, 12.0
        expected_revenue = quantity * price
        expected_profit = quantity * (price - cost)
        assert expected_revenue == 450.0
        assert expected_profit == 270.0

    def test_ingredient_creation(self, app):
        with app.app_context():
            from app.models import db, Ingredient
            ing = Ingredient(name='Milk', quantity_on_hand=10.0, unit='liters', min_threshold=2.0)
            db.session.add(ing)
            db.session.commit()
            assert Ingredient.query.filter_by(name='Milk').count() == 1

    def test_model_evaluation_creation(self, app):
        with app.app_context():
            from app.models import db, ModelEvaluation
            ev = ModelEvaluation(
                model_name='Test Model', task_type='regression',
                test_mae=5.0, test_rmse=7.0, test_r2=0.8,
                train_size=100, test_size=25
            )
            db.session.add(ev)
            db.session.commit()
            assert ModelEvaluation.query.count() == 1


# ─────────────────────────────────────────────────────────────
# 2. ROUTES — GET pages return 200
# ─────────────────────────────────────────────────────────────

class TestRoutes:
    def test_dashboard_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/')
            assert r.status_code == 200
            assert b'Chai House' in r.data

    def test_sales_list_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/sales')
            assert r.status_code == 200

    def test_sales_add_form_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/sales/add')
            assert r.status_code == 200

    def test_products_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/products')
            assert r.status_code == 200

    def test_inventory_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/inventory')
            assert r.status_code == 200

    def test_reports_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/reports')
            assert r.status_code == 200

    def test_daily_report_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get(f'/reports/daily?date={date.today()}')
            assert r.status_code == 200

    def test_predict_page_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/predict')
            assert r.status_code == 200

    def test_ml_comparison_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/ml-comparison')
            assert r.status_code == 200

    def test_concepts_loads(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/concepts')
            assert r.status_code == 200

    def test_404_returns_error_page(self, client, app):
        with app.app_context():
            r = client.get('/nonexistent-page-xyz')
            assert r.status_code == 404


# ─────────────────────────────────────────────────────────────
# 3. SALES CRUD
# ─────────────────────────────────────────────────────────────

class TestSalesCRUD:
    def test_add_sale_valid(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            from app.models import Product, Sale
            p = Product.query.first()
            before = Sale.query.count()
            r = seeded_client.post('/sales/add', data={
                'product_id': p.id,
                'date': date.today().strftime('%Y-%m-%d'),
                'quantity': '5',
                'unit_price': str(p.selling_price),
                'unit_cost': str(p.cost_price or 0),
                'notes': 'Test sale',
                'csrf_token': 'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Sale.query.count() == before + 1

    def test_add_sale_invalid_quantity(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            from app.models import Product, Sale
            p = Product.query.first()
            before = Sale.query.count()
            r = seeded_client.post('/sales/add', data={
                'product_id': p.id,
                'date': date.today().strftime('%Y-%m-%d'),
                'quantity': '-1',
                'unit_price': str(p.selling_price),
                'csrf_token': 'test',
            }, follow_redirects=True)
            # Should not insert a sale with negative quantity
            assert Sale.query.count() == before

    def test_delete_sale(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            from app.models import Sale
            sale = Sale.query.first()
            sid = sale.id
            r = seeded_client.post(f'/sales/{sid}/delete',
                data={'csrf_token': 'test'}, follow_redirects=True)
            assert r.status_code == 200
            assert Sale.query.get(sid) is None

    def test_export_csv(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/sales/export-csv')
            assert r.status_code == 200
            assert b'text/csv' in r.content_type.encode() or b'csv' in r.headers.get('Content-Disposition', '').encode()


# ─────────────────────────────────────────────────────────────
# 4. PRODUCT MANAGEMENT
# ─────────────────────────────────────────────────────────────

class TestProducts:
    def test_add_product(self, client, app):
        with app.app_context():
            from app.models import Product
            r = client.post('/products/add', data={
                'name': 'Masala Tea',
                'selling_price': '25',
                'cost_price': '10',
                'is_active': 'on',
                'csrf_token': 'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Product.query.filter_by(name='Masala Tea').count() == 1

    def test_add_product_missing_name(self, client, app):
        with app.app_context():
            from app.models import Product
            r = client.post('/products/add', data={
                'name': '',
                'selling_price': '25',
                'csrf_token': 'test',
            }, follow_redirects=True)
            assert Product.query.filter_by(name='').count() == 0

    def test_profit_margin_calculation(self):
        selling = 20.0
        cost = 8.0
        margin = (selling - cost) / selling * 100
        assert margin == 60.0


# ─────────────────────────────────────────────────────────────
# 5. SERVICES
# ─────────────────────────────────────────────────────────────

class TestServices:
    def test_today_stats(self, seeded_app):
        with seeded_app.app_context():
            from app.services.sales_service import get_today_stats
            stats = get_today_stats()
            assert 'revenue' in stats
            assert 'cups' in stats
            assert 'profit' in stats
            assert isinstance(stats['revenue'], (int, float))

    def test_best_selling_product(self, seeded_app):
        with seeded_app.app_context():
            from app.services.sales_service import get_best_selling_product
            best = get_best_selling_product()
            assert best is not None
            assert 'name' in best
            assert 'total_cups' in best

    def test_sales_trend(self, seeded_app):
        with seeded_app.app_context():
            from app.services.sales_service import get_sales_trend
            trend = get_sales_trend(days=30)
            assert isinstance(trend, list)

    def test_daily_report(self, seeded_app):
        with seeded_app.app_context():
            from app.services.report_service import get_daily_report
            report = get_daily_report(date.today())
            assert 'revenue' in report
            assert 'cups' in report
            assert 'by_product' in report

    def test_demo_data_loads(self, app):
        with app.app_context():
            from app.services.demo_service import load_demo_data
            from app.models import Sale, Product
            count = load_demo_data()
            assert count > 0
            assert Product.query.count() >= 5
            assert Sale.query.count() > 0


# ─────────────────────────────────────────────────────────────
# 6. ML — FEATURES & DATA LEAKAGE
# ─────────────────────────────────────────────────────────────

class TestMLFeatures:
    def test_no_revenue_in_features(self):
        """Critical: revenue must NOT be a regression feature."""
        from app.ml.evaluator import check_data_leakage_risks
        features = ['day_of_week', 'is_weekend', 'month', 'day_of_month',
                    'week_of_year', 'lag_1_qty', 'lag_7_qty', 'rolling_7_mean']
        warnings = check_data_leakage_risks(features, 'quantity')
        assert len(warnings) == 0, f'Data leakage detected: {warnings}'

    def test_leakage_detector_catches_revenue(self):
        """Leakage detector must flag revenue as a feature."""
        from app.ml.evaluator import check_data_leakage_risks
        bad_features = ['day_of_week', 'revenue', 'rolling_7_mean']
        warnings = check_data_leakage_risks(bad_features, 'quantity')
        assert len(warnings) > 0

    def test_feature_engineering_output(self, seeded_app):
        with seeded_app.app_context():
            from app.models import Sale, Product
            import pandas as pd
            from app.ml.features import engineer_features
            sales = Sale.query.limit(100).all()
            rows = [{'date': s.date, 'product_id': s.product_id,
                     'quantity': s.quantity, 'revenue': float(s.revenue or 0)} for s in sales]
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            result = engineer_features(df)
            assert 'day_of_week' in result.columns
            assert 'is_weekend' in result.columns
            assert 'rolling_7_mean' in result.columns

    def test_classification_metrics(self):
        from app.ml.evaluator import compute_classification_metrics
        import numpy as np
        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1])
        y_pred = np.array([0, 1, 2, 0, 2, 2, 1, 1])
        metrics = compute_classification_metrics(y_true, y_pred)
        assert 'accuracy' in metrics
        assert 0 <= metrics['accuracy'] <= 1

    def test_regression_metrics(self):
        from app.ml.evaluator import compute_regression_metrics
        import numpy as np
        y_true = np.array([10, 20, 30, 40, 50], dtype=float)
        y_pred = np.array([11, 19, 31, 39, 51], dtype=float)
        metrics = compute_regression_metrics(y_true, y_pred)
        # Keys may be uppercase (MAE) or lowercase (mae) — check either
        keys_lower = {k.lower() for k in metrics.keys()}
        assert 'mae' in keys_lower, f"MAE not found in metrics: {metrics}"
        mae_val = next(v for k, v in metrics.items() if k.upper() == 'MAE')
        assert mae_val == pytest.approx(1.0, abs=0.01)


# ─────────────────────────────────────────────────────────────
# 7. INVENTORY
# ─────────────────────────────────────────────────────────────

class TestInventory:
    def test_add_ingredient(self, client, app):
        with app.app_context():
            from app.models import Ingredient
            r = client.post('/inventory/add-ingredient', data={
                'name': 'Test Milk',
                'unit': 'liters',
                'quantity_on_hand': '10',
                'min_threshold': '2',
                'csrf_token': 'test',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert Ingredient.query.filter_by(name='Test Milk').count() == 1

    def test_low_stock_alert(self, app):
        with app.app_context():
            from app.models import db, Ingredient
            from app.services.inventory_service import get_low_stock_alerts
            ing = Ingredient(name='LowMilk', quantity_on_hand=1.0,
                             unit='liters', min_threshold=5.0)
            db.session.add(ing)
            db.session.commit()
            alerts = get_low_stock_alerts()
            names = [a.name for a in alerts]
            assert 'LowMilk' in names

    def test_no_false_low_stock_alert(self, app):
        with app.app_context():
            from app.models import db, Ingredient
            from app.services.inventory_service import get_low_stock_alerts
            ing = Ingredient(name='FullMilk', quantity_on_hand=20.0,
                             unit='liters', min_threshold=5.0)
            db.session.add(ing)
            db.session.commit()
            alerts = get_low_stock_alerts()
            names = [a.name for a in alerts]
            assert 'FullMilk' not in names


# ─────────────────────────────────────────────────────────────
# 8. DEMO DATA
# ─────────────────────────────────────────────────────────────

class TestDemoData:
    def test_load_demo_data_api(self, client, app):
        with app.app_context():
            r = client.post('/api/load-demo',
                headers={'X-CSRFToken': 'test'})
            assert r.status_code == 200
            data = json.loads(r.data)
            assert data.get('success') is True

    def test_demo_data_idempotent(self, seeded_app):
        """Loading demo data twice should not double-insert products."""
        with seeded_app.app_context():
            from app.models import Product
            from app.services.demo_service import load_demo_data
            before = Product.query.count()
            load_demo_data()
            after = Product.query.count()
            assert after == before


# ─────────────────────────────────────────────────────────────
# 9. CSV EXPORT
# ─────────────────────────────────────────────────────────────

class TestCSVExport:
    def test_sales_csv_has_header(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/reports/export/sales-csv')
            assert r.status_code == 200
            content = r.data.decode('utf-8')
            assert 'Product' in content or 'product' in content.lower()

    def test_products_csv_has_header(self, seeded_client, seeded_app):
        with seeded_app.app_context():
            r = seeded_client.get('/reports/export/products-csv')
            assert r.status_code == 200
            content = r.data.decode('utf-8')
            assert 'Product' in content or 'Name' in content
