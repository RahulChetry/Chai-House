"""
Chai House AI — 5000-Row Synthetic Dataset Generator
=====================================================
Generates realistic sales data with:
- Seasonal trends (summer = more cold drinks, winter = more hot tea)
- Weekend peaks (30% more sales on Sat/Sun)
- Morning/evening rush patterns
- Festival/holiday spikes
- Realistic variation and noise
- All 5 products with proper demand ratios
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta, datetime
import math

def generate_5000_rows():
    from app import create_app
    from app.models import db, Product, Sale, Ingredient, Recipe, InventoryTransaction

    app = create_app()
    with app.app_context():

        # ── Step 1: Ensure products exist ──────────────────────────────────────
        products_config = [
            {'name': 'Regular Tea',  'selling_price': 20.0, 'cost_price': 8.0},
            {'name': 'Medium Tea',   'selling_price': 30.0, 'cost_price': 12.0},
            {'name': 'Black Tea',    'selling_price': 10.0, 'cost_price': 3.0},
            {'name': 'Lemon Tea',    'selling_price': 15.0, 'cost_price': 5.0},
            {'name': 'Coffee',       'selling_price': 30.0, 'cost_price': 12.0},
        ]

        products = {}
        for pc in products_config:
            p = Product.query.filter_by(name=pc['name']).first()
            if not p:
                p = Product(
                    name=pc['name'],
                    selling_price=pc['selling_price'],
                    cost_price=pc['cost_price'],
                    is_active=True
                )
                db.session.add(p)
                db.session.flush()
            products[pc['name']] = p
        db.session.commit()
        print(f"  Products ready: {list(products.keys())}")

        # ── Step 2: Ensure ingredients ─────────────────────────────────────────
        ingredients_config = [
            {'name': 'Milk',          'unit': 'liters',  'quantity_on_hand': 50.0, 'min_threshold': 5.0},
            {'name': 'Tea Powder',    'unit': 'grams',   'quantity_on_hand': 2000.0, 'min_threshold': 200.0},
            {'name': 'Sugar',         'unit': 'grams',   'quantity_on_hand': 5000.0, 'min_threshold': 500.0},
            {'name': 'Ginger',        'unit': 'grams',   'quantity_on_hand': 500.0,  'min_threshold': 50.0},
            {'name': 'Lemon',         'unit': 'pieces',  'quantity_on_hand': 100.0,  'min_threshold': 10.0},
            {'name': 'Coffee Powder', 'unit': 'grams',   'quantity_on_hand': 1000.0, 'min_threshold': 100.0},
            {'name': 'Cups',          'unit': 'pieces',  'quantity_on_hand': 2000.0, 'min_threshold': 200.0},
        ]
        for ic in ingredients_config:
            if not Ingredient.query.filter_by(name=ic['name']).first():
                ing = Ingredient(**ic)
                db.session.add(ing)
        db.session.commit()

        # ── Step 3: Clear existing demo/synthetic sales ────────────────────────
        deleted = Sale.query.filter(Sale.notes.like('%[SYNTHETIC]%')).delete(synchronize_session=False)
        db.session.commit()
        print(f"  Cleared {deleted} old synthetic records.")

        # ── Step 4: Generate 5000 realistic rows ───────────────────────────────
        # Date range: ~3.5 years back from today → enough history
        end_date   = date.today()
        start_date = end_date - timedelta(days=1277)  # ~3.5 years

        # Product demand weights (sum = 1.0)
        demand_weights = {
            'Regular Tea':  0.38,
            'Medium Tea':   0.22,
            'Black Tea':    0.12,
            'Lemon Tea':    0.15,
            'Coffee':       0.13,
        }

        # Base daily cups per product (will be modulated)
        base_cups = {
            'Regular Tea':  40,
            'Medium Tea':   22,
            'Black Tea':    12,
            'Lemon Tea':    15,
            'Coffee':       14,
        }

        def seasonal_factor(d: date, product_name: str) -> float:
            """Returns a multiplier based on month/season."""
            m = d.month
            if product_name in ('Black Tea', 'Lemon Tea'):
                # Popular in summer (Mar–Jun)
                if m in (3, 4, 5, 6):   return random.uniform(1.3, 1.6)
                if m in (11, 12, 1, 2): return random.uniform(0.6, 0.85)
                return random.uniform(0.9, 1.1)
            else:
                # Hot tea/coffee popular in winter (Oct–Feb)
                if m in (10, 11, 12, 1, 2): return random.uniform(1.2, 1.45)
                if m in (4, 5, 6):           return random.uniform(0.75, 0.95)
                return random.uniform(0.95, 1.1)

        def weekend_factor(d: date) -> float:
            return random.uniform(1.20, 1.40) if d.weekday() >= 5 else random.uniform(0.9, 1.1)

        def festival_factor(d: date) -> float:
            """Spike on approx festival dates."""
            festivals = [
                (10, 2), (10, 3),   # Dussehra
                (11, 1), (11, 2), (11, 3),  # Diwali window
                (1, 14), (1, 15),   # Makar Sankranti
                (3, 25), (3, 26),   # Holi
                (8, 15),            # Independence Day
                (1, 26),            # Republic Day
            ]
            for fm, fd in festivals:
                if d.month == fm and d.day == fd:
                    return random.uniform(1.4, 1.8)
            return 1.0

        def noisy(val: float, noise_pct: float = 0.18) -> int:
            """Add realistic noise and return int."""
            noise = random.uniform(1 - noise_pct, 1 + noise_pct)
            return max(1, round(val * noise))

        sales_to_insert = []
        target = 5000

        # Build a list of (date, product_name) combinations first
        all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        random.shuffle(all_dates)

        # We need 5000 rows. Each row = one "session" sale entry for a product on a date.
        # Distribute across dates: ~3-5 products per day, variable quantity
        sales_pool = []
        for d in all_dates:
            wf = weekend_factor(d)
            ff = festival_factor(d)
            for pname, p in products.items():
                sf = seasonal_factor(d, pname)
                base = base_cups[pname]
                cups = noisy(base * sf * wf * ff)
                sales_pool.append((d, pname, cups))

        # Shuffle and take exactly 5000
        random.shuffle(sales_pool)
        sales_pool = sales_pool[:target]
        # Sort by date for chronological order
        sales_pool.sort(key=lambda x: x[0])

        # Insert into DB
        inserted = 0
        for d, pname, cups in sales_pool:
            p = products[pname]
            unit_price = float(p.selling_price)
            unit_cost  = float(p.cost_price or 0)

            # Small price variation (occasional discount/bulk)
            if random.random() < 0.05:
                unit_price = round(unit_price * random.uniform(0.85, 0.95), 1)

            revenue      = round(cups * unit_price, 2)
            gross_profit = round(cups * (unit_price - unit_cost), 2)

            # Timestamp: random hour between 6am–9pm
            hour   = random.randint(6, 21)
            minute = random.randint(0, 59)
            sale_dt = datetime(d.year, d.month, d.day, hour, minute)

            sale = Sale(
                product_id   = p.id,
                date         = sale_dt,
                quantity     = cups,
                unit_price   = unit_price,
                unit_cost    = unit_cost,
                revenue      = revenue,
                gross_profit = gross_profit,
                notes        = '[SYNTHETIC] Demo dataset — 5000 rows',
            )
            db.session.add(sale)
            inserted += 1

            if inserted % 500 == 0:
                db.session.commit()
                print(f"  Inserted {inserted}/{target} records...")

        db.session.commit()
        print(f"\n  Done! {inserted} synthetic sales records inserted.")
        print(f"  Date range: {sales_pool[0][0]} to {sales_pool[-1][0]}")

        # ── Step 5: Summary stats ──────────────────────────────────────────────
        from sqlalchemy import func
        total = Sale.query.count()
        total_rev = db.session.query(func.sum(Sale.revenue)).scalar() or 0
        print(f"\n  Total sales in DB : {total}")
        print(f"  Total revenue     : Rs {total_rev:,.2f}")
        for pname, p in products.items():
            cnt = Sale.query.filter_by(product_id=p.id).count()
            cups = db.session.query(func.sum(Sale.quantity)).filter(Sale.product_id==p.id).scalar() or 0
            print(f"    {pname:<18}: {cnt:>4} transactions, {cups:>6} cups total")

        return inserted


if __name__ == '__main__':
    print("\nChai House AI — Generating 5000-Row Dataset")
    print("=" * 50)
    count = generate_5000_rows()
    print(f"\n{'='*50}")
    print(f"  Dataset generation complete: {count} rows added")
    print(f"  Open http://127.0.0.1:5000 to see the data")
    print(f"{'='*50}\n")
