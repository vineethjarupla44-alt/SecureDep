import React from 'react';
import Icon from './Icons';

export const EmptyState = ({
  icon = 'fileText',
  title = 'No records found',
  description = 'There are no active entries matching your current filters or institution scope.',
  actionLabel,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 mb-4 border border-slate-200">
        <Icon name={icon} className="w-8 h-8" />
      </div>
      <h3 className="text-base font-bold text-slate-700">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm mt-1">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-aicte-navy text-white text-xs font-semibold rounded-lg hover:bg-aicte-dark transition shadow-sm"
        >
          <Icon name="plus" className="w-4 h-4" />
          {actionLabel}
        </button>
      )}
    </div>
  );
};

export default EmptyState;
