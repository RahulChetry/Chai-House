from datetime import datetime
from app import db


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    selling_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sales = db.relationship('Sale', backref='product', lazy='dynamic')
    recipes = db.relationship('Recipe', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.name}>'

    def total_revenue(self):
        return sum(s.revenue or 0 for s in self.sales)

    def total_cups(self):
        return sum(s.quantity or 0 for s in self.sales)


class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False)
    revenue = db.Column(db.Float, nullable=False)
    gross_profit = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Sale id={self.id} product_id={self.product_id} date={self.date}>'


class Ingredient(db.Model):
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    quantity_on_hand = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(30), nullable=False, default='units')
    min_threshold = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recipes = db.relationship('Recipe', backref='ingredient', lazy='dynamic', cascade='all, delete-orphan')
    inventory_transactions = db.relationship('InventoryTransaction', backref='ingredient', lazy='dynamic')

    def __repr__(self):
        return f'<Ingredient {self.name}>'

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.min_threshold


class Recipe(db.Model):
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity_per_serving = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Recipe product={self.product_id} ingredient={self.ingredient_id}>'


class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity_change = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)   # IN / OUT / ADJUSTMENT
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<InventoryTransaction id={self.id} type={self.transaction_type}>'


class ModelEvaluation(db.Model):
    __tablename__ = 'model_evaluations'

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    task_type = db.Column(db.String(30), nullable=False)    # regression / classification
    config_json = db.Column(db.Text, nullable=True)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Regression metrics
    val_mae = db.Column(db.Float, nullable=True)
    val_rmse = db.Column(db.Float, nullable=True)
    val_r2 = db.Column(db.Float, nullable=True)
    test_mae = db.Column(db.Float, nullable=True)
    test_rmse = db.Column(db.Float, nullable=True)
    test_r2 = db.Column(db.Float, nullable=True)

    # Classification metrics
    accuracy = db.Column(db.Float, nullable=True)
    precision_score = db.Column(db.Float, nullable=True)
    recall_score = db.Column(db.Float, nullable=True)
    f1_score = db.Column(db.Float, nullable=True)

    # Cross-validation / tuning
    cv_scores_json = db.Column(db.Text, nullable=True)
    best_params_json = db.Column(db.Text, nullable=True)

    # Dataset info
    dataset_size = db.Column(db.Integer, nullable=True)
    train_size = db.Column(db.Integer, nullable=True)
    test_size = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ModelEvaluation {self.model_name} ({self.task_type})>'
