import React, { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import Modal from '../components/common/Modal';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const ReleaseRefundPage = () => {
  const { user, isOfficial, isAdmin, isInstitutionUser } = useAuth();

  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);

  // Submit Modal State
  const [isSubmitOpen, setIsSubmitOpen] = useState(false);
  const [submitForm, setSubmitForm] = useState({
    institution_id: user?.institution_id || 1,
    fdr_record_id: '',
    request_type: 'RELEASE',
    reason: '',
    requested_amount: '',
  });
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // Action Modals State
  const [actionType, setActionType] = useState(null); // 'scrutiny', 'approval', 'close'
  const [actionForm, setActionForm] = useState({ decision: '', remarks: '', closure_ref: '' });
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const res = await api.getReleaseRequests({ per_page: 50 });
      setRequests(res.data || []);
    } catch (err) {
      console.error('Failed to load release requests:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleOpenSubmit = async () => {
    setIsSubmitOpen(true);
    setSubmitError(null);
  };

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    setSubmitLoading(true);
    setSubmitError(null);
    try {
      await api.submitReleaseRequest({
        ...submitForm,
        fdr_record_id: parseInt(submitForm.fdr_record_id),
        requested_amount: parseFloat(submitForm.requested_amount),
        institution_id: parseInt(submitForm.institution_id),
      });
      setIsSubmitOpen(false);
      fetchRequests();
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit release request');
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleExecuteAction = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setActionError(null);
    try {
      if (actionType === 'scrutiny') {
        await api.submitScrutinyAction(selectedRequest.id, actionForm.decision, actionForm.remarks);
      } else if (actionType === 'approval') {
        await api.submitApprovalAction(selectedRequest.id, actionForm.decision, actionForm.remarks);
      } else if (actionType === 'close') {
        await api.closeReleaseRequest(selectedRequest.id, actionForm.closure_ref, actionForm.remarks);
      }
      setSelectedRequest(null);
      setActionType(null);
      fetchRequests();
    } catch (err) {
      setActionError(err.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="arrowRightCircle" className="w-6 h-6 text-aicte-navy" />
            Security Deposit Release &amp; Refund Management (Phase 7)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Finite state machine, multi-level scrutiny, self-approval prevention, and statutory settlement
          </p>
        </div>

        <button
          onClick={handleOpenSubmit}
          className="inline-flex items-center gap-2 px-4 py-2 bg-aicte-navy text-white text-xs font-bold rounded-xl hover:bg-aicte-dark transition shadow-sm"
        >
          <Icon name="plus" className="w-4 h-4 text-aicte-teal" />
          Apply for Release / Refund
        </button>
      </div>

      {/* Finite State Machine Flow Indicator */}
      <div className="p-4 rounded-xl bg-white border border-slate-200">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
          Statutory Multi-Level Approval Pipeline
        </span>
        <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-slate-700">
          <span className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200">
            1. PENDING SCRUTINY
          </span>
          <Icon name="chevronRight" className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-800 border border-blue-200">
            2. UNDER OFFICIAL REVIEW
          </span>
          <Icon name="chevronRight" className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-800 border border-indigo-200">
            3. RECOMMENDED
          </span>
          <Icon name="chevronRight" className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
            4. ADMIN APPROVED
          </span>
          <Icon name="chevronRight" className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-2.5 py-1 rounded-lg bg-teal-50 text-teal-800 border border-teal-200">
            5. RELEASED CLOSED
          </span>
        </div>
      </div>

      {/* Requests Table */}
      <Card noPadding title="Formal Security Deposit Release Applications">
        {loading ? (
          <LoadingSpinner message="Querying multi-level approval states..." />
        ) : requests.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Request Number</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">FDR Principal</th>
                  <th className="py-3 px-4">Submitted (IST)</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Workflow Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {requests.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">{req.request_number}</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {req.institution?.name || `Institution #${req.institution_id}`}
                    </td>
                    <td className="py-3 px-4 font-semibold text-blue-700">{req.request_type}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(req.requested_amount)}</td>
                    <td className="py-3 px-4 text-slate-500">{formatDateTime(req.created_at)}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge status={req.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Scrutiny Action for Official/Admin */}
                        {isOfficial && ['PENDING_SCRUTINY', 'UNDER_REVIEW', 'RESUBMITTED'].includes(req.status) && (
                          <button
                            onClick={() => {
                              setSelectedRequest(req);
                              setActionType('scrutiny');
                              setActionForm({ decision: 'RECOMMEND_APPROVAL', remarks: '' });
                            }}
                            className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-800 hover:bg-blue-100 font-semibold text-[11px]"
                          >
                            Scrutinize
                          </button>
                        )}

                        {/* Admin Approval Action (Admin only) */}
                        {isAdmin && req.status === 'RECOMMENDED_FOR_APPROVAL' && (
                          <button
                            onClick={() => {
                              setSelectedRequest(req);
                              setActionType('approval');
                              setActionForm({ decision: 'APPROVE', remarks: '' });
                            }}
                            className="px-2.5 py-1 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-semibold text-[11px] shadow-xs"
                          >
                            Sanction Approval
                          </button>
                        )}

                        {/* Closure Action */}
                        {isOfficial && req.status === 'APPROVED' && (
                          <button
                            onClick={() => {
                              setSelectedRequest(req);
                              setActionType('close');
                              setActionForm({ closure_ref: `AICTE-REL-SANCTION-${req.id}`, remarks: '' });
                            }}
                            className="px-2.5 py-1 rounded-lg bg-teal-600 text-white hover:bg-teal-700 font-semibold text-[11px] shadow-xs"
                          >
                            Final Settlement
                          </button>
                        )}

                        <button
                          onClick={() => {
                            setSelectedRequest(req);
                            setActionType('view');
                          }}
                          className="px-2 py-1 text-slate-500 hover:text-slate-800"
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12">
            <EmptyState
              title="No Release or Refund Applications"
              description="No applications currently active in the selected institutional scope."
              actionLabel="Apply for Release"
              onAction={handleOpenSubmit}
            />
          </div>
        )}
      </Card>

      {/* Submission Modal */}
      {isSubmitOpen && (
        <Modal
          isOpen={isSubmitOpen}
          onClose={() => setIsSubmitOpen(false)}
          title="Submit Security Deposit Release Application"
          subtitle="Statutory application under AICTE Approval Process Handbook Section 10(1)"
          maxWidth="max-w-lg"
        >
          <form onSubmit={handleSubmitRequest} className="space-y-4 text-xs">
            {submitError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-semibold">
                {submitError}
              </div>
            )}

            <div>
              <label className="block font-bold text-slate-700 mb-1">Target FDR Record ID *</label>
              <input
                type="number"
                required
                value={submitForm.fdr_record_id}
                onChange={(e) => setSubmitForm({ ...submitForm, fdr_record_id: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300"
                placeholder="e.g. 1"
              />
              <p className="text-[10px] text-slate-400 mt-0.5">Database ID of the maturing or compliant FDR</p>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Application Type *</label>
              <select
                value={submitForm.request_type}
                onChange={(e) => setSubmitForm({ ...submitForm, request_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
              >
                <option value="RELEASE">RELEASE (Security deposit tenure completed &amp; institution compliant)</option>
                <option value="REFUND">REFUND (Excess deposit or statutory withdrawal)</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Requested Deposit Principal (INR ₹) *</label>
              <input
                type="number"
                step="0.01"
                required
                value={submitForm.requested_amount}
                onChange={(e) => setSubmitForm({ ...submitForm, requested_amount: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 font-bold"
                placeholder="e.g. 2500000.00"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Justification / Reason *</label>
              <textarea
                rows={3}
                required
                value={submitForm.reason}
                onChange={(e) => setSubmitForm({ ...submitForm, reason: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300"
                placeholder="Statutory completion of 5-year lock-in period with zero student grievances..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsSubmitOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitLoading}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-aicte-navy text-white hover:bg-aicte-dark shadow-xs disabled:opacity-50"
              >
                {submitLoading ? 'Submitting Application...' : 'Submit Release Application'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Action Dialog Modal */}
      {selectedRequest && actionType && (
        <Modal
          isOpen={!!selectedRequest}
          onClose={() => {
            setSelectedRequest(null);
            setActionType(null);
          }}
          title={
            actionType === 'scrutiny'
              ? 'Official Regulatory Scrutiny Action'
              : actionType === 'approval'
              ? 'Administrative Final Sanction'
              : actionType === 'close'
              ? 'Statutory Settlement Closure'
              : 'Release Application Dossier'
          }
          subtitle={`Application #${selectedRequest.request_number} &bull; ${formatCurrency(selectedRequest.requested_amount)}`}
          maxWidth="max-w-xl"
        >
          {actionType === 'view' ? (
            <div className="space-y-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 gap-3">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase">Status</span>
                  <div className="mt-0.5"><Badge status={selectedRequest.status} /></div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase">Amount</span>
                  <p className="font-bold text-slate-900 mt-0.5">{formatCurrency(selectedRequest.requested_amount)}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[10px] text-slate-400 font-bold uppercase">Reason</span>
                  <p className="text-slate-700 mt-0.5">{selectedRequest.reason}</p>
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleExecuteAction} className="space-y-4 text-xs">
              {actionError && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-semibold">
                  {actionError}
                </div>
              )}

              {actionType === 'scrutiny' && (
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Scrutiny Determination</label>
                  <select
                    value={actionForm.decision}
                    onChange={(e) => setActionForm({ ...actionForm, decision: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
                  >
                    <option value="RECOMMEND_APPROVAL">RECOMMEND FOR APPROVAL (All certificates compliant)</option>
                    <option value="REQUEST_CORRECTION">REQUEST CORRECTION (Missing clearance letters)</option>
                    <option value="REJECT">REJECT (Non-compliant with approval criteria)</option>
                  </select>
                </div>
              )}

              {actionType === 'approval' && (
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Sanction Decision</label>
                  <select
                    value={actionForm.decision}
                    onChange={(e) => setActionForm({ ...actionForm, decision: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
                  >
                    <option value="APPROVE">APPROVE SANCTION (Grant official deposit release)</option>
                    <option value="REJECT">REJECT SANCTION</option>
                  </select>
                </div>
              )}

              {actionType === 'close' && (
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Disbursement / Settlement Reference</label>
                  <input
                    type="text"
                    required
                    value={actionForm.closure_ref}
                    onChange={(e) => setActionForm({ ...actionForm, closure_ref: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 font-mono"
                  />
                  <p className="text-[10px] text-slate-400 mt-0.5">Physical banking disbursement proceeds through finance division channels</p>
                </div>
              )}

              <div>
                <label className="block font-bold text-slate-700 mb-1">Review Remarks / Notes *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Record observations, scrutiny checklist findings, or dispatch details..."
                  value={actionForm.remarks}
                  onChange={(e) => setActionForm({ ...actionForm, remarks: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedRequest(null);
                    setActionType(null);
                  }}
                  className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 text-xs font-semibold rounded-lg bg-aicte-navy text-white hover:bg-aicte-dark shadow-xs disabled:opacity-50"
                >
                  {actionLoading ? 'Executing Workflow...' : 'Confirm Action'}
                </button>
              </div>
            </form>
          )}
        </Modal>
      )}
    </div>
  );
};

export default ReleaseRefundPage;
