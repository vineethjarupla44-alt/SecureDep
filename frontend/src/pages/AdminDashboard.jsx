import React, { useState, useEffect } from 'react';
import Card, { MetricCard } from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import Modal from '../components/common/Modal';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import api from '../services/api';

export const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('telemetry'); // 'telemetry' | 'users' | 'institutions'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [institutionsCount, setInstitutionsCount] = useState(0);
  const [auditLogs, setAuditLogs] = useState([]);
  const [complianceSummary, setComplianceSummary] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  // User management state
  const [users, setUsers] = useState([]);
  const [userStatusFilter, setUserStatusFilter] = useState('ALL');
  const [userSearch, setUserSearch] = useState('');
  const [usersLoading, setUsersLoading] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  // Institution management state
  const [institutionsList, setInstitutionsList] = useState([]);
  const [instLoading, setInstLoading] = useState(false);
  const [isAddInstModalOpen, setIsAddInstModalOpen] = useState(false);
  const [newInstData, setNewInstData] = useState({
    institution_code: '',
    name: '',
    address: '',
    contact_email: '',
  });
  const [instFormError, setInstFormError] = useState(null);
  const [instSubmitting, setInstSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [maturityRes, instRes, auditRes, compRes, pendingUsersRes] = await Promise.allSettled([
        api.getMaturitySummary(),
        api.getInstitutions({ per_page: 1 }),
        api.getAuditLogs({ per_page: 6 }),
        api.getGlobalComplianceSummary(),
        api.getAdminUsers({ status: 'PENDING' }),
      ]);

      if (maturityRes.status === 'fulfilled') setSummary(maturityRes.value?.data);
      if (instRes.status === 'fulfilled') setInstitutionsCount(instRes.value?.total || 0);
      if (auditRes.status === 'fulfilled') setAuditLogs(auditRes.value?.data || []);
      if (compRes.status === 'fulfilled') setComplianceSummary(compRes.value);
      if (pendingUsersRes.status === 'fulfilled') setPendingCount(pendingUsersRes.value?.total || 0);
    } catch (err) {
      setError('Failed to load administrative telemetry.');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    setUsersLoading(true);
    try {
      const params = {};
      if (userStatusFilter !== 'ALL') params.status = userStatusFilter;
      if (userSearch.trim()) params.search = userSearch.trim();
      const res = await api.getAdminUsers(params);
      setUsers(res?.data || []);
      if (userStatusFilter === 'ALL' && !userSearch) {
        const pending = (res?.data || []).filter((u) => u.account_status === 'PENDING').length;
        setPendingCount(pending);
      }
    } catch (err) {
      console.error('Failed to load users list:', err);
    } finally {
      setUsersLoading(false);
    }
  };

  const fetchInstitutions = async () => {
    setInstLoading(true);
    try {
      const res = await api.getInstitutions({ per_page: 50 });
      setInstitutionsList(res?.data || []);
    } catch (err) {
      console.error('Failed to load institutions:', err);
    } finally {
      setInstLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    if (activeTab === 'institutions') fetchInstitutions();
  }, [activeTab, userStatusFilter]);

  const handleUserStatusUpdate = async (userId, targetStatus, userEmail) => {
    try {
      const remarks = prompt(
        `Enter administrative remarks for updating ${userEmail} to ${targetStatus}:`,
        `Administrative status change to ${targetStatus}`
      );
      if (remarks === null) return; // User cancelled

      await api.updateUserStatus(userId, targetStatus, remarks);
      setActionMessage(`Account for ${userEmail} successfully updated to ${targetStatus}.`);
      fetchUsers();
      fetchData();
    } catch (e) {
      alert(`Failed to update user status: ${e.message}`);
    }
  };

  const handleCreateInstitution = async (e) => {
    e.preventDefault();
    setInstFormError(null);
    setInstSubmitting(true);
    try {
      await api.createInstitution(newInstData);
      setActionMessage(`Institution '${newInstData.name}' created successfully.`);
      setIsAddInstModalOpen(false);
      setNewInstData({ institution_code: '', name: '', address: '', contact_email: '' });
      fetchInstitutions();
      fetchData();
    } catch (err) {
      setInstFormError(err.message || 'Failed to create institution.');
    } finally {
      setInstSubmitting(false);
    }
  };

  const handleTriggerMaturity = async () => {
    try {
      setActionMessage('Running automated maturity scan across database...');
      const res = await api.triggerMaturityScan();
      setActionMessage(`Scan completed: ${res.alerts_created || 0} alerts dispatched, ${res.skipped_duplicates || 0} duplicates skipped.`);
      fetchData();
    } catch (e) {
      setActionMessage(`Maturity scan failed: ${e.message}`);
    }
  };

  const handleTriggerDuplicates = async () => {
    try {
      setActionMessage('Running multi-algorithm duplicate FDR scan...');
      const res = await api.triggerDuplicateScan();
      setActionMessage(`Duplicate scan completed: ${res.data?.total_fdrs_scanned || 0} scanned, ${res.data?.new_candidates_created || 0} candidates flagged.`);
      fetchData();
    } catch (e) {
      setActionMessage(`Duplicate scan failed: ${e.message}`);
    }
  };

  if (loading) return <LoadingSpinner message="Aggregating Council-wide administrative telemetry..." />;

  const counts = summary?.counts || {};
  const sums = summary?.sums || {};

  return (
    <div className="space-y-6">
      {/* Page Title & Tab Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="dashboard" className="w-6 h-6 text-aicte-navy" />
            Executive Central Administration Dashboard
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time portfolio monitoring, institutional user provisioning, and regulatory governance
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              fetchData();
              if (activeTab === 'users') fetchUsers();
              if (activeTab === 'institutions') fetchInstitutions();
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition"
          >
            <Icon name="refreshCw" className="w-3.5 h-3.5 text-slate-500" />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-2">
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`py-2 px-4 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            activeTab === 'telemetry'
              ? 'border-aicte-navy text-aicte-navy'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Icon name="shield" className="w-4 h-4" />
          Council Telemetry & Operations
        </button>

        <button
          onClick={() => setActiveTab('users')}
          className={`py-2 px-4 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            activeTab === 'users'
              ? 'border-aicte-navy text-aicte-navy'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Icon name="user" className="w-4 h-4" />
          Access Requests & User Accounts
          {pendingCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-extrabold rounded-full bg-amber-500 text-white">
              {pendingCount} Pending
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('institutions')}
          className={`py-2 px-4 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
            activeTab === 'institutions'
              ? 'border-aicte-navy text-aicte-navy'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Icon name="building" className="w-4 h-4" />
          Affiliated Institutions Registry
        </button>
      </div>

      {actionMessage && (
        <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-blue-500 hover:text-blue-700 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 1: COUNCIL TELEMETRY & OPERATIONS */}
      {/* ========================================================================= */}
      {activeTab === 'telemetry' && (
        <div className="space-y-6">
          {/* Top 4 Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Affiliated Institutions"
              value={institutionsCount}
              subtitle="Enrolled under AICTE Act"
              icon="building"
              color="navy"
            />

            <MetricCard
              title="Active Deposit Capital"
              value={formatCurrency(sums.ACTIVE || 0)}
              subtitle={`${counts.ACTIVE || 0} Active FDR Instruments`}
              icon="shield"
              color="teal"
            />

            <MetricCard
              title="Expiring Within 30 Days"
              value={counts.EXPIRING_SOON || 0}
              subtitle={formatCurrency(sums.EXPIRING_SOON || 0)}
              icon="calendar"
              color="amber"
            />

            <MetricCard
              title="Pending User Approvals"
              value={pendingCount}
              subtitle="Institutional registration queue"
              icon="clock"
              color={pendingCount > 0 ? 'amber' : 'teal'}
            />
          </div>

          {/* Secondary Metrics Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-4 bg-white rounded-xl border border-slate-200">
              <span className="text-slate-500 font-bold uppercase text-[10px]">Renewed Instruments</span>
              <p className="text-xl font-extrabold text-slate-800 mt-1">{counts.RENEWED || 0}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{formatCurrency(sums.RENEWED || 0)}</p>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200">
              <span className="text-slate-500 font-bold uppercase text-[10px]">Sanctioned Releases</span>
              <p className="text-xl font-extrabold text-slate-800 mt-1">{counts.RELEASED || 0}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{formatCurrency(sums.RELEASED || 0)}</p>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200">
              <span className="text-slate-500 font-bold uppercase text-[10px]">Matured & Overdue</span>
              <p className="text-xl font-extrabold text-rose-700 mt-1">{counts.MATURED || 0}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{formatCurrency(sums.MATURED || 0)}</p>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200">
              <span className="text-slate-500 font-bold uppercase text-[10px]">Total Instruments</span>
              <p className="text-xl font-extrabold text-slate-800 mt-1">{summary?.total_fdrs || 0}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Across all branches</p>
            </div>
          </div>

          {/* Compliance & Quick Action Center */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card title="Council Compliance Grading Distribution" subtitle="Institutional grades under regulatory rules" icon="brain">
              <div className="space-y-3">
                {complianceSummary?.grade_distribution ? (
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200">
                      <span className="text-xl font-black text-emerald-700">A</span>
                      <p className="text-xs font-bold text-slate-800 mt-1">{complianceSummary.grade_distribution.A || 0}</p>
                      <p className="text-[10px] text-slate-500">Exemplary</p>
                    </div>
                    <div className="p-3 rounded-xl bg-teal-50 border border-teal-200">
                      <span className="text-xl font-black text-teal-700">B</span>
                      <p className="text-xs font-bold text-slate-800 mt-1">{complianceSummary.grade_distribution.B || 0}</p>
                      <p className="text-[10px] text-slate-500">Good</p>
                    </div>
                    <div className="p-3 rounded-xl bg-amber-50 border border-amber-200">
                      <span className="text-xl font-black text-amber-700">C</span>
                      <p className="text-xs font-bold text-slate-800 mt-1">{complianceSummary.grade_distribution.C || 0}</p>
                      <p className="text-[10px] text-slate-500">Attention</p>
                    </div>
                    <div className="p-3 rounded-xl bg-rose-50 border border-rose-200">
                      <span className="text-xl font-black text-rose-700">D</span>
                      <p className="text-xs font-bold text-slate-800 mt-1">{complianceSummary.grade_distribution.D || 0}</p>
                      <p className="text-[10px] text-slate-500">Intervention</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 py-4 text-center">No compliance summary available.</p>
                )}

                <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
                  <p className="font-semibold text-slate-800">Scoring Architecture:</p>
                  <p className="text-[11px] text-slate-500 leading-normal">
                    Letter grades are dynamically computed based on unresolved overdue instruments, document discrepancy logs, and duplicate submissions.
                  </p>
                </div>
              </div>
            </Card>

            <Card title="Automated Regulatory Operations" subtitle="Execute scheduled background audits" icon="shield" className="lg:col-span-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
                  <div>
                    <h4 className="font-bold text-xs text-slate-800">Maturity Scanner</h4>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Scans all active instruments against business date. Generates idempotent 30d/15d/7d alerts.
                    </p>
                  </div>
                  <button
                    onClick={handleTriggerMaturity}
                    className="mt-3 w-full py-2 px-3 rounded-lg bg-aicte-navy text-white text-xs font-semibold hover:bg-aicte-dark transition"
                  >
                    Trigger Maturity Scan
                  </button>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
                  <div>
                    <h4 className="font-bold text-xs text-slate-800">Intelligent Duplicate Detector</h4>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Runs Levenshtein string matching, cross-institution bank checks, and SHA-256 hash collision scans.
                    </p>
                  </div>
                  <button
                    onClick={handleTriggerDuplicates}
                    className="mt-3 w-full py-2 px-3 rounded-lg bg-aicte-teal text-white text-xs font-semibold hover:bg-teal-700 transition"
                  >
                    Run Duplicate Scan
                  </button>
                </div>
              </div>
            </Card>
          </div>

          {/* Audit Trail */}
          <Card title="Live Administrative Audit Trail (Phase 7)" subtitle="Tamper-evident system activity log" icon="history">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Timestamp (IST)</th>
                    <th className="py-2.5 px-4">Action</th>
                    <th className="py-2.5 px-4">Entity</th>
                    <th className="py-2.5 px-4">Actor</th>
                    <th className="py-2.5 px-4">Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {auditLogs.length > 0 ? (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-4 text-slate-500 whitespace-nowrap">{formatDateTime(log.created_at)}</td>
                        <td className="py-2.5 px-4 font-mono font-bold text-aicte-navy">{log.action}</td>
                        <td className="py-2.5 px-4 text-slate-700">
                          <span className="font-semibold">{log.entity_type}</span>
                          {log.entity_id && <span className="text-slate-400"> #{log.entity_id}</span>}
                        </td>
                        <td className="py-2.5 px-4 text-slate-800 font-medium">{log.user?.full_name || 'System'}</td>
                        <td className="py-2.5 px-4 text-slate-600 max-w-xs truncate">{log.remarks || 'No remarks'}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-400">
                        No recent audit trail entries found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: ACCESS REQUESTS & USER ACCOUNTS */}
      {/* ========================================================================= */}
      {activeTab === 'users' && (
        <Card
          title="Institutional User Management & Registration Queue"
          subtitle="Review applicant credentials and manage institutional account lifecycle"
          icon="user"
        >
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-medium w-full sm:w-auto">
              {['ALL', 'PENDING', 'ACTIVE', 'REJECTED', 'SUSPENDED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setUserStatusFilter(st)}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    userStatusFilter === st
                      ? 'bg-white shadow text-aicte-navy font-bold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {st}
                  {st === 'PENDING' && pendingCount > 0 && (
                    <span className="ml-1 px-1.5 py-0.2 bg-amber-500 text-white rounded-full text-[10px]">
                      {pendingCount}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="w-full sm:w-72">
              <input
                type="text"
                placeholder="Search user name or email..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchUsers()}
                className="w-full px-3 py-1.5 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-aicte-navy"
              />
            </div>
          </div>

          {usersLoading ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              <LoadingSpinner message="Loading user registry..." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">User Details</th>
                    <th className="py-2.5 px-4">Role</th>
                    <th className="py-2.5 px-4">Affiliated Institution</th>
                    <th className="py-2.5 px-4">Registration Date</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4 text-right">Administrative Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.length > 0 ? (
                    users.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-4">
                          <p className="font-bold text-slate-900">{u.full_name}</p>
                          <p className="text-[11px] text-slate-500 font-mono">{u.email}</p>
                        </td>
                        <td className="py-2.5 px-4">
                          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                            {u.role}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-700">
                          {u.institution ? (
                            <div>
                              <p className="font-semibold text-slate-800">{u.institution.name}</p>
                              <p className="text-[10px] font-mono text-slate-400">{u.institution.institution_code}</p>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Central AICTE / Council</span>
                          )}
                        </td>
                        <td className="py-2.5 px-4 text-slate-500 whitespace-nowrap">
                          {formatDateTime(u.created_at)}
                        </td>
                        <td className="py-2.5 px-4">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                              u.account_status === 'ACTIVE'
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : u.account_status === 'PENDING'
                                ? 'bg-amber-100 text-amber-800 border border-amber-300 animate-pulse'
                                : u.account_status === 'REJECTED'
                                ? 'bg-rose-100 text-rose-800 border border-rose-300'
                                : 'bg-slate-100 text-slate-600 border border-slate-300'
                            }`}
                          >
                            {u.account_status}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-right whitespace-nowrap">
                          {u.account_status === 'PENDING' ? (
                            <div className="inline-flex gap-1.5">
                              <button
                                onClick={() => handleUserStatusUpdate(u.id, 'ACTIVE', u.email)}
                                className="px-2.5 py-1 rounded-lg bg-emerald-600 text-white font-bold hover:bg-emerald-700 text-[11px] shadow-sm transition"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleUserStatusUpdate(u.id, 'REJECTED', u.email)}
                                className="px-2.5 py-1 rounded-lg bg-rose-600 text-white font-bold hover:bg-rose-700 text-[11px] shadow-sm transition"
                              >
                                Reject
                              </button>
                            </div>
                          ) : u.account_status === 'ACTIVE' ? (
                            <button
                              onClick={() => handleUserStatusUpdate(u.id, 'SUSPENDED', u.email)}
                              className="px-2.5 py-1 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 text-[11px] font-semibold transition"
                            >
                              Suspend
                            </button>
                          ) : (
                            <button
                              onClick={() => handleUserStatusUpdate(u.id, 'ACTIVE', u.email)}
                              className="px-2.5 py-1 rounded-lg border border-emerald-200 text-emerald-700 hover:bg-emerald-50 text-[11px] font-semibold transition"
                            >
                              Re-activate
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        No registered users found matching current filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: AFFILIATED INSTITUTIONS REGISTRY */}
      {/* ========================================================================= */}
      {activeTab === 'institutions' && (
        <Card
          title="Accredited Institutions Directory"
          subtitle="Official list of higher education institutions maintaining FDR security deposits"
          icon="building"
          action={
            <button
              onClick={() => setIsAddInstModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-aicte-navy text-white text-xs font-bold hover:bg-aicte-dark shadow-sm transition"
            >
              <Icon name="plus" className="w-3.5 h-3.5" />
              Enroll New Institution
            </button>
          }
        >
          {instLoading ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              <LoadingSpinner message="Fetching accredited institutions..." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Database ID</th>
                    <th className="py-2.5 px-4">AICTE Code</th>
                    <th className="py-2.5 px-4">Institution Name</th>
                    <th className="py-2.5 px-4">Campus Address</th>
                    <th className="py-2.5 px-4">Official Contact Email</th>
                    <th className="py-2.5 px-4 text-center">FDR Count</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {institutionsList.length > 0 ? (
                    institutionsList.map((inst) => (
                      <tr key={inst.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-4 font-mono font-bold text-slate-500">#{inst.id}</td>
                        <td className="py-2.5 px-4 font-mono font-bold text-aicte-navy">{inst.institution_code}</td>
                        <td className="py-2.5 px-4 font-bold text-slate-900">{inst.name}</td>
                        <td className="py-2.5 px-4 text-slate-600 max-w-xs truncate">{inst.address}</td>
                        <td className="py-2.5 px-4 text-slate-700 font-mono text-[11px]">{inst.contact_email}</td>
                        <td className="py-2.5 px-4 text-center font-bold text-slate-800">{inst.fdr_count || 0}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        No institutions enrolled in database. Use 'Enroll New Institution' button to add records.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Enroll Institution Modal */}
      <Modal
        isOpen={isAddInstModalOpen}
        onClose={() => setIsAddInstModalOpen(false)}
        title="Enroll Accredited Educational Institution"
        subtitle="Provision a verified institutional record in the AICTE FDR Directory"
      >
        <form onSubmit={handleCreateInstitution} className="space-y-4 text-xs">
          {instFormError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 font-semibold">
              {instFormError}
            </div>
          )}

          <div>
            <label className="block font-bold text-slate-700 mb-1">AICTE Institution Code *</label>
            <input
              type="text"
              required
              value={newInstData.institution_code}
              onChange={(e) => setNewInstData({ ...newInstData, institution_code: e.target.value })}
              placeholder="e.g. 1-1009876 or 1-DEMO-005"
              className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy font-mono"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Full Institution Name *</label>
            <input
              type="text"
              required
              value={newInstData.name}
              onChange={(e) => setNewInstData({ ...newInstData, name: e.target.value })}
              placeholder="e.g. Hyderabad Institute of Technology"
              className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Campus Physical Address *</label>
            <textarea
              required
              rows={3}
              value={newInstData.address}
              onChange={(e) => setNewInstData({ ...newInstData, address: e.target.value })}
              placeholder="e.g. Survey No. 45, Tech City Road, Hyderabad, Telangana 500081"
              className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Official Contact Email *</label>
            <input
              type="email"
              required
              value={newInstData.contact_email}
              onChange={(e) => setNewInstData({ ...newInstData, contact_email: e.target.value })}
              placeholder="e.g. finance@hit.edu.in"
              className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsAddInstModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={instSubmitting}
              className="px-4 py-2 rounded-xl bg-aicte-navy text-white font-bold hover:bg-aicte-dark shadow transition disabled:opacity-50"
            >
              {instSubmitting ? 'Enrolling Institution...' : 'Enroll Institution'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default AdminDashboard;
