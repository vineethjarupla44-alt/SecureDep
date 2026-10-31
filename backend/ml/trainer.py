"""
Model Training and Synthetic Benchmark Pipeline for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Provides:
- Synthetic dataset generation for baseline training without compromising real financial data
- Isolation Forest training and hyperparameter configuration
- Validation against injected ground-truth anomalies
- Safe model registry serialization
"""

import math
import random
from datetime import datetime
from ml.preprocessing import FEATURE_NAMES
from ml.anomaly_detector import FDRAnomalyDetector
from ml.evaluation import evaluate_anomaly_detector
from ml.model_registry import save_trained_model


def generate_synthetic_benchmark_dataset(n_samples=500, contamination=0.05, seed=42):
    """
    Generate an isolated, realistic synthetic feature matrix for baseline model training.
    Never uses or touches real financial or personally identifiable data.

    Args:
        n_samples (int): Total number of synthetic samples.
        contamination (float): Fraction of injected synthetic anomalies (default 5%).
        seed (int): Random seed for reproducibility.

    Returns:
        tuple (list of lists X, list of int y): Feature matrix and binary labels (0=Normal, 1=Anomaly).
    """
    rng = random.Random(seed)
    n_anomalies = max(1, int(n_samples * contamination))
    n_normal = n_samples - n_anomalies

    X = []
    y = []

    # 1. Generate Normal AICTE Security Deposits
    # - Standard amount: INR 1,000,000 to INR 5,000,000 (log: 13.8 to 15.4)
    # - Tenor: 1825 days (5 years) with minor natural variance (+- 30 days)
    # - OCR confidence: 80% to 98%
    # - Discrepancy count: 0 (or rarely 1)
    for _ in range(n_normal):
        amt = rng.uniform(1000000.0, 5000000.0)
        log_amt = math.log(amt)
        tenor = rng.gauss(1825.0, 45.0)
        tenor = max(tenor, 365.0)
        days_to_mat = rng.uniform(30.0, 1825.0)
        renewals = float(rng.choice([0, 0, 0, 1, 2]))
        ocr_conf = rng.uniform(82.0, 98.0)
        disc_cnt = float(rng.choice([0, 0, 0, 0, 1]))
        doc_cnt = float(rng.choice([1, 1, 2, 3]))
        has_disc = 1.0 if disc_cnt > 0 else 0.0

        row = [
            round(log_amt, 4),
            round(tenor, 1),
            round(days_to_mat, 1),
            renewals,
            round(ocr_conf, 2),
            disc_cnt,
            doc_cnt,
            has_disc,
        ]
        X.append(row)
        y.append(0)

    # 2. Inject Controlled Synthetic Anomalies
    # Types: Short tenor (<180 days), extreme deposit amount, high discrepancy count
    for _ in range(n_anomalies):
        anomaly_type = rng.choice(["short_tenor", "low_amount", "high_discrepancies", "low_ocr"])

        if anomaly_type == "short_tenor":
            amt = rng.uniform(1000000.0, 3000000.0)
            log_amt = math.log(amt)
            tenor = rng.uniform(30.0, 180.0)  # Violates 5-year lock-in
            days_to_mat = tenor
            ocr_conf = rng.uniform(80.0, 95.0)
            disc_cnt = 0.0
        elif anomaly_type == "low_amount":
            amt = rng.uniform(1000.0, 25000.0)  # Suspiciously low security deposit
            log_amt = math.log(amt)
            tenor = 1825.0
            days_to_mat = 700.0
            ocr_conf = rng.uniform(80.0, 95.0)
            disc_cnt = 0.0
        elif anomaly_type == "high_discrepancies":
            amt = 2500000.0
            log_amt = math.log(amt)
            tenor = 1825.0
            days_to_mat = 400.0
            ocr_conf = rng.uniform(50.0, 70.0)
            disc_cnt = float(rng.randint(3, 6))
        else:
            amt = 2000000.0
            log_amt = math.log(amt)
            tenor = 1825.0
            days_to_mat = 500.0
            ocr_conf = rng.uniform(25.0, 45.0)  # Severely degraded scan
            disc_cnt = 2.0

        doc_cnt = float(rng.choice([0, 1]))
        has_disc = 1.0 if disc_cnt > 0 else 0.0

        row = [
            round(log_amt, 4),
            round(tenor, 1),
            round(days_to_mat, 1),
            0.0,
            round(ocr_conf, 2),
            disc_cnt,
            doc_cnt,
            has_disc,
        ]
        X.append(row)
        y.append(1)

    return X, y


def train_and_register_isolation_forest(n_samples=500, contamination=0.05, save=True):
    """
    Train an Isolation Forest detector on synthetic baseline data, evaluate accuracy,
    and persist the artifact to the model registry.

    Returns:
        dict: Training summary and validation metrics.
    """
    X, y = generate_synthetic_benchmark_dataset(
        n_samples=n_samples,
        contamination=contamination,
        seed=42,
    )

    detector = FDRAnomalyDetector(contamination=contamination)
    detector.fit(X)

    # Evaluate on the synthetic dataset
    predictions = []
    for row in X:
        pred = {}
        # Mimic analyzer output format
        if detector.model is not None:
            raw_dec = float(detector.model.decision_function([row])[0])
            score = 1.0 / (1.0 + math.exp(raw_dec * 5.0))
            is_anom = (detector.model.predict([row])[0] == -1)
        else:
            # Fallback
            score = 0.1
            is_anom = False
        pred["anomaly_score"] = score
        pred["is_anomaly"] = is_anom
        predictions.append(pred)

    eval_results = evaluate_anomaly_detector(predictions, ground_truth=y)

    metadata = {
        "model_version": "v1.0.0",
        "algorithm": "IsolationForest",
        "contamination": contamination,
        "n_samples_trained": n_samples,
        "feature_names": list(FEATURE_NAMES),
        "trained_at": datetime.utcnow().isoformat(),
        "evaluation_metrics": eval_results,
    }

    saved_path = None
    if save and detector.model is not None:
        success, saved_path = save_trained_model(detector.model, metadata)
    else:
        save_trained_model(None, metadata)

    return {
        "status": "success",
        "model_version": "v1.0.0",
        "algorithm": "IsolationForest",
        "n_samples": n_samples,
        "samples_trained": n_samples,
        "contamination": contamination,
        "evaluation": eval_results,
        "model_saved": saved_path is not None,
        "saved_path": saved_path,
    }
