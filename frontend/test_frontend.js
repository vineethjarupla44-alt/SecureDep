/**
 * Automated Frontend Validation & Integration Test Suite
 * Inspects all components, route declarations, and API integration mappings
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const requiredFiles = [
  'package.json',
  'vite.config.js',
  'tailwind.config.js',
  'postcss.config.js',
  'index.html',
  '.env',
  '.env.example',
  'src/index.css',
  'src/main.jsx',
  'src/App.jsx',
  'src/context/AuthContext.jsx',
  'src/services/api.js',
  'src/utils/formatters.js',
  'src/components/common/Icons.jsx',
  'src/components/common/Badge.jsx',
  'src/components/common/Card.jsx',
  'src/components/common/Modal.jsx',
  'src/components/common/LoadingSpinner.jsx',
  'src/components/common/EmptyState.jsx',
  'src/components/common/Pagination.jsx',
  'src/components/layout/Navbar.jsx',
  'src/components/layout/Sidebar.jsx',
  'src/components/layout/Layout.jsx',
  'src/components/ai/RiskRadarGauge.jsx',
  'src/components/ai/DuplicateComparisonModal.jsx',
  'src/components/ai/ComplianceGradeBadge.jsx',
  'src/components/fdr/FDRFormModal.jsx',
  'src/components/documents/DocumentUploadModal.jsx',
  'src/components/documents/OCRComparisonModal.jsx',
  'src/pages/Login.jsx',
  'src/pages/Register.jsx',
  'src/pages/AdminDashboard.jsx',
  'src/pages/InstitutionDashboard.jsx',
  'src/pages/OfficialDashboard.jsx',
  'src/pages/FDRManagementPage.jsx',
  'src/pages/DocumentManagementPage.jsx',
  'src/pages/MaturityCalendarPage.jsx',
  'src/pages/ReleaseRefundPage.jsx',
  'src/pages/AIIntelligencePage.jsx',
  'src/pages/AuditTrailPage.jsx',
  'src/pages/NotFound.jsx',
];

const requiredApiEndpoints = [
  '/auth/login',
  '/auth/register',
  '/auth/me',
  '/auth/refresh',
  '/auth/logout',
  '/fdr',
  '/fdr/search',
  '/institutions',
  '/documents',
  '/process-ocr',
  '/maturity/summary',
  '/maturity/expiring',
  '/maturity/trigger-scan',
  '/alerts',
  '/renew',
  '/renewals',
  '/release-requests',
  '/scrutiny',
  '/approval',
  '/close',
  '/audit-logs',
  '/ai/duplicates',
  '/ai/anomalies',
  '/ai/risk-score',
  '/ai/compliance',
  '/ai/report',
  '/ai/models/health',
  '/ai/models/train',
];

console.log('======================================================================');
console.log('AICTE FDR PORTAL - FRONTEND COMPONENT & INTEGRATION TEST');
console.log('======================================================================');

let passedTests = 0;
let totalTests = 0;

function assert(condition, message) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`[PASS] ${message}`);
  } else {
    console.error(`[FAIL] ${message}`);
  }
}

// Test 1: Check File Existence
console.log('\n--- 1. File & Component Structure Verification ---');
requiredFiles.forEach((file) => {
  const filePath = path.join(__dirname, file);
  assert(fs.existsSync(filePath), `Required file exists: ${file}`);
});

// Test 2: Check API Service Route Coverage
console.log('\n--- 2. Flask API Integration Coverage in api.js ---');
const apiCode = fs.readFileSync(path.join(__dirname, 'src/services/api.js'), 'utf8');
requiredApiEndpoints.forEach((endpoint) => {
  assert(apiCode.includes(endpoint), `API service maps backend endpoint: ${endpoint}`);
});

// Test 3: Check Vite & Tailwind Configuration
console.log('\n--- 3. Build & Tooling Configuration Verification ---');
const viteCode = fs.readFileSync(path.join(__dirname, 'vite.config.js'), 'utf8');
assert(viteCode.includes('port: 3000'), 'Vite configured to port 3000 matching CORS origins');
assert(viteCode.includes("target: 'http://127.0.0.1:5000'"), 'Vite proxy targets Flask backend at 127.0.0.1:5000');

const tailwindCode = fs.readFileSync(path.join(__dirname, 'tailwind.config.js'), 'utf8');
assert(tailwindCode.includes('./src/**/*.{js,ts,jsx,tsx}'), 'Tailwind content covers all src component files');
assert(tailwindCode.includes('#0B2545'), 'Tailwind extends official AICTE navy primary color');

// Test 4: Check App.jsx Route Coverage
console.log('\n--- 4. App.jsx Role-Based Protected Routes ---');
const appCode = fs.readFileSync(path.join(__dirname, 'src/App.jsx'), 'utf8');
assert(appCode.includes('path="/admin"'), 'App registers /admin protected route');
assert(appCode.includes('path="/official"'), 'App registers /official protected route');
assert(appCode.includes('path="/institution"'), 'App registers /institution protected route');
assert(appCode.includes('path="/fdr"'), 'App registers /fdr route');
assert(appCode.includes('path="/documents"'), 'App registers /documents route');
assert(appCode.includes('path="/maturity"'), 'App registers /maturity route');
assert(appCode.includes('path="/release-refund"'), 'App registers /release-refund route');
assert(appCode.includes('path="/ai-intelligence"'), 'App registers /ai-intelligence route');
assert(appCode.includes('path="/audit-trail"'), 'App registers /audit-trail route');

// Test 5: Check Role Constants and Auth Flow
console.log('\n--- 5. Auth Context & RBAC Consistency ---');
const authCode = fs.readFileSync(path.join(__dirname, 'src/context/AuthContext.jsx'), 'utf8');
assert(authCode.includes('administrator'), 'AuthContext handles administrator role');
assert(authCode.includes('aicte_official'), 'AuthContext handles aicte_official role');
assert(authCode.includes('institution_user'), 'AuthContext handles institution_user role');
assert(authCode.includes('switchDemoPersona'), 'AuthContext provides persona switcher for evaluation');

console.log('\n======================================================================');
console.log(`TEST SUMMARY: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests/totalTests)*100)}%)`);
console.log('======================================================================');

if (passedTests === totalTests) {
  console.log('ALL FRONTEND INTEGRATION & ARCHITECTURE TESTS PASSED SUCCESSFULLY.\n');
} else {
  console.error('SOME FRONTEND TESTS FAILED.\n');
  process.exit(1);
}
