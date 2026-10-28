from datetime import datetime, date

from flask import Blueprint, render_template, request, Response

from app.services.report_service import (
    get_daily_report,
    get_weekly_report,
    get_monthly_report,
    generate_sales_csv,
    generate_products_csv,
)

reports_bp = Blueprint('reports', __name__)


def _parse_date(s: str):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


MONTH_NAMES = [
    (1,'January'),(2,'February'),(3,'March'),(4,'April'),
    (5,'May'),(6,'June'),(7,'July'),(8,'August'),
    (9,'September'),(10,'October'),(11,'November'),(12,'December'),
]

@reports_bp.route('/reports')
def index():
    today = date.today()
    return render_template(
        'reports/index.html',
        today=today.strftime('%Y-%m-%d'),
        months=MONTH_NAMES,
        current_year=today.year,
        current_month=today.month,
    )


@reports_bp.route('/reports/daily')
def daily_report():
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    report_date = _parse_date(date_str) or date.today()
    report = get_daily_report(report_date)
    return render_template('reports/daily.html', report=report,
                           report_date=report_date.strftime('%Y-%m-%d'))


@reports_bp.route('/reports/weekly')
def weekly_report():
    start_str = request.args.get('start', '')
    start_date = _parse_date(start_str) or date.today()
    report = get_weekly_report(start_date)
    return render_template('reports/weekly.html', report=report,
                           start_date=start_date.strftime('%Y-%m-%d'))


@reports_bp.route('/reports/monthly')
def monthly_report():
    try:
        year = int(request.args.get('year', date.today().year))
        month = int(request.args.get('month', date.today().month))
    except (ValueError, TypeError):
        year, month = date.today().year, date.today().month
    report = get_monthly_report(year, month)
    return render_template('reports/monthly.html', report=report, year=year, month=month)


@reports_bp.route('/reports/export/sales-csv')
def export_sales_csv():
    csv_content = generate_sales_csv()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sales_report.csv'},
    )


@reports_bp.route('/reports/export/products-csv')
def export_products_csv():
    csv_content = generate_products_csv()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=products_report.csv'},
    )
