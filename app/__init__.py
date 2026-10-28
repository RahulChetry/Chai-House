import os
import click
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_name: str = 'default') -> Flask:
    """Application factory."""
    from config import config

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Ensure models folder exists
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
    os.makedirs(models_dir, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    # ── Blueprints ──────────────────────────────────────────────────────────
    from app.routes.dashboard import dashboard_bp
    from app.routes.sales import sales_bp
    from app.routes.products import products_bp
    from app.routes.inventory import inventory_bp
    from app.routes.reports import reports_bp
    from app.routes.ml_prediction import ml_prediction_bp
    from app.routes.ml_comparison import ml_comparison_bp
    from app.routes.concepts import concepts_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ml_prediction_bp)
    app.register_blueprint(ml_comparison_bp)
    app.register_blueprint(concepts_bp)

    # ── Error handlers ───────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    # ── CLI commands ─────────────────────────────────────────────────────────
    @app.cli.command('init-db')
    def init_db_command():
        """Create all database tables."""
        with app.app_context():
            db.create_all()
        click.echo('✅ Database tables created.')

    @app.cli.command('seed-demo')
    def seed_demo_command():
        """Load demo data into the database."""
        with app.app_context():
            from app.services.demo_service import load_demo_data
            count = load_demo_data()
        click.echo(f'✅ Demo data loaded — {count} sales records inserted.')

    return app
