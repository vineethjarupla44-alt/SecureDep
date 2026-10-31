/**
 * Centralized API Service for AICTE FDR Portal
 * Connects directly to Flask backend endpoints (Phases 1-8)
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE.replace(/\/$/, '');
  }

  getAccessToken() {
    return localStorage.getItem('aicte_access_token');
  }

  getRefreshToken() {
    return localStorage.getItem('aicte_refresh_token');
  }

  setTokens(accessToken, refreshToken) {
    if (accessToken) localStorage.setItem('aicte_access_token', accessToken);
    if (refreshToken) localStorage.setItem('aicte_refresh_token', refreshToken);
  }

  clearTokens() {
    localStorage.removeItem('aicte_access_token');
    localStorage.removeItem('aicte_refresh_token');
    localStorage.removeItem('aicte_user');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    const token = this.getAccessToken();

    const headers = {
      ...(!options.isFormData && { 'Content-Type': 'application/json' }),
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    const config = {
      ...options,
      headers,
    };

    try {
      let response = await fetch(url, config);

      // Handle 401 Unauthorized with token refresh attempt
      if (response.status === 401 && this.getRefreshToken() && !options._retry) {
        options._retry = true;
        const refreshed = await this.refreshToken();
        if (refreshed) {
          headers.Authorization = `Bearer ${this.getAccessToken()}`;
          return await fetch(url, { ...options, headers });
        } else {
          this.clearTokens();
          window.dispatchEvent(new Event('aicte_auth_expired'));
        }
      }

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      let data = null;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else if (response.ok) {
        return response; // E.g., for file download blob
      }

      if (!response.ok) {
        const errorMsg = data?.message || data?.error || `Request failed with status ${response.status}`;
        const err = new Error(errorMsg);
        err.status = response.status;
        err.data = data;
        throw err;
      }

      return data;
    } catch (error) {
      console.error(`API Error on [${options.method || 'GET'} ${endpoint}]:`, error.message);
      throw error;
    }
  }

  async refreshToken() {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) return false;

      const res = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${refreshToken}`,
        },
      });

      if (res.ok) {
        const data = await res.json();
        if (data.access_token) {
          localStorage.setItem('aicte_access_token', data.access_token);
          return true;
        }
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  // =========================================================================
  // Auth APIs (Phase 4)
  // =========================================================================
  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data.access_token) {
      this.setTokens(data.access_token, data.refresh_token);
      if (data.user) localStorage.setItem('aicte_user', JSON.stringify(data.user));
    }
    return data;
  }

  async register(userData) {
    return await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getPublicInstitutions() {
    return await this.request('/institutions/public');
  }

  async getAdminUsers(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/auth/admin/users${query ? `?${query}` : ''}`);
  }

  async updateUserStatus(userId, status, remarks = '') {
    return await this.request(`/auth/admin/users/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, remarks }),
    });
  }

  async getAdminUserDetails(userId) {
    return await this.request(`/auth/admin/users/${userId}`);
  }

  async getCurrentUser() {
    return await this.request('/auth/me');
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (e) {
      // Ignore network failure on logout
    } finally {
      this.clearTokens();
    }
  }

  // =========================================================================
  // FDR APIs (Phase 3 & 4)
  // =========================================================================
  async getFDRs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/fdr${query ? `?${query}` : ''}`);
  }

  async searchFDRs(filters = {}) {
    const query = new URLSearchParams(filters).toString();
    return await this.request(`/fdr/search${query ? `?${query}` : ''}`);
  }

  async getFDRById(id) {
    return await this.request(`/fdr/${id}`);
  }

  async createFDR(fdrData) {
    return await this.request('/fdr', {
      method: 'POST',
      body: JSON.stringify(fdrData),
    });
  }

  async updateFDR(id, updateData) {
    return await this.request(`/fdr/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    });
  }

  // =========================================================================
  // Institutions APIs (Phase 3 & 4)
  // =========================================================================
  async getInstitutions(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/institutions${query ? `?${query}` : ''}`);
  }

  async getInstitutionById(id) {
    return await this.request(`/institutions/${id}`);
  }

  async createInstitution(instData) {
    return await this.request('/institutions', {
      method: 'POST',
      body: JSON.stringify(instData),
    });
  }

  async updateInstitution(id, updateData) {
    return await this.request(`/institutions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    });
  }

  // =========================================================================
  // Documents & OCR APIs (Phase 5)
  // =========================================================================
  async uploadFDRDocument(fdrId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return await this.request(`/fdr/${fdrId}/documents`, {
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  }

  async getFDRDocuments(fdrId) {
    return await this.request(`/fdr/${fdrId}/documents`);
  }

  async getDocumentDetails(docId) {
    return await this.request(`/documents/${docId}`);
  }

  async processDocumentOCR(docId) {
    return await this.request(`/documents/${docId}/process-ocr`, {
      method: 'POST',
    });
  }

  async reviewDocument(docId, decision, remarks) {
    return await this.request(`/documents/${docId}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, remarks }),
    });
  }

  async downloadDocument(docId) {
    const token = this.getAccessToken();
    const url = `${this.baseUrl}/documents/${docId}/download`;
    const res = await fetch(url, {
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });
    if (!res.ok) throw new Error('Failed to download document');
    return await res.blob();
  }

  // =========================================================================
  // Maturity & Alerts APIs (Phase 6)
  // =========================================================================
  async getMaturitySummary(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/maturity/summary${query ? `?${query}` : ''}`);
  }

  async getExpiringFDRs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/maturity/expiring${query ? `?${query}` : ''}`);
  }

  async getPendingRenewals(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/maturity/pending-renewals${query ? `?${query}` : ''}`);
  }

  async triggerMaturityScan() {
    return await this.request('/maturity/trigger-scan', {
      method: 'POST',
    });
  }

  async getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/alerts${query ? `?${query}` : ''}`);
  }

  async acknowledgeAlert(alertId) {
    return await this.request(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
    });
  }

  // =========================================================================
  // Renewal APIs (Phase 6)
  // =========================================================================
  async submitRenewal(fdrId, renewalData) {
    return await this.request(`/fdr/${fdrId}/renew`, {
      method: 'POST',
      body: JSON.stringify(renewalData),
    });
  }

  async getRenewals(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/renewals${query ? `?${query}` : ''}`);
  }

  async getRenewalById(id) {
    return await this.request(`/renewals/${id}`);
  }

  async reviewRenewal(id, decision, remarks) {
    return await this.request(`/renewals/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, remarks }),
    });
  }

  // =========================================================================
  // Release & Refund APIs (Phase 7)
  // =========================================================================
  async submitReleaseRequest(payload) {
    return await this.request('/release-requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getReleaseRequests(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/release-requests${query ? `?${query}` : ''}`);
  }

  async getReleaseRequestById(id) {
    return await this.request(`/release-requests/${id}`);
  }

  async updateReleaseRequest(id, payload) {
    return await this.request(`/release-requests/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  async submitScrutinyAction(id, action, remarks) {
    return await this.request(`/release-requests/${id}/scrutiny`, {
      method: 'POST',
      body: JSON.stringify({ action, remarks }),
    });
  }

  async submitApprovalAction(id, decision, remarks) {
    return await this.request(`/release-requests/${id}/approval`, {
      method: 'POST',
      body: JSON.stringify({ decision, remarks }),
    });
  }

  async closeReleaseRequest(id, closureReference, remarks) {
    return await this.request(`/release-requests/${id}/close`, {
      method: 'POST',
      body: JSON.stringify({ closure_reference: closureReference, remarks }),
    });
  }

  async triggerOverdueReleaseScan(overdueDays = 7) {
    return await this.request('/release-requests/trigger-overdue-scan', {
      method: 'POST',
      body: JSON.stringify({ overdue_days: overdueDays }),
    });
  }

  // =========================================================================
  // Audit Logs API (Phase 7)
  // =========================================================================
  async getAuditLogs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/audit-logs${query ? `?${query}` : ''}`);
  }

  // =========================================================================
  // AI & Machine Learning Intelligence APIs (Phase 8)
  // =========================================================================
  async triggerDuplicateScan() {
    return await this.request('/ai/duplicates/scan', {
      method: 'POST',
    });
  }

  async getDuplicateCandidates(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/ai/duplicates${query ? `?${query}` : ''}`);
  }

  async getDuplicateCandidateById(id) {
    return await this.request(`/ai/duplicates/${id}`);
  }

  async reviewDuplicateCandidate(id, status, remarks) {
    return await this.request(`/ai/duplicates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, remarks }),
    });
  }

  async analyzeFDRAnomalies(fdrId) {
    return await this.request(`/ai/anomalies/${fdrId}`);
  }

  async getFDRRiskScore(fdrId) {
    return await this.request(`/ai/risk-score/${fdrId}`);
  }

  async batchRiskScore(fdrIds = []) {
    return await this.request('/ai/risk-score/batch', {
      method: 'POST',
      body: JSON.stringify({ fdr_ids: fdrIds }),
    });
  }

  async getInstitutionCompliance(institutionId) {
    return await this.request(`/ai/compliance/${institutionId}`);
  }

  async getGlobalComplianceSummary() {
    return await this.request('/ai/compliance/summary');
  }

  async get360Report(fdrId) {
    return await this.request(`/ai/report/${fdrId}`);
  }

  async getModelsHealth() {
    return await this.request('/ai/models/health');
  }

  async trainModel(nSamples = 500) {
    return await this.request('/ai/models/train', {
      method: 'POST',
      body: JSON.stringify({ n_samples: nSamples }),
    });
  }
}

export const api = new ApiService();
export default api;
