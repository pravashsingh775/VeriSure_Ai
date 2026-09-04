import React, { useState } from 'react';
import { History, LogIn, LogOut, Menu, ShieldCheck, UserPlus, X } from 'lucide-react';
import type { User } from '../types';

interface NavbarProps {
  currentUser: User | null;
  activeTab: 'consumer' | 'brand' | 'admin';
  onTabChange: (tab: 'consumer' | 'brand' | 'admin') => void;
  onOpenHistory: () => void;
  onOpenLogin: (mode?: 'signin' | 'register') => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  activeTab,
  onTabChange,
  onOpenHistory,
  onOpenLogin,
  onLogout,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleTabClick = (tab: 'consumer' | 'brand' | 'admin') => {
    onTabChange(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => handleTabClick('consumer')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-black text-slate-900 tracking-tight">VeriSure AI</span>
              <span className="px-2 py-0.2 bg-blue-50 text-blue-700 text-[10px] font-bold rounded-full border border-blue-200/60">
                Amul FMCG
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Authenticity Risk Platform</p>
          </div>
        </div>

        {/* Desktop Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => handleTabClick('consumer')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'consumer'
                ? 'bg-white text-blue-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Consumer Scanner
          </button>
          <button
            onClick={() => handleTabClick('brand')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'brand'
                ? 'bg-white text-red-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Brand Portal (Amul)
          </button>
          <button
            onClick={() => handleTabClick('admin')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'admin'
                ? 'bg-white text-purple-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Admin Triage & MLOps
          </button>
        </nav>

        {/* User / Action Buttons */}
        <div className="flex items-center gap-2">
          {currentUser && activeTab === 'consumer' && (
            <button
              onClick={onOpenHistory}
              className="p-2 text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-xl transition-all cursor-pointer"
              title="My Scan History"
            >
              <History className="w-5 h-5" />
            </button>
          )}

          {currentUser ? (
            <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
              <div className="hidden sm:block text-right">
                <div className="text-xs font-bold text-slate-800">{currentUser.full_name}</div>
                <div className="text-[10px] font-semibold text-slate-500 uppercase flex items-center justify-end gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    currentUser.roles[0] === 'PLATFORM_ADMIN' ? 'bg-purple-600' :
                    currentUser.roles[0] === 'BRAND_ADMIN' ? 'bg-red-600' : 'bg-blue-600'
                  }`} />
                  {currentUser.roles[0] || 'Consumer'}
                </div>
              </div>
              <button
                onClick={onLogout}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all cursor-pointer"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 sm:gap-2">
              <button
                onClick={() => onOpenLogin('signin')}
                className="inline-flex items-center gap-1 text-xs font-bold text-slate-700 hover:text-slate-900 px-2.5 sm:px-3 py-2 rounded-xl hover:bg-slate-100 transition-all cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" /> <span className="hidden xs:inline">Sign In</span>
              </button>
              <button
                onClick={() => onOpenLogin('register')}
                className="inline-flex items-center gap-1 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white px-3 sm:px-3.5 py-2 rounded-xl shadow-xs transition-all cursor-pointer"
              >
                <UserPlus className="w-3.5 h-3.5" /> <span className="hidden xs:inline">Create Account</span>
              </button>
            </div>
          )}

          {/* Mobile Menu Hamburger Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl md:hidden transition-all cursor-pointer ml-1"
            title="Toggle Menu"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-2 pb-4 space-y-1 shadow-lg animate-in slide-in-from-top-2 duration-200">
          <button
            onClick={() => handleTabClick('consumer')}
            className={`w-full text-left px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between ${
              activeTab === 'consumer'
                ? 'bg-blue-50 text-blue-700 font-extrabold'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <span>Consumer Scanner</span>
            {activeTab === 'consumer' && <span className="w-2 h-2 rounded-full bg-blue-600" />}
          </button>
          <button
            onClick={() => handleTabClick('brand')}
            className={`w-full text-left px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between ${
              activeTab === 'brand'
                ? 'bg-red-50 text-red-700 font-extrabold'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <span>Brand Portal (Amul)</span>
            {activeTab === 'brand' && <span className="w-2 h-2 rounded-full bg-red-600" />}
          </button>
          <button
            onClick={() => handleTabClick('admin')}
            className={`w-full text-left px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between ${
              activeTab === 'admin'
                ? 'bg-purple-50 text-purple-700 font-extrabold'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <span>Admin Triage & MLOps</span>
            {activeTab === 'admin' && <span className="w-2 h-2 rounded-full bg-purple-600" />}
          </button>

          {currentUser && (
            <div className="pt-2 mt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 px-2">
              <span>Signed in as <strong>{currentUser.full_name}</strong></span>
              <span className="text-[10px] font-bold uppercase px-2 py-0.5 bg-slate-100 rounded text-slate-600">
                {currentUser.roles[0]}
              </span>
            </div>
          )}
        </div>
      )}
    </header>
  );
};
