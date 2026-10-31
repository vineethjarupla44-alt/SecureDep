import React from 'react';
import Icon from './Icons';

export const Card = ({ children, className = '', title, subtitle, action, icon, noPadding = false }) => {
  return (
    <div className={`bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden ${className}`}>
      {(title || action) && (
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            {icon && (
              <div className="p-1.5 rounded-lg bg-aicte-light text-aicte-navy">
                <Icon name={icon} className="w-5 h-5" />
              </div>
            )}
            <div>
              <h3 className="text-base font-semibold text-slate-800">{title}</h3>
              {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-5'}>{children}</div>
    </div>
  );
};

export const MetricCard = ({ title, value, subtitle, icon, trend, color = 'navy', onClick }) => {
  const colorSchemes = {
    navy: { iconBg: 'bg-aicte-light text-aicte-navy', border: 'border-l-aicte-navy' },
    teal: { iconBg: 'bg-teal-50 text-aicte-teal', border: 'border-l-aicte-teal' },
    amber: { iconBg: 'bg-amber-50 text-amber-600', border: 'border-l-amber-500' },
    rose: { iconBg: 'bg-rose-50 text-rose-600', border: 'border-l-rose-500' },
    indigo: { iconBg: 'bg-indigo-50 text-indigo-600', border: 'border-l-indigo-500' },
  };

  const scheme = colorSchemes[color] || colorSchemes.navy;

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-slate-200 p-5 shadow-sm border-l-4 ${scheme.border} transition-all hover:shadow-md ${
        onClick ? 'cursor-pointer hover:-translate-y-0.5' : ''
      }`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <h4 className="text-2xl font-bold text-slate-800 mt-1">{value}</h4>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
        {icon && (
          <div className={`p-2.5 rounded-xl ${scheme.iconBg}`}>
            <Icon name={icon} className="w-6 h-6" />
          </div>
        )}
      </div>
      {trend && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center text-xs text-slate-600">
          {trend}
        </div>
      )}
    </div>
  );
};

export default Card;
