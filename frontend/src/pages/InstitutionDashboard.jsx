import React, { useState, useEffect } from 'react';
import Card, { MetricCard } from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import FDRFormModal from '../components/fdr/FDRFormModal';
import DocumentUploadModal from '../components/documents/DocumentUploadModal';
import ComplianceGradeBadge from '../components/ai/ComplianceGradeBadge';
import { formatCurrency, formatDate } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const InstitutionDashboard = () => {
  const { user } = useAuth();
  const instId = user?.institution_id || 1;

  const [loading, setLoading] = useState(true);
  const [institution, setInstitution] = useState(null);
  const [fdrs, setFdrs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [compliance, setCompliance] = useState(null);
  const [isFDRModalOpen, setIsFDRModalOpen] = useState(false);
  const [selectedFDRForDoc, setSelectedFDRForDoc] = useState(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [instRes, fdrRes, alertsRes, compRes] = await Promise.allSettled([
        api.getInstitutionById(instId),
        api.getFDRs({ per_page: 10 }),
        api.getAlerts({ is_acknowledged: 'false', per_page: 5 }),
        api.getInstitutionCompliance(instId),
      ]);

      if (instRes.status === 'fulfilled') setInstitution(instRes.value);
      if (fdrRes.status === 'fulfilled') setFdrs(fdrRes.value?.data || []);
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value?.data || []);
      if (compRes.status === 'fulfilled') setCompliance(compRes.value?.data);
    } catch (err) {
      console.error('Error loading institution dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [instId]);

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await api.acknowledgeAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (e) {
      console.error('Failed to acknowledge alert:', e);
    }
  };

  if (loading) return <LoadingSpinner message="Loading institutional security deposit records..." />;

  const activeFdrs = fdrs.filter((f) => f.status === 'ACTIVE');
  const totalActiveCapital = activeFdrs.reduce((acc, curr) => acc + (parseFloat(curr.deposit_amount) || 0), 0);

  return (
    <div className="space-y-6">
      {/* Top Profile & Compliance Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-aicte-light text-aicte-navy flex items-center justify-center font-bold text-xl border border-slate-200">
            <Icon name="building" className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">{institution?.name || 'Delhi Institute of Technology'}</h2>
              <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-mono text-[11px] font-bold">
                {institution?.institution_code || '1-DIT-1001'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {institution?.address || 'AICTE Institutional Area, New Delhi'} &bull; Contact: {institution?.contact_email || user?.email}
            </p>
          </div>
        </div>

        {/* Regulatory Compliance Grade Badge */}
        {compliance && (
          <div>
            <ComplianceGradeBadge
              grade={compliance.compliance_grade}
              score={compliance.compliance_score}
            />
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Active Fixed Deposit Capital"
          value={formatCurrency(totalActiveCapital)}
          subtitle={`${activeFdrs.length} Active Security Deposit Instruments`}
          icon="shield"
          color="navy"
        />

        <MetricCard
          title="Total Registered Instruments"
          value={fdrs.length}
          subtitle="Lifetime registered FDR records"
          icon="fileText"
          color="teal"
        />

        <MetricCard
          title="Unread Regulatory Alerts"
          value={alerts.length}
          subtitle="Maturity & renewal notices"
          icon="bell"
          color={alerts.length > 0 ? 'amber' : 'navy'}
        />
      </div>

      {/* Quick Action Bar */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-aicte-navy to-aicte-blue text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
        <div>
          <h3 className="text-sm font-bold">Statutory Security Deposit Actions</h3>
          <p className="text-xs text-slate-200 mt-0.5">
            Submit new bank FDRs, upload renewal deposit certificates, or request refund
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setIsFDRModalOpen(true)}
            className="px-4 py-2 rounded-lg bg-white text-aicte-navy text-xs font-bold hover:bg-slate-100 transition shadow-sm flex items-center gap-1.5"
          >
            <Icon name="plus" className="w-4 h-4 text-aicte-teal" />
            Submit New FDR
          </button>
        </div>
      </div>

      {/* Active Notifications Box */}
      {alerts.length > 0 && (
        <Card title="Pending Notifications & Maturity Reminders" subtitle="Action required under AICTE regulations" icon="bell">
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3 rounded-xl border border-amber-200 bg-amber-50/60 flex items-start justify-between gap-3 text-xs"
              >
                <div className="flex items-start gap-2.5">
                  <Icon name="alertTriangle" className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-amber-900">{alert.title}</span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-200/80 text-amber-800">
                        {alert.alert_type}
                      </span>
                    </div>
                    <p className="text-slate-600 mt-0.5">{alert.message}</p>
                    <p className="text-[10px] text-slate-400 mt-1">{formatDate(alert.created_at)}</p>
                  </div>
                </div>

                <button
                  onClick={() => handleAcknowledgeAlert(alert.id)}
                  className="px-3 py-1 rounded-lg bg-white border border-amber-300 text-amber-800 font-semibold hover:bg-amber-100 transition shrink-0"
                >
                  Acknowledge
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Institution FDR Records Table */}
      <Card
        title="Institution Security Deposit Portfolio"
        subtitle="Fixed Deposit Receipts held in lien for statutory AICTE approval"
        icon="fileText"
        action={
          <button
            onClick={() => setIsFDRModalOpen(true)}
            className="text-xs font-bold text-aicte-navy hover:underline flex items-center gap-1"
          >
            <Icon name="plus" className="w-3.5 h-3.5" />
            New FDR
          </button>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">FDR Number</th>
                <th className="py-2.5 px-4">Issuing Bank</th>
                <th className="py-2.5 px-4">Deposit Amount</th>
                <th className="py-2.5 px-4">Maturity Date</th>
                <th className="py-2.5 px-4 text-center">Status</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {fdrs.length > 0 ? (
                fdrs.map((fdr) => (
                  <tr key={fdr.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-mono font-bold text-slate-800">{fdr.fdr_number}</td>
                    <td className="py-3 px-4 text-slate-700">{fdr.issuing_bank}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(fdr.deposit_amount)}</td>
                    <td className="py-3 px-4 text-slate-600">{formatDate(fdr.maturity_date)}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge status={fdr.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedFDRForDoc(fdr)}
                        className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-aicte-navy font-semibold text-[11px] inline-flex items-center gap-1"
                      >
                        <Icon name="upload" className="w-3.5 h-3.5" />
                        Attach Doc
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8">
                    <EmptyState
                      title="No FDR Instruments Registered"
                      description="Your institution has not submitted any security deposit instruments to AICTE yet."
                      actionLabel="Submit First FDR"
                      onAction={() => setIsFDRModalOpen(true)}
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* FDR Creation Modal */}
      <FDRFormModal
        isOpen={isFDRModalOpen}
        onClose={() => setIsFDRModalOpen(false)}
        onSuccess={() => fetchDashboardData()}
      />

      {/* Document Upload Modal */}
      {selectedFDRForDoc && (
        <DocumentUploadModal
          isOpen={!!selectedFDRForDoc}
          onClose={() => setSelectedFDRForDoc(null)}
          fdrId={selectedFDRForDoc.id}
          fdrNumber={selectedFDRForDoc.fdr_number}
          onSuccess={() => fetchDashboardData()}
        />
      )}
    </div>
  );
};

export default InstitutionDashboard;
