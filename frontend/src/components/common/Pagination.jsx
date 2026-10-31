import React from 'react';
import Icon from './Icons';

export const Pagination = ({ currentPage, totalPages, totalItems, onPageChange, perPage = 10 }) => {
  if (totalPages <= 1 && totalItems <= perPage) return null;

  return (
    <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200 bg-white">
      <div className="text-xs text-slate-500">
        Showing page <span className="font-semibold text-slate-700">{currentPage}</span> of{' '}
        <span className="font-semibold text-slate-700">{totalPages || 1}</span>
        {totalItems !== undefined && (
          <span>
            {' '}(total <span className="font-semibold text-slate-700">{totalItems}</span> records)
          </span>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <button
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
          title="Previous Page"
        >
          <Icon name="chevronLeft" className="w-4 h-4" />
        </button>

        <span className="px-3 py-1 text-xs font-semibold bg-aicte-light text-aicte-navy rounded-md">
          {currentPage}
        </span>

        <button
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
          title="Next Page"
        >
          <Icon name="chevronRight" className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default Pagination;
