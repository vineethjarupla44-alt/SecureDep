# AICTE Security Deposit / FDR Management Portal (SIH 26265)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-lightgrey.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-cyan.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-orange.svg)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20AICTE%20SIH-green.svg)](#)

An enterprise-grade, AI-powered regulatory governance and financial instrument tracking portal developed for the **All India Council for Technical Education (AICTE)** under **Smart India Hackathon (SIH 26265)**.

---

## 🏛️ Project Overview

Technical institutions affiliated with the AICTE maintain Fixed Deposit Receipts (FDRs) as mandatory statutory security deposits. Traditionally, tracking these multi-crore financial instruments across thousands of colleges nationwide suffered from manual oversight, tracking lapses on maturity, fraudulent duplicate submissions, and delays in legitimate release/refund workflows.

**SecureDep** solves this through a centralized, intelligent, multi-tenant portal featuring:
- **Autonomous Maturity Tracking & Automated Alerts**: Calculates remaining validity and flags expiring instruments at 30, 15, and 7 days.
- **AI/ML Duplicate Detection & Anomaly Intelligence**: Detects duplicate deposits using multi-algorithm checks (exact number match, fuzzy Levenshtein distance, cross-institution bank reference matching, and SHA-256 document hash collision).
- **Isolation Forest Risk Scoring**: Machine learning models flag high-risk anomalies, accompanied by multi-factor explainability and regulatory compliance letter grades (A through D).
- **Automated Document OCR & Discrepancy Scrutiny**: Inspects uploaded deposit certificates natively (PDF text streams and optical character recognition) to cross-verify principal amount, maturity dates, and bank names against portal records.
- **Statutory Release & Refund Workflow**: Finite-state machine (FSM) governing scrutiny, deficiency correction, resubmission, and dual-authorization sanctioning with an immutable, tamper-evident audit trail.
- **Institutional Access & Verification Queue**: Public directory selection with administrative account verification for institutional finance desks.

---

## 🏗️ Architecture & Technology Stack

```
SecureDep/
│
├── backend/                       # Flask REST API Backend (Python 3.10+, SQLAlchemy, PyMySQL)
│   ├── app.py                     # Application factory & CORS configuration
│   ├── config.py                  # Environment config & security validation
│   ├── init_db.py                 # Safe database & schema initialization
│   ├── seed_data.py               # Fictional demo institutions & accounts
│   ├── models/                    # SQLAlchemy ORM Models (12 Relational Tables)
│   ├── routes/                    # Blueprints (auth, fdr, docs, maturity, release, ai, institutions)
│   ├── services/                  # Business logic (FDR, OCR, Alerts, Audit, Release)
│   ├── ml/                        # Scikit-Learn IsolationForest, Risk Engine, Model Registry
│   ├── utils/                     # JWT decorators, validators, rate limiters
│   ├── Dockerfile                 # Container image specification for backend
│   └── test_app.py                # 50 Automated backend regression tests
│
├── frontend/                      # React 18 + Vite 5 + Tailwind CSS
│   ├── src/
│   │   ├── pages/                 # Role-based dashboards (Admin, Official, Institution)
│   │   ├── components/            # Reusable UI, AI Radar Gauge, OCR Diff Modals
│   │   ├── context/               # AuthContext with token refresh & persona switcher
│   │   └── services/api.js        # Unified REST API client
│   ├── preview.html               # Zero-setup standalone browser preview
│   ├── serve.js                   # Node.js production server with API reverse proxy
│   └── Dockerfile                 # Container image specification for frontend
│
├── docker-compose.yml             # Single-command full-stack container orchestration
├── test_system_and_security.js    # 113-test master cybersecurity & audit suite
├── test_live_workflow.js          # Live end-to-end HTTP verification script
└── package.json                   # Root orchestrator scripts (npm run dev, npm test)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher
- **MySQL**: 8.0 or higher (or Docker Desktop)

---

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Copy template and update database credentials if needed:
cp .env.example .env

# Initialize MySQL database and seed baseline demo institutions
python init_db.py

# Start Flask backend server (runs on http://127.0.0.1:5000)
python app.py
```

---

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Start frontend application (runs on http://localhost:3000)
node serve.js
# Or for live Vite development:
npm run dev
```

---

### 4. Docker Deployment (Optional - One Command)

```bash
# Start MySQL 8.0, Flask Backend, and React Frontend together:
docker compose up -d --build
```

---

## 🔑 Demonstration & Evaluation Credentials

The portal comes pre-seeded with baseline demonstration personas for rapid regulatory evaluation:

| Role | Email Address | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@aicte-india.org` | `AdminSecure2026!` | Full telemetry, user approval queue, model registry, audit logs |
| **AICTE Regulatory Official** | `regulator@aicte-india.org` | `OfficialSecure2026!` | Scrutiny desk, release request approvals, council-wide FDR search |
| **Institution User (Approved)** | `officer@dit.edu.in` | `DITSecret2026!` | Finance desk for Delhi Institute of Technology (Fictional Demo) |
| **Institution User (Pending)** | `pending.desk@mast.edu.in` | `PendingSecure2026!` | Demonstrates regulatory PENDING account verification barrier |

*Alternatively, use the **One-Click Role Switcher** on the login page or test the zero-install standalone distribution at [`frontend/preview.html`](file:///frontend/preview.html).*

---

## 🧪 Automated Testing & Verification

The project includes an exhaustive, multi-tier test suite:

```bash
# 1. Run Complete Backend Regression Test Suite (50 Tests)
python backend/test_app.py

# 2. Run Institution Registration & Approval Integration Suite (11 Tests)
python backend/test_registration_and_login.py

# 3. Run Master Cybersecurity & System Audit Suite (113 Checks - 100% Pass)
node test_system_and_security.js

# 4. Run Live End-to-End REST API Workflow Test
node test_live_workflow.js
```

---

## 🛡️ Cybersecurity & Hardening Highlights
- **Tenant Isolation**: Strict institution-level row isolation enforced across all database queries.
- **SQL Injection Defense**: 100% parameterized queries via SQLAlchemy ORM.
- **File Upload Security**: Magic-byte signature verification (`%PDF`, `\x89PNG`, `\xff\xd8\xff`), 10 MB limit, and server-side UUID storage names to prevent path traversal.
- **Password Security**: Salted hashes generated via Werkzeug PBKDF2-HMAC-SHA256; password hashes strictly excluded from JSON serialization.
- **JWT Governance**: Access & refresh tokens with database token revocation blocklist (`/api/auth/logout`).
- **HTTP Security Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and strict CORS whitelist.

---

## 📄 License
Developed for the **Smart India Hackathon (SIH 26265)**. All rights reserved by AICTE and development team.
