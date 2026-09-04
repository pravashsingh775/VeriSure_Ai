import React, { useEffect, useState } from 'react';
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
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'consumer' | 'brand' | 'admin'>('consumer');
  const [currentScan, setCurrentScan] = useState<ScanDetail | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [loginModalMode, setLoginModalMode] = useState<'signin' | 'register'>('signin');

  useEffect(() => {
    // Check existing stored user session
    const savedUser = localStorage.getItem('verisure_user');
    if (savedUser) {
      try {
        setCurrentUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('verisure_user');
      }
    }
  }, []);

  const handleLogout = () => {
    authApi.logout();
    setCurrentUser(null);
    setActiveTab('consumer');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
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

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
            onOpenLogin={(mode = 'signin') => {
              setLoginModalMode(mode);
              setIsLoginOpen(true);
            }}
          />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200/80 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div>
            <span className="font-bold text-slate-800">VeriSure AI Platform</span> • Minor Project Edition 2026
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>Powered by PyTorch & OpenCV</span>
            <span>•</span>
            <span>Zero API Cost Architecture</span>
            <span>•</span>
            <span>Multi-Evidence Fusion</span>
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
        isOpen={isLoginOpen}
        initialMode={loginModalMode}
        onClose={() => setIsLoginOpen(false)}
        onLoginSuccess={(user) => {
          setCurrentUser(user);
          // Automatically navigate to relevant portal based on role
          if (user.roles.includes('PLATFORM_ADMIN')) {
            setActiveTab('admin');
          } else if (user.roles.includes('BRAND_ADMIN') || user.roles.includes('BRAND_REVIEWER')) {
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
