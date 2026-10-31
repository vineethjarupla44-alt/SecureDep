import React from 'react';
import Badge from '../common/Badge';
import { getRiskColor } from '../../utils/formatters';

export const RiskRadarGauge = ({ score = 0, category = 'LOW', ruleScore = 0, mlScore = 0, size = 180 }) => {
  const clampedScore = Math.min(Math.max(parseFloat(score) || 0, 0), 100);
  const color = getRiskColor(category);

  // SVG Gauge calculations (semi-circle arc from 180deg to 360deg)
  const radius = 70;
  const strokeWidth = 14;
  const circumference = Math.PI * radius; // Half-circle perimeter
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  let gaugeColor = '#10B981'; // Green
  if (clampedScore >= 80) gaugeColor = '#EF4444'; // Red
  else if (clampedScore >= 60) gaugeColor = '#F97316'; // Orange
  else if (clampedScore >= 30) gaugeColor = '#F59E0B'; // Amber

  return (
    <div className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-slate-200">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size * 0.65 }}>
        <svg width={size} height={size * 0.65} viewBox="0 0 180 110" className="overflow-visible">
          {/* Background Track Arc */}
          <path
            d="M 20 100 A 70 70 0 0 1 160 100"
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Value Arc */}
          <path
            d="M 20 100 A 70 70 0 0 1 160 100"
            fill="none"
            stroke={gaugeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Score Overlay */}
        <div className="absolute bottom-2 flex flex-col items-center">
          <span className="text-3xl font-extrabold text-slate-900 leading-none">{clampedScore.toFixed(1)}</span>
          <span className="text-[10px] font-bold text-slate-400 uppercase mt-0.5">out of 100</span>
        </div>
      </div>

      {/* Category Pill */}
      <div className="mt-2">
        <Badge variant={`risk-${category.toLowerCase()}`} size="md">
          {category} RISK
        </Badge>
      </div>

      {/* Deterministic vs ML Separation Breakdown */}
      <div className="w-full mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-center text-xs">
        <div className="p-2 rounded-lg bg-slate-50">
          <p className="text-[10px] text-slate-500 font-semibold uppercase">Rule Score (70%)</p>
          <p className="font-bold text-slate-800 text-sm mt-0.5">{ruleScore.toFixed(1)}</p>
        </div>
        <div className="p-2 rounded-lg bg-slate-50">
          <p className="text-[10px] text-slate-500 font-semibold uppercase">ML Anomaly (30%)</p>
          <p className="font-bold text-slate-800 text-sm mt-0.5">{mlScore.toFixed(1)}</p>
        </div>
      </div>
    </div>
  );
};

export default RiskRadarGauge;
