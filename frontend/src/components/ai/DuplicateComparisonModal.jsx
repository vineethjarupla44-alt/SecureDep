import React, { useState } from 'react';
import Modal from '../common/Modal';
import Badge from '../common/Badge';
import Icon from '../common/Icons';
import { formatCurrency, formatDate } from '../../utils/formatters';
import { useAuth } from '../../context/AuthContext';

export const DuplicateComparisonModal = ({ isOpen, onClose, candidate, onReviewSuccess }) => {
  const { isOfficial } = useAuth();
  const [reviewStatus, setReviewStatus] = useState('CONFIRMED_DUPLICATE');
  const [remarks, setRemarks] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!candidate) return null;

  const handleReview = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (onReviewSuccess) {
        await onReviewSuccess(candidate.id, reviewStatus, remarks);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to submit candidate review');
    } finally {
      setSubmitting(false);
    }
  };

  const primary = candidate.primary_fdr || {};
  const duplicate = candidate.duplicate_fdr || {};

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Intelligent Duplicate Detection Review"
      subtitle={`Flagged Pair #${candidate.id} &bull; Similarity Score: ${(candidate.similarity_score * 100).toFixed(1)}%`}
      maxWidth="max-w-4xl"
    >
      <div className="space-y-6">
        {/* Match Header Banner */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Detection Algorithm</span>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge variant="teal">{candidate.match_type}</Badge>
              <span className="text-xs font-semibold text-slate-700">
                Confidence: <strong className="text-slate-900">{(candidate.similarity_score * 100).toFixed(1)}%</strong>
              </span>
            </div>
          </div>

          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Review Status</span>
            <div className="mt-0.5">
              <Badge status={candidate.status} />
            </div>
          </div>
        </div>

        {/* AI Explanation Callout */}
        <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200/80 flex items-start gap-3">
          <Icon name="alertTriangle" className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900">
            <p className="font-bold">AI Detection Observation:</p>
            <p className="mt-0.5 leading-relaxed">{candidate.explanation || 'Suspect matching patterns identified across FDR records or document signatures.'}</p>
          </div>
        </div>

        {/* Side-by-Side Comparison Table */}
        <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="grid grid-cols-2 bg-slate-100 border-b border-slate-200 text-xs font-bold text-slate-700">
            <div className="p-3 border-r border-slate-200 flex items-center gap-2">
              <Icon name="fileText" className="w-4 h-4 text-aicte-navy" />
              Primary Reference Record (ID: #{candidate.primary_fdr_id})
            </div>
            <div className="p-3 flex items-center gap-2">
              <Icon name="fileText" className="w-4 h-4 text-rose-600" />
              Suspect Duplicate Record (ID: #{candidate.duplicate_fdr_id})
            </div>
          </div>

          <div className="divide-y divide-slate-100 text-xs">
            {/* FDR Number */}
            <div className="grid grid-cols-2">
              <div className="p-3 border-r border-slate-100 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">FDR Number</span>
                <span className="font-mono font-bold text-slate-800 text-sm">{primary.fdr_number || 'N/A'}</span>
              </div>
              <div className="p-3 bg-amber-50/40">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">FDR Number</span>
                <span className="font-mono font-bold text-rose-700 text-sm">{duplicate.fdr_number || 'N/A'}</span>
              </div>
            </div>

            {/* Issuing Bank */}
            <div className="grid grid-cols-2">
              <div className="p-3 border-r border-slate-100 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Scheduled Bank</span>
                <span className="font-semibold text-slate-800">{primary.issuing_bank || 'N/A'}</span>
              </div>
              <div className="p-3 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Scheduled Bank</span>
                <span className="font-semibold text-slate-800">{duplicate.issuing_bank || 'N/A'}</span>
              </div>
            </div>

            {/* Deposit Amount */}
            <div className="grid grid-cols-2">
              <div className="p-3 border-r border-slate-100 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Deposit Amount</span>
                <span className="font-bold text-slate-900">{formatCurrency(primary.deposit_amount)}</span>
              </div>
              <div className="p-3 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Deposit Amount</span>
                <span className="font-bold text-slate-900">{formatCurrency(duplicate.deposit_amount)}</span>
              </div>
            </div>

            {/* Maturity Date */}
            <div className="grid grid-cols-2">
              <div className="p-3 border-r border-slate-100 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Maturity Date</span>
                <span className="font-semibold text-slate-800">{formatDate(primary.maturity_date)}</span>
              </div>
              <div className="p-3 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Maturity Date</span>
                <span className="font-semibold text-slate-800">{formatDate(duplicate.maturity_date)}</span>
              </div>
            </div>

            {/* Institution Scope */}
            <div className="grid grid-cols-2">
              <div className="p-3 border-r border-slate-100 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Institution</span>
                <span className="font-semibold text-slate-800">{primary.institution?.name || `Institution #${primary.institution_id || candidate.primary_fdr_id}`}</span>
              </div>
              <div className="p-3 bg-white">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Institution</span>
                <span className="font-semibold text-slate-800">{duplicate.institution?.name || `Institution #${duplicate.institution_id || candidate.duplicate_fdr_id}`}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Official Review Form (Privileged Role Only) */}
        {isOfficial && (
          <form onSubmit={handleReview} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Icon name="shield" className="w-4 h-4 text-aicte-navy" />
              Official Regulatory Review Decision
            </h4>

            {error && (
              <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Determination</label>
                <select
                  value={reviewStatus}
                  onChange={(e) => setReviewStatus(e.target.value)}
                  className="w-full text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                >
                  <option value="CONFIRMED_DUPLICATE">CONFIRMED DUPLICATE (Lock for Administrative Review)</option>
                  <option value="FALSE_POSITIVE">FALSE POSITIVE (Clear Flag - Legitimate Separate Instruments)</option>
                  <option value="RESOLVED">RESOLVED (Correction Provided by Institution)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Review Observations / Remarks</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Enter scrutiny notes or bank verification scroll findings..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100"
              >
                Close
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-aicte-navy text-white hover:bg-aicte-dark shadow-xs disabled:opacity-50"
              >
                {submitting ? 'Recording Decision...' : 'Save Review Decision'}
              </button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
};

export default DuplicateComparisonModal;
