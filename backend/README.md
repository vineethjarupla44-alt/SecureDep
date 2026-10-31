# AICTE FDR Management Portal - Backend

AI-powered Security Deposit / Fixed Deposit Receipt (FDR) Management Portal for AICTE.

---

## Current Status: Phase 9 — Complete Frontend Development and Full-Stack Integration

This phase implements a modern, enterprise-grade Government of India portal interface for AICTE: role-based dashboards for System Administrators, AICTE/Regulation Bureau Officials, and Institution Finance Desks; comprehensive FDR instrument management; secure document upload & local OCR discrepancy inspection; interactive maturity calendar; statutory release & refund workflow; visual Phase 8 AI/ML intelligence dashboard (interactive Risk Radar Gauge, side-by-side duplicate comparison diff modal, institutional compliance grading A–D, 360° AI dossier); immutable audit trail querying; and zero-setup standalone browser execution.

### Full-Stack Technology Stack
- **Frontend**: React 18, Vite 5, Tailwind CSS, React Router v6, SVG Data Visualizations
- **Backend**: Python 3.x, Flask Application Factory, Flask-CORS, python-dotenv
- **Security & Auth**: Flask-JWT-Extended, PBKDF2-HMAC-SHA256 password hashing, token blocklist
- **Database**: MySQL, SQLAlchemy ORM, PyMySQL driver
- **Machine Learning**: Scikit-learn (IsolationForest), NumPy, Joblib model registry
- **Document & OCR**: PyPDF native text extraction, Pillow, pytesseract engine

---

## Project Structure

```text
SecureDep/
│
├── frontend/                   # Phase 9 React + Vite + Tailwind CSS Application
│   ├── index.html              # HTML5 entry with Government of India metadata
│   ├── preview.html            # Standalone browser distribution (zero-install run)
│   ├── package.json            # Frontend dependencies & npm test scripts
│   ├── vite.config.js          # Port 3000 config & proxy to 127.0.0.1:5000
│   ├── tailwind.config.js      # Official AICTE navy/teal government palette
│   ├── postcss.config.js       # PostCSS styling pipeline
│   ├── test_frontend.js        # Automated 86-test frontend integration suite
│   ├── .env                    # Local environment config (VITE_API_BASE_URL)
│   ├── .env.example            # Environment template
│   └── src/
│       ├── main.jsx            # React root mount
│       ├── App.jsx             # React Router v6 role-protected routes
│       ├── index.css           # Tailwind directives & government background
│       ├── context/
│       │   └── AuthContext.jsx # JWT session, role guards, evaluation persona switcher
│       ├── services/
│       │   └── api.js          # Centralized API service for all Flask endpoints
│       ├── utils/
│       │   └── formatters.js   # INR currency formatters, date formatters, badges
│       ├── components/
│       │   ├── common/         # Icons, Badge, Card, Modal, Spinner, EmptyState, Pagination
│       │   ├── layout/         # Navbar, Sidebar, Responsive Layout shell
│       │   ├── ai/             # RiskRadarGauge, DuplicateComparisonModal, ComplianceGradeBadge
│       │   ├── fdr/            # FDRFormModal, FDRDetailDrawer
│       │   └── documents/      # DocumentUploadModal, OCRComparisonModal
│       └── pages/
│           ├── Login.jsx       # Portal authentication with one-click test personas
│           ├── Register.jsx    # Public institution onboarding
│           ├── AdminDashboard.jsx       # Council-wide executive statistics & actions
│           ├── OfficialDashboard.jsx    # Regulatory & finance scrutiny queue
│           ├── InstitutionDashboard.jsx # College desk, active FDRs & compliance grade
│           ├── FDRManagementPage.jsx    # Search, filters, pagination, create modal
│           ├── DocumentManagementPage.jsx # Secure files, SHA-256 hashes, OCR audit
│           ├── MaturityCalendarPage.jsx # 30d/15d/7d reminder horizons & renewal proposals
│           ├── ReleaseRefundPage.jsx    # 5-stage approval FSM & settlement
│           ├── AIIntelligencePage.jsx   # Phase 8 AI/ML intelligence & 360° dossier
│           ├── AuditTrailPage.jsx       # Immutable audit logs & pre/post JSON state diffs
│           └── NotFound.jsx             # 404 handler
│
└── backend/                    # Flask Backend & Database (Phases 1-8)
    ├── app.py                  # Application factory, JWT config, CORS, route catalog
    ├── config.py               # Environment config (ports, CORS origins, secrets)
    ├── init_db.py              # Database verification script (12 tables)
    ├── test_app.py             # 55-test master automated backend test suite
    ├── api_tests.http          # 58-request HTTP collection (Thunder Client / REST Client)
    ├── requirements.txt        # Backend dependencies
    ├── models/                 # 11 SQLAlchemy models (FDR, User, Document, Release, AI)
    ├── routes/                 # Modular Flask blueprints (/auth, /fdr, /ai, etc.)
    ├── services/               # OCR, audit, alert, and maturity services
    └── ml/                     # ML preprocessing, duplicate, anomaly, risk, compliance
│
└── README.md           # Documentation and beginner setup instructions
```

---

## Secure Document Upload Architecture

1. **Format Validation**:
   - Accepts `.pdf`, `.jpg`, `.jpeg`, `.png`.
   - Rejects disallowed extensions (`.exe`, `.sh`, `.txt`).
2. **File Signature (Magic Bytes) Verification**:
   - PDF: Must start with `%PDF` (`b"%PDF"`).
   - PNG: Must start with `b"\x89PNG\r\n\x1a\n"`.
   - JPEG: Must start with `b"\xff\xd8\xff"`.
   - Prevents extension spoofing (e.g. an executable renamed to `.pdf`).
3. **Size Limitation**:
   - Enforces a strict 10 MB limit (`MAX_DOCUMENT_SIZE = 10485760`).
4. **Server-Side Random Storage Key**:
   - Client filenames are never used for disk storage to prevent path traversal attacks.
   - Files are stored using random UUIDs (`e.g., 9a4e7f8b1c2d3e4f.pdf`) in a private storage directory outside the web root.
5. **Integrity & Tamper Detection**:
   - Automatically computes a SHA-256 checksum of every uploaded file for tamper auditing.
6. **Multi-Tenant Authorization**:
   - Institution users can only upload, list, and download documents for FDRs belonging to their assigned institution.

---

## OCR Extraction & Discrepancy Detection Engine

1. **Local Processing**:
   - Processes documents 100% locally. No financial documents or data are ever transmitted to third-party AI APIs.
2. **Dual-Extraction Pipeline**:
   - **Text-based PDFs**: Processed directly via `pypdf` native extraction (requires no OCR engine and operates with 100% text fidelity).
   - **Scanned PDFs & Images (PNG/JPG)**: Processed via local Tesseract OCR engine.
3. **Extracted Fields**:
   - FDR Certificate Number
   - Issuing Scheduled Bank Name
   - Deposit Amount in INR (normalized to `Decimal`)
   - Issue Date (normalized to `YYYY-MM-DD`)
   - Maturity Date (normalized to `YYYY-MM-DD`)
   - Depositor / Institution Name
4. **Automated Discrepancy Detection**:
   - Compares extracted values against the institution-submitted `FDRRecord` and `Institution`.
   - Flags:
     - `MISMATCH`: Field differs between document and record (with calculated monetary differences).
     - `UNREADABLE`: Field could not be extracted with confidence.
     - `MATCH`: Field matches the official record.
5. **Human Review Governance**:
   - OCR results are categorized as advisory signals and **never automatically approve, release, or refund an FDR**.
   - Only authorized reviewers (`aicte_official` or `administrator`) can approve or reject documents via `POST /api/documents/<id>/review`.

---

## Tesseract OCR Installation Guide for Windows

If you plan to process scanned images locally:

1. Download the Windows installer from the official UB-Mannheim repository:
   [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer (default directory is `C:\Program Files\Tesseract-OCR\`).
3. Ensure `tesseract.exe` is added to your Windows PATH, or verify the path in your `.env` file:
   ```env
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
*(Note: Text-based PDFs process automatically via native parsing even if Tesseract is not installed).*

---

## Document & OCR API Endpoints (Phase 5)

| Method | Endpoint | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/fdr/<fdr_id>/documents` | `institution_user` / `admin` | Securely upload an FDR supporting document (PDF/PNG/JPG). |
| `GET` | `/api/fdr/<fdr_id>/documents` | `institution_user` / `admin` | List all documents attached to an FDR record. |
| `GET` | `/api/documents/<doc_id>` | `institution_user` / `admin` | Retrieve document metadata and full OCR discrepancy report. |
| `GET` | `/api/documents/<doc_id>/download` | `institution_user` / `admin` | Securely download or view the document file. |
| `POST` | `/api/documents/<doc_id>/process-ocr` | `institution_user` / `admin` | Trigger or re-run OCR extraction and discrepancy detection. |
| `POST` | `/api/documents/<doc_id>/review` | `aicte_official` / `admin` | **Reviewer Action**: Record review decision (`ACCEPTED`, `REJECTED`) and notes. |

---

## Maturity, Alerts & Renewal API Endpoints (Phase 6)

| Method | Endpoint | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/maturity/summary` | Authenticated | Aggregated maturity statistics and financial sums (institution-scoped or global). |
| `GET` | `/api/maturity/expiring` | Authenticated | Filtered, paginated list of expiring/matured FDRs with urgency categories. |
| `GET` | `/api/maturity/pending-renewals` | Authenticated | List FDR instruments with unresolved renewal workflows. |
| `POST` | `/api/maturity/trigger-scan` | `aicte_official` / `admin` | Trigger background maturity scan job (idempotent; safe for cron/scheduled tasks). |
| `GET` | `/api/alerts` | Authenticated | List in-portal notifications (filtered by `is_acknowledged`, `type`). |
| `POST` | `/api/alerts/<id>/acknowledge` | Authenticated | Acknowledge an active notification (institution-isolated). |
| `POST` | `/api/fdr/<id>/renew` | `institution_user` / `admin` | Submit renewal proposal with replacement FDR linked to predecessor. |
| `GET` | `/api/renewals` | Authenticated | List renewal workflow proposals (tenant-isolated). |
| `GET` | `/api/renewals/<id>` | Authenticated | Retrieve renewal details, linking data, and submission notes. |
| `POST` | `/api/renewals/<id>/review` | `aicte_official` / `admin` | **Reviewer Action**: Approve or reject renewal with lifecycle transition & audit log. |

---

## Phase 6 Architecture Principles

1. **Strict Lifecycle vs. Workflow Separation**:
   - **Lifecycle Status** (`status`): `ACTIVE`, `MATURED`, `RELEASED`, `LIEN_MARKED`, `RENEWED`.
   - **Workflow Status** (`workflow_status`): `NONE`, `RENEWAL_SUBMITTED`, `RENEWAL_APPROVED`, `RENEWAL_REJECTED`.
   - Maturing instruments are never prematurely liquidated, released, or marked legally non-compliant without human audit.
2. **Deterministic Idempotency**:
   - Alert keys follow the format: `fdr_{id}_{alert_type}_{maturity_date}`.
   - Prevents duplicate alerts if background scans are run multiple times or across multi-worker instances.
3. **Predecessor-to-Successor Lineage**:
   - When an FDR renewal proposal is approved, the original FDR transitions to `RENEWED` (archived), the replacement transitions to `ACTIVE`, and the predecessor-successor relationship is preserved via `predecessor_id`.
4. **Immutable Audit Trail**:
   - Every renewal submission and reviewer decision is logged with user ID, timestamp, decision, and IP address in `fdr_audit_logs`.

---

## Release, Refund & Audit API Endpoints (Phase 7)

| Method | Endpoint | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/release-requests` | `institution_user` / `admin` | Submit a new FDR deposit release or refund request with defaults. |
| `GET` | `/api/release-requests` | Authenticated | List release requests with pagination & status filters (tenant isolated). |
| `GET` | `/api/release-requests/<id>` | Authenticated | Retrieve release request details and multi-level audit history. |
| `PATCH` | `/api/release-requests/<id>` | `institution_user` / `admin` | Update request or resubmit when in `CORRECTION_REQUIRED`. |
| `POST` | `/api/release-requests/<id>/scrutiny` | `aicte_official` / `admin` | **Scrutiny Action**: Start review, request correction, recommend, or reject. |
| `POST` | `/api/release-requests/<id>/approval` | `administrator` | **Final Decision**: Sanction approval or rejection (self-approval blocked). |
| `POST` | `/api/release-requests/<id>/close` | `aicte_official` / `admin` | **Closure**: Finalize release, transition FDR to `RELEASED`, record disclaimer. |
| `POST` | `/api/release-requests/trigger-overdue-scan` | `aicte_official` / `admin` | Trigger scan for requests exceeding turnaround SLAs (idempotent). |
| `GET` | `/api/audit-logs` | Authenticated | Query immutable audit logs with entity, action, and date filters. |

---

## Phase 7 Architecture Principles

1. **Strict Finite State Machine (FSM)**:
   - Valid status flow: `PENDING_SCRUTINY` -> `UNDER_REVIEW` -> `CORRECTION_REQUIRED` -> `RESUBMITTED` -> `RECOMMENDED_FOR_APPROVAL` -> `APPROVED` -> `RELEASED_CLOSED`.
   - `REJECTED` and `RELEASED_CLOSED` are strictly terminal states.
   - Any attempt to bypass or jump steps is rejected with `409 Conflict`.
2. **Multi-Level Approval & Conflict of Interest Controls**:
   - Official scrutiny and recommendations (`RECOMMENDED_FOR_APPROVAL`) must precede final approval (`APPROVED`).
   - Final approval requires the `administrator` role.
   - Self-approval is strictly prevented (`requested_by_id != current_user.id`).
3. **Immutable Advanced Audit Trail**:
   - Logs actor ID, actor role, entity type, entity ID, previous JSON state, new JSON state, remarks, and IP address.
   - Strictly read-only via `GET /api/audit-logs`: no update or delete routes exist.
4. **Physical Financial Disclaimer**:
   - Marking a request `RELEASED_CLOSED` transitions the database record `FDRRecord.status` to `RELEASED`.
   - All audit records and responses explicitly log that banking disbursement proceeds through statutory institutional finance channels outside the system, with zero claims of automatic bank wire transfer.

---

---

## Advanced AI & Machine Learning Intelligence (Phase 8)

### 1. Intelligent Duplicate FDR Detection Engine
Detects:
- **Exact Matches**: Identical FDR number or normalized alphanumeric string (punctuation/whitespace stripped).
- **Fuzzy Matches**: Levenshtein edit distance similarity ratio ($\ge 0.85$) capturing minor typographical or OCR errors.
- **Cross-Institution Duplicate Submissions**: Same bank FDR number or receipt certificate submitted by different institutions.
- **Document Hash Collision**: Exact cryptographic SHA-256 file collision across uploaded receipts.
- **Review Lifecycle**: Flagged pairs create `FDRDuplicateCandidate` records (`UNREVIEWED`, `CONFIRMED_DUPLICATE`, `FALSE_POSITIVE`, `RESOLVED`). Only officials can review; inst users cannot review.

### 2. Isolation Forest Anomaly Detection & Statistical Explainability
- **Multidimensional Feature Extraction**: 8 numerical features extracted per instrument (log deposit amount, tenor days, days to maturity, renewal count, OCR confidence, OCR discrepancy count, document count, discrepancy flag).
- **Dual Mode Operation**:
  - Automatically loads and runs Scikit-learn's `IsolationForest` when installed and sample size is sufficient ($N \ge 10$).
  - Gracefully falls back to robust Z-score/IQR statistical benchmark analysis when scikit-learn is absent or datasets are small.
- **Feature Attribution & Explainability**: Every flagged anomaly reports the specific deviating features with benchmark averages, z-scores, and human-readable explanations.
- **Strict Governance**: Outliers are flagged as statistical deviations, **never labeled as confirmed fraud**.

### 3. Multi-Factor Explainable Composite Risk Scoring (0–100)
- Separates deterministic rule-based compliance factors (70%) and ML anomaly signals (30%):
  - Duplicate indicators (up to 25 pts)
  - OCR discrepancies & verification mismatches (up to 25 pts)
  - Missing documents (up to 15 pts)
  - Abnormal financial values (up to 15 pts)
  - Maturity urgency & overdue status (up to 10 pts)
  - Prior rejected workflows (up to 10 pts)
- **Bounded Categories**:
  - `0.0 - 29.9`: **LOW** (Standard automated monitoring)
  - `30.0 - 59.9`: **MEDIUM** (Standard official scrutiny during routine audits)
  - `60.0 - 79.9`: **HIGH** (Priority scrutiny; bank certificate re-verification recommended)
  - `80.0 - 100.0`: **CRITICAL** (Immediate regulatory audit; locks automatic administrative actions)

### 4. Predictive Institutional Compliance Intelligence
- Computes Council compliance index ($0 - 100$) and assigns regulatory letter grades:
  - **Grade A** ($\ge 90$): Exemplary compliance.
  - **Grade B** ($75 - 89.9$): Good standing, minor administrative actions pending.
  - **Grade C** ($60 - 74.9$): Attention required, active overdue instruments or OCR discrepancies.
  - **Grade D** ($< 60$): Critical regulatory intervention, unresolved matured instruments or confirmed duplicates.
- Generates actionable warning indicators and regulatory remediation recommendations.

### 5. 360-Degree Comprehensive AI Dossier
Aggregates all instrument intelligence into a single JSON dossier:
- Instrument metadata and lifecycle state
- Institutional profile and code
- Explainable composite risk score and factor weights
- Anomaly analysis metrics and feature deviations
- Duplicate candidates and matching fields
- Document coverage and OCR discrepancy audits
- Clear regulatory disclaimer

---

## AI & Machine Learning API Endpoints (Phase 8)

| Method | Endpoint | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/ai/duplicates/scan` | `aicte_official` / `admin` | Trigger full automated duplicate FDR detection scan. |
| `GET` | `/api/ai/duplicates` | Authenticated | List duplicate candidates (tenant-isolated for institutions). |
| `GET` | `/api/ai/duplicates/<id>` | Authenticated | Retrieve duplicate candidate details and similarity scores. |
| `PATCH` | `/api/ai/duplicates/<id>` | `aicte_official` / `admin` | **Review Action**: Confirm duplicate or mark false positive with audit. |
| `GET` | `/api/ai/anomalies/<fdr_id>` | Authenticated | Isolation Forest and statistical anomaly analysis (tenant isolated). |
| `GET` | `/api/ai/risk-score/<fdr_id>` | Authenticated | Compute explainable multi-factor risk score (0–100) & save assessment. |
| `POST` | `/api/ai/risk-score/batch` | `aicte_official` / `admin` | Batch evaluate risk scores across FDR portfolio. |
| `GET` | `/api/ai/compliance/<inst_id>` | Authenticated | Institutional compliance profile and regulatory grade (tenant isolated). |
| `GET` | `/api/ai/compliance/summary` | `aicte_official` / `admin` | Council-wide institutional compliance distribution summary. |
| `GET` | `/api/ai/report/<fdr_id>` | Authenticated | 360-degree comprehensive AI intelligence dossier. |
| `GET` | `/api/ai/models/health` | Authenticated | Model versioning (`v1.0.0`), health, and registry status. |
| `POST` | `/api/ai/models/train` | `administrator` | Retrain baseline model on synthetic benchmark dataset (admin only). |

---

## Phase 8 AI Governance & Ethical Guardrails

1. **Advisory Signals Only**:
   - AI outputs are decision-support recommendations for human regulators.
   - The AI engine **never automatically approves, rejects, releases, or refunds an FDR**.
2. **Defensive Labeling**:
   - Outliers are labeled as "statistical anomalies" or "deviating distributions", **never as confirmed fraud**.
3. **No External Data Leakage**:
   - All AI models run 100% locally on the backend server.
   - Financial deposit numbers, amounts, and institutional records are never sent to external proprietary AI APIs.
4. **Transparent Fallback**:
   - If scikit-learn or joblib are absent or datasets are small, the system uses robust mathematical Z-score/IQR statistical benchmarks without crashing or reporting fabricated model metrics.

---

## Running the Full-Stack Application & Automated Test Suites

### 1. Frontend Test Suite (86 Tests Passing)
Run the automated frontend component and integration test suite:
```powershell
node "c:\Users\sonal\OneDrive\Desktop\SecureDep\frontend\test_frontend.js"
```
**Result:**
```text
======================================================================
TEST SUMMARY: 86 / 86 tests passed (100%)
======================================================================
ALL FRONTEND INTEGRATION & ARCHITECTURE TESTS PASSED SUCCESSFULLY.
```

### 2. Launching the Frontend Application
- **Option A (Vite Dev Server)**:
  ```powershell
  cd "c:\Users\sonal\OneDrive\Desktop\SecureDep\frontend"
  npm install
  npm run dev
  ```
  Opens at `http://127.0.0.1:3000` with automatic `/api` proxying to `http://127.0.0.1:5000`.

- **Option B (Instant Browser Preview - Zero Installation)**:
  Double-click or open `frontend/preview.html` directly in any web browser. Provides full interactive access to all dashboards, the AI Risk Radar gauge, duplicate diff inspector, and persona switcher.

### 3. Backend Regression Test Suite (55 Tests Passing)
```powershell
cd "c:\Users\sonal\OneDrive\Desktop\SecureDep\backend"
python test_app.py
```
**Expected Result:**
```text
Ran 55 tests in 0.950s
OK
```

---

## Local Application URLs
- **Frontend Portal**: `http://127.0.0.1:3000` (or `frontend/preview.html`)
- **Backend API Base**: `http://127.0.0.1:5000/api`
- **Health Check**: `http://127.0.0.1:5000/api/health`
- **AI Models Health**: `http://127.0.0.1:5000/api/ai/models/health`

---

## Strict Limitations Maintained (Phase 9)
- ❌ No automated bank disbursement or external payment gateway integration (deposit release is an administrative approval workflow).
- ❌ External SMTP email dispatch is disabled by default (`MAIL_ENABLED=False`) to avoid accidental email sending during development/testing.
- ❌ AI recommendations are advisory and require human administrative sign-off.
- ❌ STOP at Phase 9 frontend development and full-stack integration; do not implement Phase 10 or cloud hosting deployment yet.
