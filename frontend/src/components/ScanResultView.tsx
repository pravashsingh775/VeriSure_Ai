import React from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Download,
  Eye,
  Info,
  Layers,
  Loader2,
  Shield,
  Sparkles,
} from 'lucide-react';
import { scanApi } from '../services/api';
import type { ScanDetail } from '../types';
import { DifferenceViewer } from './DifferenceViewer';
import { EvidenceCard } from './EvidenceCard';
import { RiskBadge } from './RiskBadge';

interface ScanResultViewProps {
  scan: ScanDetail;
  onReset: () => void;
}

export const ScanResultView: React.FC<ScanResultViewProps> = ({ scan, onReset }) => {
  const [selectedImageIdx, setSelectedImageIdx] = React.useState(0);
  const currentImage = scan.images[selectedImageIdx] || scan.images[0];
  const decision = scan.decision;

  const visualEvidences = scan.evidences.filter((e) =>
    ['logo', 'layout', 'colour', 'typography', 'texture', 'shape', 'print'].includes(e.type)
  );
  const textAndCodeEvidences = scan.evidences.filter((e) =>
    ['ocr', 'barcode', 'qr', 'certification'].includes(e.type)
  );
  const packagingEvidences = scan.evidences.filter((e) => ['seal'].includes(e.type));

  const [isDownloading, setIsDownloading] = React.useState(false);

  const handleDownloadPDF = async () => {
    setIsDownloading(true);
    try {
      await scanApi.downloadReport(scan.id);
    } catch {
      window.open(scanApi.getReportDownloadUrl(scan.id), '_blank');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Top Bar with Navigation & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 text-xs font-black text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 px-4 py-2.5 rounded-xl border border-slate-200 shadow-xs transition-all active:scale-[0.98] cursor-pointer self-start"
        >
          <ArrowLeft className="w-4 h-4 text-slate-500" />
          <span>Scan Another Packaging</span>
        </button>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          {scan.suspicious_case_id && (
            <span className="px-3 py-1.5 bg-rose-50 text-rose-700 rounded-xl text-xs font-bold border border-rose-200 shadow-xs flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              Triaged to Case #{scan.suspicious_case_id.slice(0, 8).toUpperCase()}
            </span>
          )}
          <button
            onClick={handleDownloadPDF}
            disabled={isDownloading}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-60 text-white text-xs font-black px-4 py-2.5 rounded-xl shadow-md shadow-blue-500/20 transition-all active:scale-[0.98] cursor-pointer"
          >
            {isDownloading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{isDownloading ? 'Generating PDF...' : 'Download Official PDF Report'}</span>
          </button>
        </div>
      </div>

      {/* Product Banner */}
      <div className="bg-white/95 backdrop-blur-xl p-6 sm:p-7 rounded-3xl border border-slate-200/90 shadow-[0_4px_20px_-4px_rgba(15,23,42,0.05)] flex flex-col sm:flex-row sm:items-center justify-between gap-5 relative overflow-hidden">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-black text-blue-600 uppercase tracking-wider">
              Verified Packaging Target
            </span>
            {scan.images.length > 1 && (
              <span className="px-2.5 py-0.5 text-[10px] font-black bg-indigo-50 text-indigo-700 border border-indigo-200/80 rounded-full flex items-center gap-1">
                <Layers className="w-3 h-3 text-indigo-600" />
                360° Dual-Panel Verified
              </span>
            )}
            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded-md uppercase">
              Amul GCMMF
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-1">
            {scan.identified_product_name || 'Unregistered Packaging'}
          </h1>
          <p className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>Variant: <strong className="text-slate-800 font-bold">{scan.identified_variant_name || 'N/A'}</strong></span>
            <span className="text-slate-300">•</span>
            <span>Pack Size: <strong className="text-slate-800 font-bold">{scan.identified_pack_size || 'N/A'}</strong></span>
            <span className="text-slate-300">•</span>
            <span>Packaging Version: <strong className="text-slate-800 font-bold">{scan.packaging_version_code || 'V1'}</strong></span>
          </p>
        </div>

        <div className="sm:text-right sm:border-l sm:border-slate-100 sm:pl-6 space-y-0.5 shrink-0">
          <span className="text-[10px] uppercase font-black text-slate-400 tracking-wider">
            Audit Reference ID
          </span>
          <div className="text-xs font-mono font-bold text-slate-800 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200/60">
            {scan.id.slice(0, 18)}...
          </div>
          <div className="text-[10px] text-slate-400">
            {new Date(scan.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
          </div>
        </div>
      </div>

      {/* Unsupported Brand Alert */}
      {decision?.state === 'UNSUPPORTED_PRODUCT' && (
        <div className="bg-amber-500/10 border-2 border-amber-400/50 rounded-2xl p-5 flex items-start gap-4 text-amber-900 shadow-xs">
          <div className="p-2.5 bg-amber-500 text-white rounded-xl shadow-xs shrink-0 mt-0.5">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2">
              <h4 className="text-base font-bold text-amber-950">
                System Scope Notice: Amul Products Only
              </h4>
              <span className="px-2 py-0.5 bg-amber-200 text-amber-900 text-[10px] font-black uppercase rounded-md">
                Scope Rejection
              </span>
            </div>
            <p className="text-xs text-amber-900/90 leading-relaxed font-medium">
              {decision.explanation_summary}
            </p>
            <div className="pt-1 text-xs text-amber-800 font-semibold flex items-center gap-1.5">
              <span>Consumer Guidance:</span>
              <span className="font-normal">{decision.recommendation}</span>
            </div>
          </div>
        </div>
      )}

      {/* Non-Packaging Graphic Rejection Alert */}
      {decision?.state === 'INSUFFICIENT_EVIDENCE' &&
        (scan.identified_product_name?.toLowerCase().includes('diagram') ||
          decision.explanation_summary?.toLowerCase().includes('diagram')) && (
          <div className="bg-slate-900 text-white rounded-2xl p-5 flex items-start gap-4 shadow-md border border-slate-800">
            <div className="p-2.5 bg-slate-800 text-amber-400 rounded-xl shadow-xs shrink-0 mt-0.5">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center gap-2">
                <h4 className="text-base font-bold text-white">
                  Non-Physical Packaging Graphic Detected
                </h4>
                <span className="px-2 py-0.5 bg-slate-800 text-slate-300 text-[10px] font-black uppercase rounded-md border border-slate-700">
                  Out of Domain
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {decision.explanation_summary}
              </p>
              <div className="pt-1 text-xs text-slate-400 font-mono">
                Tip: VeriSure AI performs physical milk pouch and carton forensics. Please photograph authentic packaging under good lighting.
              </div>
            </div>
          </div>
        )}

      {/* Decision Risk Badge */}
      {decision && <RiskBadge decision={decision} />}

      {/* Mandatory Scientific Integrity Disclaimer */}
      {decision && (
        <div className="bg-slate-100/90 border border-slate-200 rounded-xl px-4 py-3 text-xs text-slate-700 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Info className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              <strong>Scientific Notice:</strong> Assessment confidence ({Math.round(decision.confidence * 100)}%) is <strong>NOT</strong> the probability that the product is genuine. It measures photographic clarity and evidence completeness.
            </span>
          </div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider shrink-0 hidden sm:inline">
            Packaging Risk Only
          </span>
        </div>
      )}

      {/* Actionable Consumer Advisory Box */}
      {decision && (
        <div
          className={`p-4 rounded-xl border text-xs leading-relaxed flex items-start gap-3 ${
            decision.risk_score < 30
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <Shield className="w-5 h-5 shrink-0 mt-0.5 text-current" />
          <div>
            <span className="font-bold uppercase tracking-wider block mb-0.5">
              Consumer Safety Advisory
            </span>
            <p className="font-medium">{decision.recommendation}</p>
          </div>
        </div>
      )}

      {/* Grounded Natural Language Narrative */}
      {decision && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Synthesized AI Verification Narrative
          </h3>
          <p className="text-sm text-slate-700 leading-relaxed font-normal">
            {decision.explanation_summary}
          </p>

          {decision.contradictions && decision.contradictions.length > 0 && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 font-medium">
              <span className="font-bold">Detected Contradiction:</span> {decision.contradictions[0]}
            </div>
          )}
        </div>
      )}

      {/* Dual Panel Switcher Tabs (Only if multiple images) */}
      {scan.images.length > 1 && (
        <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              Packaging Sides ({scan.images.length} Photographed)
            </span>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Select which packaging panel to inspect in the difference heatmap below:
            </p>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={() => setSelectedImageIdx(0)}
              className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold border transition-all ${
                selectedImageIdx === 0
                  ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Front Panel (Logo & Design)
            </button>
            <button
              onClick={() => setSelectedImageIdx(1)}
              className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold border transition-all ${
                selectedImageIdx === 1
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Back Panel (Barcode & Compliance)
            </button>
          </div>
        </div>
      )}

      {/* Interactive Difference Heatmap Viewer */}
      {currentImage && (
        <DifferenceViewer
          imageDetail={currentImage}
          suspiciousRegions={decision?.suspicious_regions || []}
        />
      )}

      {/* Evidence Breakdown Grid */}
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
            Visual & Aesthetic Markers ({visualEvidences.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {visualEvidences.map((ev, idx) => (
              <EvidenceCard key={idx} evidence={ev} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
            Codes, OCR & Regulatory ({textAndCodeEvidences.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {textAndCodeEvidences.map((ev, idx) => (
              <EvidenceCard key={idx} evidence={ev} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
            Packaging Integrity & Seals ({packagingEvidences.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {packagingEvidences.map((ev, idx) => (
              <EvidenceCard key={idx} evidence={ev} />
            ))}
          </div>
        </div>
      </div>

      {/* Mandatory Academic & Legal Disclaimer */}
      <div className="p-4 bg-slate-100 rounded-xl border border-slate-200 text-[11px] text-slate-500 leading-relaxed">
        <span className="font-bold text-slate-700">Academic & Legal Notice:</span> VeriSure AI is an
        authentic risk assessment platform evaluating visual, textual, and machine-readable packaging conformity
        against authorized factory reference standards. A photograph cannot verify or guarantee the chemical,
        biological, or nutritional contents inside sealed packaging. This assessment does not constitute a legal certification.
      </div>
    </div>
  );
};
