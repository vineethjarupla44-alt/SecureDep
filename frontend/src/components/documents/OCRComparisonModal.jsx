import React, { useState } from 'react';
import Modal from '../common/Modal';
import Badge from '../common/Badge';
import Icon from '../common/Icons';
import { formatCurrency, formatDate } from '../../utils/formatters';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';

export const OCRComparisonModal = ({ isOpen, onClose, document, onReviewSuccess }) => {
  const { isOfficial } = useAuth();
  const [decision, setDecision] = useState('ACCEPTED');
  const [remarks, setRemarks] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [error, setError] = useState(null);

  if (!document) return null;

  const ocr = document.ocr_result || {};
  const fdr = document.fdr_record || {};
  const comparisons = ocr.discrepancies?.comparisons || {};
  const hasDiscrepancy = ocr.has_discrepancy;

  const handleReview = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.reviewDocument(document.id, decision, remarks);
      if (onReviewSuccess) onReviewSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReprocess = async () => {
    setReprocessing(true);
    setError(null);
    try {
      await api.processDocumentOCR(document.id);
      if (onReviewSuccess) onReviewSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to trigger OCR re-processing');
    } finally {
      setReprocessing(false);
    }
  };

  const getDiscrepancyBadge = (status) => {
    if (status === 'MATCH') return <Badge status="VERIFIED">MATCH</Badge>;
    if (status === 'MISMATCH') return <Badge status="REJECTED">MISMATCH</Badge>;
    if (status === 'UNREADABLE') return <Badge status="PENDING">UNREADABLE</Badge>;
    return <Badge status="NONE">NOT EVALUATED</Badge>;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Document OCR Verification & Discrepancy Audit"
      subtitle={`File: ${document.original_filename} &bull; Document #${document.id}`}
      maxWidth="max-w-4xl"
    >
      <div className="space-y-6 text-xs">
        {/* Document Metadata Bar */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase">Processing Engine</span>
            <p className="font-semibold text-slate-800 mt-0.5">{ocr.extraction_engine || 'Native PDF / Tesseract'}</p>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase">OCR Confidence</span>
            <p className="font-bold text-slate-900 mt-0.5">{ocr.confidence_score ? `${ocr.confidence_score.toFixed(1)}%` : 'N/A'}</p>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase">Audit Checksum</span>
            <p className="font-mono text-[10px] text-slate-600 truncate mt-0.5">{document.file_hash || 'SHA-256 Pending'}</p>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase">Discrepancy Flag</span>
            <div className="mt-0.5">
              {hasDiscrepancy ? (
                <span className="px-2 py-0.5 rounded-full font-bold bg-rose-100 text-rose-700">DISCREPANCIES DETECTED</span>
              ) : (
                <span className="px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-700">ALL FIELDS MATCH</span>
              )}
            </div>
          </div>
        </div>

        {/* Comparison Grid Table */}
        <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <table className="w-full text-left">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Field Attribute</th>
                <th className="py-2.5 px-4">Official Record Value</th>
                <th className="py-2.5 px-4">OCR Extracted Value</th>
                <th className="py-2.5 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* FDR Number */}
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-4 font-semibold text-slate-700">FDR Number</td>
                <td className="py-3 px-4 font-mono font-bold text-slate-800">{fdr.fdr_number || comparisons.fdr_number?.expected || 'N/A'}</td>
                <td className="py-3 px-4 font-mono text-slate-600">{ocr.extracted_fdr_number || comparisons.fdr_number?.extracted || 'N/A'}</td>
                <td className="py-3 px-4 text-center">{getDiscrepancyBadge(comparisons.fdr_number?.status)}</td>
              </tr>

              {/* Bank Name */}
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-4 font-semibold text-slate-700">Scheduled Bank</td>
                <td className="py-3 px-4 font-semibold text-slate-800">{fdr.issuing_bank || comparisons.bank_name?.expected || 'N/A'}</td>
                <td className="py-3 px-4 text-slate-600">{ocr.extracted_bank_name || comparisons.bank_name?.extracted || 'N/A'}</td>
                <td className="py-3 px-4 text-center">{getDiscrepancyBadge(comparisons.bank_name?.status)}</td>
              </tr>

              {/* Deposit Amount */}
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-4 font-semibold text-slate-700">Deposit Principal (₹)</td>
                <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(fdr.deposit_amount || comparisons.deposit_amount?.expected)}</td>
                <td className="py-3 px-4 text-slate-600">
                  {ocr.extracted_deposit_amount ? formatCurrency(ocr.extracted_deposit_amount) : comparisons.deposit_amount?.extracted ? formatCurrency(comparisons.deposit_amount.extracted) : 'N/A'}
                </td>
                <td className="py-3 px-4 text-center">{getDiscrepancyBadge(comparisons.deposit_amount?.status)}</td>
              </tr>

              {/* Issue Date */}
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-4 font-semibold text-slate-700">Issue Date</td>
                <td className="py-3 px-4 text-slate-800">{formatDate(fdr.issue_date || comparisons.issue_date?.expected)}</td>
                <td className="py-3 px-4 text-slate-600">{formatDate(ocr.extracted_issue_date || comparisons.issue_date?.extracted)}</td>
                <td className="py-3 px-4 text-center">{getDiscrepancyBadge(comparisons.issue_date?.status)}</td>
              </tr>

              {/* Maturity Date */}
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-4 font-semibold text-slate-700">Maturity Date</td>
                <td className="py-3 px-4 text-slate-800">{formatDate(fdr.maturity_date || comparisons.maturity_date?.expected)}</td>
                <td className="py-3 px-4 text-slate-600">{formatDate(ocr.extracted_maturity_date || comparisons.maturity_date?.extracted)}</td>
                <td className="py-3 px-4 text-center">{getDiscrepancyBadge(comparisons.maturity_date?.status)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Regulatory Governance Note */}
        <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-900 leading-normal">
          <p className="font-bold flex items-center gap-1.5">
            <Icon name="info" className="w-3.5 h-3.5 text-blue-700" />
            AICTE Regulatory Review Guidelines:
          </p>
          <p className="text-[11px] text-blue-800 mt-0.5">
            OCR discrepancy results are advisory indicators to guide human inspection. Final verification requires manual review of the scanned certificate by an AICTE Official.
          </p>
        </div>

        {/* Official Review Form */}
        {isOfficial && (
          <form onSubmit={handleReview} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Icon name="shield" className="w-4 h-4 text-aicte-navy" />
              Official Review Decision
            </h4>

            {error && (
              <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Decision</label>
                <select
                  value={decision}
                  onChange={(e) => setDecision(e.target.value)}
                  className="w-full text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                >
                  <option value="ACCEPTED">ACCEPT DOCUMENT (Verified Legitimate &amp; Compliant)</option>
                  <option value="REJECTED">REJECT DOCUMENT (Unclear Scan / Discrepancy Found)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Reviewer Remarks</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Record observations regarding certificate stamp, seal, or discrepancies..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-aicte-navy"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={handleReprocess}
                disabled={reprocessing}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 flex items-center gap-1.5"
              >
                <Icon name="refreshCw" className={`w-3.5 h-3.5 ${reprocessing ? 'animate-spin' : ''}`} />
                {reprocessing ? 'Reprocessing OCR...' : 'Reprocess OCR'}
              </button>

              <div className="flex gap-2">
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
                  className="px-5 py-2 text-xs font-semibold rounded-lg bg-aicte-navy text-white hover:bg-aicte-dark shadow-xs disabled:opacity-50"
                >
                  {submitting ? 'Recording Decision...' : 'Save Decision'}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
};

export default OCRComparisonModal;
