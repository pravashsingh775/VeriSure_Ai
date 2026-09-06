import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, HelpCircle, ShieldAlert, ShieldCheck } from 'lucide-react';
import type { DecisionResult, DecisionState } from '../types';

interface RiskBadgeProps {
  decision: DecisionResult;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ decision }) => {
  const getBadgeConfig = (state: DecisionState) => {
    switch (state) {
      case 'LIKELY_GENUINE':
        return {
          bg: 'bg-emerald-50 border-emerald-300 text-emerald-900',
          badgeBg: 'bg-emerald-600 text-white',
          icon: <ShieldCheck className="w-8 h-8 text-emerald-600" />,
          title: 'LIKELY GENUINE',
          subtitle: 'Packaging conforms closely to registered factory specifications (visual risk only).',
        };
      case 'LOW_RISK':
        return {
          bg: 'bg-green-50 border-green-300 text-green-900',
          badgeBg: 'bg-green-600 text-white',
          icon: <CheckCircle2 className="w-8 h-8 text-green-600" />,
          title: 'LOW RISK',
          subtitle: 'Low counterfeit risk based on packaging evidence (cannot verify internal contents).',
        };
      case 'MEDIUM_RISK':
        return {
          bg: 'bg-amber-50 border-amber-300 text-amber-900',
          badgeBg: 'bg-amber-500 text-white',
          icon: <AlertTriangle className="w-8 h-8 text-amber-600" />,
          title: 'MEDIUM RISK',
          subtitle: 'Noticeable variations detected. Verify retail source.',
        };
      case 'HIGH_RISK':
        return {
          bg: 'bg-orange-50 border-orange-300 text-orange-900',
          badgeBg: 'bg-orange-600 text-white',
          icon: <AlertCircle className="w-8 h-8 text-orange-600" />,
          title: 'HIGH RISK',
          subtitle: 'Significant deviations. High probability of replica packaging.',
        };
      case 'CRITICAL_RISK':
        return {
          bg: 'bg-rose-50 border-rose-300 text-rose-900',
          badgeBg: 'bg-rose-600 text-white',
          icon: <ShieldAlert className="w-8 h-8 text-rose-600" />,
          title: 'CRITICAL RISK',
          subtitle: 'Severe counterfeit indicators or multi-marker conflict.',
        };
      case 'TAMPERED_OR_DAMAGED':
        return {
          bg: 'bg-purple-50 border-purple-300 text-purple-900',
          badgeBg: 'bg-purple-700 text-white',
          icon: <ShieldAlert className="w-8 h-8 text-purple-700" />,
          title: 'TAMPERED / DAMAGED',
          subtitle: 'Heat-seal crimp or package integrity compromised. DO NOT CONSUME.',
        };
      case 'UNSUPPORTED_PRODUCT':
        return {
          bg: 'bg-amber-50 border-amber-300 text-amber-900',
          badgeBg: 'bg-amber-600 text-white',
          icon: <AlertCircle className="w-8 h-8 text-amber-600" />,
          title: 'UNSUPPORTED BRAND / PRODUCT',
          subtitle: 'Non-Amul product or competitor brand detected. VeriSure AI only assesses authorized Amul products.',
        };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return {
          bg: 'bg-slate-50 border-slate-300 text-slate-900',
          badgeBg: 'bg-slate-600 text-white',
          icon: <HelpCircle className="w-8 h-8 text-slate-600" />,
          title: 'INSUFFICIENT EVIDENCE',
          subtitle: 'Image quality insufficient for reliable assessment.',
        };
    }
  };

  const config = getBadgeConfig(decision.state);
  const isHighAlert = ['CRITICAL_RISK', 'TAMPERED_OR_DAMAGED'].includes(decision.state);

  return (
    <div className={`p-6 rounded-3xl border ${config.bg} bg-white/95 backdrop-blur-xl shadow-[0_4px_20px_-4px_rgba(15,23,42,0.06)] ${isHighAlert ? 'ring-2 ring-rose-400/40 animate-pulse-glow' : ''} transition-all relative overflow-hidden`}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
        <div className="flex items-start sm:items-center gap-4">
          <div className="p-3.5 bg-white rounded-2xl shadow-xs border border-slate-200/80 shrink-0">
            {config.icon}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-[11px] font-black tracking-wider uppercase ${config.badgeBg}`}>
                {config.title}
              </span>
              <span className="text-xs font-bold text-slate-500 bg-slate-100/80 px-2.5 py-0.5 rounded-full border border-slate-200/60">
                Certainty: {Math.round(decision.confidence * 100)}%
              </span>
            </div>
            <p className="mt-1.5 text-sm font-semibold text-slate-700 leading-snug">{config.subtitle}</p>
          </div>
        </div>

        {/* Numerical Risk Gauge */}
        <div className="flex items-center gap-5 sm:gap-6 bg-slate-50/90 backdrop-blur-xs px-5 py-3 rounded-2xl border border-slate-200/80 shadow-xs self-stretch sm:self-auto justify-around sm:justify-start">
          <div className="text-center">
            <div className="text-2xl font-black text-slate-900 tracking-tight">
              {decision.risk_score}
              <span className="text-xs font-semibold text-slate-400">/100</span>
            </div>
            <div className="text-[10px] uppercase font-black text-slate-500 tracking-wider mt-0.5">
              Risk Score
            </div>
          </div>
          <div className="w-px h-8 bg-slate-200" />
          <div className="text-center">
            <div className="text-sm font-black text-slate-800">
              {Math.round(decision.evidence_coverage * 100)}%
            </div>
            <div className="text-[10px] uppercase font-black text-slate-500 tracking-wider mt-0.5">
              Coverage
            </div>
          </div>
          <div className="w-px h-8 bg-slate-200" />
          <div className="text-center">
            <div className="text-sm font-black text-slate-800">
              {Math.round(decision.uncertainty * 100)}%
            </div>
            <div className="text-[10px] uppercase font-black text-slate-500 tracking-wider mt-0.5">
              Uncertainty
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

