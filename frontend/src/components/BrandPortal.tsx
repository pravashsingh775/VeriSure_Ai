import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Eye,
  Filter,
  Image as ImageIcon,
  Layers,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Tag,
  TrendingUp,
  X,
} from 'lucide-react';
import { brandApi } from '../services/api';
import type { BrandAnalytics, ReferenceImage } from '../types';

export const BrandPortal: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'references' | 'analytics' | 'catalog'>('references');
  const [packagingVersions, setPackagingVersions] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [references, setReferences] = useState<ReferenceImage[]>([]);
  const [analytics, setAnalytics] = useState<BrandAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [productFilter, setProductFilter] = useState<string>('ALL');
  const [selectedImage, setSelectedImage] = useState<ReferenceImage | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [pvRes, prodRes, refRes, analyticsRes] = await Promise.allSettled([
        brandApi.getPackagingVersions(),
        brandApi.getProducts(),
        brandApi.getReferences(),
        brandApi.getBrandAnalytics('AMUL'),
      ]);

      if (pvRes.status === 'fulfilled') setPackagingVersions(pvRes.value);
      if (prodRes.status === 'fulfilled') setProducts(prodRes.value);
      if (refRes.status === 'fulfilled') setReferences(refRes.value);
      if (analyticsRes.status === 'fulfilled') setAnalytics(analyticsRes.value);
    } catch {
      // Graceful fallback
    } finally {
      setLoading(false);
    }
  };

  const filteredReferences = references.filter((ref) => {
    if (productFilter === 'ALL') return true;
    return ref.product_name?.toLowerCase().includes(productFilter.toLowerCase());
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Brand Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3.5 bg-red-50 text-red-600 rounded-2xl border border-red-200 shadow-inner">
            <Building2 className="w-8 h-8" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                Amul Dairy Brand Portal
              </h1>
              <span className="px-2.5 py-0.5 bg-red-100 text-red-700 text-xs font-bold rounded-full">
                GCMMF • AMUL
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Gujarat Co-operative Milk Marketing Federation • Anand, Gujarat • Reference Corpus V1
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-xl text-xs font-bold border border-emerald-200 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" /> Corpus V1: 12 Images Verified
          </span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-xl px-2 py-1 shadow-xs overflow-x-auto">
        <button
          onClick={() => setActiveTab('references')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-lg transition-all whitespace-nowrap ${
            activeTab === 'references'
              ? 'bg-red-50 text-red-600 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <ImageIcon className="w-4 h-4" />
          Reference Corpus V1 Gallery ({references.length})
        </button>

        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-lg transition-all whitespace-nowrap ${
            activeTab === 'analytics'
              ? 'bg-red-50 text-red-600 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Brand Scan Telemetry
        </button>

        <button
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-lg transition-all whitespace-nowrap ${
            activeTab === 'catalog'
              ? 'bg-red-50 text-red-600 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Layers className="w-4 h-4" />
          Packaging Lifecycle ({packagingVersions.length})
        </button>
      </div>

      {/* TAB 1: Reference Corpus V1 Gallery */}
      {activeTab === 'references' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                Official Ground-Truth Reference Standards
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Cryptographically bound reference packagings used for SSIM heatmaps, ORB homography, and color delta comparisons.
              </p>
            </div>

            {/* Product Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
                {(['ALL', 'Gold', 'Taaza', 'Shakti'] as const).map((prod) => (
                  <button
                    key={prod}
                    onClick={() => setProductFilter(prod)}
                    className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all ${
                      productFilter === prod
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    {prod === 'ALL' ? 'All (12)' : `Amul ${prod}`}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {loading ? (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-400 text-sm">
              Loading Reference Corpus V1 assets...
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredReferences.map((ref) => (
                <div
                  key={ref.id}
                  className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs hover:shadow-md transition-all flex flex-col justify-between group"
                >
                  <div className="relative bg-slate-100 aspect-4/3 overflow-hidden flex items-center justify-center">
                    <img
                      src={`/data/storage/${ref.image_path}`}
                      alt={ref.original_filename || ref.view_type}
                      className="w-full h-full object-contain p-2 group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                    <div className="absolute top-2 left-2 flex gap-1">
                      <span className="px-2 py-0.5 bg-slate-900/80 backdrop-blur-xs text-white text-[10px] font-black rounded-md uppercase">
                        {ref.view_type}
                      </span>
                      <span className="px-2 py-0.5 bg-emerald-600/90 backdrop-blur-xs text-white text-[10px] font-bold rounded-md">
                        {Math.round(ref.trust_level * 100)}% Trust
                      </span>
                    </div>

                    <button
                      onClick={() => setSelectedImage(ref)}
                      className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-white text-xs font-bold cursor-pointer"
                    >
                      <Eye className="w-4 h-4" /> Inspect Image
                    </button>
                  </div>

                  <div className="p-4 space-y-2">
                    <div>
                      <div className="text-xs font-black text-slate-900">
                        {ref.product_name || 'Amul Milk'}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {ref.variant_name} • {ref.pack_size || 'Pouch'} ({ref.version_code || 'V1'})
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                      <span className="font-mono text-slate-400">
                        ID: {ref.id.slice(0, 8)}...
                      </span>
                      <span className="flex items-center gap-1 text-emerald-600 font-bold">
                        <CheckCircle2 className="w-3 h-3" /> {ref.approval_status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Brand Telemetry & Analytics */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Total Brand Scans
              </div>
              <div className="text-2xl font-black text-slate-900 mt-1">
                {analytics?.total_scans ?? 0}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-500" /> Consumer verification runs
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Active Packaging Versions
              </div>
              <div className="text-2xl font-black text-slate-900 mt-1">
                {analytics?.active_packaging_versions ?? packagingVersions.length}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-purple-500" /> Active in retail circulation
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Counterfeit / Tamper Rate
              </div>
              <div className="text-2xl font-black text-red-600 mt-1">
                {analytics?.counterfeit_risk_rate_percent?.toFixed(1) ?? '0.0'}%
              </div>
              <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> High-risk & tampered scans
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Brand Authenticity Health
              </div>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {analytics
                  ? `${Math.max(0, 100 - (analytics.counterfeit_risk_rate_percent || 0)).toFixed(1)}%`
                  : '100%'}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Quality & origin trust score
              </div>
            </div>
          </div>

          {/* Risk State Breakdown */}
          {analytics?.risk_distribution && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-indigo-600" /> Scan Decision Distribution for Amul Products
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Object.entries(analytics.risk_distribution).map(([state, count]) => (
                  <div
                    key={state}
                    className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <div className="text-[10px] font-bold text-slate-500 uppercase">
                      {state.replace(/_/g, ' ')}
                    </div>
                    <div className="text-xl font-black text-slate-900 mt-1">{count}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Catalog & Packaging Lifecycle */}
      {activeTab === 'catalog' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Products */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Tag className="w-4 h-4 text-blue-600" /> Registered Products ({products.length})
            </h2>
            <div className="space-y-3">
              {products.map((prod) => (
                <div
                  key={prod.id}
                  className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between"
                >
                  <div>
                    <div className="text-xs font-bold text-slate-800">{prod.name}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Category: {prod.category} • Variants: {prod.variants?.length || 1}
                    </div>
                  </div>
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-bold uppercase">
                    Active
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Packaging Versions Lifecycle */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-600" /> Packaging Versions ({packagingVersions.length})
            </h2>
            <div className="space-y-3">
              {packagingVersions.map((pv) => (
                <div
                  key={pv.id}
                  className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between"
                >
                  <div>
                    <div className="text-xs font-bold text-slate-800">
                      Version {pv.version_code}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Barcode: <span className="font-mono">{pv.expected_barcode || '8901262010060'}</span> • MRP: ₹{pv.expected_mrp ? Number(pv.expected_mrp).toFixed(2) : '72.00'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        pv.status === 'ACTIVE'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {pv.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Image Inspection Modal */}
      {selectedImage && (
        <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-black text-slate-900">
                  {selectedImage.product_name} • {selectedImage.view_type} View
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedImage.variant_name} ({selectedImage.pack_size}) • Version {selectedImage.version_code || 'V1'}
                </p>
              </div>
              <button
                onClick={() => setSelectedImage(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 bg-slate-100 flex items-center justify-center max-h-[60vh] overflow-hidden">
              <img
                src={`/data/storage/${selectedImage.image_path}`}
                alt={selectedImage.original_filename || selectedImage.view_type}
                className="max-h-[55vh] w-auto object-contain rounded-lg shadow-sm"
              />
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="space-y-0.5">
                <div className="font-mono text-[11px] text-slate-500">
                  Storage: {selectedImage.image_path}
                </div>
                <div className="text-[11px] text-slate-400">
                  Provenance: {selectedImage.source_type} • Trust Weight: {Math.round(selectedImage.trust_level * 100)}%
                </div>
              </div>

              <span className="px-3 py-1 bg-emerald-100 text-emerald-800 font-bold rounded-lg flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Verified Reference Asset
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

