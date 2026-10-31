"""
Machine Learning and Artificial Intelligence Intelligence Package for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Exports:
- FDRAnomalyDetector
- calculate_fdr_risk
- analyze_institution_compliance
- run_full_duplicate_scan
- evaluate_fdr_pair_similarity
- train_and_register_isolation_forest
- get_model_health_status
"""

from ml.preprocessing import extract_features_from_fdr, FEATURE_NAMES
from ml.duplicate_detector import (
    evaluate_fdr_pair_similarity,
    detect_document_hash_duplicates,
    run_full_duplicate_scan,
    normalize_fdr_string,
    levenshtein_ratio,
)
from ml.anomaly_detector import FDRAnomalyDetector
from ml.risk_scorer import calculate_fdr_risk, RISK_WEIGHTS
from ml.compliance_intelligence import analyze_institution_compliance
from ml.evaluation import evaluate_anomaly_detector
from ml.trainer import (
    generate_synthetic_benchmark_dataset,
    train_and_register_isolation_forest,
)
from ml.model_registry import (
    save_trained_model,
    load_registered_model,
    get_model_health_status,
)

__all__ = [
    "extract_features_from_fdr",
    "FEATURE_NAMES",
    "evaluate_fdr_pair_similarity",
    "detect_document_hash_duplicates",
    "run_full_duplicate_scan",
    "normalize_fdr_string",
    "levenshtein_ratio",
    "FDRAnomalyDetector",
    "calculate_fdr_risk",
    "RISK_WEIGHTS",
    "analyze_institution_compliance",
    "evaluate_anomaly_detector",
    "generate_synthetic_benchmark_dataset",
    "train_and_register_isolation_forest",
    "save_trained_model",
    "load_registered_model",
    "get_model_health_status",
]
