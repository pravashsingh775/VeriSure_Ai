import React, { useEffect, useState } from 'react';
import {
  Database,
  Lock,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import { analyticsApi, caseApi, modelApi } from '../services/api';
import type { AdminAnalytics, ModelEntity, SuspiciousCase, User } from '../types';

interface AdminPortalProps {
  currentUser?: User | null;
  onOpenLogin?: (mode?: 'signin' | 'register') => void;
}

export const AdminPortal: React.FC<AdminPortalProps> = ({ currentUser, onOpenLogin }) => {
  const [cases, setCases] = useState<SuspiciousCase[]>([]);
  const [models, setModels] = useState<ModelEntity[]>([]);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [selectedCase, setSelectedCase] = useState<SuspiciousCase | null>(null);
  const [reviewComments, setReviewComments] = useState('');
  const [isReviewing, setIsReviewing] = useState(false);
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [caseFilter, setCaseFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [hasCaseAccess, setHasCaseAccess] = useState<boolean | null>(null);
  const [hasAdminAccess, setHasAdminAccess] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadAdminData = async () => {
    // Pre-flight client credential check: prevents 403 Forbidden log spam for unauthorized visitors
    const token = localStorage.getItem('verisure_token');
    const storedUserStr = localStorage.getItem('verisure_user');
    let userRoles: string[] = [];
    if (storedUserStr) {
      try {
        const u = JSON.parse(storedUserStr);
        userRoles = u.roles || [];
      } catch {
        // ignore parse error
      }
    }

    const hasAnyAdminRole = userRoles.some((r) =>
      ['PLATFORM_ADMIN', 'BRAND_ADMIN', 'BRAND_REVIEWER'].includes(r)
    );

    if (!token || !hasAnyAdminRole) {
      Promise.resolve().then(() => {
        setHasCaseAccess(false);
        setHasAdminAccess(false);
        setCases([]);
        setModels([]);
        setAnalytics(null);
        setIsLoading(false);
      });
      return;
    }

    Promise.resolve().then(() => setIsLoading(true));

    const [casesRes, modelsRes, analyticsRes] = await Promise.allSettled([
      caseApi.listCases(),
      modelApi.listModels(),
      analyticsApi.getAdminAnalytics(),
    ]);

    if (casesRes.status === 'fulfilled') {
      setCases(casesRes.value);
      setHasCaseAccess(true);
    } else {
      setHasCaseAccess(false);
    }

    if (modelsRes.status === 'fulfilled') {
      setModels(modelsRes.value);
      setHasAdminAccess(true);
    } else {
      setHasAdminAccess(false);
    }

    if (analyticsRes.status === 'fulfilled') {
      setAnalytics(analyticsRes.value);
    } else {
      setAnalytics(null);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    let ignore = false;
    Promise.resolve().then(() => {
      if (!ignore) {
        loadAdminData();
      }
    });
    return () => {
      ignore = true;
    };
  }, [currentUser]);

  const handleReviewAction = async (status: string) => {
    if (!selectedCase) return;
    setIsReviewing(true);
    try {
      await caseApi.reviewCase(
        selectedCase.id,
        status,
        reviewComments || `Expert triage transition to ${status}.`
      );
      setReviewComments('');
      setSelectedCase(null);
      await loadAdminData();
    } finally {
      setIsReviewing(false);
    }
  };

  const handleRunEvaluation = async (versionId: string) => {
    setEvaluatingId(versionId);
    try {
      await modelApi.runEvaluation(versionId);
      await loadAdminData();
    } finally {
      setEvaluatingId(null);
    }
  };

  const filteredCases = cases.filter((c) => {
    const matchesFilter =
      caseFilter === 'ALL' ||
      (caseFilter === 'OPEN' && (c.status === 'OPEN' || c.status === 'PENDING')) ||
      c.status === caseFilter;
    const matchesSearch =
      searchQuery === '' ||
      c.case_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.notes && c.notes.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Admin Header Banner */}
      <div className="bg-white/95 backdrop-blur-xl p-6 sm:p-8 rounded-3xl border border-slate-200/90 shadow-[0_4px_20px_-4px_rgba(15,23,42,0.05)] flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative overflow-hidden">
        {/* Subtle Top Accent Line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600" />

        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              Platform Administration &amp; MLOps
            </h1>
            <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-black rounded-full uppercase tracking-wider">
              Admin / Reviewer Tier
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Suspicious case triage, human-in-the-loop expert review, and model evaluation telemetry.
          </p>
        </div>

        <button
          onClick={loadAdminData}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-all self-start sm:self-auto cursor-pointer shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
          <span>{isLoading ? 'Refreshing...' : 'Refresh Telemetry'}</span>
        </button>
      </div>

      {/* Role Access Guard Warning if user lacks admin privileges */}
      {!isLoading && hasAdminAccess === false && hasCaseAccess === false && (
        <div className="bg-amber-50/90 border border-amber-200 rounded-3xl p-8 text-center max-w-xl mx-auto space-y-4 shadow-sm">
          <div className="w-14 h-14 bg-amber-100 text-amber-700 rounded-2xl flex items-center justify-center mx-auto shadow-xs ring-4 ring-amber-100/60">
            <Lock className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-black text-slate-900">Elevated Privileges Required</h2>
            <p className="text-xs text-slate-600 leading-relaxed max-w-md mx-auto">
              You are currently browsing as a Consumer. The Triage Queue, Model Registry, and Telemetry require <strong>Platform Admin</strong> or <strong>Brand Reviewer</strong> credentials.
            </p>
          </div>
          {onOpenLogin && (
            <div className="pt-2">
              <button
                onClick={() => onOpenLogin('signin')}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white text-xs font-black rounded-xl shadow-md shadow-amber-600/20 transition-all cursor-pointer"
              >
                <UserCheck className="w-4 h-4" />
                <span>Sign In as Admin or Reviewer</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Operational Telemetry Cards */}
      {analytics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-xs hover-lift">
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
              Total Scans
            </span>
            <div className="text-3xl font-black text-slate-900 mt-1">{analytics.total_scans}</div>
          </div>
          <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-xs hover-lift">
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
              Open Triage Cases
            </span>
            <div className="text-3xl font-black text-amber-600 mt-1">{analytics.open_cases}</div>
          </div>
          <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-xs hover-lift">
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
              Verified Anomalies
            </span>
            <div className="text-3xl font-black text-rose-600 mt-1">{analytics.verified_counterfeits}</div>
          </div>
          <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-xs hover-lift">
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
              Quality Pass Rate
            </span>
            <div className="text-3xl font-black text-emerald-600 mt-1">
              {analytics.quality_pass_rate_percent}%
            </div>
          </div>
        </div>
      )}

      {/* Suspicious Case Triage Queue */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Suspicious Case Triage Queue ({cases.length})
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Auto-triaged by risk threshold for physical verification &amp; human oversight
            </p>
          </div>

          {/* Search & Status Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search case #..."
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 w-36 sm:w-44 font-medium"
              />
            </div>
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
              {['ALL', 'OPEN', 'VERIFIED_SUSPICIOUS', 'VERIFIED_GENUINE'].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setCaseFilter(filter)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                    caseFilter === filter
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {filter === 'ALL' ? 'All' : filter.replace('VERIFIED_', '')}
                </button>
              ))}
            </div>
          </div>
        </div>

        {hasCaseAccess === false ? (
          <div className="text-center py-10 text-slate-400 text-xs font-medium">
            Sign in with Reviewer or Admin credentials to inspect suspicious cases.
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-xs font-medium">
            {cases.length === 0 ? 'No pending suspicious cases in queue.' : 'No cases match your filter criteria.'}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredCases.map((c) => (
              <div
                key={c.id}
                className="p-4 bg-slate-50/80 hover:bg-slate-50 border border-slate-200/80 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-black text-slate-900">{c.case_number}</span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase ${
                        c.status === 'OPEN' || c.status === 'PENDING'
                          ? 'bg-amber-100 text-amber-800'
                          : c.status === 'VERIFIED_SUSPICIOUS'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {c.status}
                    </span>
                    <span className="text-[10px] text-slate-400 font-semibold">
                      Priority: {c.priority}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1 font-medium">{c.notes}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setSelectedCase(c)}
                    className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl text-xs font-black transition-all cursor-pointer shadow-xs"
                  >
                    Review Case
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Review Action Modal */}
        {selectedCase && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl p-6 sm:p-7 max-w-lg w-full shadow-2xl space-y-4 border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
              <h3 className="text-base font-black text-slate-900">
                Review Case: {selectedCase.case_number}
              </h3>
              <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                {selectedCase.notes}
              </p>

              <div>
                <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1.5">
                  Expert Reviewer Feedback &amp; Verification Notes
                </label>
                <textarea
                  value={reviewComments}
                  onChange={(e) => setReviewComments(e.target.value)}
                  placeholder="Enter physical verification notes, barcode confirmation, or reason for verdict..."
                  rows={3}
                  className="w-full text-xs p-3.5 border border-slate-200 rounded-2xl focus:outline-blue-600 font-medium"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  onClick={() => setSelectedCase(null)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleReviewAction('VERIFIED_GENUINE')}
                  disabled={isReviewing}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black cursor-pointer transition-all shadow-xs"
                >
                  Confirm Genuine
                </button>
                <button
                  onClick={() => handleReviewAction('VERIFIED_SUSPICIOUS')}
                  disabled={isReviewing}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-black cursor-pointer transition-all shadow-xs"
                >
                  Confirm Suspicious
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Model Registry & Benchmark Metrics */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs space-y-4">
        <h2 className="text-sm font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <Database className="w-4 h-4 text-purple-600" />
          Model Registry &amp; Scientific Benchmarks ({models.length})
        </h2>

        {hasAdminAccess === false ? (
          <div className="text-center py-10 text-slate-400 text-xs font-medium">
            Model registry and evaluation benchmarks are restricted to Platform Administrators.
          </div>
        ) : models.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-xs font-medium">
            No registered models found in registry.
          </div>
        ) : (
          <div className="space-y-4">
            {models.map((model) => {
              const version = model.versions?.[0];
              const evalRun = version?.evaluations?.[0];
              const hasMetrics = evalRun && evalRun.accuracy !== null && evalRun.accuracy !== undefined;

              return (
                <div key={model.id} className="p-5 bg-slate-50/80 border border-slate-200/80 rounded-2xl space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-black text-slate-900">{model.name}</span>
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-[10px] font-black rounded-full">
                          {version?.version_tag || 'v1.0.0'}
                        </span>
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-black rounded-full uppercase">
                          {version?.status || 'PRODUCTION'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5 font-medium">{model.architecture}</p>
                    </div>

                    {version && (
                      <button
                        onClick={() => handleRunEvaluation(version.id)}
                        disabled={evaluatingId === version.id}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-white border border-slate-200 hover:border-purple-300 rounded-xl text-xs font-bold text-purple-700 shadow-xs transition-all active:scale-[0.98] cursor-pointer"
                      >
                        <Play className="w-3.5 h-3.5" />
                        {evaluatingId === version.id ? 'Evaluating...' : 'Run Benchmark'}
                      </button>
                    )}
                  </div>

                  {/* Honest Metrics Display without fake fallbacks */}
                  {evalRun ? (
                    hasMetrics ? (
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2 border-t border-slate-200/60">
                        <div className="bg-white p-2.5 rounded-xl border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-black text-slate-400">Accuracy</span>
                          <div className="text-xs font-black text-slate-900 mt-0.5">
                            {Math.round((evalRun.accuracy || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2.5 rounded-xl border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-black text-slate-400">Precision</span>
                          <div className="text-xs font-black text-slate-900 mt-0.5">
                            {Math.round((evalRun.precision || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2.5 rounded-xl border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-black text-slate-400">Recall</span>
                          <div className="text-xs font-black text-slate-900 mt-0.5">
                            {Math.round((evalRun.recall || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2.5 rounded-xl border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-black text-slate-400">F1 Score</span>
                          <div className="text-xs font-black text-slate-900 mt-0.5">
                            {Math.round((evalRun.f1 || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2.5 rounded-xl border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-black text-slate-400">ROC-AUC</span>
                          <div className="text-xs font-black text-slate-900 mt-0.5">
                            {evalRun.roc_auc !== null && evalRun.roc_auc !== undefined ? evalRun.roc_auc.toFixed(3) : 'N/A'}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs bg-white p-3 rounded-xl border border-slate-200">
                        <span className="text-slate-600 font-medium flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                          <span>Status: <strong>{evalRun.confusion_matrix?.status || 'PENDING_PHYSICAL_BENCHMARK'}</strong></span>
                        </span>
                        <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md font-bold">
                          Empirical Retail Dataset Required
                        </span>
                      </div>
                    )
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
