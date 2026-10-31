"""
Explainable FDR Risk Scoring Module for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Provides:
- Configurable multi-factor risk assessment generating scores between 0 and 100
- Multi-tier categorization (LOW, MEDIUM, HIGH, CRITICAL)
- Clear separation between deterministic rule-based indicators and ML anomaly signals
- Actionable recommendations and evidence attribution
- Does not present scores as probability of fraud
"""

from decimal import Decimal
from models import db, FDRRecord, FDRDocument, FDRDuplicateCandidate, OCRResult
from ml.anomaly_detector import FDRAnomalyDetector

# Factor Weight Configuration (Sum = 100)
RISK_WEIGHTS = {
    "duplicate_indicators": 25.0,
    "ocr_discrepancies": 25.0,
    "missing_documents": 15.0,
    "unusual_financial_values": 15.0,
    "maturity_urgency": 10.0,
    "workflow_compliance": 10.0,
}


def calculate_fdr_risk(fdr_record, anomaly_detector=None, reference_date=None):
    """
    Perform multi-factor explainable risk evaluation on an FDRRecord.

    Args:
        fdr_record (FDRRecord): The instrument to assess.
        anomaly_detector (FDRAnomalyDetector, optional): Anomaly detector instance.
        reference_date (date, optional): Date for temporal computations.

    Returns:
        dict: Composite risk score, category, contributing factors, evidence, and actions.
    """
    contributing_factors = []
    evidence = {}

    rule_subscores = {}

    # -------------------------------------------------------------------------
    # Factor 1: Duplicate Indicators (Max 25 pts)
    # -------------------------------------------------------------------------
    duplicate_score = 0.0
    dup_candidates = FDRDuplicateCandidate.query.filter(
        (FDRDuplicateCandidate.primary_fdr_id == fdr_record.id) |
        (FDRDuplicateCandidate.duplicate_fdr_id == fdr_record.id)
    ).all()

    evidence["duplicate_count"] = len(dup_candidates)
    if dup_candidates:
        max_sim = max(c.similarity_score for c in dup_candidates)
        unreviewed = any(c.status == FDRDuplicateCandidate.STATUS_UNREVIEWED for c in dup_candidates)
        confirmed = any(c.status == FDRDuplicateCandidate.STATUS_CONFIRMED for c in dup_candidates)

        if confirmed:
            duplicate_score = 25.0
            factor_desc = f"Confirmed duplicate record detected (Similarity: {max_sim*100:.1f}%)."
            severity = "CRITICAL"
        elif unreviewed and max_sim >= 0.95:
            duplicate_score = 22.0
            factor_desc = f"Unreviewed high-similarity duplicate match detected ({max_sim*100:.1f}%)."
            severity = "HIGH"
        elif unreviewed and max_sim >= 0.80:
            duplicate_score = 15.0
            factor_desc = f"Suspected near-duplicate match detected ({max_sim*100:.1f}%)."
            severity = "MEDIUM"
        else:
            duplicate_score = 5.0
            factor_desc = "Minor duplicate candidate flagged."
            severity = "LOW"

        contributing_factors.append({
            "factor": "duplicate_indicators",
            "weight": RISK_WEIGHTS["duplicate_indicators"],
            "score": round(duplicate_score, 1),
            "severity": severity,
            "explanation": factor_desc,
        })
    rule_subscores["duplicate_indicators"] = duplicate_score

    # -------------------------------------------------------------------------
    # Factor 2: Document Inconsistencies & OCR Discrepancies (Max 25 pts)
    # -------------------------------------------------------------------------
    ocr_score = 0.0
    docs = list(fdr_record.documents) if hasattr(fdr_record, "documents") else []
    evidence["document_count"] = len(docs)

    has_ocr_discrepancy = False
    discrepancy_count = 0
    min_confidence = 100.0

    for doc in docs:
        if hasattr(doc, "ocr_result") and doc.ocr_result:
            ocr = doc.ocr_result
            if ocr.has_discrepancy:
                has_ocr_discrepancy = True
                discrepancy_count += int(ocr.discrepancy_count or 1)
            if ocr.confidence_score is not None:
                min_confidence = min(min_confidence, float(ocr.confidence_score))

    evidence["ocr_discrepancy_count"] = discrepancy_count
    evidence["min_ocr_confidence"] = min_confidence if docs else None

    if has_ocr_discrepancy:
        if discrepancy_count >= 2:
            ocr_score = 25.0
            sev = "HIGH"
            desc = f"Multiple OCR discrepancies ({discrepancy_count}) detected between uploaded certificate and record."
        else:
            ocr_score = 18.0
            sev = "MEDIUM"
            desc = "OCR discrepancy flagged between certificate text and recorded deposit details."

        contributing_factors.append({
            "factor": "ocr_discrepancies",
            "weight": RISK_WEIGHTS["ocr_discrepancies"],
            "score": round(ocr_score, 1),
            "severity": sev,
            "explanation": desc,
        })
    elif docs and min_confidence < 60.0:
        ocr_score = 10.0
        contributing_factors.append({
            "factor": "ocr_confidence",
            "weight": RISK_WEIGHTS["ocr_discrepancies"],
            "score": 10.0,
            "severity": "LOW",
            "explanation": f"Low OCR extraction confidence ({min_confidence:.1f}%). Document may be blurry or poorly scanned.",
        })
    rule_subscores["ocr_discrepancies"] = ocr_score

    # -------------------------------------------------------------------------
    # Factor 3: Missing Information & Supporting Documents (Max 15 pts)
    # -------------------------------------------------------------------------
    missing_doc_score = 0.0
    if len(docs) == 0:
        missing_doc_score = 15.0
        contributing_factors.append({
            "factor": "missing_documents",
            "weight": RISK_WEIGHTS["missing_documents"],
            "score": 15.0,
            "severity": "HIGH",
            "explanation": "No supporting deposit certificates or scanned receipts have been uploaded.",
        })
    elif any(d.processing_status == FDRDocument.STATUS_FAILED for d in docs):
        missing_doc_score = 8.0
        contributing_factors.append({
            "factor": "document_processing_failure",
            "weight": RISK_WEIGHTS["missing_documents"],
            "score": 8.0,
            "severity": "LOW",
            "explanation": "One or more uploaded supporting documents failed verification processing.",
        })
    rule_subscores["missing_documents"] = missing_doc_score

    # -------------------------------------------------------------------------
    # Factor 4: Unusual Financial Values & Tenor (Max 15 pts)
    # -------------------------------------------------------------------------
    financial_score = 0.0
    tenor_days = (fdr_record.maturity_date - fdr_record.issue_date).days if (fdr_record.issue_date and fdr_record.maturity_date) else 1825
    evidence["tenor_days"] = tenor_days
    evidence["deposit_amount"] = float(fdr_record.deposit_amount) if fdr_record.deposit_amount else 0.0

    if tenor_days < 365:
        financial_score = 15.0
        contributing_factors.append({
            "factor": "abnormal_tenor",
            "weight": RISK_WEIGHTS["unusual_financial_values"],
            "score": 15.0,
            "severity": "CRITICAL",
            "explanation": f"Tenor duration is unusually short ({tenor_days} days). Minimum standard regulatory lock-in is 5 years.",
        })
    elif tenor_days < 1095:  # Less than 3 years
        financial_score = 8.0
        contributing_factors.append({
            "factor": "short_tenor",
            "weight": RISK_WEIGHTS["unusual_financial_values"],
            "score": 8.0,
            "severity": "MEDIUM",
            "explanation": f"Tenor duration ({tenor_days} days) is less than 3 years.",
        })
    elif float(fdr_record.deposit_amount or 0) < 50000.0:
        financial_score = 10.0
        contributing_factors.append({
            "factor": "low_deposit_amount",
            "weight": RISK_WEIGHTS["unusual_financial_values"],
            "score": 10.0,
            "severity": "LOW",
            "explanation": f"Deposit amount (INR {fdr_record.deposit_amount:,.2f}) is unusually low for institutional security deposits.",
        })
    rule_subscores["unusual_financial_values"] = financial_score

    # -------------------------------------------------------------------------
    # Factor 5: Maturity Urgency & Expiration (Max 10 pts)
    # -------------------------------------------------------------------------
    maturity_score = 0.0
    days_left = fdr_record.days_to_maturity
    evidence["days_to_maturity"] = days_left

    if days_left is not None:
        if days_left <= 0 and fdr_record.status not in (FDRRecord.STATUS_RENEWED, FDRRecord.STATUS_RELEASED):
            maturity_score = 10.0
            contributing_factors.append({
                "factor": "matured_instrument",
                "weight": RISK_WEIGHTS["maturity_urgency"],
                "score": 10.0,
                "severity": "HIGH",
                "explanation": f"Instrument has already matured ({abs(days_left)} days overdue) without approved renewal or release.",
            })
        elif 0 < days_left <= 15:
            maturity_score = 7.0
            contributing_factors.append({
                "factor": "expiring_imminently",
                "weight": RISK_WEIGHTS["maturity_urgency"],
                "score": 7.0,
                "severity": "MEDIUM",
                "explanation": f"Instrument will mature in {days_left} days. Renewal required urgently.",
            })
    rule_subscores["maturity_urgency"] = maturity_score

    # -------------------------------------------------------------------------
    # Factor 6: Workflow & Compliance Status (Max 10 pts)
    # -------------------------------------------------------------------------
    workflow_score = 0.0
    if fdr_record.workflow_status == FDRRecord.WORKFLOW_RENEWAL_REJECTED:
        workflow_score = 10.0
        contributing_factors.append({
            "factor": "rejected_renewal",
            "weight": RISK_WEIGHTS["workflow_compliance"],
            "score": 10.0,
            "severity": "HIGH",
            "explanation": "A prior renewal proposal for this instrument was rejected by AICTE regulators.",
        })
    rule_subscores["workflow_compliance"] = workflow_score

    # Aggregate Rule-Based Score (0 to 100)
    total_rule_score = sum(rule_subscores.values())

    # -------------------------------------------------------------------------
    # ML Anomaly Score Integration (Isolation Forest)
    # -------------------------------------------------------------------------
    if anomaly_detector is None:
        anomaly_detector = FDRAnomalyDetector()

    anomaly_result = anomaly_detector.analyze_record(fdr_record, reference_date=reference_date)
    ml_anomaly_score = anomaly_result["anomaly_score"] * 100.0  # Scale 0-1 to 0-100
    is_ml_anomaly = anomaly_result["is_anomaly"]
    evidence["ml_engine"] = anomaly_result["engine"]
    evidence["ml_anomaly_score"] = round(ml_anomaly_score, 1)

    if is_ml_anomaly:
        contributing_factors.append({
            "factor": "ml_anomaly_flag",
            "weight": "Statistical Isolation",
            "score": round(ml_anomaly_score, 1),
            "severity": "HIGH",
            "explanation": "Isolation Forest flagged multidimensional anomaly in feature distribution.",
        })

    # Weighted Composite Score: 70% Deterministic Rules + 30% ML Anomaly Score
    composite_score = (0.70 * total_rule_score) + (0.30 * ml_anomaly_score)
    composite_score = min(max(composite_score, 0.0), 100.0)

    # Risk Category Assignment
    if composite_score >= 80.0:
        category = "CRITICAL"
        action = "Immediate regulatory audit required. Lock instrument from automatic administrative approvals."
    elif composite_score >= 60.0:
        category = "HIGH"
        action = "Priority official scrutiny recommended. Require bank verification scroll and fresh deposit certificate."
    elif composite_score >= 30.0:
        category = "MEDIUM"
        action = "Standard official scrutiny recommended. Verify flagged discrepancies during regular audit."
    else:
        category = "LOW"
        action = "Instrument compliant with normal risk profiles. Standard automated monitoring."

    return {
        "risk_score": round(composite_score, 1),
        "risk_category": category,
        "rule_score": round(total_rule_score, 1),
        "ml_score": round(ml_anomaly_score, 1),
        "is_anomaly": is_ml_anomaly,
        "contributing_factors": contributing_factors,
        "evidence": evidence,
        "recommended_action": action,
        "model_version": "v1.0.0",
    }
