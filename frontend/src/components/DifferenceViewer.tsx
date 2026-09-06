import React, { useState } from 'react';
import { AlertTriangle, Layers } from 'lucide-react';
import type { RegionBox, ScanImageDetail } from '../types';
import { resolveStorageUrl } from '../services/api';

interface DifferenceViewerProps {
  imageDetail: ScanImageDetail;
  suspiciousRegions: RegionBox[];
}

export const DifferenceViewer: React.FC<DifferenceViewerProps> = ({
  imageDetail,
  suspiciousRegions,
}) => {
  const [viewMode, setViewMode] = useState<'crop' | 'heatmap' | 'side-by-side'>('heatmap');
  const [activeRegion, setActiveRegion] = useState<RegionBox | null>(null);

  const [cropError, setCropError] = useState(false);
  const [heatError, setHeatError] = useState(false);

  const rawCropUrl = resolveStorageUrl(imageDetail.crop_path);
  const rawHeatUrl = resolveStorageUrl(imageDetail.heatmap_path);
  const cropUrl = rawCropUrl && !cropError ? rawCropUrl : null;
  const heatUrl = rawHeatUrl && !heatError ? rawHeatUrl : null;

  return (
    <div className="bg-white/95 backdrop-blur-xl rounded-3xl border border-slate-200/90 p-6 sm:p-7 shadow-[0_4px_20px_-4px_rgba(15,23,42,0.06)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div>
          <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            Packaging Difference & Anomaly Inspection
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 font-medium">
            Pixel-wise SSIM comparison against factory reference standard.
          </p>
        </div>

        {/* View Mode Controls */}
        <div className="flex items-center gap-1 bg-slate-100/90 p-1.5 rounded-2xl self-start sm:self-auto text-xs font-bold border border-slate-200/60">
          <button
            onClick={() => setViewMode('crop')}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              viewMode === 'crop'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/60'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Clean Crop
          </button>
          <button
            onClick={() => setViewMode('heatmap')}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              viewMode === 'heatmap'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm shadow-blue-500/20'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Difference Heatmap
          </button>
          <button
            onClick={() => setViewMode('side-by-side')}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              viewMode === 'side-by-side'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/60'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      {/* Main Image Frame */}
      <div className="relative bg-slate-950/95 rounded-2xl overflow-hidden flex items-center justify-center min-h-[360px] sm:min-h-[440px] border border-slate-800/80 shadow-inner">
        {viewMode === 'side-by-side' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full h-full p-3">
            <div className="relative flex flex-col items-center justify-center bg-slate-950/40 rounded-lg p-2 min-h-[200px]">
              <span className="absolute top-3 left-3 px-2 py-0.5 bg-black/70 text-white rounded text-[10px] font-bold uppercase backdrop-blur-xs z-10">
                Isolated Packaging
              </span>
              {cropUrl ? (
                <img
                  src={cropUrl}
                  alt="Packaging Crop"
                  onError={() => setCropError(true)}
                  className="max-h-[380px] w-auto object-contain rounded-lg"
                />
              ) : (
                <div className="text-slate-500 text-xs text-center p-6">
                  Clean crop asset unavailable
                </div>
              )}
            </div>
            <div className="relative flex flex-col items-center justify-center bg-slate-950/40 rounded-lg p-2 min-h-[200px]">
              <span className="absolute top-3 left-3 px-2 py-0.5 bg-blue-600/90 text-white rounded text-[10px] font-bold uppercase backdrop-blur-xs z-10">
                Discrepancy Heatmap
              </span>
              {heatUrl ? (
                <img
                  src={heatUrl}
                  alt="Difference Heatmap"
                  onError={() => setHeatError(true)}
                  className="max-h-[380px] w-auto object-contain rounded-lg"
                />
              ) : (
                <div className="text-slate-500 text-xs text-center p-6">
                  SSIM heatmap asset unavailable
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="relative w-full h-full flex items-center justify-center p-2">
            {viewMode === 'heatmap' && heatUrl ? (
              <img
                src={heatUrl}
                alt="Difference Heatmap"
                onError={() => setHeatError(true)}
                className="max-h-[440px] w-auto object-contain rounded-lg shadow-md"
              />
            ) : cropUrl ? (
              <img
                src={cropUrl}
                alt="Packaging Crop"
                onError={() => setCropError(true)}
                className="max-h-[440px] w-auto object-contain rounded-lg shadow-md"
              />
            ) : (
              <div className="text-slate-500 text-xs text-center p-12">
                No image inspection assets available for this view mode.
              </div>
            )}

            {/* Bounding Box Overlays with Anomaly Pulse Animation */}
            {suspiciousRegions.map((region, idx) => (
              <div
                key={idx}
                onMouseEnter={() => setActiveRegion(region)}
                onMouseLeave={() => setActiveRegion(null)}
                className="absolute border-2 rounded-xl cursor-pointer transition-all hover:scale-[1.02] animate-anomaly shadow-lg"
                style={{
                  top: `${region.y_min * 100}%`,
                  left: `${region.x_min * 100}%`,
                  width: `${(region.x_max - region.x_min) * 100}%`,
                  height: `${(region.y_max - region.y_min) * 100}%`,
                }}
              >
                <span className="absolute -top-6 left-0 px-2 py-0.5 bg-rose-600 text-white text-[10px] font-black rounded-lg shadow-md whitespace-nowrap flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-amber-300" />
                  {region.label || 'Mismatch'} ({Math.round((region.difference_score || 0) * 100)}%)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Anomaly Tooltip / Detail Banner */}
      {activeRegion ? (
        <div className="mt-4 p-4 bg-rose-50/90 border border-rose-200 rounded-2xl text-xs text-rose-950 shadow-xs flex items-start gap-3">
          <div className="p-2 bg-rose-100 text-rose-600 rounded-xl shrink-0 mt-0.5">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <div className="font-black text-rose-900 text-sm mb-0.5 flex items-center gap-2">
              <span>{activeRegion.label}</span>
              <span className="px-2 py-0.5 bg-rose-200/80 text-rose-800 text-[10px] rounded-full uppercase">
                Deviation: {Math.round((activeRegion.difference_score || 0) * 100)}%
              </span>
            </div>
            <p className="text-slate-700 leading-relaxed font-medium">{activeRegion.explanation}</p>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500 px-1">
          <div className="flex items-center gap-5">
            <span className="flex items-center gap-2 font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-xs shadow-blue-500/50" /> Blue = Authentic Match (SSIM &ge; 0.90)
            </span>
            <span className="flex items-center gap-2 font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-xs shadow-rose-500/50" /> Red = Structural Variance / Tampering
            </span>
          </div>
          {suspiciousRegions.length > 0 && (
            <span className="px-3 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded-full font-bold text-[11px] flex items-center gap-1.5 self-start sm:self-auto">
              <AlertTriangle className="w-3.5 h-3.5" />
              {suspiciousRegions.length} Anomaly Zones Detected
            </span>
          )}
        </div>
      )}
    </div>
  );
};
