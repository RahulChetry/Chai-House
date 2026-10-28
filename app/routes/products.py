import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func

from app import db
from app.models import Product, Sale

products_bp = Blueprint('products', __name__)


@products_bp.route('/products')
def list_products():
    products_data = (
        db.session.query(
            Product,
            func.coalesce(func.sum(Sale.quantity), 0).label('total_cups'),
            func.coalesce(func.sum(Sale.revenue), 0.0).label('total_revenue'),
        )
        .outerjoin(Sale, Sale.product_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.name)
        .all()
    )
    return render_template('products/list.html', products_data=products_data)


@products_bp.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        selling_price_str = request.form.get('selling_price', '').strip()
        cost_price_str = request.form.get('cost_price', '').strip()
        is_active = request.form.get('is_active') == 'on'

        errors = []
        if not name:
            errors.append('Product name is required.')
        if Product.query.filter_by(name=name).first():
            errors.append(f'A product named "{name}" already exists.')
        try:
            selling_price = float(selling_price_str)
            if selling_price <= 0:
                raise ValueError
        except (ValueError, TypeError):
            selling_price = None
            errors.append('Selling price must be a positive number.')
        try:
            cost_price = float(cost_price_str)
            if cost_price < 0:
                raise ValueError
        except (ValueError, TypeError):
            cost_price = None
            errors.append('Cost price must be a non-negative number.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('products/form.html', action='add', form_data=request.form)

        product = Product(
            name=name,
            selling_price=selling_price,
            cost_price=cost_price,
            is_active=is_active,
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{name}" added successfully.', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/form.html', action='add', form_data={})


@products_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id: int):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        selling_price_str = request.form.get('selling_price', '').strip()
        cost_price_str = request.form.get('cost_price', '').strip()
        is_active = request.form.get('is_active') == 'on'

        errors = []
        if not name:
            errors.append('Product name is required.')
        existing = Product.query.filter_by(name=name).first()
        if existing and existing.id != product_id:
            errors.append(f'A product named "{name}" already exists.')
        try:
            selling_price = float(selling_price_str)
            if selling_price <= 0:
                raise ValueError
        except (ValueError, TypeError):
            selling_price = None
            errors.append('Selling price must be a positive number.')
        try:
            cost_price = float(cost_price_str)
            if cost_price < 0:
                raise ValueError
        except (ValueError, TypeError):
            cost_price = None
            errors.append('Cost price must be a non-negative number.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('products/form.html', action='edit',
                                   product=product, form_data=request.form)

        product.name = name
        product.selling_price = selling_price
        product.cost_price = cost_price
        product.is_active = is_active
        db.session.commit()
        flash('Product updated. Existing sales prices are unchanged.', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/form.html', action='edit', product=product, form_data={})


@products_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
def toggle_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    state = 'activated' if product.is_active else 'deactivated'
    flash(f'Product "{product.name}" {state}.', 'info')
    return redirect(url_for('products.list_products'))


@products_bp.route('/products/<int:product_id>/stats')
def product_stats(product_id: int):
    product = Product.query.get_or_404(product_id)
    from sqlalchemy import func
    rows = (
        db.session.query(Sale.date, func.sum(Sale.quantity), func.sum(Sale.revenue))
        .filter(Sale.product_id == product_id)
        .group_by(Sale.date)
        .order_by(Sale.date)
        .all()
    )
    data = [{'date': str(r[0]), 'cups': int(r[1]), 'revenue': float(r[2])} for r in rows]
    return jsonify({'product': product.name, 'data': data})
