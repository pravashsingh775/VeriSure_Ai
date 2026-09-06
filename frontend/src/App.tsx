import React, { useState } from 'react';
import { AdminPortal } from './components/AdminPortal';
import { BrandPortal } from './components/BrandPortal';
import { LoginModal } from './components/LoginModal';
import { Navbar } from './components/Navbar';
import { ScanHistoryDrawer } from './components/ScanHistoryDrawer';
import { ScanResultView } from './components/ScanResultView';
import { ScanUpload } from './components/ScanUpload';
import { authApi } from './services/api';
import type { ScanDetail, User } from './types';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('verisure_user');
    if (savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch {
        localStorage.removeItem('verisure_user');
      }
    }
    return null;
  });
  const [activeTab, setActiveTab] = useState<'consumer' | 'brand' | 'admin'>('consumer');
  const [currentScan, setCurrentScan] = useState<ScanDetail | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [loginModalMode, setLoginModalMode] = useState<'signin' | 'register'>('signin');

  const handleLogout = () => {
    authApi.logout();
    setCurrentUser(null);
    setActiveTab('consumer');
  };

  return (
    <div className="min-h-screen bg-slate-50 relative flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Subtle Ambient Background Gradients */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-[20%] -left-[10%] w-[50vw] h-[50vw] rounded-full bg-blue-100/40 blur-3xl" />
        <div className="absolute top-[30%] -right-[15%] w-[45vw] h-[45vw] rounded-full bg-indigo-50/50 blur-3xl" />
        <div className="absolute -bottom-[20%] left-[20%] w-[40vw] h-[40vw] rounded-full bg-emerald-50/40 blur-3xl" />
      </div>

      <Navbar
        currentUser={currentUser}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          // If switching away from consumer, clear current scan view so consumer is ready when returning
          if (tab !== 'consumer') {
            setCurrentScan(null);
          }
        }}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenLogin={(mode = 'signin') => {
          setLoginModalMode(mode);
          setIsLoginOpen(true);
        }}
        onLogout={handleLogout}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        {activeTab === 'consumer' && (
          <>
            {currentScan ? (
              <ScanResultView
                scan={currentScan}
                onReset={() => setCurrentScan(null)}
              />
            ) : (
              <ScanUpload onScanCompleted={(result) => setCurrentScan(result)} />
            )}
          </>
        )}

        {activeTab === 'brand' && <BrandPortal />}

        {activeTab === 'admin' && (
          <AdminPortal
            currentUser={currentUser}
            onOpenLogin={(mode = 'signin') => {
              setLoginModalMode(mode);
              setIsLoginOpen(true);
            }}
          />
        )}
      </main>

      <footer className="bg-white/85 backdrop-blur-md border-t border-slate-200/80 py-6 mt-12 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800">VeriSure AI Platform</span>
            <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded-full border border-blue-200/50">
              v1.0.0-rc1
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-slate-500">Minor Project Edition 2026</span>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-slate-400 text-[11px]">
            <span>PyTorch &amp; OpenCV Runtime</span>
            <span>•</span>
            <span>Zero Cloud API Cost</span>
            <span>•</span>
            <span>Evidential Deep Fusion</span>
            <span>•</span>
            <span className="text-emerald-600 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" /> All Systems Nominal
            </span>
          </div>
        </div>
      </footer>

      {/* Slide-in History Drawer */}
      <ScanHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectScan={(scan) => setCurrentScan(scan)}
      />

      {/* Role Switcher & Login Modal */}
      <LoginModal
        key={isLoginOpen ? `login-${loginModalMode}` : 'closed'}
        isOpen={isLoginOpen}
        initialMode={loginModalMode}
        onClose={() => setIsLoginOpen(false)}
        onLoginSuccess={(user) => {
          if (!user) return;
          setCurrentUser(user);
          // Safely determine roles array
          const roles = Array.isArray(user.roles) ? user.roles : [];
          // Automatically navigate to relevant portal based on role
          if (roles.includes('PLATFORM_ADMIN')) {
            setActiveTab('admin');
          } else if (roles.includes('BRAND_ADMIN') || roles.includes('BRAND_REVIEWER')) {
            setActiveTab('brand');
          } else {
            setActiveTab('consumer');
          }
        }}
      />
    </div>
  );
};

export default App;
