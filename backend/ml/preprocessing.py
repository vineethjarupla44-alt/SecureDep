"""
Data Preprocessing and Feature Engineering Module for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Provides:
- Feature extraction from FDRRecord, Institution, and OCR metadata
- Missing value imputation and safe numerical fallbacks
- Preprocessing pipelines (standardization, log-transforms)
- Compatibility with both Scikit-learn pipelines and pure Python fallbacks
"""

import math
from datetime import date, datetime
from decimal import Decimal
from utils.time import local_business_date

# Defined features for ML anomaly detection and risk scoring
FEATURE_NAMES = [
    "log_deposit_amount",
    "tenor_days",
    "days_to_maturity",
    "renewal_count",
    "ocr_confidence",
    "discrepancy_count",
    "document_count",
    "has_discrepancy",
]

DEFAULT_FEATURE_VALUES = {
    "log_deposit_amount": 14.5,   # ~ INR 2,000,000
    "tenor_days": 1825.0,         # 5 years mandatory lock-in
    "days_to_maturity": 365.0,
    "renewal_count": 0.0,
    "ocr_confidence": 85.0,
    "discrepancy_count": 0.0,
    "document_count": 1.0,
    "has_discrepancy": 0.0,
}


def extract_features_from_fdr(fdr_record, reference_date=None):
    """
    Extract a normalized numerical feature vector and metadata dict for a single FDRRecord.

    Args:
        fdr_record (FDRRecord): SQLAlchemy FDRRecord instance.
        reference_date (date, optional): Reference date for days-to-maturity calculations.

    Returns:
        dict: Extracted raw and normalized features with feature names.
    """
    if reference_date is None:
        reference_date = local_business_date()

    # 1. Deposit Amount & Log Transform
    try:
        amt = float(fdr_record.deposit_amount) if fdr_record.deposit_amount else 100000.0
        amt = max(amt, 1.0)
        log_amt = math.log(amt)
    except (ValueError, TypeError, OverflowError):
        amt = 100000.0
        log_amt = math.log(amt)

    # 2. Tenor (Total validity duration in days)
    if fdr_record.issue_date and fdr_record.maturity_date:
        tenor_days = (fdr_record.maturity_date - fdr_record.issue_date).days
    else:
        tenor_days = 1825  # 5 years standard AICTE lock-in

    tenor_days = max(tenor_days, 1)

    # 3. Days to Maturity
    if fdr_record.maturity_date:
        days_to_maturity = (fdr_record.maturity_date - reference_date).days
    else:
        days_to_maturity = 365

    # 4. Renewal Count (Lineage tracking)
    renewal_count = 0
    curr = fdr_record
    depth = 0
    while curr and curr.predecessor_id and depth < 20:
        renewal_count += 1
        curr = curr.predecessor
        depth += 1

    # 5. Document & OCR Metadata
    docs = list(fdr_record.documents) if hasattr(fdr_record, "documents") else []
    document_count = len(docs)

    ocr_confidence = 85.0  # Default baseline
    discrepancy_count = 0
    has_discrepancy = 0.0

    if docs:
        latest_doc = docs[0]
        if hasattr(latest_doc, "ocr_result") and latest_doc.ocr_result:
            ocr = latest_doc.ocr_result
            ocr_confidence = float(ocr.confidence_score or 85.0)
            discrepancy_count = int(ocr.discrepancy_count or 0)
            has_discrepancy = 1.0 if ocr.has_discrepancy else 0.0

    feature_dict = {
        "log_deposit_amount": round(log_amt, 4),
        "tenor_days": float(tenor_days),
        "days_to_maturity": float(days_to_maturity),
        "renewal_count": float(renewal_count),
        "ocr_confidence": round(ocr_confidence, 2),
        "discrepancy_count": float(discrepancy_count),
        "document_count": float(document_count),
        "has_discrepancy": float(has_discrepancy),
    }

    # Vector representation in fixed order
    feature_vector = [feature_dict[name] for name in FEATURE_NAMES]

    return {
        "feature_dict": feature_dict,
        "feature_vector": feature_vector,
        "feature_names": list(FEATURE_NAMES),
        "raw_amount": amt,
        "raw_tenor_days": tenor_days,
        "raw_days_to_maturity": days_to_maturity,
    }


def normalize_features(matrix, feature_names=None):
    """
    Standardize a 2D feature matrix (mean=0, variance=1) with safe fallbacks.
    Works independently of whether Scikit-learn is installed.

    Args:
        matrix (list of lists): List of feature rows.
        feature_names (list, optional): Names of features.

    Returns:
        tuple: (normalized_matrix, means, stds)
    """
    if not matrix or not matrix[0]:
        return [], {}, {}

    n_rows = len(matrix)
    n_cols = len(matrix[0])
    names = feature_names or FEATURE_NAMES

    means = {}
    stds = {}
    normalized = [[0.0] * n_cols for _ in range(n_rows)]

    for c in range(n_cols):
        col_vals = [matrix[r][c] for r in range(n_rows)]
        mean_val = sum(col_vals) / n_rows
        variance = sum((x - mean_val) ** 2 for x in col_vals) / max(n_rows, 1)
        std_val = math.sqrt(variance)

        if std_val < 1e-6:
            std_val = 1.0  # Prevent zero division on constant features

        col_name = names[c] if c < len(names) else f"feature_{c}"
        means[col_name] = mean_val
        stds[col_name] = std_val

        for r in range(n_rows):
            normalized[r][c] = (matrix[r][c] - mean_val) / std_val

    return normalized, means, stds
