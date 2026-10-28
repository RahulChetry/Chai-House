from flask import Blueprint, render_template

concepts_bp = Blueprint('concepts', __name__)


@concepts_bp.route('/concepts')
def concepts():
    """Educational page explaining ML concepts used in Chai House AI."""
    return render_template('ml/concepts.html')
