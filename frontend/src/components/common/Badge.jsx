import React from 'react';
import { getStatusColor, getRiskColor } from '../../utils/formatters';

export const Badge = ({ children, status, variant = 'default', size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-semibold',
    lg: 'px-3 py-1.5 text-sm font-semibold',
  };

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-200';

  if (status) {
    colorClasses = getStatusColor(status);
  } else if (variant === 'risk-low') {
    colorClasses = getRiskColor('LOW').badge;
  } else if (variant === 'risk-medium') {
    colorClasses = getRiskColor('MEDIUM').badge;
  } else if (variant === 'risk-high') {
    colorClasses = getRiskColor('HIGH').badge;
  } else if (variant === 'risk-critical') {
    colorClasses = getRiskColor('CRITICAL').badge;
  } else if (variant === 'primary') {
    colorClasses = 'bg-aicte-navy text-white border-transparent';
  } else if (variant === 'teal') {
    colorClasses = 'bg-teal-50 text-teal-800 border-teal-200';
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border ${sizeClasses[size]} ${colorClasses} ${className}`}
    >
      {children || status}
    </span>
  );
};

export default Badge;
