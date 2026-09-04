import React from 'react';
import { AlertTriangle, CheckCircle2, ShieldQuestion } from 'lucide-react';
import type { EvidenceObject } from '../types';

interface EvidenceCardProps {
  evidence: EvidenceObject;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ evidence }) => {
  const percentScore = evidence.score != null ? Math.round(evidence.score * 100) : 0;
  const percentConf = Math.round(evidence.confidence * 100);

  const getScoreColor = (score: number | null) => {
    if (score == null) return 'bg-slate-300';
    if (score >= 0.75) return 'bg-emerald-500';
    if (score >= 0.50) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  const getStatusIcon = (score: number | null, available: boolean) => {
    if (!available || score == null) return <ShieldQuestion className="w-4 h-4 text-slate-400" />;
    if (score >= 0.75) return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
    return <AlertTriangle className="w-4 h-4 text-rose-600" />;
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getStatusIcon(evidence.score, evidence.availability)}
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            {evidence.type}
          </h4>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
          <span>{evidence.availability ? `${percentScore}%` : 'N/A'}</span>
          <span className="text-[10px] text-slate-400">({percentConf}% cert)</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-2.5">
        <div
          className={`h-full ${getScoreColor(evidence.score)} transition-all duration-500`}
          style={{ width: `${evidence.availability ? percentScore : 0}%` }}
        />
      </div>

      <p className="text-xs text-slate-600 leading-relaxed line-clamp-2">
        {evidence.explanation}
      </p>

      {evidence.warnings && evidence.warnings.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-1 text-[11px] text-amber-700 font-medium">
          <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
          <span className="truncate">{evidence.warnings[0]}</span>
        </div>
      )}

      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400 pt-1">
        <span className="truncate">Src: {evidence.source}</span>
        <span>v{evidence.model_version}</span>
      </div>
    </div>
  );
};

