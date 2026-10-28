"""
Chai House AI — Production Startup Entry Point
================================================
Used by Render/Railway/Heroku via:  gunicorn wsgi:app
"""
import os
from app import create_app

# Detect environment
env = os.environ.get('FLASK_ENV', 'production')
config_name = 'production' if env == 'production' else 'development'

app = create_app(config_name)


def init_production_db():
    """Create tables and seed demo data if DB is empty."""
    with app.app_context():
        from app.models import db, Product, Sale, Ingredient
        db.create_all()

        # Only seed if completely empty
        if Product.query.count() == 0:
            print("[STARTUP] Fresh database detected — seeding demo data...")
            from app.services.demo_service import load_demo_data
            count = load_demo_data()
            print(f"[STARTUP] Seeded {count} demo sales records.")

            # Train basic models
            try:
                print("[STARTUP] Training ML models...")
                from app.ml.trainer import run_full_training_pipeline
                from app.models import Sale
                sales = Sale.query.all()
                sales_data = [{
                    'id': s.id, 'product_id': s.product_id,
                    'product_name': s.product.name,
                    'date': s.date.strftime('%Y-%m-%d'),
                    'quantity': s.quantity,
                    'revenue': float(s.revenue or 0),
                    'gross_profit': float(s.gross_profit or 0),
                } for s in sales]
                results = run_full_training_pipeline(sales_data)
                if 'error' not in results:
                    print(f"[STARTUP] ML training complete. Best model: {results.get('best_regression_model')}")
                else:
                    print(f"[STARTUP] ML training skipped: {results.get('error')}")
            except Exception as e:
                print(f"[STARTUP] ML training error (non-fatal): {e}")
        else:
            print(f"[STARTUP] Database has {Product.query.count()} products — skipping seed.")


# Run initialization
init_production_db()


if __name__ == '__main__':
    app.run()
