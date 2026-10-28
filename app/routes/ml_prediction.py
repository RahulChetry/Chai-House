"""
Chai House AI — ML Prediction Routes
Uses the best trained model from models/best_regression.pkl
"""
import os
from datetime import date, timedelta

from flask import Blueprint, render_template, request, flash, redirect, url_for

from app.models import Product, Sale
from app import db

ml_prediction_bp = Blueprint('ml_prediction', __name__)


@ml_prediction_bp.route('/predict', methods=['GET', 'POST'])
def predict_form():
    from app.ml.trainer import load_best_regression_model, predict_demand

    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    model_available = load_best_regression_model() is not None
    today = date.today().strftime('%Y-%m-%d')
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    prediction = None
    selected_product = None
    selected_date = tomorrow

    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        forecast_date = request.form.get('forecast_date', '').strip()
        selected_product = product_id
        selected_date = forecast_date or tomorrow

        if not product_id:
            flash('Please select a product.', 'danger')
        elif not model_available:
            flash('No trained model found. Go to ML Comparison page to train models first.', 'warning')
        else:
            try:
                # Load all sales data for feature engineering
                sales = Sale.query.join(Product).all()
                sales_data = [{
                    'product_id': s.product_id,
                    'product_name': s.product.name,
                    'date': s.date.strftime('%Y-%m-%d'),
                    'quantity': s.quantity,
                    'revenue': float(s.revenue or 0),
                } for s in sales]

                result = predict_demand(product_id, forecast_date or tomorrow, sales_data)

                if 'error' in result:
                    flash(result['error'], 'warning')
                else:
                    product = Product.query.get(product_id)

                    # Estimate ingredient requirements
                    ingredient_requirements = {}
                    if product:
                        from app.services.inventory_service import estimate_ingredient_needs
                        ingredient_requirements = estimate_ingredient_needs(
                            {product_id: result['predicted_cups']}
                        )

                    prediction = {
                        'product_name': product.name if product else 'Unknown',
                        'forecast_date': result.get('forecast_date', forecast_date),
                        'predicted_cups': result['predicted_cups'],
                        'expected_revenue': round(result['expected_revenue'], 2),
                        'model_name': result.get('model_name', 'Unknown'),
                        'ingredient_requirements': ingredient_requirements,
                        'warning_message': result.get('warning_message', ''),
                    }

            except Exception as exc:
                flash(f'Prediction error: {str(exc)}', 'danger')

    return render_template(
        'ml/prediction.html',
        products=products,
        model_available=model_available,
        today=today,
        selected_date=selected_date,
        selected_product=selected_product,
        prediction=prediction,
    )
