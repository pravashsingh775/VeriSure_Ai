import React from 'react';
import { ArrowLeft, Download, Info, Loader2, Shield, Sparkles } from 'lucide-react';
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
  const primaryImage = scan.images[0];
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
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Bar with Navigation & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-slate-900 bg-white px-3 py-2 rounded-xl border border-slate-200 transition-all self-start"
        >
          <ArrowLeft className="w-4 h-4" /> Scan Another Product
        </button>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          {scan.suspicious_case_id && (
            <span className="px-3 py-1.5 bg-rose-100 text-rose-800 rounded-xl text-xs font-bold border border-rose-200">
              Triaged to Case #{scan.suspicious_case_id.slice(0, 8).toUpperCase()}
            </span>
          )}
          <button
            onClick={handleDownloadPDF}
            disabled={isDownloading}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-xs transition-all active:scale-[0.98]"
          >
            {isDownloading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {isDownloading ? 'Generating PDF...' : 'Download PDF Report'}
          </button>
        </div>
      </div>

      {/* Product Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold text-blue-600 uppercase tracking-wider">
            Verified Packaging Target
          </span>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-0.5">
            {scan.identified_product_name || 'Unregistered Packaging'}
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Variant: <span className="font-semibold text-slate-700">{scan.identified_variant_name || 'N/A'}</span> •
            Pack Size: <span className="font-semibold text-slate-700">{scan.identified_pack_size || 'N/A'}</span> •
            Packaging Version: <span className="font-semibold text-slate-700">{scan.packaging_version_code || 'V1'}</span>
          </p>
        </div>

        <div className="text-right sm:border-l sm:border-slate-100 sm:pl-6">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Scan Reference
          </span>
          <div className="text-xs font-mono font-bold text-slate-800">{scan.id.slice(0, 16)}...</div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {new Date(scan.created_at).toLocaleString()}
          </div>
        </div>
      </div>

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

      {/* Interactive Difference Heatmap Viewer */}
      {primaryImage && (
        <DifferenceViewer
          imageDetail={primaryImage}
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
