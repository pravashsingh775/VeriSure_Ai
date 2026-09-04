import React, { useEffect, useState } from 'react';
import { Database, Lock, Play, Search, ShieldAlert, UserCheck } from 'lucide-react';
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

  useEffect(() => {
    loadAdminData();
  }, [currentUser]);

  const loadAdminData = async () => {
    setIsLoading(true);

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
      setHasCaseAccess(false);
      setHasAdminAccess(false);
      setCases([]);
      setModels([]);
      setAnalytics(null);
      setIsLoading(false);
      return;
    }

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
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Admin Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">
              Platform Administration & MLOps
            </h1>
            <span className="px-2.5 py-0.5 bg-blue-100 text-blue-800 text-xs font-bold rounded-full">
              ADMIN / REVIEWER TIER
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Suspicious case triage, human-in-the-loop review, and model evaluation telemetry.
          </p>
        </div>

        <button
          onClick={loadAdminData}
          disabled={isLoading}
          className="px-3.5 py-2 text-xs font-bold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-all self-start sm:self-auto cursor-pointer"
        >
          {isLoading ? 'Refreshing...' : 'Refresh Data'}
        </button>
      </div>

      {/* Role Access Guard Warning if user lacks admin privileges */}
      {!isLoading && hasAdminAccess === false && hasCaseAccess === false && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center max-w-xl mx-auto space-y-3">
          <div className="w-12 h-12 bg-amber-100 text-amber-700 rounded-2xl flex items-center justify-center mx-auto shadow-xs">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-base font-black text-slate-900">Elevated Privileges Required</h2>
          <p className="text-xs text-slate-600 leading-relaxed max-w-md mx-auto">
            You are currently browsing as a Consumer. The Triage Queue, Model Registry, and Telemetry require <strong>Platform Admin</strong> or <strong>Brand Reviewer</strong> credentials.
          </p>
          {onOpenLogin && (
            <div className="pt-1">
              <button
                onClick={() => onOpenLogin('signin')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer"
              >
                <UserCheck className="w-4 h-4" /> Sign In as Admin
              </button>
            </div>
          )}
        </div>
      )}

      {/* Operational Telemetry Cards */}
      {analytics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Total Scans
            </span>
            <div className="text-2xl font-black text-slate-900 mt-1">{analytics.total_scans}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Open Triage Cases
            </span>
            <div className="text-2xl font-black text-amber-600 mt-1">{analytics.open_cases}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Verified Anomalies
            </span>
            <div className="text-2xl font-black text-rose-600 mt-1">{analytics.verified_counterfeits}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Quality Pass Rate
            </span>
            <div className="text-2xl font-black text-emerald-600 mt-1">
              {analytics.quality_pass_rate_percent}%
            </div>
          </div>
        </div>
      )}

      {/* Suspicious Case Triage Queue */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Suspicious Case Triage Queue ({cases.length})
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Auto-triaged by risk decision threshold</p>
          </div>

          {/* Search & Status Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search case #..."
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-blue-600 w-36 sm:w-44"
              />
            </div>
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
              {['ALL', 'OPEN', 'VERIFIED_SUSPICIOUS', 'VERIFIED_GENUINE'].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setCaseFilter(filter)}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-all cursor-pointer ${
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
          <div className="text-center py-8 text-slate-400 text-xs font-medium">
            Sign in with Reviewer or Admin credentials to inspect suspicious cases.
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs font-medium">
            {cases.length === 0 ? 'No pending suspicious cases in queue.' : 'No cases match your filter criteria.'}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredCases.map((c) => (
              <div
                key={c.id}
                className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-900">{c.case_number}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        c.status === 'OPEN' || c.status === 'PENDING'
                          ? 'bg-amber-100 text-amber-800'
                          : c.status === 'VERIFIED_SUSPICIOUS'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {c.status}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Priority: {c.priority}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{c.notes}</p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedCase(c)}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all cursor-pointer"
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
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Review Case: {selectedCase.case_number}
              </h3>
              <p className="text-xs text-slate-600">{selectedCase.notes}</p>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Expert Feedback & Notes
                </label>
                <textarea
                  value={reviewComments}
                  onChange={(e) => setReviewComments(e.target.value)}
                  placeholder="Enter physical verification notes, lab findings, or reason for verdict..."
                  rows={3}
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  onClick={() => setSelectedCase(null)}
                  className="px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleReviewAction('VERIFIED_GENUINE')}
                  disabled={isReviewing}
                  className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold cursor-pointer transition-all"
                >
                  Confirm Genuine
                </button>
                <button
                  onClick={() => handleReviewAction('VERIFIED_SUSPICIOUS')}
                  disabled={isReviewing}
                  className="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold cursor-pointer transition-all"
                >
                  Confirm Suspicious
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Model Registry & Benchmark Metrics */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Database className="w-4 h-4 text-purple-600" />
          Model Registry & Scientific Benchmarks ({models.length})
        </h2>

        {hasAdminAccess === false ? (
          <div className="text-center py-8 text-slate-400 text-xs font-medium">
            Model registry and evaluation benchmarks are restricted to Platform Administrators.
          </div>
        ) : models.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs font-medium">
            No registered models found in registry.
          </div>
        ) : (
          <div className="space-y-4">
            {models.map((model) => {
              const version = model.versions?.[0];
              const evalRun = version?.evaluations?.[0];
              const hasMetrics = evalRun && evalRun.accuracy !== null && evalRun.accuracy !== undefined;

              return (
                <div key={model.id} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900">{model.name}</span>
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-[10px] font-bold rounded-full">
                          {version?.version_tag || 'v1.0.0'}
                        </span>
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded-full uppercase">
                          {version?.status || 'PRODUCTION'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{model.architecture}</p>
                    </div>

                    {version && (
                      <button
                        onClick={() => handleRunEvaluation(version.id)}
                        disabled={evaluatingId === version.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 hover:border-purple-300 rounded-lg text-xs font-bold text-purple-700 shadow-xs transition-all active:scale-[0.98] cursor-pointer"
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
                        <div className="bg-white p-2 rounded-lg border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-bold text-slate-400">Accuracy</span>
                          <div className="text-xs font-bold text-slate-900">
                            {Math.round((evalRun.accuracy || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2 rounded-lg border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-bold text-slate-400">Precision</span>
                          <div className="text-xs font-bold text-slate-900">
                            {Math.round((evalRun.precision || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2 rounded-lg border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-bold text-slate-400">Recall</span>
                          <div className="text-xs font-bold text-slate-900">
                            {Math.round((evalRun.recall || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2 rounded-lg border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-bold text-slate-400">F1 Score</span>
                          <div className="text-xs font-bold text-slate-900">
                            {Math.round((evalRun.f1 || 0) * 100)}%
                          </div>
                        </div>
                        <div className="bg-white p-2 rounded-lg border border-slate-200 text-center">
                          <span className="text-[9px] uppercase font-bold text-slate-400">ROC-AUC</span>
                          <div className="text-xs font-bold text-slate-900">
                            {evalRun.roc_auc !== null && evalRun.roc_auc !== undefined ? evalRun.roc_auc.toFixed(3) : 'N/A'}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs bg-white p-2.5 rounded-lg border border-slate-200">
                        <span className="text-slate-600 font-medium">
                          Benchmark Status: <strong>{evalRun.confusion_matrix?.status || 'PENDING_PHYSICAL_BENCHMARK'}</strong>
                        </span>
                        <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded font-bold">
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

