from datetime import date, timedelta

from sqlalchemy import func

from app import db
from app.models import Sale, Product


def get_today_stats() -> dict:
    """Return revenue, cups sold, profit, and transaction count for today."""
    today = date.today()
    result = (
        db.session.query(
            func.coalesce(func.sum(Sale.revenue), 0.0).label('revenue'),
            func.coalesce(func.sum(Sale.quantity), 0).label('cups'),
            func.coalesce(func.sum(Sale.gross_profit), 0.0).label('profit'),
            func.count(Sale.id).label('transactions'),
        )
        .filter(Sale.date == today)
        .one()
    )
    return {
        'revenue': round(float(result.revenue), 2),
        'cups': int(result.cups),
        'profit': round(float(result.profit), 2),
        'transactions': int(result.transactions),
    }


def get_sales_trend(days: int = 30) -> list:
    """Return daily revenue and cups for the last `days` days."""
    start_date = date.today() - timedelta(days=days - 1)
    rows = (
        db.session.query(
            Sale.date,
            func.sum(Sale.revenue).label('revenue'),
            func.sum(Sale.quantity).label('cups'),
        )
        .filter(Sale.date >= start_date)
        .group_by(Sale.date)
        .order_by(Sale.date)
        .all()
    )
    # Fill in missing dates with zeros
    date_map = {r.date: {'revenue': float(r.revenue), 'cups': int(r.cups)} for r in rows}
    result = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        entry = date_map.get(d, {'revenue': 0.0, 'cups': 0})
        result.append({'date': d, 'revenue': round(entry['revenue'], 2), 'cups': entry['cups']})
    return result


def get_revenue_by_product() -> list:
    """Return total revenue grouped by product."""
    rows = (
        db.session.query(
            Product.name.label('product_name'),
            func.coalesce(func.sum(Sale.revenue), 0.0).label('revenue'),
        )
        .outerjoin(Sale, Sale.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(Sale.revenue).desc())
        .all()
    )
    return [
        {'product_name': r.product_name, 'revenue': round(float(r.revenue), 2)}
        for r in rows
    ]


def get_recent_transactions(limit: int = 10) -> list:
    """Return the most recent `limit` sales with product names."""
    sales = (
        Sale.query
        .order_by(Sale.date.desc(), Sale.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            'id': s.id,
            'date': str(s.date),
            'product_name': s.product.name,
            'quantity': s.quantity,
            'unit_price': s.unit_price,
            'revenue': s.revenue,
            'gross_profit': s.gross_profit,
        }
        for s in sales
    ]


def get_best_selling_product() -> dict:
    """Return the product with the highest total cups sold."""
    row = (
        db.session.query(
            Product.name.label('name'),
            func.coalesce(func.sum(Sale.quantity), 0).label('total_cups'),
        )
        .outerjoin(Sale, Sale.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(Sale.quantity).desc())
        .first()
    )
    if row:
        return {'name': row.name, 'total_cups': int(row.total_cups)}
    return {'name': 'N/A', 'total_cups': 0}
