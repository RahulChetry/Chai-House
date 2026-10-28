import csv
import io
from datetime import date, datetime

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, Response, abort,
)

from app import db
from app.models import Sale, Product

sales_bp = Blueprint('sales', __name__)


def _parse_date(date_str: str):
    """Parse a YYYY-MM-DD string; return None on failure."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@sales_bp.route('/sales')
def list_sales():
    page = request.args.get('page', 1, type=int)
    start_str = request.args.get('start_date', '')
    end_str = request.args.get('end_date', '')
    product_id = request.args.get('product_id', None, type=int)

    query = Sale.query.order_by(Sale.date.desc(), Sale.created_at.desc())

    start_date = _parse_date(start_str)
    end_date = _parse_date(end_str)
    if start_date:
        query = query.filter(Sale.date >= start_date)
    if end_date:
        query = query.filter(Sale.date <= end_date)
    if product_id:
        query = query.filter(Sale.product_id == product_id)

    pagination = query.paginate(page=page, per_page=20, error_out=False)
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    return render_template(
        'sales/list.html',
        sales=pagination.items,
        pagination=pagination,
        products=products,
        start_date=start_str,
        end_date=end_str,
        selected_product_id=product_id,
    )


@sales_bp.route('/sales/add', methods=['GET', 'POST'])
def add_sale():
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        date_str = request.form.get('date', '').strip()
        quantity_str = request.form.get('quantity', '').strip()
        unit_price_str = request.form.get('unit_price', '').strip()
        unit_cost_str = request.form.get('unit_cost', '').strip()
        notes = request.form.get('notes', '').strip()

        errors = []

        product = Product.query.get(product_id) if product_id else None
        if not product or not product.is_active:
            errors.append('Please select a valid active product.')

        sale_date = _parse_date(date_str)
        if not sale_date:
            errors.append('Invalid date format. Use YYYY-MM-DD.')

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            quantity = None
            errors.append('Quantity must be a positive integer.')

        try:
            unit_price = float(unit_price_str)
            if unit_price <= 0:
                raise ValueError
        except (ValueError, TypeError):
            unit_price = None
            errors.append('Unit price must be a positive number.')

        try:
            unit_cost = float(unit_cost_str)
            if unit_cost < 0:
                raise ValueError
        except (ValueError, TypeError):
            unit_cost = None
            errors.append('Unit cost must be a non-negative number.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('sales/form.html', products=products, action='add',
                                   form_data=request.form)

        revenue = round(quantity * unit_price, 2)
        gross_profit = round(revenue - (quantity * unit_cost), 2)

        sale = Sale(
            product_id=product.id,
            date=sale_date,
            quantity=quantity,
            unit_price=unit_price,
            unit_cost=unit_cost,
            revenue=revenue,
            gross_profit=gross_profit,
            notes=notes or None,
        )
        db.session.add(sale)
        db.session.commit()
        flash(f'Sale recorded — ₹{revenue:.2f} revenue.', 'success')
        return redirect(url_for('sales.list_sales'))

    return render_template('sales/form.html', products=products, action='add', form_data={})


@sales_bp.route('/sales/<int:sale_id>/edit', methods=['GET', 'POST'])
def edit_sale(sale_id: int):
    sale = Sale.query.get_or_404(sale_id)
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        date_str = request.form.get('date', '').strip()
        quantity_str = request.form.get('quantity', '').strip()
        unit_price_str = request.form.get('unit_price', '').strip()
        unit_cost_str = request.form.get('unit_cost', '').strip()
        notes = request.form.get('notes', '').strip()

        errors = []

        product = Product.query.get(product_id) if product_id else None
        if not product:
            errors.append('Please select a valid product.')

        sale_date = _parse_date(date_str)
        if not sale_date:
            errors.append('Invalid date format. Use YYYY-MM-DD.')

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            quantity = None
            errors.append('Quantity must be a positive integer.')

        try:
            unit_price = float(unit_price_str)
            if unit_price <= 0:
                raise ValueError
        except (ValueError, TypeError):
            unit_price = None
            errors.append('Unit price must be a positive number.')

        try:
            unit_cost = float(unit_cost_str)
            if unit_cost < 0:
                raise ValueError
        except (ValueError, TypeError):
            unit_cost = None
            errors.append('Unit cost must be a non-negative number.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('sales/form.html', products=products, action='edit',
                                   sale=sale, form_data=request.form)

        sale.product_id = product.id
        sale.date = sale_date
        sale.quantity = quantity
        sale.unit_price = unit_price
        sale.unit_cost = unit_cost
        sale.revenue = round(quantity * unit_price, 2)
        sale.gross_profit = round(sale.revenue - (quantity * unit_cost), 2)
        sale.notes = notes or None
        db.session.commit()
        flash('Sale updated successfully.', 'success')
        return redirect(url_for('sales.list_sales'))

    return render_template('sales/form.html', products=products, action='edit',
                           sale=sale, form_data={})


@sales_bp.route('/sales/<int:sale_id>/delete', methods=['POST'])
def delete_sale(sale_id: int):
    sale = Sale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    flash('Sale deleted.', 'warning')
    return redirect(url_for('sales.list_sales'))


@sales_bp.route('/sales/export-csv')
def export_csv():
    sales = (
        Sale.query
        .join(Product)
        .order_by(Sale.date.desc())
        .all()
    )

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['ID', 'Date', 'Product', 'Quantity', 'Unit Price', 'Unit Cost',
                         'Revenue', 'Gross Profit', 'Notes', 'Created At'])
        for s in sales:
            writer.writerow([
                s.id, s.date, s.product.name, s.quantity,
                s.unit_price, s.unit_cost, s.revenue, s.gross_profit,
                s.notes or '', s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    headers = {
        'Content-Disposition': 'attachment; filename=sales_export.csv',
        'Content-Type': 'text/csv; charset=utf-8',
    }
    return Response(generate(), headers=headers)
