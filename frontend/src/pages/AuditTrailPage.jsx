import React, { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Pagination from '../components/common/Pagination';
import EmptyState from '../components/common/EmptyState';
import Modal from '../components/common/Modal';
import { formatDateTime } from '../utils/formatters';
import api from '../services/api';

export const AuditTrailPage = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Filters
  const [entityType, setEntityType] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  // Selected Log State Diff Modal
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchAuditLogs = async (targetPage = page) => {
    setLoading(true);
    try {
      const params = {
        page: targetPage,
        per_page: 15,
      };
      if (entityType) params.entity_type = entityType;
      if (actionFilter.trim()) params.action = actionFilter.trim();

      const res = await api.getAuditLogs(params);
      setLogs(res.data || []);
      setTotalPages(res.pages || 1);
      setTotalItems(res.total || 0);
      setPage(res.page || 1);
    } catch (err) {
      console.error('Failed to load audit trail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs(1);
  }, [entityType]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchAuditLogs(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="history" className="w-6 h-6 text-aicte-navy" />
            Immutable Audit Trail &amp; Forensic Log (Phase 7)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Tamper-evident, append-only regulatory event tracking with pre/post state differential snapshots
          </p>
        </div>

        <button
          onClick={() => fetchAuditLogs(page)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition"
        >
          <Icon name="refreshCw" className="w-3.5 h-3.5 text-slate-500" />
          Refresh Log
        </button>
      </div>

      {/* Filter and Query Bar */}
      <Card noPadding>
        <form onSubmit={handleSearchSubmit} className="p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
          <div className="flex-1 min-w-[220px] flex items-center gap-2">
            <input
              type="text"
              placeholder="Filter by action name (e.g. RELEASE_SCRUTINY, FDR_CREATED)..."
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-aicte-navy bg-white"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-slate-800 text-white text-xs font-semibold rounded-xl hover:bg-slate-900 transition"
            >
              Filter
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="px-3 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
            >
              <option value="">All Entity Classes</option>
              <option value="FDR_RECORD">FDR_RECORD</option>
              <option value="RELEASE_REQUEST">RELEASE_REQUEST</option>
              <option value="DOCUMENT">DOCUMENT</option>
              <option value="DUPLICATE_CANDIDATE">DUPLICATE_CANDIDATE</option>
              <option value="SYSTEM">SYSTEM</option>
            </select>

            {(entityType || actionFilter) && (
              <button
                type="button"
                onClick={() => {
                  setEntityType('');
                  setActionFilter('');
                  fetchAuditLogs(1);
                }}
                className="px-3 py-2 text-slate-500 hover:text-slate-700 font-semibold"
              >
                Clear
              </button>
            )}
          </div>
        </form>

        {/* Audit Log Table */}
        {loading ? (
          <LoadingSpinner message="Querying immutable audit records..." />
        ) : logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold border-y border-slate-200">
                <tr>
                  <th className="py-3 px-4">Event ID</th>
                  <th className="py-3 px-4">Timestamp (IST)</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Target Entity</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">IP Address</th>
                  <th className="py-3 px-4">Remarks</th>
                  <th className="py-3 px-4 text-right">State Diff</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-500">#{log.id}</td>
                    <td className="py-3 px-4 text-slate-600 whitespace-nowrap">{formatDateTime(log.created_at)}</td>
                    <td className="py-3 px-4 font-mono font-bold text-aicte-navy">{log.action}</td>
                    <td className="py-3 px-4 text-slate-700">
                      <span className="font-semibold block">{log.entity_type}</span>
                      {log.entity_id && <span className="text-[10px] text-slate-400 font-mono">ID: #{log.entity_id}</span>}
                    </td>
                    <td className="py-3 px-4 text-slate-800">
                      <span className="font-bold block">{log.user?.full_name || 'Automated Engine'}</span>
                      <span className="text-[10px] text-slate-400 block">{log.user?.role}</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-[10px] text-slate-500">{log.ip_address || '127.0.0.1'}</td>
                    <td className="py-3 px-4 text-slate-600 max-w-xs truncate" title={log.remarks}>
                      {log.remarks || '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {(log.previous_state || log.new_state || log.details) && (
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-aicte-navy hover:text-white text-slate-700 font-semibold text-[11px] transition"
                        >
                          View Diff
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12">
            <EmptyState
              title="No Audit Records Found"
              description="No audit trail events matched your query parameters."
            />
          </div>
        )}

        <Pagination
          currentPage={page}
          totalPages={totalPages}
          totalItems={totalItems}
          onPageChange={(p) => fetchAuditLogs(p)}
          perPage={15}
        />
      </Card>

      {/* State Diff Modal */}
      {selectedLog && (
        <Modal
          isOpen={!!selectedLog}
          onClose={() => setSelectedLog(null)}
          title={`Audit Event #${selectedLog.id}: ${selectedLog.action}`}
          subtitle={`Recorded on ${formatDateTime(selectedLog.created_at)} by ${selectedLog.user?.full_name || 'System'}`}
          maxWidth="max-w-3xl"
        >
          <div className="space-y-4 text-xs font-sans">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="font-bold text-slate-700">Remarks / Audit Note:</span>
              <p className="text-slate-600 mt-0.5">{selectedLog.remarks || 'No descriptive remarks entered.'}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Pre State */}
              <div>
                <span className="font-bold text-slate-700 block mb-1">Previous State (Before Mutation):</span>
                <pre className="p-3 bg-slate-900 text-slate-100 rounded-xl overflow-x-auto text-[11px] font-mono max-h-64">
                  {selectedLog.previous_state ? JSON.stringify(selectedLog.previous_state, null, 2) : 'null'}
                </pre>
              </div>

              {/* Post State */}
              <div>
                <span className="font-bold text-slate-700 block mb-1">New State (After Mutation):</span>
                <pre className="p-3 bg-slate-900 text-emerald-400 rounded-xl overflow-x-auto text-[11px] font-mono max-h-64">
                  {selectedLog.new_state ? JSON.stringify(selectedLog.new_state, null, 2) : selectedLog.details ? JSON.stringify(selectedLog.details, null, 2) : 'null'}
                </pre>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200"
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

export default AuditTrailPage;
