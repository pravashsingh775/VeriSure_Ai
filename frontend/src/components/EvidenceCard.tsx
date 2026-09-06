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
    if (score >= 0.75) return 'bg-gradient-to-r from-emerald-500 to-teal-500';
    if (score >= 0.50) return 'bg-gradient-to-r from-amber-500 to-orange-400';
    return 'bg-gradient-to-r from-rose-500 to-red-600';
  };

  const getStatusIcon = (score: number | null, available: boolean) => {
    if (!available || score == null) return <ShieldQuestion className="w-4 h-4 text-slate-400" />;
    if (score >= 0.75) return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
    return <AlertTriangle className="w-4 h-4 text-rose-600" />;
  };

  return (
    <div className="bg-white/95 backdrop-blur-xs p-4 sm:p-4.5 rounded-2xl border border-slate-200/90 shadow-[0_2px_10px_-2px_rgba(15,23,42,0.03)] hover-lift hover:border-blue-300/80 flex flex-col justify-between group">
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded-lg bg-slate-50 border border-slate-200/60 group-hover:bg-blue-50/50 transition-colors">
              {getStatusIcon(evidence.score, evidence.availability)}
            </div>
            <h4 className="text-xs font-black text-slate-800 uppercase tracking-wider">
              {evidence.type}
            </h4>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
            <span className={evidence.availability ? 'text-slate-900' : 'text-slate-400'}>
              {evidence.availability ? `${percentScore}%` : 'N/A'}
            </span>
            <span className="text-[10px] text-slate-400 font-medium">({percentConf}% cert)</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100/80 h-2 rounded-full overflow-hidden mb-2.5 border border-slate-200/40">
          <div
            className={`h-full ${getScoreColor(evidence.score)} transition-all duration-500 rounded-full`}
            style={{ width: `${evidence.availability ? percentScore : 0}%` }}
          />
        </div>

        <p className="text-xs text-slate-600 leading-relaxed line-clamp-2 font-medium">
          {evidence.explanation}
        </p>
      </div>

      <div>
        {evidence.warnings && evidence.warnings.length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center gap-1.5 text-[11px] text-amber-800 font-semibold bg-amber-50/60 p-1.5 rounded-lg border border-amber-100">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="truncate">{evidence.warnings[0]}</span>
          </div>
        )}

        <div className="mt-2.5 flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100/80">
          <span className="truncate font-medium">Src: {evidence.source}</span>
          <span className="font-mono bg-slate-100/80 px-1.5 py-0.5 rounded text-slate-500">v{evidence.model_version}</span>
        </div>
      </div>
    </div>
  );
};

