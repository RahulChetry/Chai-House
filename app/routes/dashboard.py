import json
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, jsonify

from app.models import Sale, Product, Ingredient
from app.services.sales_service import (
    get_today_stats,
    get_sales_trend,
    get_revenue_by_product,
    get_recent_transactions,
    get_best_selling_product,
)
from app import db

dashboard_bp = Blueprint('dashboard', __name__)


def _load_next_day_forecast():
    """Try to load the best saved regression model and forecast tomorrow."""
    import os, joblib, numpy as np
    models_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'models'
    )
    if not os.path.isdir(models_dir):
        return None

    model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib') and 'regression' in f]
    if not model_files:
        return None

    try:
        # Pick the first available regression model
        model_path = os.path.join(models_dir, sorted(model_files)[0])
        bundle = joblib.load(model_path)
        model = bundle.get('model')
        feature_names = bundle.get('feature_names', [])
        product_ids = bundle.get('product_ids', [])

        tomorrow = date.today() + timedelta(days=1)
        dow = tomorrow.weekday()
        is_weekend = 1 if dow >= 5 else 0
        month = tomorrow.month

        forecasts = []
        products = Product.query.filter(Product.id.in_(product_ids), Product.is_active == True).all()
        for prod in products:
            features = np.array([[prod.id, dow, is_weekend, month]])
            predicted_cups = max(0, int(round(model.predict(features)[0])))
            expected_revenue = round(predicted_cups * prod.selling_price, 2)
            forecasts.append({
                'product_name': prod.name,
                'predicted_cups': predicted_cups,
                'expected_revenue': expected_revenue,
            })

        total_cups = sum(f['predicted_cups'] for f in forecasts)
        total_revenue = sum(f['expected_revenue'] for f in forecasts)
        return {
            'model_name': sorted(model_files)[0].replace('.joblib', ''),
            'forecast_date': tomorrow.strftime('%Y-%m-%d'),
            'total_predicted_cups': total_cups,
            'total_expected_revenue': round(total_revenue, 2),
            'by_product': forecasts,
        }
    except Exception:
        return None


@dashboard_bp.route('/')
def index():
    today_stats = get_today_stats()
    sales_trend = get_sales_trend(30)
    revenue_by_product = get_revenue_by_product()
    recent_transactions = get_recent_transactions(10)
    best_selling = get_best_selling_product()
    next_day_forecast = _load_next_day_forecast()

    low_stock = Ingredient.query.filter(
        Ingredient.quantity_on_hand <= Ingredient.min_threshold
    ).all()

    has_data = Sale.query.count() > 0

    # Serialize for Chart.js
    sales_trend_data = json.dumps([
        {'date': str(r['date']), 'revenue': r['revenue'], 'cups': r['cups']}
        for r in sales_trend
    ])
    revenue_by_product_data = json.dumps([
        {'product_name': r['product_name'], 'revenue': r['revenue']}
        for r in revenue_by_product
    ])

    return render_template(
        'dashboard.html',
        today_revenue=today_stats['revenue'],
        today_cups=today_stats['cups'],
        today_profit=today_stats['profit'],
        total_transactions=today_stats['transactions'],
        best_selling_product=best_selling,
        sales_trend_data=sales_trend_data,
        revenue_by_product=revenue_by_product_data,
        recent_transactions=recent_transactions,
        low_stock_ingredients=low_stock,
        next_day_forecast=next_day_forecast,
        has_data=has_data,
    )


@dashboard_bp.route('/api/load-demo', methods=['POST'])
def load_demo():
    try:
        from app.services.demo_service import load_demo_data
        count = load_demo_data()
        return jsonify({'success': True, 'message': 'Demo data loaded successfully.', 'count': count})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc), 'count': 0}), 500
