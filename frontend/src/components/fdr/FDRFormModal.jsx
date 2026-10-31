import React, { useState } from 'react';
import Modal from '../common/Modal';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';

export const FDRFormModal = ({ isOpen, onClose, onSuccess }) => {
  const { user, isInstitutionUser } = useAuth();
  const [formData, setFormData] = useState({
    fdr_number: '',
    issuing_bank: 'State Bank of India',
    deposit_amount: '',
    issue_date: new Date().toISOString().split('T')[0],
    maturity_date: new Date(Date.now() + 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    status: 'ACTIVE',
    institution_id: isInstitutionUser ? user?.institution_id : 1,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const bankOptions = [
    'State Bank of India',
    'Punjab National Bank',
    'Bank of Baroda',
    'Canara Bank',
    'HDFC Bank',
    'ICICI Bank',
    'Axis Bank',
    'Union Bank of India',
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        ...formData,
        deposit_amount: parseFloat(formData.deposit_amount),
        institution_id: parseInt(formData.institution_id),
      };

      if (isNaN(payload.deposit_amount) || payload.deposit_amount <= 0) {
        throw new Error('Deposit amount must be a positive number greater than 0.');
      }

      if (new Date(payload.maturity_date) <= new Date(payload.issue_date)) {
        throw new Error('Maturity date must be strictly later than issue date.');
      }

      const res = await api.createFDR(payload);
      if (onSuccess) onSuccess(res.data);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create FDR record');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Submit Security Deposit / FDR Instrument"
      subtitle="Register an official Fixed Deposit Receipt with AICTE"
      maxWidth="max-w-xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-medium">
            {error}
          </div>
        )}

        {/* Institution Scope */}
        {!isInstitutionUser && (
          <div>
            <label className="block font-bold text-slate-700 mb-1">Target Institution ID</label>
            <input
              type="number"
              required
              value={formData.institution_id}
              onChange={(e) => setFormData({ ...formData, institution_id: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
              placeholder="e.g. 1"
            />
          </div>
        )}

        {/* FDR Certificate Number */}
        <div>
          <label className="block font-bold text-slate-700 mb-1">FDR Certificate Number *</label>
          <input
            type="text"
            required
            value={formData.fdr_number}
            onChange={(e) => setFormData({ ...formData, fdr_number: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy font-mono"
            placeholder="e.g. FDR-SBI-2026-9081"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">As printed on the physical bank fixed deposit receipt</p>
        </div>

        {/* Issuing Bank */}
        <div>
          <label className="block font-bold text-slate-700 mb-1">Issuing Scheduled Commercial Bank *</label>
          <select
            value={formData.issuing_bank}
            onChange={(e) => setFormData({ ...formData, issuing_bank: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-aicte-navy"
          >
            {bankOptions.map((bank) => (
              <option key={bank} value={bank}>
                {bank}
              </option>
            ))}
          </select>
        </div>

        {/* Deposit Amount (INR) */}
        <div>
          <label className="block font-bold text-slate-700 mb-1">Deposit Principal Amount (INR ₹) *</label>
          <input
            type="number"
            step="0.01"
            min="1000"
            required
            value={formData.deposit_amount}
            onChange={(e) => setFormData({ ...formData, deposit_amount: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy font-semibold text-sm"
            placeholder="e.g. 2500000.00"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">Minimum statutory security deposit under AICTE Approval Process</p>
        </div>

        {/* Dates Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block font-bold text-slate-700 mb-1">Date of Issue *</label>
            <input
              type="date"
              required
              value={formData.issue_date}
              onChange={(e) => setFormData({ ...formData, issue_date: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Date of Maturity *</label>
            <input
              type="date"
              required
              value={formData.maturity_date}
              onChange={(e) => setFormData({ ...formData, maturity_date: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            />
          </div>
        </div>

        {/* Status */}
        <div>
          <label className="block font-bold text-slate-700 mb-1">Instrument Status</label>
          <select
            value={formData.status}
            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-aicte-navy"
          >
            <option value="ACTIVE">ACTIVE (Statutory Security Deposit)</option>
            <option value="LIEN_MARKED">LIEN MARKED (Lien in favor of AICTE)</option>
          </select>
        </div>

        {/* Form Actions */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-slate-300 text-slate-600 font-semibold hover:bg-slate-50 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 rounded-lg bg-aicte-navy text-white font-semibold hover:bg-aicte-dark transition shadow-xs disabled:opacity-50"
          >
            {loading ? 'Submitting to AICTE...' : 'Submit FDR Instrument'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default FDRFormModal;
