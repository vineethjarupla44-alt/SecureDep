import React from 'react';

export const ComplianceGradeBadge = ({ grade = 'B', score = 85, size = 'md' }) => {
  const gradeStyles = {
    A: {
      bg: 'bg-emerald-500',
      lightBg: 'bg-emerald-50',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
      label: 'Exemplary Compliance',
    },
    B: {
      bg: 'bg-teal-500',
      lightBg: 'bg-teal-50',
      text: 'text-teal-700',
      border: 'border-teal-200',
      label: 'Good Standing',
    },
    C: {
      bg: 'bg-amber-500',
      lightBg: 'bg-amber-50',
      text: 'text-amber-700',
      border: 'border-amber-200',
      label: 'Attention Required',
    },
    D: {
      bg: 'bg-rose-500',
      lightBg: 'bg-rose-50',
      text: 'text-rose-700',
      border: 'border-rose-200',
      label: 'Regulatory Intervention',
    },
  };

  const current = gradeStyles[grade] || gradeStyles.B;

  return (
    <div className={`inline-flex items-center gap-2.5 px-3 py-1.5 rounded-xl border ${current.lightBg} ${current.border}`}>
      <div className={`w-7 h-7 rounded-lg ${current.bg} text-white flex items-center justify-center font-black text-sm shadow-xs`}>
        {grade}
      </div>
      <div>
        <div className="flex items-center gap-1.5">
          <span className={`text-xs font-bold ${current.text}`}>Grade {grade}</span>
          <span className="text-[10px] text-slate-500 font-semibold">({score.toFixed(1)}/100)</span>
        </div>
        <p className="text-[10px] text-slate-500 font-medium leading-none mt-0.5">{current.label}</p>
      </div>
    </div>
  );
};

export default ComplianceGradeBadge;
