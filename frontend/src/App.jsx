import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/layout/Layout';
import LoadingSpinner from './components/common/LoadingSpinner';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import AdminDashboard from './pages/AdminDashboard';
import OfficialDashboard from './pages/OfficialDashboard';
import InstitutionDashboard from './pages/InstitutionDashboard';
import FDRManagementPage from './pages/FDRManagementPage';
import DocumentManagementPage from './pages/DocumentManagementPage';
import MaturityCalendarPage from './pages/MaturityCalendarPage';
import ReleaseRefundPage from './pages/ReleaseRefundPage';
import AIIntelligencePage from './pages/AIIntelligencePage';
import AuditTrailPage from './pages/AuditTrailPage';
import NotFound from './pages/NotFound';

// Protected Route Guard
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, loading, role } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingSpinner message="Verifying security credentials &amp; permissions..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    // If unauthorized for specific dashboard, redirect to their home
    if (role === 'administrator') return <Navigate to="/admin" replace />;
    if (role === 'aicte_official') return <Navigate to="/official" replace />;
    return <Navigate to="/institution" replace />;
  }

  return <Layout>{children}</Layout>;
};

// Role-based Root Redirector
const RootRedirect = () => {
  const { isAuthenticated, role, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingSpinner message="Loading user dashboard..." />
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (role === 'administrator') return <Navigate to="/admin" replace />;
  if (role === 'aicte_official') return <Navigate to="/official" replace />;
  return <Navigate to="/institution" replace />;
};

export const App = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Root Redirect */}
          <Route path="/" element={<RootRedirect />} />

          {/* Role-Specific Dashboards */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['administrator']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/official"
            element={
              <ProtectedRoute allowedRoles={['aicte_official', 'administrator']}>
                <OfficialDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/institution"
            element={
              <ProtectedRoute allowedRoles={['institution_user', 'administrator', 'aicte_official']}>
                <InstitutionDashboard />
              </ProtectedRoute>
            }
          />

          {/* Core Functional Modules (All Authenticated) */}
          <Route
            path="/fdr"
            element={
              <ProtectedRoute>
                <FDRManagementPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/documents"
            element={
              <ProtectedRoute>
                <DocumentManagementPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/maturity"
            element={
              <ProtectedRoute>
                <MaturityCalendarPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/release-refund"
            element={
              <ProtectedRoute>
                <ReleaseRefundPage />
              </ProtectedRoute>
            }
          />

          {/* AI Intelligence & Audit Trail */}
          <Route
            path="/ai-intelligence"
            element={
              <ProtectedRoute>
                <AIIntelligencePage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/audit-trail"
            element={
              <ProtectedRoute>
                <AuditTrailPage />
              </ProtectedRoute>
            }
          />

          {/* 404 Catch-All */}
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <NotFound />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
