"""
AI & Machine Learning Intelligence Routes for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Endpoints:
- POST /api/ai/duplicates/scan             : Trigger intelligent duplicate detection scan (AICTE/Admin)
- GET  /api/ai/duplicates                  : List duplicate candidates (tenant-isolated & paginated)
- GET  /api/ai/duplicates/<id>             : Retrieve candidate details
- PATCH /api/ai/duplicates/<id>            : Review candidate status (AICTE/Admin only)
- GET  /api/ai/anomalies/<fdr_id>          : Isolation Forest anomaly analysis for single FDR
- GET  /api/ai/risk-score/<fdr_id>         : Explainable composite risk score (0-100) & factors
- POST /api/ai/risk-score/batch            : Batch risk evaluation across portfolio
- GET  /api/ai/compliance/<institution_id> : Institutional compliance profile & regulatory grade
- GET  /api/ai/compliance/summary          : Global compliance summary (AICTE/Admin only)
- GET  /api/ai/report/<fdr_id>             : Comprehensive 360-degree AI audit dossier
- GET  /api/ai/models/health               : Model versioning, health, and registry status
- POST /api/ai/models/train                : Retrain baseline model on synthetic benchmark (Admin only)
"""

from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import current_user
from sqlalchemy import or_

from models import (
    db,
    FDRRecord,
    Institution,
    User,
    FDRDuplicateCandidate,
    FDRRiskAssessment,
)
from utils.decorators import (
    any_authenticated_user,
    aicte_or_admin_required,
    admin_required,
)
from services.audit_service import record_audit_event
from ml.duplicate_detector import run_full_duplicate_scan
from ml.anomaly_detector import FDRAnomalyDetector
from ml.risk_scorer import calculate_fdr_risk
from ml.compliance_intelligence import analyze_institution_compliance
from ml.model_registry import get_model_health_status, load_registered_model
from ml.trainer import train_and_register_isolation_forest

ai_bp = Blueprint("ai", __name__)

# Cached detector instance with lazy load
_detector_instance = None


def get_detector():
    """Retrieve or initialize the active anomaly detector."""
    global _detector_instance
    if _detector_instance is None:
        model, _ = load_registered_model()
        _detector_instance = FDRAnomalyDetector(model=model)
    return _detector_instance


# -----------------------------------------------------------------------------
# 1. Duplicate Detection Endpoints
# -----------------------------------------------------------------------------
@ai_bp.route("/duplicates/scan", methods=["POST"])
@aicte_or_admin_required()
def trigger_duplicate_scan():
    """
    Trigger intelligent duplicate scan across all FDR records and documents.
    Detects exact numbers, document SHA-256 hashes, and fuzzy formatting variations.
    """
    results = run_full_duplicate_scan()

    record_audit_event(
        action="AI_DUPLICATE_SCAN_TRIGGERED",
        entity_type="SYSTEM",
        entity_id=None,
        user=current_user,
        remarks=(
            f"AI duplicate scan executed by {current_user.email}. "
            f"Found: {results['duplicate_candidates_found']} candidates."
        ),
        details=results,
        ip_address=request.remote_addr,
    )
    db.session.commit()

    response_payload = {
        "status": "success",
        "message": "AI duplicate detection scan completed successfully.",
        "data": results,
    }
    # Also expose top-level keys for backward-compatibility
    response_payload.update(results)
    return jsonify(response_payload), 200


@ai_bp.route("/duplicates", methods=["GET"])
@any_authenticated_user()
def list_duplicate_candidates():
    """
    List suspect duplicate pairs with pagination and filters.
    Institution users only see candidates involving their own institution.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or per_page < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "'page' and 'per_page' must be positive integers."}), 400

    per_page = min(per_page, 100)
    query = FDRDuplicateCandidate.query

    # Tenant Isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        inst_id = current_user.institution_id
        query = query.join(
            FDRRecord,
            or_(
                FDRDuplicateCandidate.primary_fdr_id == FDRRecord.id,
                FDRDuplicateCandidate.duplicate_fdr_id == FDRRecord.id,
            ),
        ).filter(FDRRecord.institution_id == inst_id)

    # Status filter
    status_filter = request.args.get("status")
    if status_filter and status_filter.strip().upper() in FDRDuplicateCandidate.ALLOWED_STATUSES:
        query = query.filter(FDRDuplicateCandidate.status == status_filter.strip().upper())

    # Match type filter
    type_filter = request.args.get("match_type")
    if type_filter:
        query = query.filter(FDRDuplicateCandidate.match_type == type_filter.strip().upper())

    query = query.order_by(FDRDuplicateCandidate.similarity_score.desc(), FDRDuplicateCandidate.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "data": [c.to_dict() for c in pagination.items],
    }), 200


@ai_bp.route("/duplicates/<int:candidate_id>", methods=["GET"])
@any_authenticated_user()
def get_duplicate_candidate(candidate_id):
    """
    Retrieve single duplicate candidate details.
    """
    cand = db.session.get(FDRDuplicateCandidate, candidate_id)
    if not cand:
        return jsonify({"error": "Not Found", "message": f"Duplicate candidate with ID {candidate_id} was not found."}), 404

    # Tenant check
    if current_user.role == User.ROLE_INSTITUTION_USER:
        p_inst = cand.primary_fdr.institution_id if cand.primary_fdr else None
        d_inst = cand.duplicate_fdr.institution_id if cand.duplicate_fdr else None
        if current_user.institution_id not in (p_inst, d_inst):
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view duplicate candidates belonging to other institutions."
            }), 403

    return jsonify({"status": "success", "data": cand.to_dict()}), 200


@ai_bp.route("/duplicates/<int:candidate_id>", methods=["PATCH"])
@aicte_or_admin_required()
def review_duplicate_candidate(candidate_id):
    """
    Review duplicate candidate status (CONFIRMED_DUPLICATE, FALSE_POSITIVE, RESOLVED).
    Authorized for AICTE Officials and Administrators only.
    """
    cand = db.session.get(FDRDuplicateCandidate, candidate_id)
    if not cand:
        return jsonify({"error": "Not Found", "message": f"Duplicate candidate with ID {candidate_id} was not found."}), 404

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    new_status = data.get("status")
    remarks = data.get("remarks", "")

    if not new_status or str(new_status).strip().upper() not in FDRDuplicateCandidate.ALLOWED_STATUSES:
        return jsonify({
            "error": "Validation Error",
            "message": f"Field 'status' is required and must be one of: {', '.join(sorted(FDRDuplicateCandidate.ALLOWED_STATUSES))}."
        }), 400

    status_clean = str(new_status).strip().upper()
    now_utc = datetime.utcnow()

    prev_status = cand.status
    cand.status = status_clean
    cand.reviewed_by_id = current_user.id
    cand.reviewed_at = now_utc
    cand.review_remarks = str(remarks).strip() if remarks else None
    cand.updated_at = now_utc

    record_audit_event(
        action=f"AI_DUPLICATE_REVIEW_{status_clean}",
        entity_type="DUPLICATE_CANDIDATE",
        entity_id=cand.id,
        user=current_user,
        fdr_record_id=cand.primary_fdr_id,
        previous_state={"status": prev_status},
        new_state={"status": status_clean, "remarks": remarks},
        remarks=f"Duplicate candidate status updated to {status_clean}.",
        ip_address=request.remote_addr,
    )

    try:
        db.session.commit()
        return jsonify({
            "message": f"Duplicate candidate reviewed successfully ({status_clean}).",
            "data": cand.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "Failed to update duplicate review."}), 500


# -----------------------------------------------------------------------------
# 2. Anomaly Detection & Risk Scoring Endpoints
# -----------------------------------------------------------------------------
@ai_bp.route("/anomalies/<int:fdr_id>", methods=["GET"])
@any_authenticated_user()
def analyze_fdr_anomalies(fdr_id):
    """
    Perform Isolation Forest and statistical anomaly analysis on a single FDR.
    Tenant isolated: institution users cannot analyze cross-institution FDRs.
    """
    fdr = db.session.get(FDRRecord, fdr_id)
    if not fdr:
        return jsonify({"error": "Not Found", "message": f"FDR record with ID {fdr_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if fdr.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot analyze FDR records belonging to another institution."
            }), 403

    detector = get_detector()
    analysis = detector.analyze_record(fdr)

    return jsonify({
        "status": "success",
        "fdr_id": fdr.id,
        "fdr_number": fdr.fdr_number,
        "institution_id": fdr.institution_id,
        "analysis": analysis,
    }), 200


@ai_bp.route("/risk-score/<int:fdr_id>", methods=["GET"])
@any_authenticated_user()
def get_fdr_risk_score(fdr_id):
    """
    Compute explainable multi-factor risk score (0-100) and persist evaluation.
    Enforces institution-level access control.
    """
    fdr = db.session.get(FDRRecord, fdr_id)
    if not fdr:
        return jsonify({"error": "Not Found", "message": f"FDR record with ID {fdr_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if fdr.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view risk assessments for another institution's FDR."
            }), 403

    detector = get_detector()
    assessment_dict = calculate_fdr_risk(fdr, anomaly_detector=detector)

    # Persist or update Risk Assessment record in database
    risk_rec = FDRRiskAssessment.query.filter_by(fdr_record_id=fdr.id).first()
    if not risk_rec:
        risk_rec = FDRRiskAssessment(
            fdr_record_id=fdr.id,
            institution_id=fdr.institution_id,
            risk_score=assessment_dict["risk_score"],
            risk_category=assessment_dict["risk_category"],
            is_anomaly=assessment_dict["is_anomaly"],
            rule_score=assessment_dict["rule_score"],
            ml_score=assessment_dict["ml_score"],
            model_version=assessment_dict["model_version"],
            recommended_action=assessment_dict["recommended_action"],
        )
        db.session.add(risk_rec)
    else:
        risk_rec.risk_score = assessment_dict["risk_score"]
        risk_rec.risk_category = assessment_dict["risk_category"]
        risk_rec.is_anomaly = assessment_dict["is_anomaly"]
        risk_rec.rule_score = assessment_dict["rule_score"]
        risk_rec.ml_score = assessment_dict["ml_score"]
        risk_rec.recommended_action = assessment_dict["recommended_action"]
        risk_rec.created_at = datetime.utcnow()

    risk_rec.set_contributing_factors_list(assessment_dict["contributing_factors"])
    risk_rec.set_evidence_dict(assessment_dict["evidence"])

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({
        "status": "success",
        "data": risk_rec.to_dict(),
    }), 200


@ai_bp.route("/risk-score/batch", methods=["POST"])
@aicte_or_admin_required()
def batch_risk_score():
    """
    Evaluate and persist risk scores for multiple FDR records.
    Restricted to AICTE Officials and Administrators.
    """
    fdr_ids = []
    if request.is_json:
        data = request.get_json()
        fdr_ids = data.get("fdr_ids", [])

    query = FDRRecord.query
    if fdr_ids:
        query = query.filter(FDRRecord.id.in_(fdr_ids))
    else:
        # Default: evaluate active instruments
        query = query.filter(FDRRecord.status.notin_([FDRRecord.STATUS_RELEASED, FDRRecord.STATUS_RENEWED])).limit(50)

    records = query.all()
    detector = get_detector()
    results = []

    for fdr in records:
        res = calculate_fdr_risk(fdr, anomaly_detector=detector)
        results.append({
            "fdr_id": fdr.id,
            "fdr_number": fdr.fdr_number,
            "institution_id": fdr.institution_id,
            "risk_score": res["risk_score"],
            "risk_category": res["risk_category"],
            "is_anomaly": res["is_anomaly"],
        })

    return jsonify({
        "status": "success",
        "total_evaluated": len(results),
        "data": results,
    }), 200


# -----------------------------------------------------------------------------
# 3. Compliance Intelligence Endpoints
# -----------------------------------------------------------------------------
@ai_bp.route("/compliance/<int:institution_id>", methods=["GET"])
@any_authenticated_user()
def get_institution_compliance(institution_id):
    """
    Retrieve compliance intelligence profile and regulatory grading for an institution.
    Tenant isolated: institution users can only view their own institution's compliance.
    """
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view compliance profiles belonging to another institution."
            }), 403

    compliance_profile = analyze_institution_compliance(institution_id)
    if not compliance_profile:
        return jsonify({"error": "Not Found", "message": f"Institution with ID {institution_id} was not found."}), 404

    return jsonify({
        "status": "success",
        "data": compliance_profile,
    }), 200


@ai_bp.route("/compliance/summary", methods=["GET"])
@aicte_or_admin_required()
def get_global_compliance_summary():
    """
    Council-wide institutional compliance distribution summary.
    Restricted to AICTE Officials and Administrators.
    """
    institutions = Institution.query.all()
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    total_inst = len(institutions)
    profiles = []

    for inst in institutions:
        profile = analyze_institution_compliance(inst.id)
        if profile:
            grade_counts[profile["compliance_grade"]] = grade_counts.get(profile["compliance_grade"], 0) + 1
            profiles.append({
                "institution_id": inst.id,
                "name": inst.name,
                "code": inst.institution_code,
                "compliance_score": profile["compliance_score"],
                "compliance_grade": profile["compliance_grade"],
                "risk_level": profile["risk_level"],
                "matured_unresolved_count": profile["metrics"]["matured_unresolved_count"],
            })

    return jsonify({
        "status": "success",
        "total_institutions": total_inst,
        "grade_distribution": grade_counts,
        "institutions": sorted(profiles, key=lambda x: x["compliance_score"]),
    }), 200


# -----------------------------------------------------------------------------
# 4. 360-Degree AI Dossier Report
# -----------------------------------------------------------------------------
@ai_bp.route("/report/<int:fdr_id>", methods=["GET"])
@any_authenticated_user()
def get_fdr_ai_dossier(fdr_id):
    """
    Generate comprehensive 360-degree AI intelligence dossier on an FDR instrument:
    Combines:
    - Metadata and verification state
    - Document coverage and OCR discrepancy results
    - Isolation Forest anomaly metrics
    - Duplicate match candidate history
    - Explainable composite risk score
    - Supervisory action guidance
    """
    fdr = db.session.get(FDRRecord, fdr_id)
    if not fdr:
        return jsonify({"error": "Not Found", "message": f"FDR record with ID {fdr_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if fdr.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view AI reports for another institution's FDR."
            }), 403

    detector = get_detector()
    risk_info = calculate_fdr_risk(fdr, anomaly_detector=detector)
    anomaly_info = detector.analyze_record(fdr)

    # Duplicates involving this FDR
    dup_candidates = FDRDuplicateCandidate.query.filter(
        (FDRDuplicateCandidate.primary_fdr_id == fdr.id) |
        (FDRDuplicateCandidate.duplicate_fdr_id == fdr.id)
    ).all()

    # Documents summary
    docs = list(fdr.documents) if hasattr(fdr, "documents") else []
    doc_summary = []
    for d in docs:
        doc_summary.append({
            "id": d.id,
            "filename": d.original_filename,
            "file_hash": d.file_hash,
            "status": d.processing_status,
            "has_ocr": d.ocr_result is not None,
            "ocr_discrepancy": d.ocr_result.has_discrepancy if d.ocr_result else False,
        })

    dossier = {
        "fdr_details": fdr.to_dict(),
        "institution": {
            "id": fdr.institution.id if fdr.institution else None,
            "name": fdr.institution.name if fdr.institution else None,
            "code": fdr.institution.institution_code if fdr.institution else None,
        },
        "risk_assessment": risk_info,
        "anomaly_analysis": anomaly_info,
        "duplicate_detection": {
            "flagged_duplicates_count": len(dup_candidates),
            "candidates": [c.to_dict() for c in dup_candidates],
        },
        "documents_verification": {
            "total_documents": len(docs),
            "documents": doc_summary,
        },
        "regulatory_disclaimer": (
            "AI and ML intelligence signals are advisory analytical recommendations. "
            "They do not automatically execute financial releases or legal sanctions."
        ),
        "generated_at": datetime.utcnow().isoformat(),
    }

    return jsonify({
        "status": "success",
        "data": dossier,
    }), 200


# -----------------------------------------------------------------------------
# 5. Model Management Endpoints
# -----------------------------------------------------------------------------
@ai_bp.route("/models/health", methods=["GET"])
@any_authenticated_user()
def get_models_health():
    """
    Retrieve operational health, active versions, and registry status of ML engines.
    """
    health = get_model_health_status()
    return jsonify({
        "status": "success",
        "data": health,
    }), 200


@ai_bp.route("/models/train", methods=["POST"])
@admin_required()
def trigger_model_training():
    """
    Retrain the baseline Isolation Forest anomaly detector on synthetic benchmark data.
    Restricted to system Administrators.
    """
    samples = 500
    if request.is_json:
        req_samples = request.get_json().get("n_samples")
        if req_samples and str(req_samples).isdigit() and int(req_samples) >= 50:
            samples = min(int(req_samples), 5000)

    train_result = train_and_register_isolation_forest(n_samples=samples, save=True)

    # Refresh cached detector in memory
    global _detector_instance
    _detector_instance = None

    record_audit_event(
        action="AI_MODEL_RETRAINED",
        entity_type="SYSTEM",
        entity_id=None,
        user=current_user,
        remarks=f"Trained IsolationForest model with {samples} synthetic benchmark samples.",
        details=train_result,
        ip_address=request.remote_addr,
    )
    db.session.commit()

    return jsonify({
        "message": "Model training completed and registered successfully.",
        "data": train_result,
    }), 200
