import React, { useRef, useState } from 'react';
import { Camera, CheckCircle2, Image as ImageIcon, Info, Loader2, ShieldCheck, Sparkles, Upload, X } from 'lucide-react';
import { scanApi } from '../services/api';
import type { ScanDetail } from '../types';

interface ScanUploadProps {
  onScanCompleted: (result: ScanDetail) => void;
}

export const ScanUpload: React.FC<ScanUploadProps> = ({ onScanCompleted }) => {
  const [scanMode, setScanMode] = useState<'dual' | 'single'>('dual');

  // Single-panel state
  const [singleFile, setSingleFile] = useState<File | null>(null);
  const [singlePreview, setSinglePreview] = useState<string | null>(null);
  const [viewType, setViewType] = useState('FRONT');
  const singleInputRef = useRef<HTMLInputElement>(null);

  // Dual-panel state (Front + Back)
  const [fileFront, setFileFront] = useState<File | null>(null);
  const [previewFront, setPreviewFront] = useState<string | null>(null);
  const frontInputRef = useRef<HTMLInputElement>(null);

  const [fileBack, setFileBack] = useState<File | null>(null);
  const [previewBack, setPreviewBack] = useState<string | null>(null);
  const backInputRef = useRef<HTMLInputElement>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const MAX_FILE_SIZE_MB = 15;
  const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

  const validateFile = (file: File): boolean => {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError(
        `Selected image (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the ${MAX_FILE_SIZE_MB} MB limit.`
      );
      return false;
    }
    setError(null);
    return true;
  };

  const handleSingleSelect = (f: File) => {
    if (!validateFile(f)) return;
    setSingleFile(f);
    setSinglePreview(URL.createObjectURL(f));
  };

  const handleFrontSelect = (f: File) => {
    if (!validateFile(f)) return;
    setFileFront(f);
    setPreviewFront(URL.createObjectURL(f));
  };

  const handleBackSelect = (f: File) => {
    if (!validateFile(f)) return;
    setFileBack(f);
    setPreviewBack(URL.createObjectURL(f));
  };

  const executeDualScan = async () => {
    if (!fileFront || !fileBack) {
      setError('Please provide both Front and Back packaging photographs for 360° verification.');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      setUploadStep('Validating physical packaging & brand authenticity...');
      setTimeout(() => setUploadStep('Running dual-side vision & code inspection engines...'), 1200);
      const result = await scanApi.uploadDualScan(fileFront, fileBack);
      setUploadStep('Verification complete! Synthesizing 360° report...');
      setTimeout(() => {
        onScanCompleted(result);
        setIsUploading(false);
      }, 500);
    } catch (err: any) {
      setIsUploading(false);
      if (!err.response) {
        setError('Unable to reach VeriSure backend server. Please verify the backend is running on port 8000.');
      } else {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (Array.isArray(detail)) {
          setError(detail.map((d: any) => d.msg || JSON.stringify(d)).join(', '));
        } else {
          setError('Failed to process dual-side scan. Please verify images and try again.');
        }
      }
    }
  };

  const executeSingleScan = async () => {
    if (!singleFile) return;

    setIsUploading(true);
    setError(null);

    try {
      setUploadStep('Validating physical packaging & brand authenticity...');
      setTimeout(() => setUploadStep('Executing multi-evidence AI verification...'), 1000);
      const result = await scanApi.uploadScan(singleFile, viewType);
      setUploadStep('Analysis complete! Synthesizing report...');
      setTimeout(() => {
        onScanCompleted(result);
        setIsUploading(false);
      }, 500);
    } catch (err: any) {
      setIsUploading(false);
      if (!err.response) {
        setError('Unable to reach VeriSure backend server. Please verify the backend is running on port 8000.');
      } else {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (Array.isArray(detail)) {
          setError(detail.map((d: any) => d.msg || JSON.stringify(d)).join(', '));
        } else {
          setError('Failed to process product photograph. Please try again.');
        }
      }
    }
  };

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 p-6 sm:p-8 shadow-sm max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-6">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 mb-2">
          <Sparkles className="w-3.5 h-3.5" /> AI Authenticity Risk Assessment
        </span>
        <h2 className="text-2xl font-black text-slate-900 tracking-tight">
          Verify Product Packaging
        </h2>
        <p className="text-sm text-slate-500 mt-1 max-w-lg mx-auto">
          Calibrated specifically for <strong className="text-slate-700">Amul Dairy flexible milk pouches</strong> (Amul Gold, Amul Taaza, Amul Shakti).
        </p>
      </div>

      {/* Mode Selector */}
      <div className="grid grid-cols-2 p-1.5 bg-slate-100 rounded-2xl mb-6">
        <button
          type="button"
          onClick={() => {
            setScanMode('dual');
            setError(null);
          }}
          className={`py-2.5 px-4 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 ${
            scanMode === 'dual'
              ? 'bg-white text-blue-700 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <ShieldCheck className="w-4 h-4 text-blue-600" />
          <span>360° Dual-Side Scan (Front + Back)</span>
          <span className="hidden sm:inline-block px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[9px] font-black uppercase">
            Recommended
          </span>
        </button>

        <button
          type="button"
          onClick={() => {
            setScanMode('single');
            setError(null);
          }}
          className={`py-2.5 px-4 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 ${
            scanMode === 'single'
              ? 'bg-white text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Camera className="w-4 h-4 text-slate-500" />
          <span>Single Panel Quick Scan</span>
        </button>
      </div>

      {/* DUAL-SIDE SCAN MODE */}
      {scanMode === 'dual' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* FRONT PANEL DROPZONE */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600"></span> Front Panel
                </span>
                <span className="text-[11px] text-slate-400">Logo, Title & Graphics</span>
              </div>

              <div
                onClick={() => frontInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) handleFrontSelect(e.dataTransfer.files[0]);
                }}
                className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all min-h-[220px] flex flex-col items-center justify-center ${
                  previewFront
                    ? 'border-blue-300 bg-blue-50/20'
                    : 'border-slate-200 hover:border-blue-400 bg-slate-50/50 hover:bg-blue-50/30'
                }`}
              >
                <input
                  ref={frontInputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => e.target.files?.[0] && handleFrontSelect(e.target.files[0])}
                  className="hidden"
                />

                {previewFront ? (
                  <div className="relative w-full flex flex-col items-center">
                    <img
                      src={previewFront}
                      alt="Front Preview"
                      className="max-h-36 object-contain rounded-lg shadow-xs mb-2"
                    />
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-blue-600">Change</span>
                      <span className="text-slate-300">•</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFileFront(null);
                          setPreviewFront(null);
                          if (frontInputRef.current) frontInputRef.current.value = '';
                        }}
                        className="text-[11px] font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-0.5"
                      >
                        <X className="w-3 h-3" /> Remove
                      </button>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[200px]">
                      {fileFront?.name}
                    </span>
                  </div>
                ) : (
                  <div className="py-4 flex flex-col items-center">
                    <div className="p-3 bg-white rounded-xl shadow-xs border border-slate-100 text-blue-600 mb-2">
                      <ImageIcon className="w-6 h-6" />
                    </div>
                    <span className="text-xs font-bold text-slate-700">Upload Front Side</span>
                    <span className="text-[11px] text-slate-400 mt-0.5">Amul Logo & Front Art</span>
                  </div>
                )}
              </div>
            </div>

            {/* BACK PANEL DROPZONE */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-600"></span> Back Panel
                </span>
                <span className="text-[11px] text-slate-400">Barcode, FSSAI & Nutrition</span>
              </div>

              <div
                onClick={() => backInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) handleBackSelect(e.dataTransfer.files[0]);
                }}
                className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all min-h-[220px] flex flex-col items-center justify-center ${
                  previewBack
                    ? 'border-emerald-300 bg-emerald-50/20'
                    : 'border-slate-200 hover:border-emerald-400 bg-slate-50/50 hover:bg-emerald-50/30'
                }`}
              >
                <input
                  ref={backInputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => e.target.files?.[0] && handleBackSelect(e.target.files[0])}
                  className="hidden"
                />

                {previewBack ? (
                  <div className="relative w-full flex flex-col items-center">
                    <img
                      src={previewBack}
                      alt="Back Preview"
                      className="max-h-36 object-contain rounded-lg shadow-xs mb-2"
                    />
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-emerald-700">Change</span>
                      <span className="text-slate-300">•</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFileBack(null);
                          setPreviewBack(null);
                          if (backInputRef.current) backInputRef.current.value = '';
                        }}
                        className="text-[11px] font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-0.5"
                      >
                        <X className="w-3 h-3" /> Remove
                      </button>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[200px]">
                      {fileBack?.name}
                    </span>
                  </div>
                ) : (
                  <div className="py-4 flex flex-col items-center">
                    <div className="p-3 bg-white rounded-xl shadow-xs border border-slate-100 text-emerald-600 mb-2">
                      <Camera className="w-6 h-6" />
                    </div>
                    <span className="text-xs font-bold text-slate-700">Upload Back Side</span>
                    <span className="text-[11px] text-slate-400 mt-0.5">Barcode EAN-13 & FSSAI</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Dual Scan Info Card */}
          <div className="p-3.5 bg-blue-50/60 rounded-xl border border-blue-100 flex items-start gap-3 text-xs text-blue-900 leading-relaxed">
            <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <strong>Complete 360° Verification:</strong> Uploading both Front and Back ensures
              visual branding, heat seals, 1D EAN-13 barcode checksum, and 14-digit FSSAI regulatory license are cross-verified for total authenticity.
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 font-medium">
              {error}
            </div>
          )}

          {/* Action Button */}
          <button
            onClick={executeDualScan}
            disabled={!fileFront || !fileBack || isUploading}
            className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2 ${
              !fileFront || !fileBack || isUploading
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20 active:scale-[0.99]'
            }`}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{uploadStep || 'Executing 360° dual-panel verification...'}</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Run 360° Dual-Side Authenticity Verification</span>
              </>
            )}
          </button>
        </div>
      ) : (
        /* SINGLE PANEL SCAN MODE */
        <div className="space-y-6">
          {/* View Angle Selector */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Packaging Perspective
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { id: 'FRONT', label: 'Front Face' },
                { id: 'BACK', label: 'Back & Nutrition' },
                { id: 'SEAL_TOP', label: 'Heat-Seal Band' },
                { id: 'BARCODE_CLOSEUP', label: 'Barcode / Codes' },
              ].map((angle) => (
                <button
                  key={angle.id}
                  type="button"
                  onClick={() => setViewType(angle.id)}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                    viewType === angle.id
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {angle.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files?.[0]) handleSingleSelect(e.dataTransfer.files[0]);
            }}
            onClick={() => singleInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
              singlePreview
                ? 'border-blue-300 bg-blue-50/20'
                : 'border-slate-200 hover:border-blue-400 bg-slate-50/50 hover:bg-blue-50/30'
            }`}
          >
            <input
              ref={singleInputRef}
              type="file"
              accept="image/*"
              onChange={(e) => e.target.files?.[0] && handleSingleSelect(e.target.files[0])}
              className="hidden"
            />

            {singlePreview ? (
              <div className="flex flex-col items-center">
                <img
                  src={singlePreview}
                  alt="Scan Preview"
                  className="max-h-64 object-contain rounded-xl shadow-xs mb-3"
                />
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-blue-600">Click to change photograph</span>
                  <span className="text-slate-300">•</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSingleFile(null);
                      setSinglePreview(null);
                      if (singleInputRef.current) singleInputRef.current.value = '';
                    }}
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" /> Remove photo
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  {singleFile?.name} ({singleFile ? (singleFile.size / (1024 * 1024)).toFixed(2) : '0'} MB)
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center py-6">
                <div className="p-4 bg-white rounded-2xl shadow-xs border border-slate-100 mb-3 text-blue-600">
                  <Camera className="w-8 h-8" />
                </div>
                <p className="text-sm font-bold text-slate-800">
                  Click to capture or upload product image
                </p>
                <p className="text-xs text-slate-400 mt-1">Supports PNG, JPG, WEBP up to 15MB</p>
              </div>
            )}
          </div>

          {/* Capture Checklist */}
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/60 flex items-start gap-3">
            <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-600 leading-relaxed">
              <span className="font-semibold text-slate-800">For optimal risk assessment:</span> Hold
              camera parallel to packaging, avoid heavy glare, and ensure the packaging fills the frame.
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 font-medium">
              {error}
            </div>
          )}

          {/* Single Execute Button */}
          <button
            onClick={executeSingleScan}
            disabled={!singleFile || isUploading}
            className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2 ${
              !singleFile || isUploading
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20 active:scale-[0.99]'
            }`}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{uploadStep || 'Executing multi-evidence AI verification...'}</span>
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                <span>Verify Packaging Panel</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
