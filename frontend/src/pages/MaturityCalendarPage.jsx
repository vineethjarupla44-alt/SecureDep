import React, { useState, useEffect } from 'react';
import Card, { MetricCard } from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import Modal from '../components/common/Modal';
import { formatCurrency, formatDate } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const MaturityCalendarPage = () => {
  const { isOfficial, isInstitutionUser } = useAuth();

  const [loading, setLoading] = useState(true);
  const [expiringList, setExpiringList] = useState([]);
  const [activeTab, setActiveTab] = useState('30'); // '30', '15', '7', 'overdue'
  const [scanMessage, setScanMessage] = useState(null);
  const [scanning, setScanning] = useState(false);

  // Renewal proposal modal state
  const [renewalFdr, setRenewalFdr] = useState(null);
  const [renewalForm, setRenewalForm] = useState({
    renewal_type: 'ROLLOVER',
    replacement_fdr_number: '',
    replacement_issuing_bank: 'State Bank of India',
    replacement_deposit_amount: '',
    replacement_issue_date: new Date().toISOString().split('T')[0],
    replacement_maturity_date: new Date(Date.now() + 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    submission_notes: '',
  });
  const [renewalSubmitting, setRenewalSubmitting] = useState(false);
  const [renewalError, setRenewalError] = useState(null);

  const fetchMaturityData = async (days = activeTab) => {
    setLoading(true);
    try {
      let params = {};
      if (days === 'overdue') {
        params.status = 'MATURED';
      } else {
        params.days = parseInt(days);
      }
      const res = await api.getExpiringFDRs(params);
      setExpiringList(res.data || []);
    } catch (err) {
      console.error('Failed to load maturity data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaturityData(activeTab);
  }, [activeTab]);

  const handleTriggerScan = async () => {
    setScanning(true);
    setScanMessage(null);
    try {
      const res = await api.triggerMaturityScan();
      setScanMessage(`Scan finished: ${res.alerts_created || 0} alerts generated, ${res.skipped_duplicates || 0} duplicate alerts skipped.`);
      fetchMaturityData(activeTab);
    } catch (err) {
      setScanMessage(`Scan error: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  const handleOpenRenewalModal = (fdr) => {
    setRenewalFdr(fdr);
    setRenewalForm({
      renewal_type: 'ROLLOVER',
      replacement_fdr_number: `${fdr.fdr_number}-R1`,
      replacement_issuing_bank: fdr.issuing_bank,
      replacement_deposit_amount: fdr.deposit_amount,
      replacement_issue_date: fdr.maturity_date || new Date().toISOString().split('T')[0],
      replacement_maturity_date: new Date(Date.now() + 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      submission_notes: 'Standard 5-year statutory rollover under AICTE guidelines.',
    });
    setRenewalError(null);
  };

  const handleRenewalSubmit = async (e) => {
    e.preventDefault();
    setRenewalSubmitting(true);
    setRenewalError(null);
    try {
      await api.submitRenewal(renewalFdr.id, {
        ...renewalForm,
        replacement_deposit_amount: parseFloat(renewalForm.replacement_deposit_amount),
      });
      setRenewalFdr(null);
      fetchMaturityData(activeTab);
    } catch (err) {
      setRenewalError(err.message || 'Failed to submit renewal proposal');
    } finally {
      setRenewalSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="calendar" className="w-6 h-6 text-aicte-navy" />
            Maturity Tracking &amp; Renewal Monitoring (Phase 6)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Idempotent automated alerts, 30d/15d/7d reminder horizons, and rollover lineages
          </p>
        </div>

        {isOfficial && (
          <button
            onClick={handleTriggerScan}
            disabled={scanning}
            className="inline-flex items-center gap-2 px-4 py-2 bg-aicte-navy text-white text-xs font-bold rounded-xl hover:bg-aicte-dark transition shadow-sm disabled:opacity-50"
          >
            <Icon name="refreshCw" className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            {scanning ? 'Running Background Scan...' : 'Trigger Maturity Scan'}
          </button>
        )}
      </div>

      {scanMessage && (
        <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold flex items-center justify-between">
          <span>{scanMessage}</span>
          <button onClick={() => setScanMessage(null)} className="text-blue-500 hover:text-blue-700 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Expiry Window Filter Tabs */}
      <div className="flex border-b border-slate-200 space-x-2 text-xs font-bold">
        {[
          { key: '30', label: '30-Day Reminder View' },
          { key: '15', label: '15-Day Urgent Horizon' },
          { key: '7', label: '7-Day Critical Horizon' },
          { key: 'overdue', label: 'Matured & Overdue' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`py-2.5 px-4 border-b-2 font-bold transition ${
              activeTab === tab.key
                ? 'border-aicte-navy text-aicte-navy'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Instruments Table */}
      <Card noPadding title={`Instruments in ${activeTab === 'overdue' ? 'Overdue Status' : `${activeTab}-Day Horizon`}`}>
        {loading ? (
          <LoadingSpinner message="Calculating maturity timelines and business dates..." />
        ) : expiringList.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">FDR Number</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Scheduled Bank</th>
                  <th className="py-3 px-4">Deposit Principal</th>
                  <th className="py-3 px-4">Maturity Date</th>
                  <th className="py-3 px-4 text-center">Urgency</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {expiringList.map((fdr) => (
                  <tr key={fdr.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-800">{fdr.fdr_number}</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {fdr.institution?.name || `Institution #${fdr.institution_id}`}
                    </td>
                    <td className="py-3 px-4 text-slate-600">{fdr.issuing_bank}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(fdr.deposit_amount)}</td>
                    <td className="py-3 px-4 text-slate-600 font-semibold">{formatDate(fdr.maturity_date)}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge status={fdr.maturity_category || fdr.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleOpenRenewalModal(fdr)}
                        className="px-3 py-1 bg-aicte-navy text-white rounded-lg hover:bg-aicte-dark transition font-semibold text-[11px]"
                      >
                        Propose Renewal
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12">
            <EmptyState
              title="No Instruments in Current Expiry Horizon"
              description={`There are currently zero fixed deposit instruments falling into the selected ${activeTab === 'overdue' ? 'overdue' : `${activeTab}-day`} category.`}
            />
          </div>
        )}
      </Card>

      {/* Renewal Proposal Modal */}
      {renewalFdr && (
        <Modal
          isOpen={!!renewalFdr}
          onClose={() => setRenewalFdr(null)}
          title="Submit FDR Renewal Proposal"
          subtitle={`Predecessor Instrument: ${renewalFdr.fdr_number} &bull; Maturing: ${formatDate(renewalFdr.maturity_date)}`}
          maxWidth="max-w-xl"
        >
          <form onSubmit={handleRenewalSubmit} className="space-y-4 text-xs">
            {renewalError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-semibold">
                {renewalError}
              </div>
            )}

            <div>
              <label className="block font-bold text-slate-700 mb-1">Renewal Strategy</label>
              <select
                value={renewalForm.renewal_type}
                onChange={(e) => setRenewalForm({ ...renewalForm, renewal_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
              >
                <option value="ROLLOVER">ROLLOVER (Extend tenure with same bank &amp; principal)</option>
                <option value="REPLACEMENT">REPLACEMENT (Fresh FDR certificate from new bank branch)</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Replacement / Renewed FDR Number *</label>
              <input
                type="text"
                required
                value={renewalForm.replacement_fdr_number}
                onChange={(e) => setRenewalForm({ ...renewalForm, replacement_fdr_number: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Bank Name</label>
                <input
                  type="text"
                  required
                  value={renewalForm.replacement_issuing_bank}
                  onChange={(e) => setRenewalForm({ ...renewalForm, replacement_issuing_bank: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Deposit Principal (INR ₹)</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={renewalForm.replacement_deposit_amount}
                  onChange={(e) => setRenewalForm({ ...renewalForm, replacement_deposit_amount: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 font-semibold"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Issue Date</label>
                <input
                  type="date"
                  required
                  value={renewalForm.replacement_issue_date}
                  onChange={(e) => setRenewalForm({ ...renewalForm, replacement_issue_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">New Maturity Date</label>
                <input
                  type="date"
                  required
                  value={renewalForm.replacement_maturity_date}
                  onChange={(e) => setRenewalForm({ ...renewalForm, replacement_maturity_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Submission Notes</label>
              <textarea
                rows={2}
                value={renewalForm.submission_notes}
                onChange={(e) => setRenewalForm({ ...renewalForm, submission_notes: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300"
                placeholder="Details of renewal letter or bank rollover certificate..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setRenewalFdr(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={renewalSubmitting}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-aicte-navy text-white hover:bg-aicte-dark shadow-xs disabled:opacity-50"
              >
                {renewalSubmitting ? 'Transmitting Proposal...' : 'Submit Renewal Proposal'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

export default MaturityCalendarPage;
