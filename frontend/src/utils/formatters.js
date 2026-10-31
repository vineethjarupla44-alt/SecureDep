/**
 * Utility formatters for AICTE FDR Portal
 */

export const formatCurrency = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) return '₹0.00';
  const num = parseFloat(amount);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(num);
};

export const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch (e) {
    return dateStr;
  }
};

export const formatDateTime = (dateStr) => {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (e) {
    return dateStr;
  }
};

export const formatRoleName = (role) => {
  switch (role) {
    case 'administrator':
      return 'System Administrator';
    case 'aicte_official':
      return 'AICTE Regulatory Official';
    case 'institution_user':
      return 'Institution Finance Officer';
    default:
      return role ? role.replace(/_/g, ' ').toUpperCase() : 'User';
  }
};

export const getStatusColor = (status) => {
  switch (status) {
    case 'ACTIVE':
    case 'APPROVED':
    case 'PROCESSED':
    case 'VERIFIED':
    case 'ACCEPTED':
    case 'RESOLVED':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    case 'PENDING':
    case 'PENDING_SCRUTINY':
    case 'UNDER_REVIEW':
    case 'UNREVIEWED':
    case 'EXPIRING_SOON':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'MATURED':
    case 'OVERDUE':
    case 'REJECTED':
    case 'CONFIRMED_DUPLICATE':
    case 'FAILED':
      return 'bg-rose-100 text-rose-800 border-rose-200';
    case 'RELEASED':
    case 'RELEASED_CLOSED':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'RENEWED':
    case 'LIEN_MARKED':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200';
    case 'CORRECTION_REQUIRED':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
};

export const getRiskColor = (category) => {
  switch (category) {
    case 'LOW':
      return { text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300', badge: 'bg-emerald-100 text-emerald-800' };
    case 'MEDIUM':
      return { text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-300', badge: 'bg-amber-100 text-amber-800' };
    case 'HIGH':
      return { text: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-300', badge: 'bg-orange-100 text-orange-800' };
    case 'CRITICAL':
      return { text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-300', badge: 'bg-rose-100 text-rose-800' };
    default:
      return { text: 'text-slate-700', bg: 'bg-slate-50', border: 'border-slate-300', badge: 'bg-slate-100 text-slate-800' };
  }
};
