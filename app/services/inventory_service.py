from datetime import date

from app import db
from app.models import Ingredient, InventoryTransaction, Recipe


def get_low_stock_alerts() -> list:
    """Return list of ingredients where quantity_on_hand <= min_threshold."""
    return (
        Ingredient.query
        .filter(Ingredient.quantity_on_hand <= Ingredient.min_threshold)
        .order_by(Ingredient.name)
        .all()
    )


def estimate_ingredient_needs(forecast: dict) -> dict:
    """
    Estimate ingredient quantities needed for a given demand forecast.

    :param forecast: {product_id: predicted_cups}
    :return: {ingredient_name: total_quantity_needed}
    """
    needs: dict[str, float] = {}

    for product_id, predicted_cups in forecast.items():
        if predicted_cups <= 0:
            continue
        recipes = Recipe.query.filter_by(product_id=product_id).all()
        for recipe in recipes:
            ing_name = recipe.ingredient.name
            qty_needed = recipe.quantity_per_serving * predicted_cups
            needs[ing_name] = round(needs.get(ing_name, 0.0) + qty_needed, 3)

    return needs


def update_stock(
    ingredient_id: int,
    quantity_change: float,
    transaction_type: str,
    notes: str | None = None,
) -> bool:
    """
    Record a stock transaction and update ingredient's quantity_on_hand.

    :param ingredient_id: PK of Ingredient
    :param quantity_change: absolute change value (always positive; direction from transaction_type)
    :param transaction_type: 'IN', 'OUT', or 'ADJUSTMENT'
    :param notes: optional note
    :return: True on success, False on failure
    """
    try:
        ingredient = Ingredient.query.get(ingredient_id)
        if not ingredient:
            return False

        if transaction_type == 'IN':
            ingredient.quantity_on_hand = round(ingredient.quantity_on_hand + abs(quantity_change), 3)
        elif transaction_type == 'OUT':
            ingredient.quantity_on_hand = round(ingredient.quantity_on_hand - abs(quantity_change), 3)
        elif transaction_type == 'ADJUSTMENT':
            # quantity_change is the new absolute value
            ingredient.quantity_on_hand = round(float(quantity_change), 3)
        else:
            return False

        txn = InventoryTransaction(
            ingredient_id=ingredient_id,
            quantity_change=quantity_change,
            transaction_type=transaction_type,
            date=date.today(),
            notes=notes,
        )
        db.session.add(txn)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
