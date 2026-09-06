import React, { useEffect, useRef, useState } from 'react';
import {
  Camera,
  CheckCircle2,
  Image as ImageIcon,
  Info,
  Layers,
  Loader2,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  Zap,
} from 'lucide-react';
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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadPhase, setUploadPhase] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const MAX_FILE_SIZE_MB = 15;
  const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

  // Cleanup object URLs on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (singlePreview) URL.revokeObjectURL(singlePreview);
      if (previewFront) URL.revokeObjectURL(previewFront);
      if (previewBack) URL.revokeObjectURL(previewBack);
    };
  }, [singlePreview, previewFront, previewBack]);

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
    if (singlePreview) URL.revokeObjectURL(singlePreview);
    setSingleFile(f);
    setSinglePreview(URL.createObjectURL(f));
  };

  const handleFrontSelect = (f: File) => {
    if (!validateFile(f)) return;
    if (previewFront) URL.revokeObjectURL(previewFront);
    setFileFront(f);
    setPreviewFront(URL.createObjectURL(f));
  };

  const handleBackSelect = (f: File) => {
    if (!validateFile(f)) return;
    if (previewBack) URL.revokeObjectURL(previewBack);
    setFileBack(f);
    setPreviewBack(URL.createObjectURL(f));
  };

  const loadSamplePouch = async (frontRelPath: string, backRelPath: string, name: string) => {
    try {
      setError(null);
      const frontUrl = `/data/storage/${frontRelPath}`;
      const backUrl = `/data/storage/${backRelPath}`;
      const [frontBlob, backBlob] = await Promise.all([
        fetch(frontUrl).then((r) => r.blob()),
        fetch(backUrl).then((r) => r.blob()),
      ]);
      const frontFile = new File([frontBlob], `${name}_front.jpg`, { type: 'image/jpeg' });
      const backFile = new File([backBlob], `${name}_back.jpg`, { type: 'image/jpeg' });
      if (previewFront) URL.revokeObjectURL(previewFront);
      if (previewBack) URL.revokeObjectURL(previewBack);
      setFileFront(frontFile);
      setPreviewFront(URL.createObjectURL(frontFile));
      setFileBack(backFile);
      setPreviewBack(URL.createObjectURL(backFile));
      setScanMode('dual');
    } catch (err) {
      console.error('Failed to load sample pouch:', err);
    }
  };

  const loadSingleSample = async (frontRelPath: string, name: string) => {
    try {
      setError(null);
      const frontUrl = `/data/storage/${frontRelPath}`;
      const frontBlob = await fetch(frontUrl).then((r) => r.blob());
      const frontFile = new File([frontBlob], `${name}_front.jpg`, { type: 'image/jpeg' });
      if (singlePreview) URL.revokeObjectURL(singlePreview);
      setSingleFile(frontFile);
      setSinglePreview(URL.createObjectURL(frontFile));
      setViewType('FRONT');
      setScanMode('single');
    } catch (err) {
      console.error('Failed to load single sample pouch:', err);
    }
  };

  const executeDualScan = async () => {
    if (!fileFront || !fileBack) {
      setError('Please provide both Front and Back packaging photographs for 360° verification.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(15);
    setUploadPhase(1);
    setUploadStep('Validating physical packaging integrity & domain gate...');
    setError(null);

    const t1 = setTimeout(() => {
      setUploadProgress(40);
      setUploadPhase(2);
      setUploadStep('Retrieving factory reference standards & aligning pixel heatmaps...');
    }, 600);

    const t2 = setTimeout(() => {
      setUploadProgress(75);
      setUploadPhase(3);
      setUploadStep('Executing 12-engine vision & code analysis (Logo, OCR, EAN-13, Seals)...');
    }, 1200);

    try {
      const result = await scanApi.uploadDualScan(fileFront, fileBack);
      clearTimeout(t1);
      clearTimeout(t2);
      setUploadProgress(100);
      setUploadPhase(4);
      setUploadStep('Verification complete! Synthesizing calibrated 360° report...');
      setTimeout(() => {
        onScanCompleted(result);
        setIsUploading(false);
      }, 400);
    } catch (err: any) {
      clearTimeout(t1);
      clearTimeout(t2);
      setIsUploading(false);
      setUploadProgress(0);
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
    setUploadProgress(20);
    setUploadPhase(1);
    setUploadStep('Validating packaging photograph & domain gatekeeper...');
    setError(null);

    const t1 = setTimeout(() => {
      setUploadProgress(50);
      setUploadPhase(2);
      setUploadStep('Matching factory standard & generating SSIM difference heatmap...');
    }, 500);

    const t2 = setTimeout(() => {
      setUploadProgress(80);
      setUploadPhase(3);
      setUploadStep('Executing parallel forensic evidence analysis...');
    }, 1000);

    try {
      const result = await scanApi.uploadScan(singleFile, viewType);
      clearTimeout(t1);
      clearTimeout(t2);
      setUploadProgress(100);
      setUploadPhase(4);
      setUploadStep('Analysis complete! Synthesizing explainable narrative...');
      setTimeout(() => {
        onScanCompleted(result);
        setIsUploading(false);
      }, 400);
    } catch (err: any) {
      clearTimeout(t1);
      clearTimeout(t2);
      setIsUploading(false);
      setUploadProgress(0);
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
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Executive Hero Banner */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold bg-white/90 border border-slate-200/80 shadow-xs backdrop-blur-md animate-float">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          <span className="text-slate-700 font-semibold">Amul GCMMF Verified Packaging Standard</span>
          <span className="text-slate-300">•</span>
          <span className="text-blue-600 font-bold flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" /> 12 Forensic AI Engines
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
          Packaging Authenticity & Integrity Studio
        </h1>
        <p className="text-sm text-slate-500 max-w-2xl mx-auto leading-relaxed">
          Real-time physical pouch verification evaluating visual branding, heat seals, 
          1D EAN-13 barcode checksums, and 14-digit FSSAI regulatory compliance.
        </p>

        {/* Feature Pills */}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
          <span className="px-3 py-1 bg-white/80 rounded-full border border-slate-200/70 text-[11px] font-bold text-slate-600 shadow-2xs flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-amber-500" /> Sub-Second Inference
          </span>
          <span className="px-3 py-1 bg-white/80 rounded-full border border-slate-200/70 text-[11px] font-bold text-slate-600 shadow-2xs flex items-center gap-1.5">
            <Layers className="w-3 h-3 text-blue-600" /> SSIM Difference Heatmaps
          </span>
          <span className="px-3 py-1 bg-white/80 rounded-full border border-slate-200/70 text-[11px] font-bold text-slate-600 shadow-2xs flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-emerald-600" /> Dirichlet Uncertainty Calibration
          </span>
        </div>
      </div>

      {/* Main Studio Card */}
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl border border-slate-200/90 p-6 sm:p-8 shadow-[0_4px_24px_-4px_rgba(15,23,42,0.06)] relative overflow-hidden">
        {/* Top Accent Gradient Line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500" />

        {/* Mode Selector */}
        <div className="grid grid-cols-2 p-1.5 bg-slate-100/90 rounded-2xl mb-6 border border-slate-200/60">
          <button
            type="button"
            onClick={() => {
              setScanMode('dual');
              setError(null);
            }}
            className={`py-3 px-4 text-xs font-black rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer ${
              scanMode === 'dual'
                ? 'bg-white text-blue-700 shadow-xs border border-slate-200/60'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>360° Dual-Side Verification</span>
            <span className="hidden sm:inline-block px-2 py-0.5 bg-blue-100 text-blue-700 rounded-md text-[9px] font-extrabold uppercase">
              Recommended
            </span>
          </button>

          <button
            type="button"
            onClick={() => {
              setScanMode('single');
              setError(null);
            }}
            className={`py-3 px-4 text-xs font-black rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer ${
              scanMode === 'single'
                ? 'bg-white text-slate-900 shadow-xs border border-slate-200/60'
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
                  <span className="text-xs font-black text-slate-800 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-600"></span> Front Panel
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">Logo, Title & Graphics</span>
                </div>

                <div
                  onClick={() => frontInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) handleFrontSelect(e.dataTransfer.files[0]);
                  }}
                  className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all min-h-[220px] flex flex-col items-center justify-center relative overflow-hidden ${
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

                  {/* Laser Scanning Line Animation when Uploading */}
                  {isUploading && previewFront && (
                    <div className="absolute inset-0 pointer-events-none z-10">
                      <div className="laser-sweep" />
                    </div>
                  )}

                  {previewFront ? (
                    <div className="relative w-full flex flex-col items-center">
                      <img
                        src={previewFront}
                        alt="Front Preview"
                        className="max-h-36 object-contain rounded-xl shadow-xs mb-2"
                      />
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-blue-600">Change Photo</span>
                        <span className="text-slate-300">•</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (previewFront) URL.revokeObjectURL(previewFront);
                            setFileFront(null);
                            setPreviewFront(null);
                            if (frontInputRef.current) frontInputRef.current.value = '';
                          }}
                          className="text-[11px] font-bold text-rose-600 hover:text-rose-700 flex items-center gap-0.5 cursor-pointer"
                        >
                          <X className="w-3 h-3" /> Remove
                        </button>
                      </div>
                      <span className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[200px] font-mono">
                        {fileFront?.name}
                      </span>
                    </div>
                  ) : (
                    <div className="py-4 flex flex-col items-center">
                      <div className="p-3.5 bg-white rounded-2xl shadow-xs border border-slate-100 text-blue-600 mb-2 hover-lift">
                        <ImageIcon className="w-6 h-6" />
                      </div>
                      <span className="text-xs font-black text-slate-800">Upload Front Side</span>
                      <span className="text-[11px] text-slate-400 mt-0.5 font-medium">Amul Brand Logo & Graphics</span>
                    </div>
                  )}
                </div>
              </div>

              {/* BACK PANEL DROPZONE */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-slate-800 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-600"></span> Back Panel
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">Barcode, FSSAI & Nutrition</span>
                </div>

                <div
                  onClick={() => backInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) handleBackSelect(e.dataTransfer.files[0]);
                  }}
                  className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all min-h-[220px] flex flex-col items-center justify-center relative overflow-hidden ${
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

                  {/* Laser Scanning Line Animation when Uploading */}
                  {isUploading && previewBack && (
                    <div className="absolute inset-0 pointer-events-none z-10">
                      <div className="laser-sweep" />
                    </div>
                  )}

                  {previewBack ? (
                    <div className="relative w-full flex flex-col items-center">
                      <img
                        src={previewBack}
                        alt="Back Preview"
                        className="max-h-36 object-contain rounded-xl shadow-xs mb-2"
                      />
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-emerald-700">Change Photo</span>
                        <span className="text-slate-300">•</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (previewBack) URL.revokeObjectURL(previewBack);
                            setFileBack(null);
                            setPreviewBack(null);
                            if (backInputRef.current) backInputRef.current.value = '';
                          }}
                          className="text-[11px] font-bold text-rose-600 hover:text-rose-700 flex items-center gap-0.5 cursor-pointer"
                        >
                          <X className="w-3 h-3" /> Remove
                        </button>
                      </div>
                      <span className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[200px] font-mono">
                        {fileBack?.name}
                      </span>
                    </div>
                  ) : (
                    <div className="py-4 flex flex-col items-center">
                      <div className="p-3.5 bg-white rounded-2xl shadow-xs border border-slate-100 text-emerald-600 mb-2 hover-lift">
                        <Camera className="w-6 h-6" />
                      </div>
                      <span className="text-xs font-black text-slate-800">Upload Back Side</span>
                      <span className="text-[11px] text-slate-400 mt-0.5 font-medium">Barcode EAN-13 & FSSAI</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Quick-Load Benchmark Packaging Samples (Dual-Scan) */}
            <div className="p-4 bg-slate-50/90 rounded-2xl border border-slate-200/80">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-3">
                <span className="text-xs font-black text-slate-800 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  Instant Benchmark: Load 360° Factory Standards
                </span>
                <span className="text-[10px] text-slate-400 font-medium">1-click verification with verified packaging</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() =>
                    loadSamplePouch(
                      'references/media_1788440125203.jpg',
                      'references/media_1788440132882.jpg',
                      'Amul_Gold_1L'
                    )
                  }
                  className="p-3 bg-white hover:bg-amber-50/60 border border-slate-200 hover:border-amber-300 rounded-2xl text-left transition-all group disabled:opacity-50 cursor-pointer shadow-xs hover-lift"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-400 shadow-xs" />
                    <span className="text-xs font-black text-slate-900 group-hover:text-amber-800">
                      Amul Gold 1L
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Full Cream Milk • V1 Ref</div>
                </button>

                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() =>
                    loadSamplePouch(
                      'references/media_1788440168117.jpg',
                      'references/media_1788440175260.jpg',
                      'Amul_Taaza_1L'
                    )
                  }
                  className="p-3 bg-white hover:bg-blue-50/60 border border-slate-200 hover:border-blue-300 rounded-2xl text-left transition-all group disabled:opacity-50 cursor-pointer shadow-xs hover-lift"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-blue-500 to-cyan-400 shadow-xs" />
                    <span className="text-xs font-black text-slate-900 group-hover:text-blue-800">
                      Amul Taaza 1L
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Toned Milk • V1 Ref</div>
                </button>

                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() =>
                    loadSamplePouch(
                      'references/media_1788440237491.jpg',
                      'references/media_1788440250225.jpg',
                      'Amul_Shakti_1L'
                    )
                  }
                  className="p-3 bg-white hover:bg-purple-50/60 border border-slate-200 hover:border-purple-300 rounded-2xl text-left transition-all group disabled:opacity-50 cursor-pointer shadow-xs hover-lift"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-400 shadow-xs" />
                    <span className="text-xs font-black text-slate-900 group-hover:text-purple-800">
                      Amul Shakti 1L
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Standardized Milk • V1 Ref</div>
                </button>
              </div>
            </div>

            {/* Complete 360 Information Card */}
            <div className="p-3.5 bg-blue-50/70 rounded-2xl border border-blue-100 flex items-start gap-3 text-xs text-blue-900 leading-relaxed">
              <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <div className="font-medium">
                <strong>360° Forensic Cross-Check:</strong> Uploading both Front and Back panels allows the AI engine to verify that front artwork matches back barcode identity and FSSAI manufacturer registration.
              </div>
            </div>

            {/* Error Alert */}
            {error && (
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800 font-medium animate-in fade-in">
                {error}
              </div>
            )}

            {/* Live Forensic Radar & Progress Bar (Visible while scanning) */}
            {isUploading && (
              <div className="p-6 bg-slate-900 text-white rounded-3xl border border-slate-800 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-300 relative overflow-hidden">
                <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full border border-blue-500/20 animate-radar-ring pointer-events-none" />
                <div className="absolute -right-6 -top-6 w-36 h-36 rounded-full border border-indigo-500/30 animate-radar-ring pointer-events-none" />
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3.5">
                    <div className="p-2.5 bg-blue-600/30 text-blue-400 rounded-2xl border border-blue-500/40 relative shadow-inner">
                      <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black tracking-tight text-white flex items-center gap-2">
                        Forensic Analysis in Progress
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] font-mono rounded-full border border-blue-400/30">
                          Live AI Pipeline
                        </span>
                      </h4>
                      <p className="text-xs text-slate-300 mt-0.5 font-medium">{uploadStep}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-black font-mono text-blue-400">{uploadProgress}%</span>
                  </div>
                </div>

                {/* Animated Gradient Progress Bar */}
                <div className="w-full bg-slate-800/80 h-2.5 rounded-full overflow-hidden border border-slate-700/60 p-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-400 rounded-full transition-all duration-300 shadow-sm shadow-blue-500/50"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>

                {/* 4 Forensic Milestones */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 1 ? 'bg-blue-950/60 border-blue-500/40 text-blue-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 1 ? 'bg-blue-400 animate-pulse' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">1. Domain Gate</span>
                  </div>
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 2 ? 'bg-indigo-950/60 border-indigo-500/40 text-indigo-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 2 ? 'bg-indigo-400 animate-pulse' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">2. Factory Match</span>
                  </div>
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 3 ? 'bg-purple-950/60 border-purple-500/40 text-purple-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 3 ? 'bg-purple-400 animate-pulse' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">3. 12-Engines</span>
                  </div>
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 4 ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 4 ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">4. Epistemic Risk</span>
                  </div>
                </div>
              </div>
            )}

            {/* Action Button */}
            <button
              onClick={executeDualScan}
              disabled={!fileFront || !fileBack || isUploading}
              className={`w-full py-4 px-6 rounded-2xl font-black text-sm shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer ${
                !fileFront || !fileBack || isUploading
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-blue-500/25 active:scale-[0.99] hover-lift'
              }`}
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Processing Physical Packaging Forensics...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-5 h-5" />
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
              <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
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
                    className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                      viewType === angle.id
                        ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
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
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all relative overflow-hidden ${
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

              {isUploading && singlePreview && (
                <div className="absolute inset-0 pointer-events-none z-10">
                  <div className="laser-sweep" />
                </div>
              )}

              {singlePreview ? (
                <div className="flex flex-col items-center">
                  <img
                    src={singlePreview}
                    alt="Scan Preview"
                    className="max-h-64 object-contain rounded-2xl shadow-xs mb-3"
                  />
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-blue-600">Change Photo</span>
                    <span className="text-slate-300">•</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (singlePreview) URL.revokeObjectURL(singlePreview);
                        setSingleFile(null);
                        setSinglePreview(null);
                        if (singleInputRef.current) singleInputRef.current.value = '';
                      }}
                      className="text-xs font-bold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" /> Remove photo
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 font-mono">
                    {singleFile?.name} ({singleFile ? (singleFile.size / (1024 * 1024)).toFixed(2) : '0'} MB)
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center py-6">
                  <div className="p-4 bg-white rounded-2xl shadow-xs border border-slate-100 mb-3 text-blue-600 hover-lift">
                    <Camera className="w-8 h-8" />
                  </div>
                  <p className="text-sm font-black text-slate-800">
                    Click to capture or upload product image
                  </p>
                  <p className="text-xs text-slate-400 mt-1 font-medium">Supports PNG, JPG, WEBP up to 15MB</p>
                </div>
              )}
            </div>

            {/* Quick-Load Benchmark Samples (Single Scan Mode) */}
            <div className="p-4 bg-slate-50/90 rounded-2xl border border-slate-200/80">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2.5">
                <span className="text-xs font-black text-slate-800 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  Instant Single-Panel Test Samples
                </span>
                <span className="text-[10px] text-slate-400 font-medium">1-click test with genuine reference</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() => loadSingleSample('references/media_1788440125203.jpg', 'Amul_Gold_Front')}
                  className="p-3 bg-white hover:bg-amber-50/60 border border-slate-200 hover:border-amber-300 rounded-2xl text-left transition-all group disabled:opacity-50 cursor-pointer shadow-xs hover-lift"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-400 shadow-xs" />
                    <span className="text-xs font-black text-slate-900 group-hover:text-amber-800">Amul Gold Front</span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Logo & Typography standard</div>
                </button>

                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() => loadSingleSample('references/media_1788440168117.jpg', 'Amul_Taaza_Front')}
                  className="p-3 bg-white hover:bg-blue-50/60 border border-slate-200 hover:border-blue-300 rounded-2xl text-left transition-all group disabled:opacity-50 cursor-pointer shadow-xs hover-lift"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-blue-500 to-cyan-400 shadow-xs" />
                    <span className="text-xs font-black text-slate-900 group-hover:text-blue-800">Amul Taaza Front</span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Toned Milk standard</div>
                </button>

                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() => loadSingleSample('references/media_1788440237491.jpg', 'Amul_Shakti_Front')}
                  className="p-3 bg-white hover:bg-purple-50/60 border border-slate-200 hover:border-purple-300 rounded-2xl text-left transition-all group disabled:opacity-50 cursor-pointer shadow-xs hover-lift"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-400 shadow-xs" />
                    <span className="text-xs font-black text-slate-900 group-hover:text-purple-800">Amul Shakti Front</span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Standardized Milk</div>
                </button>
              </div>
            </div>

            {/* Live Forensic Radar & Progress Bar (Single Scan) */}
            {isUploading && (
              <div className="p-6 bg-slate-900 text-white rounded-3xl border border-slate-800 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-300 relative overflow-hidden">
                <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full border border-blue-500/20 animate-radar-ring pointer-events-none" />
                <div className="absolute -right-6 -top-6 w-36 h-36 rounded-full border border-indigo-500/30 animate-radar-ring pointer-events-none" />
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3.5">
                    <div className="p-2.5 bg-blue-600/30 text-blue-400 rounded-2xl border border-blue-500/40 relative shadow-inner">
                      <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black tracking-tight text-white flex items-center gap-2">
                        Forensic Analysis in Progress
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] font-mono rounded-full border border-blue-400/30">
                          Live AI Pipeline
                        </span>
                      </h4>
                      <p className="text-xs text-slate-300 mt-0.5 font-medium">{uploadStep}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-black font-mono text-blue-400">{uploadProgress}%</span>
                  </div>
                </div>

                {/* Animated Gradient Progress Bar */}
                <div className="w-full bg-slate-800/80 h-2.5 rounded-full overflow-hidden border border-slate-700/60 p-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-400 rounded-full transition-all duration-300 shadow-sm shadow-blue-500/50"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>

                {/* 4 Forensic Milestones */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 1 ? 'bg-blue-950/60 border-blue-500/40 text-blue-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 1 ? 'bg-blue-400 animate-pulse' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">1. Domain Gate</span>
                  </div>
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 2 ? 'bg-indigo-950/60 border-indigo-500/40 text-indigo-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 2 ? 'bg-indigo-400 animate-pulse' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">2. Factory Match</span>
                  </div>
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 3 ? 'bg-purple-950/60 border-purple-500/40 text-purple-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 3 ? 'bg-purple-400 animate-pulse' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">3. 12-Engines</span>
                  </div>
                  <div className={`p-2 rounded-xl border flex items-center gap-2 ${uploadPhase >= 4 ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}>
                    <span className={`w-2 h-2 rounded-full ${uploadPhase >= 4 ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="truncate font-medium">4. Epistemic Risk</span>
                  </div>
                </div>
              </div>
            )}

            {/* Capture Checklist */}
            <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200/70 flex items-start gap-3">
              <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
              <div className="text-xs text-slate-600 leading-relaxed font-medium">
                <span className="font-black text-slate-800">Capture Recommendation:</span> Ensure packaging fills the viewfinder, with clear illumination and no harsh flash reflection.
              </div>
            </div>

            {/* Error Alert */}
            {error && (
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800 font-medium animate-in fade-in">
                {error}
              </div>
            )}

            {/* Single Execute Button */}
            <button
              onClick={executeSingleScan}
              disabled={!singleFile || isUploading}
              className={`w-full py-4 px-6 rounded-2xl font-black text-sm shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer ${
                !singleFile || isUploading
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-blue-500/25 active:scale-[0.99] hover-lift'
              }`}
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Processing Physical Packaging Forensics...</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  <span>Verify Packaging Panel</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
