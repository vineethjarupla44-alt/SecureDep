import React, { useState, useEffect } from 'react';
import Card, { MetricCard } from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import DuplicateComparisonModal from '../components/ai/DuplicateComparisonModal';
import OCRComparisonModal from '../components/documents/OCRComparisonModal';
import { formatCurrency, formatDate } from '../utils/formatters';
import api from '../services/api';

export const OfficialDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [duplicateCandidates, setDuplicateCandidates] = useState([]);
  const [releaseRequests, setReleaseRequests] = useState([]);
  const [expiringFDRs, setExpiringFDRs] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);

  const fetchOfficialData = async () => {
    setLoading(true);
    try {
      const [dupRes, releaseRes, expiringRes] = await Promise.allSettled([
        api.getDuplicateCandidates({ status: 'UNREVIEWED', per_page: 5 }),
        api.getReleaseRequests({ status: 'PENDING_SCRUTINY', per_page: 5 }),
        api.getExpiringFDRs({ days: 30, per_page: 5 }),
      ]);

      if (dupRes.status === 'fulfilled') setDuplicateCandidates(dupRes.value?.data || []);
      if (releaseRes.status === 'fulfilled') setReleaseRequests(releaseRes.value?.data || []);
      if (expiringRes.status === 'fulfilled') setExpiringFDRs(expiringRes.value?.data || []);
    } catch (err) {
      console.error('Error loading official dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOfficialData();
  }, []);

  const handleReviewCandidate = async (candidateId, status, remarks) => {
    await api.reviewDuplicateCandidate(candidateId, status, remarks);
    fetchOfficialData();
  };

  if (loading) return <LoadingSpinner message="Loading Regulatory & Finance Scrutiny Queues..." />;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="shield" className="w-6 h-6 text-aicte-navy" />
            AICTE Regulatory &amp; Finance Bureau Scrutiny Queue
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Official instrument verification, OCR discrepancy audit, and release scrutiny actions
          </p>
        </div>

        <button
          onClick={fetchOfficialData}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition"
        >
          <Icon name="refreshCw" className="w-3.5 h-3.5 text-slate-500" />
          Refresh Queues
        </button>
      </div>

      {/* Top 3 Queues Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Unreviewed Duplicate Flags"
          value={duplicateCandidates.length}
          subtitle="AI flagged suspect pairs"
          icon="brain"
          color="rose"
        />

        <MetricCard
          title="Pending Release Scrutiny"
          value={releaseRequests.length}
          subtitle="Institutions awaiting refund"
          icon="arrowRightCircle"
          color="amber"
        />

        <MetricCard
          title="Upcoming Maturities (30d)"
          value={expiringFDRs.length}
          subtitle="Notice tracking & renewal scrutiny"
          icon="calendar"
          color="indigo"
        />
      </div>

      {/* 1. Intelligent Duplicate Queue (Phase 8 AI) */}
      <Card
        title="AI Duplicate Flag Queue (Phase 8)"
        subtitle="Suspect exact, normalized, or cross-institution duplicate FDR submissions"
        icon="brain"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Flag ID</th>
                <th className="py-2.5 px-4">Primary FDR</th>
                <th className="py-2.5 px-4">Duplicate Candidate</th>
                <th className="py-2.5 px-4">Algorithm / Match Type</th>
                <th className="py-2.5 px-4">Similarity</th>
                <th className="py-2.5 px-4 text-right">Review Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {duplicateCandidates.length > 0 ? (
                duplicateCandidates.map((cand) => (
                  <tr key={cand.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-mono font-bold text-slate-800">#{cand.id}</td>
                    <td className="py-3 px-4 font-mono text-slate-700">{cand.primary_fdr?.fdr_number || `#${cand.primary_fdr_id}`}</td>
                    <td className="py-3 px-4 font-mono text-rose-700 font-semibold">{cand.duplicate_fdr?.fdr_number || `#${cand.duplicate_fdr_id}`}</td>
                    <td className="py-3 px-4">
                      <Badge variant="teal">{cand.match_type}</Badge>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-800">
                      {(cand.similarity_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedCandidate(cand)}
                        className="px-3 py-1 rounded-lg bg-aicte-navy text-white text-[11px] font-semibold hover:bg-aicte-dark transition shadow-xs"
                      >
                        Scrutinize Diff
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    No unreviewed duplicate FDR candidates pending regulatory review.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 2. Release & Refund Scrutiny Queue (Phase 7 FSM) */}
      <Card
        title="Security Deposit Release & Refund Scrutiny Queue (Phase 7)"
        subtitle="Formal applications under Section 10(1) regulations awaiting official recommendation"
        icon="arrowRightCircle"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Request #</th>
                <th className="py-2.5 px-4">Institution</th>
                <th className="py-2.5 px-4">Type</th>
                <th className="py-2.5 px-4">Requested Principal</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {releaseRequests.length > 0 ? (
                releaseRequests.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-mono font-bold text-slate-800">{req.request_number}</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">{req.institution?.name || `Institution #${req.institution_id}`}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded font-bold bg-blue-50 text-blue-700 text-[10px]">
                        {req.request_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(req.requested_amount)}</td>
                    <td className="py-3 px-4">
                      <Badge status={req.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <a
                        href="/release-refund"
                        className="px-3 py-1 rounded-lg border border-slate-300 bg-white text-slate-700 text-[11px] font-semibold hover:bg-slate-50"
                      >
                        Open Workflow
                      </a>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    No release or refund requests currently pending official scrutiny.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Modals */}
      {selectedCandidate && (
        <DuplicateComparisonModal
          isOpen={!!selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
          candidate={selectedCandidate}
          onReviewSuccess={handleReviewCandidate}
        />
      )}

      {selectedDoc && (
        <OCRComparisonModal
          isOpen={!!selectedDoc}
          onClose={() => setSelectedDoc(null)}
          document={selectedDoc}
          onReviewSuccess={() => fetchOfficialData()}
        />
      )}
    </div>
  );
};

export default OfficialDashboard;
