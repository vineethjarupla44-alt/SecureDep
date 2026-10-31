import React, { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Pagination from '../components/common/Pagination';
import EmptyState from '../components/common/EmptyState';
import FDRFormModal from '../components/fdr/FDRFormModal';
import DocumentUploadModal from '../components/documents/DocumentUploadModal';
import Modal from '../components/common/Modal';
import RiskRadarGauge from '../components/ai/RiskRadarGauge';
import { formatCurrency, formatDate } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const FDRManagementPage = () => {
  const { isInstitutionUser, isAdmin, isOfficial } = useAuth();

  const [fdrs, setFdrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalItems, setTotalItems] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [searchNumber, setSearchNumber] = useState('');
  const [selectedBank, setSelectedBank] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [uploadFdr, setUploadFdr] = useState(null);
  const [selectedFdrDetail, setSelectedFdrDetail] = useState(null);
  const [riskAssessment, setRiskAssessment] = useState(null);
  const [riskLoading, setRiskLoading] = useState(false);

  const fetchFDRList = async (targetPage = page) => {
    setLoading(true);
    try {
      const filters = {
        page: targetPage,
        per_page: 10,
      };
      if (searchNumber.trim()) filters.fdr_number = searchNumber.trim();
      if (selectedBank) filters.bank_name = selectedBank;
      if (selectedStatus) filters.status = selectedStatus;

      const res = await api.searchFDRs(filters);
      setFdrs(res.data || []);
      setTotalItems(res.total || 0);
      setTotalPages(res.pages || 1);
      setPage(res.page || 1);
    } catch (err) {
      console.error('Failed to load FDR records:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFDRList(1);
  }, [selectedBank, selectedStatus]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchFDRList(1);
  };

  const handleViewDetails = async (fdr) => {
    setSelectedFdrDetail(fdr);
    setRiskAssessment(null);
    setRiskLoading(true);
    try {
      const res = await api.getFDRRiskScore(fdr.id);
      if (res?.data) setRiskAssessment(res.data);
    } catch (e) {
      // Soft fallback
    } finally {
      setRiskLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="fileText" className="w-6 h-6 text-aicte-navy" />
            Security Deposit / FDR Instrument Management
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Registered Fixed Deposit Receipts held in statutory lien under AICTE regulations
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-aicte-navy text-white text-xs font-bold rounded-xl hover:bg-aicte-dark transition shadow-sm"
        >
          <Icon name="plus" className="w-4 h-4 text-aicte-teal" />
          Register New FDR
        </button>
      </div>

      {/* Filter and Search Bar */}
      <Card noPadding>
        <form onSubmit={handleSearchSubmit} className="p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
          <div className="flex-1 min-w-[240px] flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Search by FDR certificate number..."
                value={searchNumber}
                onChange={(e) => setSearchNumber(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy bg-white"
              />
              <Icon name="search" className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-slate-800 text-white text-xs font-semibold rounded-xl hover:bg-slate-900 transition"
            >
              Search
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Bank Filter */}
            <select
              value={selectedBank}
              onChange={(e) => setSelectedBank(e.target.value)}
              className="px-3 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            >
              <option value="">All Scheduled Banks</option>
              <option value="State Bank of India">State Bank of India</option>
              <option value="Punjab National Bank">Punjab National Bank</option>
              <option value="HDFC Bank">HDFC Bank</option>
              <option value="ICICI Bank">ICICI Bank</option>
              <option value="Bank of Baroda">Bank of Baroda</option>
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-3 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            >
              <option value="">All Lifecycle Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="MATURED">MATURED</option>
              <option value="LIEN_MARKED">LIEN MARKED</option>
              <option value="RENEWED">RENEWED</option>
              <option value="RELEASED">RELEASED</option>
            </select>

            {(searchNumber || selectedBank || selectedStatus) && (
              <button
                type="button"
                onClick={() => {
                  setSearchNumber('');
                  setSelectedBank('');
                  setSelectedStatus('');
                  fetchFDRList(1);
                }}
                className="px-3 py-2 text-slate-500 hover:text-slate-700 font-semibold"
              >
                Clear
              </button>
            )}
          </div>
        </form>

        {/* Data Table */}
        {loading ? (
          <LoadingSpinner message="Retrieving filtered FDR instruments..." />
        ) : fdrs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold border-y border-slate-200">
                <tr>
                  <th className="py-3 px-4">FDR Number</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Issuing Scheduled Bank</th>
                  <th className="py-3 px-4">Principal Amount</th>
                  <th className="py-3 px-4">Issue Date</th>
                  <th className="py-3 px-4">Maturity Date</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {fdrs.map((fdr) => (
                  <tr key={fdr.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">{fdr.fdr_number}</td>
                    <td className="py-3 px-4 text-slate-700">
                      <span className="font-semibold block">{fdr.institution?.name || `Institution #${fdr.institution_id}`}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{fdr.institution?.institution_code}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">{fdr.issuing_bank}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(fdr.deposit_amount)}</td>
                    <td className="py-3 px-4 text-slate-600">{formatDate(fdr.issue_date)}</td>
                    <td className="py-3 px-4 text-slate-600 font-medium">{formatDate(fdr.maturity_date)}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge status={fdr.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setUploadFdr(fdr)}
                          title="Attach Supporting Document"
                          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition"
                        >
                          <Icon name="upload" className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleViewDetails(fdr)}
                          className="px-2.5 py-1 rounded-lg bg-aicte-light hover:bg-aicte-navy hover:text-white text-aicte-navy text-[11px] font-semibold transition"
                        >
                          Details
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
              title="No Matching FDR Records"
              description="No fixed deposit records matched your current search parameters or institution scope."
              actionLabel="Register New Instrument"
              onAction={() => setIsCreateOpen(true)}
            />
          </div>
        )}

        <Pagination
          currentPage={page}
          totalPages={totalPages}
          totalItems={totalItems}
          onPageChange={(p) => fetchFDRList(p)}
        />
      </Card>

      {/* Register FDR Modal */}
      <FDRFormModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => fetchFDRList(1)}
      />

      {/* Attach Document Modal */}
      {uploadFdr && (
        <DocumentUploadModal
          isOpen={!!uploadFdr}
          onClose={() => setUploadFdr(null)}
          fdrId={uploadFdr.id}
          fdrNumber={uploadFdr.fdr_number}
          onSuccess={() => fetchFDRList(page)}
        />
      )}

      {/* FDR Details Drawer Modal */}
      {selectedFdrDetail && (
        <Modal
          isOpen={!!selectedFdrDetail}
          onClose={() => setSelectedFdrDetail(null)}
          title={`FDR Instrument: ${selectedFdrDetail.fdr_number}`}
          subtitle={`Institution: ${selectedFdrDetail.institution?.name || `#${selectedFdrDetail.institution_id}`}`}
          maxWidth="max-w-3xl"
        >
          <div className="space-y-5 text-xs">
            {/* Top Stat Grid */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Principal Amount</span>
                <p className="text-base font-extrabold text-slate-900 mt-0.5">{formatCurrency(selectedFdrDetail.deposit_amount)}</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Issuing Bank</span>
                <p className="font-semibold text-slate-800 mt-0.5">{selectedFdrDetail.issuing_bank}</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Issue Date</span>
                <p className="font-semibold text-slate-800 mt-0.5">{formatDate(selectedFdrDetail.issue_date)}</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase">Maturity Date</span>
                <p className="font-semibold text-slate-800 mt-0.5">{formatDate(selectedFdrDetail.maturity_date)}</p>
              </div>
            </div>

            {/* AI Risk Scoring Component */}
            {riskLoading ? (
              <LoadingSpinner size="sm" message="Computing explainable composite risk score..." />
            ) : riskAssessment ? (
              <div className="p-4 rounded-xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-bold text-slate-800 text-xs flex items-center gap-1.5">
                    <Icon name="brain" className="w-4 h-4 text-aicte-teal" />
                    AI Explainable Risk Assessment (Phase 8)
                  </h4>
                  <Badge variant={`risk-${riskAssessment.risk_category?.toLowerCase()}`}>
                    {riskAssessment.risk_category}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
                  <div className="sm:col-span-1">
                    <RiskRadarGauge
                      score={riskAssessment.risk_score}
                      category={riskAssessment.risk_category}
                      ruleScore={riskAssessment.rule_score}
                      mlScore={riskAssessment.ml_score}
                      size={150}
                    />
                  </div>
                  <div className="sm:col-span-2 text-xs space-y-2">
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <p className="font-bold text-slate-800 text-[11px]">Recommended Supervisory Action:</p>
                      <p className="text-slate-600 mt-0.5">{riskAssessment.recommended_action}</p>
                    </div>

                    {riskAssessment.contributing_factors?.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase">Contributing Factor Attribution</p>
                        <ul className="list-disc pl-4 mt-1 space-y-1 text-slate-600">
                          {riskAssessment.contributing_factors.map((f, i) => (
                            <li key={i}>{f.explanation || f.factor}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            {/* Modal Actions */}
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setSelectedFdrDetail(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default FDRManagementPage;
