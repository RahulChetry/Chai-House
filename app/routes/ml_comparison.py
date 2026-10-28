"""
Chai House AI — ML Comparison Routes (Rewritten to match templates)
"""
import os
import json
import traceback
from datetime import date, datetime

import numpy as np
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

from app import db
from app.models import ModelEvaluation, Sale, Product

ml_comparison_bp = Blueprint('ml_comparison', __name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'models'
)


@ml_comparison_bp.route('/ml-comparison')
def comparison_dashboard():
    """Main ML model comparison dashboard."""
    from app.ml.trainer import load_best_regression_model, load_best_classifier
    from app.ml.evaluator import interpret_regression_results, interpret_classification_results

    # Load regression evaluations from DB
    reg_evals = (
        ModelEvaluation.query
        .filter_by(task_type='regression')
        .order_by(ModelEvaluation.test_mae.asc())
        .all()
    )

    cls_eval = (
        ModelEvaluation.query
        .filter_by(task_type='classification')
        .first()
    )

    has_results = len(reg_evals) > 0

    regression_results = []
    best_model = None
    best_mae = None
    best_r2 = None
    n_train = 0
    n_test = 0

    if has_results:
        best_ev = reg_evals[0]  # sorted by test_mae asc
        best_model = best_ev.model_name
        best_mae = best_ev.test_mae or 0
        best_r2 = best_ev.test_r2 or 0
        n_train = best_ev.train_size or 0
        n_test = best_ev.test_size or 0

        for ev in reg_evals:
            cv_scores = json.loads(ev.cv_scores_json or '[]')
            best_params_raw = json.loads(ev.best_params_json or '{}') if ev.best_params_json else {}
            best_params_str = ', '.join(f'{k}={v}' for k, v in best_params_raw.items()) if best_params_raw else ''
            regression_results.append({
                'model_name': ev.model_name,
                'train_mae': round(ev.val_mae or 0, 2),
                'test_mae': round(ev.test_mae or 0, 2),
                'test_rmse': round(ev.test_rmse or 0, 2),
                'test_r2': round(ev.test_r2 or 0, 3),
                'cv_mean': round(float(np.mean(cv_scores)) if cv_scores else 0, 2),
                'cv_std': round(float(np.std(cv_scores)) if cv_scores else 0, 2),
                'best_params': best_params_str,
                'is_best': ev.model_name == best_model,
            })

    # Classification result
    classification_result = None
    class_interpretation = None
    if cls_eval:
        cm_raw = json.loads(cls_eval.cv_scores_json or '[]') if cls_eval.cv_scores_json else []
        thresholds_raw = json.loads(cls_eval.best_params_json or '{}') if cls_eval.best_params_json else {}
        confusion_m = None
        # Try to get confusion matrix from notes
        if cls_eval.notes:
            try:
                notes_data = json.loads(cls_eval.notes)
                confusion_m = notes_data.get('confusion_matrix')
                thresholds_raw = notes_data.get('class_thresholds', thresholds_raw)
            except Exception:
                pass

        classification_result = {
            'accuracy': cls_eval.accuracy or 0,
            'precision': cls_eval.precision_score or 0,
            'recall': cls_eval.recall_score or 0,
            'f1': cls_eval.f1_score or 0,
            'cv_mean': float(np.mean(cm_raw)) if cm_raw else 0,
            'cv_std': float(np.std(cm_raw)) if cm_raw else 0,
            'best_params': thresholds_raw.get('best_params', ''),
            'n_train': cls_eval.train_size or 0,
            'n_test': cls_eval.test_size or 0,
            'confusion_matrix': confusion_m,
            'class_thresholds': thresholds_raw,
        }
        class_interpretation = f"SVM Classifier achieved {classification_result['accuracy']*100:.1f}% accuracy on held-out test data."

    interpretation = ''
    if regression_results:
        best = regression_results[0]
        interpretation = (
            f"{best['model_name']} performed best with Test MAE = {best['test_mae']:.2f} cups, "
            f"meaning predictions are off by about {best['test_mae']:.0f} cups on average. "
            f"R² = {best['test_r2']:.3f} (1.0 = perfect). "
            f"Cross-validation MAE: {best['cv_mean']:.2f} ± {best['cv_std']:.2f}."
        )

    return render_template(
        'ml/comparison.html',
        has_results=has_results,
        regression_results=regression_results,
        classification_result=classification_result,
        best_model=best_model,
        best_mae=best_mae or 0,
        best_r2=best_r2 or 0,
        n_train=n_train,
        n_test=n_test,
        interpretation=interpretation,
        class_interpretation=class_interpretation,
    )


@ml_comparison_bp.route('/ml-comparison/train', methods=['POST'])
def train_models():
    """Trigger full ML training pipeline."""
    try:
        from app.ml.trainer import run_full_training_pipeline
        from app.ml.evaluator import interpret_regression_results, interpret_classification_results

        sales = Sale.query.join(Product).all()
        if len(sales) < 30:
            return jsonify({
                'success': False,
                'message': f'Only {len(sales)} sales records. Need at least 30. Load demo data first.'
            }), 400

        sales_data = [{
            'id': s.id,
            'product_id': s.product_id,
            'product_name': s.product.name,
            'date': s.date.strftime('%Y-%m-%d'),
            'quantity': s.quantity,
            'revenue': float(s.revenue or 0),
            'gross_profit': float(s.gross_profit or 0),
        } for s in sales]

        results = run_full_training_pipeline(sales_data)

        if 'error' in results:
            return jsonify({'success': False, 'message': results['error']}), 400

        # Save regression results to DB
        for r in results.get('regression_results', []):
            existing = ModelEvaluation.query.filter_by(
                model_name=r['model_name'], task_type='regression'
            ).first()
            ev = existing or ModelEvaluation(model_name=r['model_name'], task_type='regression')
            if not existing:
                db.session.add(ev)

            ev.trained_at = datetime.utcnow()
            ev.val_mae = r.get('train_mae')
            ev.val_rmse = r.get('train_rmse')
            ev.val_r2 = r.get('train_r2')
            ev.test_mae = r.get('test_mae')
            ev.test_rmse = r.get('test_rmse')
            ev.test_r2 = r.get('test_r2')
            ev.cv_scores_json = json.dumps(r.get('cv_scores', []))
            ev.best_params_json = json.dumps(r.get('best_params', {}))
            ev.dataset_size = r.get('n_train', 0) + r.get('n_test', 0)
            ev.train_size = r.get('n_train')
            ev.test_size = r.get('n_test')

        # Save classification result
        cr = results.get('classification_result', {})
        if cr and 'error' not in cr:
            cls_ev = ModelEvaluation.query.filter_by(
                model_name='SVM Classifier', task_type='classification'
            ).first()
            if not cls_ev:
                cls_ev = ModelEvaluation(model_name='SVM Classifier', task_type='classification')
                db.session.add(cls_ev)

            cls_ev.trained_at = datetime.utcnow()
            cls_ev.accuracy = cr.get('accuracy')
            cls_ev.precision_score = cr.get('precision')
            cls_ev.recall_score = cr.get('recall')
            cls_ev.f1_score = cr.get('f1')
            cls_ev.train_size = cr.get('n_train')
            cls_ev.test_size = cr.get('n_test')
            cls_ev.cv_scores_json = json.dumps(cr.get('cv_accuracy_scores', []))
            cls_ev.notes = json.dumps({
                'confusion_matrix': cr.get('confusion_matrix'),
                'class_thresholds': cr.get('class_thresholds', {}),
                'best_params': str(cr.get('best_params', '')),
            })

        db.session.commit()

        best = results.get('best_regression_model', 'Unknown')
        mae = results.get('best_regression_mae', 0)
        return jsonify({
            'success': True,
            'message': f'Training complete! Best model: {best} (MAE={mae:.2f} cups). Page will reload.'
        })

    except Exception as exc:
        return jsonify({
            'success': False,
            'message': str(exc),
            'trace': traceback.format_exc()
        }), 500


@ml_comparison_bp.route('/ml-comparison/classify', methods=['GET', 'POST'])
def classify():
    """SVM demand classification page."""
    from app.ml.trainer import load_best_classifier, classify_demand

    model_available = load_best_classifier() is not None
    classification = None
    eval_metrics = None

    if request.method == 'POST':
        try:
            day_of_week = int(request.form.get('day_of_week', 0))
            month = int(request.form.get('month', 1))
            rolling_7_mean = float(request.form.get('rolling_7_mean', 0))
            day_of_month = int(request.form.get('day_of_month', 15))
            is_weekend = 1 if day_of_week >= 5 else 0

            features = {
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'month': month,
                'day_of_month': day_of_month,
                'week_of_year': 20,
                'lag_1_qty': rolling_7_mean,
                'lag_7_qty': rolling_7_mean,
                'rolling_7_mean': rolling_7_mean,
                'rolling_14_mean': rolling_7_mean,
            }

            result = classify_demand(features)

            if 'error' in result:
                flash(result['error'], 'warning')
            else:
                classification = result
                # Load eval metrics from DB
                cls_ev = ModelEvaluation.query.filter_by(
                    model_name='SVM Classifier', task_type='classification'
                ).first()
                if cls_ev:
                    thresholds = {}
                    if cls_ev.notes:
                        try:
                            notes = json.loads(cls_ev.notes)
                            thresholds = notes.get('class_thresholds', {})
                        except Exception:
                            pass
                    eval_metrics = {
                        'accuracy': cls_ev.accuracy or 0,
                        'precision': cls_ev.precision_score or 0,
                        'recall': cls_ev.recall_score or 0,
                        'f1': cls_ev.f1_score or 0,
                        'class_thresholds': thresholds,
                    }
        except Exception as exc:
            flash(f'Classification error: {str(exc)}', 'danger')

    return render_template(
        'ml/classification.html',
        model_available=model_available,
        classification=classification,
        eval_metrics=eval_metrics,
    )
