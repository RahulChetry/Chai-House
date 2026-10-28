from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from app import db
from app.models import Ingredient, InventoryTransaction
from app.services.inventory_service import get_low_stock_alerts, update_stock as svc_update_stock

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/inventory')
def list_inventory():
    ingredients_raw = Ingredient.query.order_by(Ingredient.name).all()
    # Add is_low flag as a dynamic attribute for the template
    ingredients = []
    for ing in ingredients_raw:
        ing.is_low = float(ing.quantity_on_hand or 0) <= float(ing.min_threshold or 0)
        ingredients.append(ing)
    return render_template('inventory/list.html', ingredients=ingredients)


@inventory_bp.route('/inventory/add-ingredient', methods=['POST'])
def add_ingredient():
    name = request.form.get('name', '').strip()
    unit = request.form.get('unit', 'units').strip()
    quantity_str = request.form.get('quantity_on_hand', '0').strip()
    threshold_str = request.form.get('min_threshold', '0').strip()

    errors = []
    if not name:
        errors.append('Ingredient name is required.')
    if Ingredient.query.filter_by(name=name).first():
        errors.append(f'Ingredient "{name}" already exists.')
    try:
        quantity_on_hand = float(quantity_str)
    except (ValueError, TypeError):
        quantity_on_hand = 0.0
        errors.append('Quantity must be a number.')
    try:
        min_threshold = float(threshold_str)
    except (ValueError, TypeError):
        min_threshold = 0.0
        errors.append('Min threshold must be a number.')

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('inventory.list_inventory'))

    ingredient = Ingredient(
        name=name, unit=unit,
        quantity_on_hand=quantity_on_hand,
        min_threshold=min_threshold,
    )
    db.session.add(ingredient)
    db.session.commit()

    # Record initial stock transaction
    if quantity_on_hand > 0:
        txn = InventoryTransaction(
            ingredient_id=ingredient.id,
            quantity_change=quantity_on_hand,
            transaction_type='IN',
            date=date.today(),
            notes='Initial stock',
        )
        db.session.add(txn)
        db.session.commit()

    flash(f'Ingredient "{name}" added.', 'success')
    return redirect(url_for('inventory.list_inventory'))


@inventory_bp.route('/inventory/update-stock', methods=['POST'])
def update_stock_route():
    ingredient_id = request.form.get('ingredient_id', type=int)
    quantity_str = request.form.get('quantity_change', '').strip()
    transaction_type = request.form.get('transaction_type', 'IN').strip().upper()
    notes = request.form.get('notes', '').strip()

    if transaction_type not in ('IN', 'OUT', 'ADJUSTMENT'):
        flash('Invalid transaction type.', 'danger')
        return redirect(url_for('inventory.list_inventory'))

    try:
        quantity_change = float(quantity_str)
    except (ValueError, TypeError):
        flash('Quantity change must be a number.', 'danger')
        return redirect(url_for('inventory.list_inventory'))

    ingredient = Ingredient.query.get_or_404(ingredient_id)
    success = svc_update_stock(ingredient_id, quantity_change, transaction_type, notes or None)
    if success:
        flash(f'Stock updated for "{ingredient.name}".', 'success')
    else:
        flash('Failed to update stock.', 'danger')
    return redirect(url_for('inventory.list_inventory'))


@inventory_bp.route('/inventory/transactions')
def list_transactions():
    transactions = (
        InventoryTransaction.query
        .order_by(InventoryTransaction.date.desc(), InventoryTransaction.created_at.desc())
        .all()
    )
    return render_template('inventory/transactions.html', transactions=transactions)


@inventory_bp.route('/inventory/estimate')
def estimate_needs():
    forecast_date_str = request.args.get('forecast_date', '')
    if not forecast_date_str:
        return jsonify({'error': 'forecast_date parameter is required (YYYY-MM-DD)'}), 400

    try:
        forecast_date = datetime.strptime(forecast_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # Build a simple forecast dict using the ML model if available
    import os, joblib, numpy as np
    from app.models import Product
    models_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'models'
    )
    forecast = {}
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib') and 'regression' in f] if os.path.isdir(models_dir) else []
    if model_files:
        try:
            bundle = joblib.load(os.path.join(models_dir, sorted(model_files)[0]))
            model = bundle.get('model')
            product_ids = bundle.get('product_ids', [])
            dow = forecast_date.weekday()
            is_weekend = 1 if dow >= 5 else 0
            month = forecast_date.month
            products = Product.query.filter(Product.id.in_(product_ids), Product.is_active == True).all()
            for prod in products:
                features = np.array([[prod.id, dow, is_weekend, month]])
                predicted_cups = max(0, int(round(model.predict(features)[0])))
                forecast[prod.id] = predicted_cups
        except Exception:
            pass

    from app.services.inventory_service import estimate_ingredient_needs
    needs = estimate_ingredient_needs(forecast)
    return jsonify({'forecast_date': forecast_date_str, 'ingredient_needs': needs})
