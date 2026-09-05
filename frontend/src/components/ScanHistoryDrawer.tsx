import React, { useEffect, useState } from 'react';
import { Clock, ExternalLink, History, Loader2, X } from 'lucide-react';
import { scanApi } from '../services/api';
import type { ScanDetail, ScanSummary } from '../types';

interface ScanHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectScan: (scan: ScanDetail) => void;
}

export const ScanHistoryDrawer: React.FC<ScanHistoryDrawerProps> = ({
  isOpen,
  onClose,
  onSelectScan,
}) => {
  const [history, setHistory] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let ignore = false;
    Promise.resolve().then(() => {
      if (!ignore) setLoading(true);
    });
    scanApi.getMyHistory()
      .then((data) => {
        if (!ignore) setHistory(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [isOpen]);

  const handleSelect = async (scanId: string) => {
    setLoadingId(scanId);
    try {
      const detail = await scanApi.getScanDetail(scanId);
      onSelectScan(detail);
      onClose();
    } finally {
      setLoadingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-sm text-slate-800">
            <History className="w-4 h-4 text-blue-600" />
            <span>My Scan History</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-48 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin mb-2" />
              <p className="text-xs">Loading past scans...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-60" />
              <p className="text-xs font-semibold">No recent scans recorded</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Log in and scan products to build your history.
              </p>
            </div>
          ) : (
            history.map((scan) => (
              <div
                key={scan.id}
                onClick={() => handleSelect(scan.id)}
                className="p-3.5 bg-slate-50 hover:bg-blue-50/50 border border-slate-200 hover:border-blue-300 rounded-xl cursor-pointer transition-all flex items-center justify-between group"
              >
                <div>
                  <div className="text-xs font-bold text-slate-800">
                    {scan.product_name || 'Amul Product'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {new Date(scan.created_at).toLocaleDateString()} at{' '}
                    {new Date(scan.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      (scan.risk_score || 0) < 30
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    Risk: {scan.risk_score || 0}
                  </span>
                  {loadingId === scan.id ? (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  ) : (
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600" />
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

