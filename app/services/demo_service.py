import random
from datetime import date, timedelta

from app import db
from app.models import Product, Ingredient, Recipe, Sale, InventoryTransaction


_PRODUCTS = [
    {'name': 'Regular Tea',  'selling_price': 20.0, 'cost_price': 8.0},
    {'name': 'Medium Tea',   'selling_price': 30.0, 'cost_price': 12.0},
    {'name': 'Black Tea',    'selling_price': 10.0, 'cost_price': 3.0},
    {'name': 'Lemon Tea',    'selling_price': 15.0, 'cost_price': 5.0},
    {'name': 'Coffee',       'selling_price': 30.0, 'cost_price': 12.0},
]

_INGREDIENTS = [
    {'name': 'Milk',          'unit': 'liters',  'quantity_on_hand': 20.0,  'min_threshold': 5.0},
    {'name': 'Tea Powder',    'unit': 'grams',   'quantity_on_hand': 2000.0, 'min_threshold': 300.0},
    {'name': 'Sugar',         'unit': 'grams',   'quantity_on_hand': 3000.0, 'min_threshold': 500.0},
    {'name': 'Ginger',        'unit': 'grams',   'quantity_on_hand': 500.0,  'min_threshold': 50.0},
    {'name': 'Lemon',         'unit': 'pieces',  'quantity_on_hand': 30.0,  'min_threshold': 5.0},
    {'name': 'Coffee Powder', 'unit': 'grams',   'quantity_on_hand': 500.0,  'min_threshold': 100.0},
    {'name': 'Cups',          'unit': 'pieces',  'quantity_on_hand': 500.0,  'min_threshold': 50.0},
]

# recipe: {product_name: [(ingredient_name, qty_per_serving)]}
_RECIPES = {
    'Regular Tea':  [('Milk', 0.15), ('Tea Powder', 5.0), ('Sugar', 10.0), ('Ginger', 2.0), ('Cups', 1)],
    'Medium Tea':   [('Milk', 0.20), ('Tea Powder', 7.0), ('Sugar', 12.0), ('Ginger', 2.0), ('Cups', 1)],
    'Black Tea':    [('Tea Powder', 4.0), ('Sugar', 5.0), ('Ginger', 1.0), ('Cups', 1)],
    'Lemon Tea':    [('Tea Powder', 4.0), ('Sugar', 5.0), ('Lemon', 0.5), ('Cups', 1)],
    'Coffee':       [('Milk', 0.15), ('Coffee Powder', 8.0), ('Sugar', 10.0), ('Cups', 1)],
}

# Base daily demand per product (cups)
_BASE_DEMAND = {
    'Regular Tea': 40,
    'Medium Tea':  20,
    'Black Tea':   15,
    'Lemon Tea':   10,
    'Coffee':      15,
}


def load_demo_data() -> int:
    """
    Populate the database with demo products, ingredients, recipes, and 90 days of sales.
    Idempotent: if products already exist, skip product/ingredient insertion but still adds sales.
    Returns the number of sale records inserted.
    """
    random.seed(42)

    # ── Products ────────────────────────────────────────────────────────────
    if Product.query.count() == 0:
        for p_data in _PRODUCTS:
            product = Product(
                name=p_data['name'],
                selling_price=p_data['selling_price'],
                cost_price=p_data['cost_price'],
                is_active=True,
            )
            db.session.add(product)
        db.session.flush()

    # ── Ingredients ─────────────────────────────────────────────────────────
    if Ingredient.query.count() == 0:
        for i_data in _INGREDIENTS:
            ingredient = Ingredient(
                name=i_data['name'],
                unit=i_data['unit'],
                quantity_on_hand=i_data['quantity_on_hand'],
                min_threshold=i_data['min_threshold'],
            )
            db.session.add(ingredient)
            db.session.flush()
            # Record initial stock-in transaction
            txn = InventoryTransaction(
                ingredient_id=ingredient.id,
                quantity_change=i_data['quantity_on_hand'],
                transaction_type='IN',
                date=date.today(),
                notes='Demo initial stock',
            )
            db.session.add(txn)
        db.session.flush()

    # ── Recipes ─────────────────────────────────────────────────────────────
    if Recipe.query.count() == 0:
        for prod_name, items in _RECIPES.items():
            product = Product.query.filter_by(name=prod_name).first()
            if not product:
                continue
            for ing_name, qty in items:
                ingredient = Ingredient.query.filter_by(name=ing_name).first()
                if not ingredient:
                    continue
                recipe = Recipe(
                    product_id=product.id,
                    ingredient_id=ingredient.id,
                    quantity_per_serving=qty,
                )
                db.session.add(recipe)
        db.session.flush()

    # ── Sales (90 days) ─────────────────────────────────────────────────────
    today = date.today()
    start_date = today - timedelta(days=89)
    sales_inserted = 0

    for day_offset in range(90):
        sale_date = start_date + timedelta(days=day_offset)
        is_weekend = sale_date.weekday() >= 5  # Sat/Sun

        for prod_name, base in _BASE_DEMAND.items():
            product = Product.query.filter_by(name=prod_name).first()
            if not product:
                continue

            weekend_boost = 1.4 if is_weekend else 1.0
            noise = random.gauss(1.0, 0.15)
            quantity = max(1, int(round(base * weekend_boost * noise)))

            revenue = round(quantity * product.selling_price, 2)
            gross_profit = round(revenue - (quantity * product.cost_price), 2)

            sale = Sale(
                product_id=product.id,
                date=sale_date,
                quantity=quantity,
                unit_price=product.selling_price,
                unit_cost=product.cost_price,
                revenue=revenue,
                gross_profit=gross_profit,
                notes='demo',
            )
            db.session.add(sale)
            sales_inserted += 1

    db.session.commit()
    return sales_inserted
