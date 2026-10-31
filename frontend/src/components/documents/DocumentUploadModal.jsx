import React, { useState } from 'react';
import Modal from '../common/Modal';
import Icon from '../common/Icons';
import api from '../../services/api';

export const DocumentUploadModal = ({ isOpen, onClose, fdrId, fdrNumber, onSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    setError(null);
    const validExtensions = ['pdf', 'png', 'jpg', 'jpeg'];
    const ext = selectedFile.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
      setError('Only PDF, PNG, and JPG files are supported under AICTE document standards.');
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File exceeds the 10 MB maximum upload limit.');
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please choose or drop an FDR supporting document.');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const res = await api.uploadFDRDocument(fdrId, file);
      if (onSuccess) onSuccess(res.data);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Upload Scanned FDR Document"
      subtitle={`Instrument: ${fdrNumber || `#${fdrId}`} &bull; Phase 5 Local OCR Processing`}
      maxWidth="max-w-md"
    >
      <form onSubmit={handleUpload} className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
            {error}
          </div>
        )}

        {/* Drag and Drop Box */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
            dragActive
              ? 'border-aicte-navy bg-aicte-light/50'
              : file
              ? 'border-emerald-400 bg-emerald-50/30'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
          }`}
          onClick={() => document.getElementById('fdr-doc-input').click()}
        >
          <input
            id="fdr-doc-input"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="hidden"
            onChange={handleFileChange}
          />

          <div className="flex flex-col items-center">
            {file ? (
              <>
                <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-2">
                  <Icon name="checkCircle" className="w-6 h-6" />
                </div>
                <p className="text-xs font-bold text-slate-800 truncate max-w-xs">{file.name}</p>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Ready for upload
                </p>
                <span className="text-[10px] text-aicte-teal font-semibold mt-2 underline">Click to choose another</span>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mb-2">
                  <Icon name="upload" className="w-6 h-6" />
                </div>
                <p className="text-xs font-bold text-slate-700">Drop scanned PDF, PNG or JPG here</p>
                <p className="text-[10px] text-slate-500 mt-1">or click to browse your computer (Max 10 MB)</p>
                <div className="flex gap-2 mt-3 text-[10px] text-slate-400 font-semibold uppercase">
                  <span>&bull; PDF (Text/Scan)</span>
                  <span>&bull; JPEG</span>
                  <span>&bull; PNG</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Security Notice */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1">
          <p className="font-semibold text-slate-800 flex items-center gap-1.5">
            <Icon name="shield" className="w-3.5 h-3.5 text-aicte-navy" />
            Security &amp; Privacy Verification:
          </p>
          <p className="text-slate-500 leading-normal">
            Documents are stored in a private directory with SHA-256 integrity hashing. OCR text extraction runs 100% locally on the backend.
          </p>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!file || uploading}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-aicte-navy text-white hover:bg-aicte-dark transition shadow-xs disabled:opacity-50"
          >
            {uploading ? 'Processing & Hashing...' : 'Upload & Process OCR'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default DocumentUploadModal;
