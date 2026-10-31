"""
Predictive Compliance Intelligence Module for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Provides:
- Institution-level regulatory compliance profiling
- Detection of repeated late renewals, missing documents, and discrepancies
- Transparent Compliance Index (0-100) and regulatory grading (A, B, C, D)
- Objective metrics derived solely from deposit transaction history
- No use of protected personal attributes or unsupported subjective predictions
"""

from datetime import date
from models import db, Institution, FDRRecord, FDRDocument, FDRReleaseRequest, FDRRenewalRequest
from utils.time import local_business_date


def analyze_institution_compliance(institution_id, reference_date=None):
    """
    Compute an explainable, data-driven compliance profile for an educational institution.

    Args:
        institution_id (int): Primary key of the Institution.
        reference_date (date, optional): Reference date for timeliness checks.

    Returns:
        dict: Compliance index, grade, metrics breakdown, warnings, and recommended actions.
    """
    if reference_date is None:
        reference_date = local_business_date()

    inst = db.session.get(Institution, institution_id)
    if not inst:
        return None

    # Query institution records
    fdrs = FDRRecord.query.filter_by(institution_id=institution_id).all()
    total_fdrs = len(fdrs)

    if total_fdrs == 0:
        return {
            "institution_id": institution_id,
            "institution_name": inst.name,
            "institution_code": inst.institution_code,
            "compliance_score": 100.0,
            "compliance_grade": "A",
            "risk_level": "LOW",
            "summary": "No active or historical FDR records on file.",
            "metrics": {
                "total_fdrs": 0,
                "active_fdrs": 0,
                "matured_unresolved": 0,
                "document_coverage_pct": 100.0,
                "discrepancy_rate_pct": 0.0,
                "unresolved_scrutiny_count": 0,
                "pending_release_requests": 0,
            },
            "warning_indicators": [],
            "recommendations": ["Standard monitoring."],
            "recommended_supervisory_action": "Standard monitoring.",
        }

    # 1. Matured and overdue instruments without resolved rollover
    matured_unresolved = 0
    active_count = 0
    total_deposit_sum = 0.0

    for f in fdrs:
        if f.deposit_amount:
            total_deposit_sum += float(f.deposit_amount)

        if f.status == FDRRecord.STATUS_ACTIVE:
            active_count += 1
            if f.maturity_date and (f.maturity_date - reference_date).days <= 0:
                matured_unresolved += 1

    # 2. Document coverage rate
    fdrs_with_docs = 0
    total_discrepancies = 0

    for f in fdrs:
        docs = list(f.documents) if hasattr(f, "documents") else []
        if docs:
            fdrs_with_docs += 1
            for d in docs:
                if hasattr(d, "ocr_result") and d.ocr_result and d.ocr_result.has_discrepancy:
                    total_discrepancies += 1

    doc_coverage_pct = round((fdrs_with_docs / total_fdrs) * 100.0, 1)
    discrepancy_rate_pct = round((total_discrepancies / total_fdrs) * 100.0, 1)

    # 3. Release & Renewal scrutiny observations
    release_reqs = FDRReleaseRequest.query.filter_by(institution_id=institution_id).all()
    pending_releases = [r for r in release_reqs if r.status not in FDRReleaseRequest.TERMINAL_STATUSES]
    unresolved_scrutiny = [r for r in release_reqs if r.status == FDRReleaseRequest.STATUS_CORRECTION_REQUIRED]

    # Calculate Deductions from baseline 100
    deductions = 0.0
    warning_indicators = []

    # Deduction 1: Matured unresolved instruments (15 pts per instrument, max 40)
    if matured_unresolved > 0:
        pen = min(matured_unresolved * 15.0, 40.0)
        deductions += pen
        warning_indicators.append({
            "code": "OVERDUE_MATURITY",
            "severity": "HIGH",
            "message": f"{matured_unresolved} FDR instrument(s) have matured without an approved renewal or release.",
        })

    # Deduction 2: Missing supporting documentation (max 25 pts)
    if doc_coverage_pct < 80.0:
        pen = min((80.0 - doc_coverage_pct) * 0.5, 25.0)
        deductions += pen
        warning_indicators.append({
            "code": "LOW_DOCUMENT_COVERAGE",
            "severity": "MEDIUM",
            "message": f"Supporting document coverage is {doc_coverage_pct}% ({fdrs_with_docs}/{total_fdrs} FDRs have uploaded receipts).",
        })

    # Deduction 3: High OCR discrepancy rate (max 20 pts)
    if discrepancy_rate_pct >= 25.0:
        pen = min(discrepancy_rate_pct * 0.4, 20.0)
        deductions += pen
        warning_indicators.append({
            "code": "REPEATED_DISCREPANCIES",
            "severity": "HIGH",
            "message": f"Elevated discrepancy rate ({discrepancy_rate_pct}%). OCR extracted parameters mismatch submitted records.",
        })

    # Deduction 4: Lingering correction requests (10 pts per unresolved item, max 20)
    if len(unresolved_scrutiny) > 0:
        pen = min(len(unresolved_scrutiny) * 10.0, 20.0)
        deductions += pen
        warning_indicators.append({
            "code": "UNRESOLVED_CORRECTIONS",
            "severity": "MEDIUM",
            "message": f"{len(unresolved_scrutiny)} release request(s) remain uncorrected after official regulatory feedback.",
        })

    compliance_score = max(round(100.0 - deductions, 1), 0.0)

    # Assign Grade
    if compliance_score >= 90.0:
        grade = "A"
        risk_level = "LOW"
        action = "Full institutional compliance. Eligible for expedited processing."
    elif compliance_score >= 75.0:
        grade = "B"
        risk_level = "MEDIUM"
        action = "Satisfactory compliance with minor documentation gaps. Standard regulatory monitoring."
    elif compliance_score >= 50.0:
        grade = "C"
        risk_level = "HIGH"
        action = "Sub-optimal compliance. Issue automated reminder notice for overdue rollovers and missing certificates."
    else:
        grade = "D"
        risk_level = "CRITICAL"
        action = "Regulatory non-compliance warning. Immediate physical inspection of bank scrolls recommended."

    return {
        "institution_id": institution_id,
        "institution_name": inst.name,
        "institution_code": inst.institution_code,
        "contact_email": inst.contact_email,
        "compliance_score": compliance_score,
        "compliance_grade": grade,
        "risk_level": risk_level,
        "metrics": {
            "total_fdrs": total_fdrs,
            "active_fdrs": active_count,
            "total_deposit_amount": round(total_deposit_sum, 2),
            "matured_unresolved_count": matured_unresolved,
            "document_coverage_pct": doc_coverage_pct,
            "discrepancy_count": total_discrepancies,
            "discrepancy_rate_pct": discrepancy_rate_pct,
            "pending_release_requests": len(pending_releases),
            "unresolved_scrutiny_count": len(unresolved_scrutiny),
        },
        "warning_indicators": warning_indicators,
        "recommendations": [action],
        "recommended_supervisory_action": action,
    }
