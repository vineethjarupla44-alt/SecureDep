"""
OCR Extraction and Discrepancy Detection Service for AICTE FDR Portal.

Phase 5: Secure Document Processing
Handles:
- System dependency checking (Tesseract OCR binary)
- Document text extraction (Native text extraction for PDFs, Tesseract for Images)
- Named entity extraction (FDR number, bank name, deposit amount, dates, institution)
- Discrepancy comparison against institution-submitted FDR records
"""

import os
import re
import shutil
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from PIL import Image
from pypdf import PdfReader
from config import Config

# Try importing pytesseract
try:
    import pytesseract
except ImportError:
    pytesseract = None


KNOWN_BANKS = [
    "State Bank of India",
    "Punjab National Bank",
    "HDFC Bank",
    "ICICI Bank",
    "Canara Bank",
    "Bank of Baroda",
    "Axis Bank",
    "Union Bank of India",
    "Bank of India",
    "Indian Bank",
    "Central Bank of India",
    "Indian Overseas Bank",
    "UCO Bank",
    "Bank of Maharashtra",
    "Punjab & Sind Bank",
    "Kotak Mahindra Bank",
    "Federal Bank",
    "IDBI Bank",
    "Yes Bank",
    "IndusInd Bank",
]


def check_tesseract_availability():
    """
    Check if the Tesseract OCR engine is available on the system.
    Returns (bool, path_or_error_msg).
    """
    if pytesseract is None:
        return False, "pytesseract Python library is not installed."

    # 1. Check system PATH
    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_in_path
        return True, tesseract_in_path

    # 2. Check configured path in Config / .env (default Windows path)
    configured_path = getattr(Config, "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if configured_path and os.path.isfile(configured_path):
        pytesseract.pytesseract.tesseract_cmd = configured_path
        return True, configured_path

    return False, (
        f"Tesseract OCR executable not found at '{configured_path}' or on PATH. "
        "Install Tesseract OCR on Windows (e.g. from UB-Mannheim/tesseract) or set TESSERACT_CMD."
    )


def extract_text_from_document(file_path, content_type):
    """
    Extract raw text from a document (PDF, JPG, PNG).

    Returns:
        tuple: (raw_text: str, engine_used: str, error_message: str or None)
    """
    if not os.path.exists(file_path):
        return "", "None", f"Document file not found at {file_path}"

    content_type = content_type.lower()

    # Case 1: PDF Document
    if content_type == "application/pdf" or file_path.lower().endswith(".pdf"):
        try:
            reader = PdfReader(file_path)
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    extracted_pages.append(text)

            full_text = "\n".join(extracted_pages).strip()
            if len(full_text) >= 15:
                # Successfully extracted text directly from PDF text layer
                return full_text, "PDF-Native", None
            else:
                # Scanned PDF without text layer
                return (
                    "",
                    "Scanned-PDF",
                    "PDF appears to be a scanned image with no embedded text layer. "
                    "Flagged for manual review."
                )
        except Exception as exc:
            return "", "PDF-Error", f"Failed to parse PDF document: {str(exc)}"

    # Case 2: Image Document (JPG, PNG)
    elif content_type in ("image/jpeg", "image/png") or file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        tesseract_ok, tesseract_info = check_tesseract_availability()
        if not tesseract_ok:
            return "", "Tesseract-Missing", f"OCR engine unavailable: {tesseract_info}"

        try:
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode not in ("L", "RGB"):
                    img = img.convert("RGB")
                text = pytesseract.image_to_string(img)
                return text.strip(), "Tesseract-OCR", None
        except Exception as exc:
            return "", "Tesseract-Error", f"Failed during OCR image processing: {str(exc)}"

    return "", "Unsupported", f"Unsupported document format: {content_type}"


def parse_extracted_date(date_str):
    """
    Parse a date string found in document text into a datetime.date object.
    Supports DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, DD Month YYYY.
    """
    if not date_str:
        return None

    clean_str = re.sub(r"[^\w\s\-\/\.]", "", date_str).strip()

    formats = [
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d %b %Y", "%d %B %Y",
        "%d-%b-%Y", "%d-%B-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue
    return None


def extract_fields_from_text(raw_text):
    """
    Extract structured FDR metadata from document text using regex heuristics.

    Returns:
        dict: Extracted values and confidence analysis.
    """
    if not raw_text:
        return {
            "fdr_number": None,
            "issuing_bank": None,
            "deposit_amount": None,
            "issue_date": None,
            "maturity_date": None,
            "institution_name": None,
            "confidence_score": 0.0,
            "confidence_level": "FAILED",
            "review_required": True,
        }

    extracted = {
        "fdr_number": None,
        "issuing_bank": None,
        "deposit_amount": None,
        "issue_date": None,
        "maturity_date": None,
        "institution_name": None,
    }

    # 1. FDR Number Extraction
    # Matches patterns like "FDR No: 12345", "Receipt No. FDR-SBI-001", "Certificate No: ..."
    fdr_patterns = [
        r"(?:FDR|FD|Receipt|Certificate|A\/c|Account)\s*(?:No\.?|Number|#)?[\s:.-]*([A-Z0-9\/-]{5,30})",
        r"\b([A-Z]{3,4}[0-9]{6,15})\b",
    ]
    for pattern in fdr_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # Ensure candidate has at least one digit and is not a common label
            if any(char.isdigit() for char in candidate) and len(candidate) >= 5:
                extracted["fdr_number"] = candidate
                break

    # 2. Issuing Bank Extraction
    for bank in KNOWN_BANKS:
        if re.search(rf"\b{re.escape(bank)}\b", raw_text, re.IGNORECASE):
            extracted["issuing_bank"] = bank
            break

    # If full bank name not found, check generic Bank pattern
    if not extracted["issuing_bank"]:
        generic_bank = re.search(r"([A-Za-z\s]+Bank(?:\s+of\s+[A-Za-z]+)?)", raw_text, re.IGNORECASE)
        if generic_bank:
            cleaned_bank = generic_bank.group(1).strip()
            if len(cleaned_bank) <= 50:
                extracted["issuing_bank"] = cleaned_bank

    # 3. Deposit Amount Extraction
    # Matches "Rs. 25,00,000", "INR 2500000.00", "Deposit Amount: 1000000"
    amount_patterns = [
        r"(?:Rs\.?|INR|₹|Deposit\s+Amount|Sum\s+of)[\s:.]*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)",
        r"(?:Amount)[\s:.]*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            raw_amt = match.group(1).replace(",", "").strip()
            try:
                dec_val = Decimal(raw_amt).quantize(Decimal("0.01"))
                if dec_val > Decimal("0.00"):
                    extracted["deposit_amount"] = dec_val
                    break
            except (InvalidOperation, TypeError):
                continue

    # 4. Dates Extraction (Issue Date & Maturity Date)
    issue_date_match = re.search(
        r"(?:Issue\s+Date|Date\s+of\s+Issue|Issued\s+on|Deposit\s+Date)[\s:.]*([0-9]{1,2}[-\/.][0-9]{1,2}[-\/.][0-9]{2,4}|[0-9]{4}[-\/.][0-9]{1,2}[-\/.][0-9]{1,2})",
        raw_text,
        re.IGNORECASE,
    )
    if issue_date_match:
        extracted["issue_date"] = parse_extracted_date(issue_date_match.group(1))

    maturity_date_match = re.search(
        r"(?:Maturity\s+Date|Due\s+Date|Valid\s+Upto|Date\s+of\s+Maturity|Expires\s+on)[\s:.]*([0-9]{1,2}[-\/.][0-9]{1,2}[-\/.][0-9]{2,4}|[0-9]{4}[-\/.][0-9]{1,2}[-\/.][0-9]{1,2})",
        raw_text,
        re.IGNORECASE,
    )
    if maturity_date_match:
        extracted["maturity_date"] = parse_extracted_date(maturity_date_match.group(1))

    # 5. Institution Name Extraction
    # Matches patterns like "Favor of: Delhi Institute of Technology" or "Name: XYZ College"
    inst_match = re.search(
        r"(?:In\s+Favor\s+of|Favoring|Account\s+Holder|Depositor|Institution|College|Institute)[\s:.]*([A-Za-z0-9\s,\.\-]{5,80}(?:Institute|College|University|Academy|Trust|Society|Foundation|Technology))",
        raw_text,
        re.IGNORECASE,
    )
    if inst_match:
        extracted["institution_name"] = inst_match.group(1).strip()

    # Calculate Confidence Score & Quality
    total_fields = 6
    found_count = sum(1 for v in extracted.values() if v is not None)
    confidence = found_count / float(total_fields)

    if found_count >= 5:
        confidence_level = "HIGH"
    elif found_count >= 3:
        confidence_level = "MEDIUM"
    elif found_count >= 1:
        confidence_level = "LOW"
    else:
        confidence_level = "FAILED"

    extracted["confidence_score"] = confidence
    extracted["confidence_level"] = confidence_level
    # OCR always requires human validation before making financial decisions
    extracted["review_required"] = True

    return extracted


def compare_extracted_with_fdr(extracted_fields, fdr_record):
    """
    Compare OCR-extracted fields against the corresponding stored FDRRecord
    and Institution details to identify discrepancies.

    Returns:
        tuple: (has_discrepancy: bool, discrepancy_count: int, discrepancy_details: dict)
    """
    discrepancies = {}
    mismatch_count = 0

    # 1. FDR Number Comparison (Normalized)
    extracted_fdr = extracted_fields.get("fdr_number")
    record_fdr = fdr_record.fdr_number
    if not extracted_fdr:
        discrepancies["fdr_number"] = {
            "status": "UNREADABLE",
            "extracted": None,
            "submitted": record_fdr,
            "message": "FDR number could not be read from document.",
            "severity": "HIGH",
        }
        mismatch_count += 1
    elif extracted_fdr.strip().upper() != record_fdr.strip().upper():
        discrepancies["fdr_number"] = {
            "status": "MISMATCH",
            "extracted": extracted_fdr,
            "submitted": record_fdr,
            "message": f"Document FDR number '{extracted_fdr}' does not match submitted number '{record_fdr}'.",
            "severity": "HIGH",
        }
        mismatch_count += 1
    else:
        discrepancies["fdr_number"] = {"status": "MATCH", "extracted": extracted_fdr, "submitted": record_fdr}

    # 2. Issuing Bank Comparison
    extracted_bank = extracted_fields.get("issuing_bank")
    record_bank = fdr_record.issuing_bank
    if not extracted_bank:
        discrepancies["issuing_bank"] = {
            "status": "UNREADABLE",
            "extracted": None,
            "submitted": record_bank,
            "message": "Bank name could not be identified in document.",
            "severity": "HIGH",
        }
        mismatch_count += 1
    else:
        # Flexible substring comparison (e.g. "State Bank of India" vs "SBI" or bank with branch suffix)
        norm_ext = re.sub(r"[^\w]", "", extracted_bank).lower()
        norm_rec = re.sub(r"[^\w]", "", record_bank).lower()
        if norm_ext in norm_rec or norm_rec in norm_ext:
            discrepancies["issuing_bank"] = {"status": "MATCH", "extracted": extracted_bank, "submitted": record_bank}
        else:
            discrepancies["issuing_bank"] = {
                "status": "MISMATCH",
                "extracted": extracted_bank,
                "submitted": record_bank,
                "message": f"Document bank '{extracted_bank}' differs from submitted '{record_bank}'.",
                "severity": "HIGH",
            }
            mismatch_count += 1

    # 3. Deposit Amount Comparison
    extracted_amt = extracted_fields.get("deposit_amount")
    record_amt = fdr_record.deposit_amount
    if extracted_amt is None:
        discrepancies["deposit_amount"] = {
            "status": "UNREADABLE",
            "extracted": None,
            "submitted": float(record_amt) if record_amt else 0.0,
            "message": "Deposit amount could not be read from document.",
            "severity": "HIGH",
        }
        mismatch_count += 1
    else:
        diff = abs(Decimal(str(extracted_amt)) - Decimal(str(record_amt)))
        if diff != Decimal("0.00"):
            discrepancies["deposit_amount"] = {
                "status": "MISMATCH",
                "extracted": float(extracted_amt),
                "submitted": float(record_amt),
                "difference": float(diff),
                "message": f"Amount difference detected: INR {diff:,.2f}",
                "severity": "HIGH",
            }
            mismatch_count += 1
        else:
            discrepancies["deposit_amount"] = {
                "status": "MATCH",
                "extracted": float(extracted_amt),
                "submitted": float(record_amt),
            }

    # 4. Issue Date Comparison
    extracted_issue = extracted_fields.get("issue_date")
    record_issue = fdr_record.issue_date
    if not extracted_issue:
        discrepancies["issue_date"] = {
            "status": "UNREADABLE",
            "extracted": None,
            "submitted": record_issue.isoformat() if record_issue else None,
            "message": "Issue date could not be read from document.",
            "severity": "MEDIUM",
        }
        mismatch_count += 1
    elif extracted_issue != record_issue:
        discrepancies["issue_date"] = {
            "status": "MISMATCH",
            "extracted": extracted_issue.isoformat(),
            "submitted": record_issue.isoformat(),
            "message": f"Issue date mismatch: document shows {extracted_issue.isoformat()}, record shows {record_issue.isoformat()}.",
            "severity": "MEDIUM",
        }
        mismatch_count += 1
    else:
        discrepancies["issue_date"] = {
            "status": "MATCH",
            "extracted": extracted_issue.isoformat(),
            "submitted": record_issue.isoformat(),
        }

    # 5. Maturity Date Comparison
    extracted_maturity = extracted_fields.get("maturity_date")
    record_maturity = fdr_record.maturity_date
    if not extracted_maturity:
        discrepancies["maturity_date"] = {
            "status": "UNREADABLE",
            "extracted": None,
            "submitted": record_maturity.isoformat() if record_maturity else None,
            "message": "Maturity date could not be read from document.",
            "severity": "HIGH",
        }
        mismatch_count += 1
    elif extracted_maturity != record_maturity:
        discrepancies["maturity_date"] = {
            "status": "MISMATCH",
            "extracted": extracted_maturity.isoformat(),
            "submitted": record_maturity.isoformat(),
            "message": f"Maturity date mismatch: document shows {extracted_maturity.isoformat()}, record shows {record_maturity.isoformat()}.",
            "severity": "HIGH",
        }
        mismatch_count += 1
    else:
        discrepancies["maturity_date"] = {
            "status": "MATCH",
            "extracted": extracted_maturity.isoformat(),
            "submitted": record_maturity.isoformat(),
        }

    # 6. Institution Name Comparison
    extracted_inst = extracted_fields.get("institution_name")
    inst_obj = getattr(fdr_record, "institution", None)
    inst_name = inst_obj.name if (inst_obj and hasattr(inst_obj, "name")) else ""
    if not extracted_inst:
        discrepancies["institution_name"] = {
            "status": "UNREADABLE",
            "extracted": None,
            "submitted": inst_name,
            "message": "Institution name could not be identified in document.",
            "severity": "LOW",
        }
    else:
        norm_inst_ext = re.sub(r"[^\w]", "", extracted_inst).lower()
        norm_inst_rec = re.sub(r"[^\w]", "", inst_name).lower()
        if norm_inst_ext in norm_inst_rec or norm_inst_rec in norm_inst_ext:
            discrepancies["institution_name"] = {"status": "MATCH", "extracted": extracted_inst, "submitted": inst_name}
        else:
            discrepancies["institution_name"] = {
                "status": "MISMATCH",
                "extracted": extracted_inst,
                "submitted": inst_name,
                "message": f"Institution name on document differs from registered name.",
                "severity": "MEDIUM",
            }
            mismatch_count += 1

    has_discrepancy = mismatch_count > 0
    return has_discrepancy, mismatch_count, discrepancies
