"""
Document Management and OCR Routes for AICTE FDR Portal.

Phase 5: Secure Document Management and OCR
Endpoints:
- POST /api/fdr/<fdr_id>/documents        : Secure document upload (PDF, JPG, PNG)
- GET  /api/fdr/<fdr_id>/documents        : List documents for an FDR record
- GET  /api/documents/<doc_id>            : Retrieve document metadata and OCR results
- GET  /api/documents/<doc_id>/download   : Secure document streaming download
- POST /api/documents/<doc_id>/process-ocr: Trigger/re-run OCR and discrepancy analysis
- POST /api/documents/<doc_id>/review     : Reviewer-only approval/rejection audit
"""

import os
import uuid
import hashlib
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import current_user
from config import Config
from models import db, FDRRecord, FDRDocument, OCRResult, User
from utils.decorators import any_authenticated_user, aicte_or_admin_required
from services.audit_service import record_audit_event
from services.ocr_service import (
    extract_text_from_document,
    extract_fields_from_text,
    compare_extracted_with_fdr,
)

documents_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = getattr(Config, "MAX_DOCUMENT_SIZE", 10 * 1024 * 1024)  # 10 MB default

# File signature magic bytes
MAGIC_NUMBERS = {
    "pdf": b"%PDF",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}


def get_upload_directory():
    """Ensure upload storage folder exists securely."""
    upload_dir = current_app.config.get(
        "DOCUMENTS_UPLOAD_FOLDER",
        os.path.join(current_app.config.get("UPLOAD_FOLDER", Config.UPLOAD_FOLDER), "documents"),
    )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def validate_file_signature(stream, extension):
    """
    Validate file signature (magic bytes) to prevent file-type spoofing.
    Returns True if valid or if extension has no strict signature.
    """
    ext = extension.lower()
    magic = MAGIC_NUMBERS.get(ext)
    if not magic:
        return True

    pos = stream.tell()
    header = stream.read(len(magic))
    stream.seek(pos)  # Reset stream position

    return header.startswith(magic)


def execute_ocr_and_discrepancy(document):
    """
    Execute text extraction, field parsing, and discrepancy comparison for a document.
    Saves or updates OCRResult in database.
    """
    raw_text, engine_used, err_msg = extract_text_from_document(document.file_path, document.content_type)

    if err_msg and not raw_text:
        # OCR could not extract text
        document.processing_status = FDRDocument.STATUS_MANUAL_REVIEW
        ocr_result = document.ocr_result
        if not ocr_result:
            ocr_result = OCRResult(
                document_id=document.id,
                fdr_record_id=document.fdr_record_id,
            )
            db.session.add(ocr_result)

        ocr_result.raw_text = err_msg
        ocr_result.ocr_engine = engine_used
        ocr_result.confidence_score = 0.0
        ocr_result.confidence_level = "FAILED"
        ocr_result.review_required = True
        ocr_result.has_discrepancy = True
        ocr_result.discrepancy_count = 1
        ocr_result.discrepancy_details = json.dumps({
            "error": err_msg,
            "status": "MANUAL_REVIEW_REQUIRED"
        })
        db.session.commit()
        return ocr_result

    # Extract fields from text
    fields = extract_fields_from_text(raw_text)

    # Compare extracted fields against FDRRecord
    has_disc, count_disc, disc_details = compare_extracted_with_fdr(fields, document.fdr_record)

    document.processing_status = (
        FDRDocument.STATUS_MANUAL_REVIEW if (has_disc or fields["confidence_level"] != "HIGH")
        else FDRDocument.STATUS_PROCESSED
    )

    ocr_result = document.ocr_result
    if not ocr_result:
        ocr_result = OCRResult(
            document_id=document.id,
            fdr_record_id=document.fdr_record_id,
        )
        db.session.add(ocr_result)

    ocr_result.raw_text = raw_text
    ocr_result.extracted_fdr_number = fields["fdr_number"]
    ocr_result.extracted_bank_name = fields["issuing_bank"]
    ocr_result.extracted_amount = fields["deposit_amount"]
    ocr_result.extracted_issue_date = fields["issue_date"]
    ocr_result.extracted_maturity_date = fields["maturity_date"]
    ocr_result.extracted_institution_name = fields["institution_name"]
    ocr_result.ocr_engine = engine_used
    ocr_result.confidence_score = fields["confidence_score"]
    ocr_result.confidence_level = fields["confidence_level"]
    ocr_result.review_required = True
    ocr_result.has_discrepancy = has_disc
    ocr_result.discrepancy_count = count_disc
    ocr_result.discrepancy_details = json.dumps(disc_details)

    db.session.commit()
    return ocr_result


# ---------------------------------------------------------------------------
# 1. POST /api/fdr/<fdr_id>/documents - Upload Document
# ---------------------------------------------------------------------------
@documents_bp.route("/fdr/<int:fdr_id>/documents", methods=["POST"])
@any_authenticated_user()
def upload_fdr_document(fdr_id):
    """
    Securely upload an FDR supporting document (PDF, JPG, PNG).
    Validates extension, size (<=10MB), MIME type, and magic bytes.
    Generates server-side random filename.
    """
    # 1. Check parent FDR Record exists
    fdr_record = db.session.get(FDRRecord, fdr_id)
    if not fdr_record:
        return jsonify({
            "error": "Not Found",
            "message": f"FDR record with ID {fdr_id} does not exist."
        }), 404

    # 2. Enforce Institution Isolation
    if current_user.role == User.ROLE_INSTITUTION_USER:
        if fdr_record.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot upload documents for an FDR belonging to another institution."
            }), 403

    # 3. Validate multipart file presence
    if "file" not in request.files:
        return jsonify({
            "error": "Bad Request",
            "message": "No file part in request. Expected multipart/form-data with key 'file'."
        }), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "error": "Bad Request",
            "message": "No file selected for upload."
        }), 400

    original_filename = secure_filename(uploaded_file.filename) or "document"
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""

    # 4. Validate Extension
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "Validation Error",
            "message": f"Invalid file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        }), 400

    # 5. Validate MIME type
    content_type = uploaded_file.content_type or ""
    if content_type.lower() not in ALLOWED_MIME_TYPES:
        # Fallback to extension mapping if client sent generic octet-stream
        mime_map = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
        content_type = mime_map.get(ext, "application/octet-stream")

    # 6. Validate File Size & Magic Bytes
    file_bytes = uploaded_file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        return jsonify({"error": "Validation Error", "message": "Uploaded file is empty (0 bytes)."}), 400

    max_file_size = current_app.config.get("MAX_DOCUMENT_SIZE", MAX_FILE_SIZE)
    if file_size > max_file_size:
        max_mb = max_file_size // (1024 * 1024)
        return jsonify({
            "error": "Validation Error",
            "message": f"File size exceeds maximum allowed limit of {max_mb} MB."
        }), 400

    # Validate Magic Bytes
    magic = MAGIC_NUMBERS.get(ext)
    if magic and not file_bytes.startswith(magic):
        return jsonify({
            "error": "Validation Error",
            "message": f"File content does not match extension '{ext}'. Invalid file signature."
        }), 400

    # 7. Generate Random Storage Key (never trust client filename for filesystem storage)
    storage_key = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = get_upload_directory()
    storage_path = os.path.join(upload_dir, storage_key)

    # Calculate SHA-256 Checksum
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Save to disk
    try:
        with open(storage_path, "wb") as f:
            f.write(file_bytes)
    except Exception as exc:
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to write file to private storage."
        }), 500

    # 8. Create Database Metadata Record
    doc = FDRDocument(
        fdr_record_id=fdr_record.id,
        institution_id=fdr_record.institution_id,
        uploader_id=current_user.id,
        original_filename=original_filename,
        storage_key=storage_key,
        file_path=storage_path,
        content_type=content_type,
        file_size_bytes=file_size,
        file_hash=file_hash,
        processing_status=FDRDocument.STATUS_PENDING,
    )

    try:
        db.session.add(doc)
        db.session.flush()

        record_audit_event(
            action="DOCUMENT_UPLOADED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            user=current_user,
            institution_id=doc.institution_id,
            fdr_record_id=doc.fdr_record_id,
            new_state=doc.to_dict(),
            remarks=f"Uploaded supporting document '{doc.original_filename}'.",
            ip_address=request.remote_addr,
        )

        db.session.commit()
    except Exception:
        db.session.rollback()
        # Clean up file on disk if DB fails
        if os.path.exists(storage_path):
            os.remove(storage_path)
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to persist document metadata in database."
        }), 500

    # 9. Perform Separable OCR and Discrepancy Extraction
    ocr_result = None
    try:
        ocr_result = execute_ocr_and_discrepancy(doc)
    except Exception as ocr_err:
        doc.processing_status = FDRDocument.STATUS_FAILED
        db.session.commit()

    return jsonify({
        "message": "Document uploaded successfully.",
        "data": doc.to_dict(),
        "ocr_summary": {
            "processing_status": doc.processing_status,
            "has_discrepancy": ocr_result.has_discrepancy if ocr_result else False,
            "confidence_level": ocr_result.confidence_level if ocr_result else "FAILED",
        }
    }), 201


# ---------------------------------------------------------------------------
# 2. GET /api/fdr/<fdr_id>/documents - List Documents for an FDR
# ---------------------------------------------------------------------------
@documents_bp.route("/fdr/<int:fdr_id>/documents", methods=["GET"])
@any_authenticated_user()
def list_fdr_documents(fdr_id):
    """
    List all uploaded documents associated with an FDR record.
    Enforces institution-level isolation.
    """
    fdr_record = db.session.get(FDRRecord, fdr_id)
    if not fdr_record:
        return jsonify({"error": "Not Found", "message": f"FDR record with ID {fdr_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if fdr_record.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You do not have permission to view documents of another institution."
            }), 403

    documents = FDRDocument.query.filter_by(fdr_record_id=fdr_id).order_by(FDRDocument.created_at.desc()).all()
    return jsonify({
        "status": "success",
        "fdr_id": fdr_id,
        "total_documents": len(documents),
        "data": [d.to_dict() for d in documents]
    }), 200


# ---------------------------------------------------------------------------
# 3. GET /api/documents/<doc_id> - Document Metadata & OCR Discrepancies
# ---------------------------------------------------------------------------
@documents_bp.route("/documents/<int:doc_id>", methods=["GET"])
@any_authenticated_user()
def get_document_details(doc_id):
    """
    Retrieve document metadata along with detailed OCR discrepancy detection results.
    Enforces institution ownership.
    """
    doc = db.session.get(FDRDocument, doc_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document with ID {doc_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if doc.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot view documents belonging to another institution."
            }), 403

    doc_data = doc.to_dict()
    if doc.ocr_result:
        doc_data["ocr_details"] = doc.ocr_result.to_dict()
    else:
        doc_data["ocr_details"] = None

    return jsonify({"status": "success", "data": doc_data}), 200


# ---------------------------------------------------------------------------
# 4. GET /api/documents/<doc_id>/download - Secure Document Download
# ---------------------------------------------------------------------------
@documents_bp.route("/documents/<int:doc_id>/download", methods=["GET"])
@any_authenticated_user()
def download_document(doc_id):
    """
    Securely stream the document file.
    Enforces authorization; never reveals absolute filesystem paths.
    """
    doc = db.session.get(FDRDocument, doc_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document with ID {doc_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if doc.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You do not have permission to download this document."
            }), 403

    if not os.path.exists(doc.file_path):
        return jsonify({
            "error": "Not Found",
            "message": "The document file was not found on private storage."
        }), 404

    return send_file(
        doc.file_path,
        mimetype=doc.content_type,
        as_attachment=True,
        download_name=doc.original_filename,
    )


# ---------------------------------------------------------------------------
# 5. POST /api/documents/<doc_id>/process-ocr - Trigger/Re-run OCR Processing
# ---------------------------------------------------------------------------
@documents_bp.route("/documents/<int:doc_id>/process-ocr", methods=["POST"])
@any_authenticated_user()
def process_document_ocr(doc_id):
    """
    Trigger or re-run OCR extraction and discrepancy detection on an uploaded document.
    """
    doc = db.session.get(FDRDocument, doc_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document with ID {doc_id} was not found."}), 404

    if current_user.role == User.ROLE_INSTITUTION_USER:
        if doc.institution_id != current_user.institution_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Access denied: You cannot process documents of another institution."
            }), 403

    doc.processing_status = FDRDocument.STATUS_PROCESSING
    db.session.commit()

    try:
        ocr_result = execute_ocr_and_discrepancy(doc)
        return jsonify({
            "message": "OCR processing and discrepancy detection completed.",
            "data": ocr_result.to_dict()
        }), 200
    except Exception as exc:
        doc.processing_status = FDRDocument.STATUS_FAILED
        db.session.commit()
        return jsonify({
            "error": "Internal Server Error",
            "message": f"OCR processing failed: {str(exc)}"
        }), 500


# ---------------------------------------------------------------------------
# 6. POST /api/documents/<doc_id>/review - Reviewer Action (AICTE/Admin Only)
# ---------------------------------------------------------------------------
@documents_bp.route("/documents/<int:doc_id>/review", methods=["POST"])
@aicte_or_admin_required()
def review_document_ocr(doc_id):
    """
    Authorized review endpoint for AICTE Officials and Administrators.
    Records reviewer decision (ACCEPTED, REJECTED, CORRECTION_PROPOSED) and audit notes.
    Never lets OCR automatically approve an FDR.
    """
    doc = db.session.get(FDRDocument, doc_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document with ID {doc_id} was not found."}), 404

    ocr_result = doc.ocr_result
    if not ocr_result:
        return jsonify({
            "error": "Bad Request",
            "message": "No OCR result exists for this document. Run OCR processing first."
        }), 400

    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request body must be valid JSON."}), 400

    data = request.get_json()
    decision = data.get("decision")
    notes = data.get("notes", "")

    if not decision:
        return jsonify({
            "error": "Validation Error",
            "message": f"Field 'decision' is required. Allowed: {', '.join(sorted(OCRResult.ALLOWED_DECISIONS))}."
        }), 400

    decision_clean = str(decision).strip().upper()
    if decision_clean not in OCRResult.ALLOWED_DECISIONS:
        return jsonify({
            "error": "Validation Error",
            "message": f"Invalid decision '{decision_clean}'. Allowed: {', '.join(sorted(OCRResult.ALLOWED_DECISIONS))}."
        }), 400

    # Record Review Audit Trail
    ocr_result.reviewed_by_id = current_user.id
    ocr_result.reviewed_at = datetime.utcnow()
    ocr_result.review_decision = decision_clean
    ocr_result.review_notes = str(notes).strip() if notes else None

    # Update document status based on decision
    if decision_clean == OCRResult.DECISION_ACCEPTED:
        doc.processing_status = FDRDocument.STATUS_PROCESSED
    elif decision_clean == OCRResult.DECISION_REJECTED:
        doc.processing_status = FDRDocument.STATUS_FAILED

    try:
        record_audit_event(
            action=f"DOCUMENT_REVIEW_{decision_clean}",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            user=current_user,
            institution_id=doc.institution_id,
            fdr_record_id=doc.fdr_record_id,
            remarks=str(notes).strip() if notes else f"Review decision: {decision_clean}",
            details={"decision": decision_clean, "notes": notes},
            ip_address=request.remote_addr,
        )
        db.session.commit()
        return jsonify({
            "message": f"Document review recorded successfully with decision '{decision_clean}'.",
            "data": ocr_result.to_dict()
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to save review decision."
        }), 500
