import React, { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import OCRComparisonModal from '../components/documents/OCRComparisonModal';
import { formatDateTime } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export const DocumentManagementPage = () => {
  const { isOfficial } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      // In backend, documents are listed via parent FDR or audit.
      // We can load active FDRs and collect their documents
      const fdrRes = await api.getFDRs({ per_page: 50 });
      const fdrsList = fdrRes.data || [];

      // Query documents for all retrieved FDRs
      const docPromises = fdrsList.map((fdr) =>
        api.getFDRDocuments(fdr.id).catch(() => ({ data: [] }))
      );
      const results = await Promise.all(docPromises);

      const allDocs = [];
      results.forEach((res, index) => {
        const parentFdr = fdrsList[index];
        const docs = res.data || [];
        docs.forEach((doc) => {
          allDocs.push({
            ...doc,
            fdr_record: parentFdr,
          });
        });
      });

      setDocuments(allDocs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDownload = async (doc) => {
    setDownloadingId(doc.id);
    try {
      const blob = await api.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.original_filename || `fdr_doc_${doc.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Icon name="upload" className="w-6 h-6 text-aicte-navy" />
            Secure Document Storage &amp; OCR Engine (Phase 5)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographic SHA-256 verification, local text extraction, and discrepancy auditing
          </p>
        </div>

        <button
          onClick={fetchDocuments}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition"
        >
          <Icon name="refreshCw" className="w-3.5 h-3.5 text-slate-500" />
          Refresh Documents
        </button>
      </div>

      {/* Security Architecture Info Callout */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="flex items-start gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 shrink-0">
            <Icon name="shield" className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800">SHA-256 Integrity Checksum</h4>
            <p className="text-slate-500 text-[11px] mt-0.5">Every file has a tamper-evident cryptographic hash.</p>
          </div>
        </div>

        <div className="flex items-start gap-2.5">
          <div className="p-2 rounded-lg bg-teal-100 text-teal-700 shrink-0">
            <Icon name="fileText" className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800">100% Local Inference</h4>
            <p className="text-slate-500 text-[11px] mt-0.5">No financial data is sent to external cloud AI APIs.</p>
          </div>
        </div>

        <div className="flex items-start gap-2.5">
          <div className="p-2 rounded-lg bg-blue-100 text-blue-700 shrink-0">
            <Icon name="lock" className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800">Tenant Isolation</h4>
            <p className="text-slate-500 text-[11px] mt-0.5">Cross-institution document downloads are strictly prohibited.</p>
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <Card noPadding title="Uploaded FDR Certificates & Supporting Documents" subtitle="Verified files held in private storage">
        {loading ? (
          <LoadingSpinner message="Scanning secure storage directories and OCR results..." />
        ) : documents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Doc ID</th>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Linked FDR</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">SHA-256 Hash</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-center">OCR Check</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => {
                  const hasOcr = doc.ocr_result !== undefined && doc.ocr_result !== null;
                  const hasDiscrepancy = doc.ocr_result?.has_discrepancy;

                  return (
                    <tr key={doc.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4 font-mono font-bold text-slate-800">#{doc.id}</td>
                      <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                        <Icon name="fileText" className="w-4 h-4 text-aicte-navy shrink-0" />
                        <span className="truncate max-w-xs">{doc.original_filename}</span>
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-slate-700">
                        {doc.fdr_record?.fdr_number || `#${doc.fdr_record_id}`}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {((doc.file_size_bytes || 0) / 1024).toFixed(1)} KB
                      </td>
                      <td className="py-3 px-4 font-mono text-[10px] text-slate-400 max-w-[120px] truncate" title={doc.file_hash}>
                        {doc.file_hash ? `${doc.file_hash.substring(0, 16)}...` : 'Pending'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge status={doc.processing_status} />
                      </td>
                      <td className="py-3 px-4 text-center">
                        {hasOcr ? (
                          hasDiscrepancy ? (
                            <span className="px-2 py-0.5 rounded-full font-bold bg-rose-100 text-rose-700 text-[10px]">
                              DISCREPANCY
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-700 text-[10px]">
                              MATCH
                            </span>
                          )
                        ) : (
                          <span className="text-slate-400 font-medium">Pending OCR</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleDownload(doc)}
                            disabled={downloadingId === doc.id}
                            title="Download Document"
                            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition"
                          >
                            <Icon name="download" className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setSelectedDoc(doc)}
                            className="px-2.5 py-1 rounded-lg bg-aicte-light hover:bg-aicte-navy hover:text-white text-aicte-navy font-semibold text-[11px] transition"
                          >
                            Inspect OCR
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12">
            <EmptyState
              title="No Documents Uploaded"
              description="No scanned FDR supporting documents have been uploaded in the current scope."
            />
          </div>
        )}
      </Card>

      {/* OCR Discrepancy Inspect Modal */}
      {selectedDoc && (
        <OCRComparisonModal
          isOpen={!!selectedDoc}
          onClose={() => setSelectedDoc(null)}
          document={selectedDoc}
          onReviewSuccess={() => fetchDocuments()}
        />
      )}
    </div>
  );
};

export default DocumentManagementPage;
