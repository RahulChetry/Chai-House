import csv
import io
from datetime import date, timedelta

from sqlalchemy import func

from app import db
from app.models import Sale, Product


# ── Helpers ──────────────────────────────────────────────────────────────────

def _aggregate_sales_for_range(start_date: date, end_date: date) -> dict:
    """Return aggregated metrics for a date range."""
    rows = (
        db.session.query(
            Product.name.label('product_name'),
            func.sum(Sale.quantity).label('cups'),
            func.sum(Sale.revenue).label('revenue'),
            func.sum(Sale.gross_profit).label('profit'),
            func.count(Sale.id).label('transactions'),
        )
        .join(Product, Sale.product_id == Product.id)
        .filter(Sale.date >= start_date, Sale.date <= end_date)
        .group_by(Product.id, Product.name)
        .all()
    )

    by_product = [
        {
            'product_name': r.product_name,
            'cups': int(r.cups or 0),
            'revenue': round(float(r.revenue or 0), 2),
            'profit': round(float(r.profit or 0), 2),
            'transactions': int(r.transactions or 0),
        }
        for r in rows
    ]

    total_revenue = sum(p['revenue'] for p in by_product)
    total_cups = sum(p['cups'] for p in by_product)
    total_profit = sum(p['profit'] for p in by_product)
    total_transactions = sum(p['transactions'] for p in by_product)

    return {
        'revenue': round(total_revenue, 2),
        'cups': total_cups,
        'profit': round(total_profit, 2),
        'transactions': total_transactions,
        'by_product': by_product,
    }


def _daily_breakdown(start_date: date, end_date: date) -> list:
    """Return per-day revenue/cups for the specified range."""
    rows = (
        db.session.query(
            Sale.date,
            func.sum(Sale.revenue).label('revenue'),
            func.sum(Sale.quantity).label('cups'),
            func.sum(Sale.gross_profit).label('profit'),
        )
        .filter(Sale.date >= start_date, Sale.date <= end_date)
        .group_by(Sale.date)
        .order_by(Sale.date)
        .all()
    )
    date_map = {
        r.date: {
            'revenue': round(float(r.revenue or 0), 2),
            'cups': int(r.cups or 0),
            'profit': round(float(r.profit or 0), 2),
        }
        for r in rows
    }

    result = []
    delta = (end_date - start_date).days + 1
    for i in range(delta):
        d = start_date + timedelta(days=i)
        entry = date_map.get(d, {'revenue': 0.0, 'cups': 0, 'profit': 0.0})
        result.append({'date': str(d), **entry})
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def get_daily_report(report_date: date) -> dict:
    """Return metrics for a single day."""
    report = _aggregate_sales_for_range(report_date, report_date)
    report['date'] = str(report_date)
    return report


def get_weekly_report(start_date: date) -> dict:
    """Return metrics for a 7-day period starting at start_date."""
    end_date = start_date + timedelta(days=6)
    report = _aggregate_sales_for_range(start_date, end_date)
    report['start_date'] = str(start_date)
    report['end_date'] = str(end_date)
    report['daily_breakdown'] = _daily_breakdown(start_date, end_date)
    return report


def get_monthly_report(year: int, month: int) -> dict:
    """Return metrics for a full calendar month."""
    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    report = _aggregate_sales_for_range(start_date, end_date)
    report['year'] = year
    report['month'] = month
    report['daily_breakdown'] = _daily_breakdown(start_date, end_date)
    return report


def generate_sales_csv() -> str:
    """Generate a full CSV export of all sales."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'ID', 'Date', 'Product', 'Quantity', 'Unit Price',
        'Unit Cost', 'Revenue', 'Gross Profit', 'Notes', 'Created At',
    ])

    sales = (
        Sale.query
        .join(Product, Sale.product_id == Product.id)
        .order_by(Sale.date.desc())
        .all()
    )
    for s in sales:
        writer.writerow([
            s.id, s.date, s.product.name, s.quantity,
            s.unit_price, s.unit_cost, s.revenue, s.gross_profit,
            s.notes or '', s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    return buf.getvalue()


def generate_products_csv() -> str:
    """Generate a product-level summary CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'Product ID', 'Product Name', 'Selling Price', 'Cost Price',
        'Is Active', 'Total Cups Sold', 'Total Revenue', 'Total Profit',
    ])

    rows = (
        db.session.query(
            Product,
            func.coalesce(func.sum(Sale.quantity), 0).label('total_cups'),
            func.coalesce(func.sum(Sale.revenue), 0.0).label('total_revenue'),
            func.coalesce(func.sum(Sale.gross_profit), 0.0).label('total_profit'),
        )
        .outerjoin(Sale, Sale.product_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.name)
        .all()
    )
    for row in rows:
        p = row[0]
        writer.writerow([
            p.id, p.name, p.selling_price, p.cost_price,
            'Yes' if p.is_active else 'No',
            int(row.total_cups), round(float(row.total_revenue), 2),
            round(float(row.total_profit), 2),
        ])
    return buf.getvalue()
