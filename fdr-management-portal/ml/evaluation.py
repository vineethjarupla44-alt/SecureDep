"""
Model Evaluation and Metrics Module for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Provides:
- Anomaly detector performance evaluation
- Precision, Recall, F1-Score on synthetic evaluation benchmarks
- Score distribution analytics (min, mean, max, percentiles)
- Unsupervised cluster validation
"""

import math


def evaluate_anomaly_detector(predictions, ground_truth=None):
    """
    Evaluate anomaly detection performance.

    Args:
        predictions (list of dict): List of predictions containing 'is_anomaly' and 'anomaly_score'.
        ground_truth (list of int/bool, optional): Ground truth labels (1 for anomaly, 0 for normal).

    Returns:
        dict: Evaluation metrics and score distributions.
    """
    if not predictions:
        return {"total_evaluated": 0, "status": "NO_DATA"}

    scores = [p.get("anomaly_score", 0.0) for p in predictions]
    predicted_flags = [bool(p.get("is_anomaly", False)) for p in predictions]

    n = len(predictions)
    flagged_count = sum(predicted_flags)
    normal_count = n - flagged_count
    anomaly_rate = round((flagged_count / n) * 100.0, 2)

    # Score Distribution Metrics
    min_score = min(scores)
    max_score = max(scores)
    mean_score = sum(scores) / n
    var_score = sum((s - mean_score) ** 2 for s in scores) / max(n, 1)
    std_score = math.sqrt(var_score)

    sorted_scores = sorted(scores)
    median_score = sorted_scores[n // 2]

    metrics = {
        "total_evaluated": n,
        "flagged_anomalies": flagged_count,
        "normal_samples": normal_count,
        "anomaly_rate_pct": anomaly_rate,
        "score_distribution": {
            "min": round(min_score, 4),
            "max": round(max_score, 4),
            "mean": round(mean_score, 4),
            "median": round(median_score, 4),
            "std": round(std_score, 4),
        },
    }

    # If ground truth labels are supplied (synthetic benchmark testing)
    if ground_truth and len(ground_truth) == n:
        tp = sum(1 for p, y in zip(predicted_flags, ground_truth) if p and y)
        fp = sum(1 for p, y in zip(predicted_flags, ground_truth) if p and not y)
        fn = sum(1 for p, y in zip(predicted_flags, ground_truth) if not p and y)
        tn = sum(1 for p, y in zip(predicted_flags, ground_truth) if not p and not y)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / n if n > 0 else 0.0

        metrics["benchmark_validation"] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "accuracy": round(accuracy, 4),
        }

    return metrics
