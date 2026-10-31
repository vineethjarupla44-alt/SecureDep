import React from 'react';

export const LoadingSpinner = ({ size = 'md', message = 'Loading regulatory records...' }) => {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div
        className={`${sizeMap[size]} border-aicte-light border-t-aicte-navy rounded-full animate-spin mb-3`}
      />
      {message && <p className="text-sm font-medium text-slate-500 animate-pulse">{message}</p>}
    </div>
  );
};

export const TableSkeleton = ({ rows = 5, cols = 6 }) => {
  return (
    <div className="animate-pulse space-y-3 p-4">
      <div className="h-8 bg-slate-200 rounded w-full mb-4"></div>
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="flex gap-4">
          {[...Array(cols)].map((_, j) => (
            <div key={j} className="h-6 bg-slate-100 rounded flex-1"></div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default LoadingSpinner;
