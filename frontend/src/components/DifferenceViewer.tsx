import React, { useState } from 'react';
import { Layers } from 'lucide-react';
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
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            Packaging Difference & Anomaly Inspection
          </h3>
          <p className="text-xs text-slate-500">
            Pixel-wise SSIM comparison against factory reference standard.
          </p>
        </div>

        {/* View Mode Controls */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl self-start sm:self-auto text-xs font-semibold">
          <button
            onClick={() => setViewMode('crop')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              viewMode === 'crop'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Clean Crop
          </button>
          <button
            onClick={() => setViewMode('heatmap')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              viewMode === 'heatmap'
                ? 'bg-white text-blue-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Difference Heatmap
          </button>
          <button
            onClick={() => setViewMode('side-by-side')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              viewMode === 'side-by-side'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      {/* Main Image Frame */}
      <div className="relative bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center min-h-[360px] sm:min-h-[440px]">
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

            {/* Bounding Box Overlays */}
            {suspiciousRegions.map((region, idx) => (
              <div
                key={idx}
                onMouseEnter={() => setActiveRegion(region)}
                onMouseLeave={() => setActiveRegion(null)}
                className="absolute border-2 border-rose-500 bg-rose-500/20 rounded cursor-pointer transition-all hover:bg-rose-500/40"
                style={{
                  top: `${region.y_min * 100}%`,
                  left: `${region.x_min * 100}%`,
                  width: `${(region.x_max - region.x_min) * 100}%`,
                  height: `${(region.y_max - region.y_min) * 100}%`,
                }}
              >
                <span className="absolute -top-5 left-0 px-1.5 py-0.2 bg-rose-600 text-white text-[9px] font-bold rounded shadow-xs whitespace-nowrap">
                  {region.label || 'Mismatch'} ({Math.round((region.difference_score || 0) * 100)}%)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Anomaly Tooltip / Detail Banner */}
      {activeRegion ? (
        <div className="mt-3 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900">
          <div className="font-bold mb-0.5">
            {activeRegion.label} (Deviation Score: {Math.round((activeRegion.difference_score || 0) * 100)}%)
          </div>
          <p>{activeRegion.explanation}</p>
        </div>
      ) : (
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500 px-1">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Blue = Identical match
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Red = Structural variance
            </span>
          </div>
          {suspiciousRegions.length > 0 && (
            <span className="text-rose-600 font-semibold">
              {suspiciousRegions.length} Anomaly Zones Detected
            </span>
          )}
        </div>
      )}
    </div>
  );
};
