import React, { useEffect, useState } from 'react';
import { Clock, ExternalLink, History, Loader2, ShieldCheck, X } from 'lucide-react';
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
    scanApi
      .getMyHistory()
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
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300 border-l border-slate-200/90">
        {/* Header */}
        <div className="p-5 border-b border-slate-200/90 flex items-center justify-between bg-white/95 backdrop-blur-md">
          <div className="flex items-center gap-2.5 font-black text-sm text-slate-900">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
              <History className="w-4 h-4" />
            </div>
            <div>
              <span>My Verification History</span>
              <p className="text-[10px] text-slate-400 font-medium">Your recent product scans</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-56 text-slate-400">
              <Loader2 className="w-7 h-7 animate-spin mb-2 text-blue-600" />
              <p className="text-xs font-semibold text-slate-600">Retrieving scan records...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-16 text-slate-400 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-black text-slate-700">No recent scans recorded</p>
                <p className="text-[11px] text-slate-400 mt-1 max-w-xs mx-auto">
                  Log in and verify packaging to archive your inspection reports here.
                </p>
              </div>
            </div>
          ) : (
            history.map((scan) => (
              <div
                key={scan.id}
                onClick={() => handleSelect(scan.id)}
                className="p-4 bg-slate-50/80 hover:bg-blue-50/50 border border-slate-200/80 hover:border-blue-300 rounded-2xl cursor-pointer hover-lift flex items-center justify-between group shadow-xs"
              >
                <div className="space-y-1">
                  <div className="text-xs font-black text-slate-800 group-hover:text-blue-700 transition-colors">
                    {scan.product_name || 'Amul Milk Pouch'}
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-1.5 font-medium">
                    <Clock className="w-3 h-3" />
                    <span>
                      {new Date(scan.created_at).toLocaleDateString()} at{' '}
                      {new Date(scan.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`px-2.5 py-1 rounded-full text-[10px] font-black ${
                      (scan.risk_score || 0) < 30
                        ? 'bg-emerald-100 text-emerald-800'
                        : (scan.risk_score || 0) < 70
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    Risk: {scan.risk_score || 0}
                  </span>

                  {loadingId === scan.id ? (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  ) : (
                    <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200/80 bg-slate-50/80 text-[11px] text-slate-500 flex items-center justify-between">
          <span className="flex items-center gap-1 font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
            <span>Encrypted Scan Archive</span>
          </span>
          <span className="text-[10px] text-slate-400 font-mono">Total: {history.length}</span>
        </div>
      </div>
    </div>
  );
};

