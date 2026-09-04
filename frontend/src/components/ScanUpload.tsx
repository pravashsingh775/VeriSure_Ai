import React, { useRef, useState } from 'react';
import { Camera, Info, Loader2, Sparkles, Upload, X } from 'lucide-react';
import { scanApi } from '../services/api';
import type { ScanDetail } from '../types';

interface ScanUploadProps {
  onScanCompleted: (result: ScanDetail) => void;
}

export const ScanUpload: React.FC<ScanUploadProps> = ({ onScanCompleted }) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [viewType, setViewType] = useState('FRONT');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE_MB = 15;
  const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

  const handleSelectedFile = (selected: File) => {
    if (selected.size > MAX_FILE_SIZE_BYTES) {
      setError(
        `Selected image (${(selected.size / (1024 * 1024)).toFixed(1)} MB) exceeds the ${MAX_FILE_SIZE_MB} MB limit. Please select a smaller photo or compress it.`
      );
      setFile(null);
      setPreview(null);
      return;
    }
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleClearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    setPreview(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const executeScan = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      setUploadStep('Assessing image clarity, blur & lighting...');
      const result = await scanApi.uploadScan(file, viewType);
      setUploadStep('Analysis complete! Synthesizing report...');
      setTimeout(() => {
        onScanCompleted(result);
        setIsUploading(false);
      }, 500);
    } catch (err: any) {
      setIsUploading(false);
      if (!err.response) {
        setError('Unable to reach VeriSure backend server. Please ensure the backend is running on http://localhost:8000.');
      } else {
        setError(err.response?.data?.detail || 'Failed to process product photograph. Please try again.');
      }
    }
  };

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 p-6 sm:p-8 shadow-sm max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 mb-2">
          <Sparkles className="w-3.5 h-3.5" /> Fast AI Authenticity Risk Assessment
        </span>
        <h2 className="text-2xl font-black text-slate-900 tracking-tight">
          Verify Product Packaging
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Upload or capture a photo of Amul milk packaging for multi-modal authenticity verification.
        </p>
      </div>

      {/* View Angle Selector */}
      <div className="mb-6">
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
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
          preview
            ? 'border-blue-300 bg-blue-50/20'
            : 'border-slate-200 hover:border-blue-400 bg-slate-50/50 hover:bg-blue-50/30'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          className="hidden"
        />

        {preview ? (
          <div className="flex flex-col items-center">
            <img
              src={preview}
              alt="Scan Preview"
              className="max-h-64 object-contain rounded-xl shadow-xs mb-3"
            />
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-blue-600">Click to change photograph</span>
              <span className="text-slate-300">•</span>
              <button
                type="button"
                onClick={handleClearFile}
                className="text-xs font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" /> Remove photo
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              {file?.name} ({file ? (file.size / (1024 * 1024)).toFixed(2) : '0'} MB)
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

      {/* Capture Quality Checklist */}
      <div className="mt-4 p-3.5 bg-slate-50 rounded-xl border border-slate-200/60 flex items-start gap-3">
        <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-600 leading-relaxed">
          <span className="font-semibold text-slate-800">For optimal risk assessment:</span> Hold
          camera parallel to packaging, avoid severe surface reflections, and keep the packaging
          centered in frame.
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mt-4 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 font-medium">
          {error}
        </div>
      )}

      {/* Execute Button */}
      <div className="mt-6">
        <button
          onClick={executeScan}
          disabled={!file || isUploading}
          className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2 ${
            !file || isUploading
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
              <span>Verify Authenticity</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
