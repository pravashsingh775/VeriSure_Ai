import React, { useState } from 'react';
import { Building2, Loader2, Lock, Shield, User as UserIcon, UserPlus, X } from 'lucide-react';
import { authApi } from '../services/api';
import type { User } from '../types';

interface LoginModalProps {
  isOpen: boolean;
  initialMode?: 'signin' | 'register';
  onClose: () => void;
  onLoginSuccess: (user: User) => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({
  isOpen,
  initialMode = 'signin',
  onClose,
  onLoginSuccess,
}) => {
  const [mode, setMode] = useState<'signin' | 'register'>(initialMode);
  const [prevInitialMode, setPrevInitialMode] = useState(initialMode);

  // Sign In fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Registration fields
  const [fullName, setFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [regRole, setRegRole] = useState<'CONSUMER' | 'BRAND_ADMIN'>('CONSUMER');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (initialMode !== prevInitialMode) {
    setPrevInitialMode(initialMode);
    setMode(initialMode);
    setError(null);
  }

  if (!isOpen) return null;

  const handleLogin = async (loginEmail?: string, loginPass?: string) => {
    setLoading(true);
    setError(null);
    try {
      const targetEmail = (loginEmail || email).trim();
      const targetPass = loginPass || password;

      if (!targetEmail) {
        setError('Please enter your email address.');
        setLoading(false);
        return;
      }
      if (!targetPass) {
        setError('Please enter your password.');
        setLoading(false);
        return;
      }

      const res = await authApi.login(targetEmail, targetPass);
      if (res && res.user) {
        onLoginSuccess(res.user);
      }
      onClose();
    } catch (err: any) {
      if (err.response) {
        const detail = err.response.data?.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (Array.isArray(detail)) {
          setError(detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', '));
        } else {
          setError('Invalid email or password. Please check your credentials.');
        }
      } else if (err.request) {
        setError('Unable to reach backend server. Please verify the server is running on port 8000.');
      } else {
        console.error('Login error:', err);
        setError(err.message || 'An unexpected error occurred during login.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!fullName.trim()) {
      setError('Please enter your full name.');
      return;
    }
    if (!regEmail.trim()) {
      setError('Please enter a valid email address.');
      return;
    }
    if (regPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (regPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await authApi.register({
        email: regEmail.trim(),
        password: regPassword,
        full_name: fullName.trim(),
        role_name: regRole,
      });

      const loginRes = await authApi.login(regEmail.trim(), regPassword);
      if (loginRes && loginRes.user) {
        onLoginSuccess(loginRes.user);
      }
      onClose();
    } catch (err: any) {
      if (err.response) {
        const detail = err.response.data?.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (Array.isArray(detail)) {
          setError(detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', '));
        } else {
          setError('Registration failed. Email may already be in use.');
        }
      } else if (err.request) {
        setError('Unable to reach backend server. Please verify the server is running on port 8000.');
      } else {
        console.error('Registration error:', err);
        setError(err.message || 'An unexpected error occurred during registration.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 border border-slate-200/90 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
              {mode === 'signin' ? <Lock className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-900">
                {mode === 'signin' ? 'Sign In to VeriSure' : 'Create an Account'}
              </h2>
              <p className="text-[11px] text-slate-400 font-medium">
                {mode === 'signin'
                  ? 'Access consumer history or enterprise brand tools'
                  : 'Register a new consumer or brand account'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher: Sign In vs Create Account */}
        <div className="grid grid-cols-2 p-1 bg-slate-100/90 rounded-2xl border border-slate-200/50">
          <button
            type="button"
            onClick={() => {
              setMode('signin');
              setError(null);
            }}
            className={`py-2 text-xs font-black rounded-xl transition-all cursor-pointer ${
              mode === 'signin'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('register');
              setError(null);
            }}
            className={`py-2 text-xs font-black rounded-xl transition-all cursor-pointer ${
              mode === 'register'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-700 font-medium flex items-start gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {mode === 'signin' ? (
          <>
            {/* 1-Click Demo Accounts */}
            <div>
              <label className="block text-[10px] font-black text-slate-400 uppercase tracking-wider mb-2">
                Quick 1-Click Demo Roles
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleLogin('consumer@verisure.ai', 'Consumer@12345')}
                  className="p-3 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded-2xl text-center transition-all group cursor-pointer shadow-xs"
                >
                  <UserIcon className="w-5 h-5 mx-auto text-slate-500 group-hover:text-blue-600 mb-1" />
                  <div className="text-[11px] font-black text-slate-700 group-hover:text-blue-700">
                    Consumer
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleLogin('amul_admin@verisure.ai', 'Amul@12345')}
                  className="p-3 bg-slate-50 hover:bg-red-50 border border-slate-200 hover:border-red-300 rounded-2xl text-center transition-all group cursor-pointer shadow-xs"
                >
                  <Building2 className="w-5 h-5 mx-auto text-slate-500 group-hover:text-red-600 mb-1" />
                  <div className="text-[11px] font-black text-slate-700 group-hover:text-red-700">
                    Brand GCMMF
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleLogin('admin@verisure.ai', 'Admin@12345')}
                  className="p-3 bg-slate-50 hover:bg-purple-50 border border-slate-200 hover:border-purple-300 rounded-2xl text-center transition-all group cursor-pointer shadow-xs"
                >
                  <Shield className="w-5 h-5 mx-auto text-slate-500 group-hover:text-purple-600 mb-1" />
                  <div className="text-[11px] font-black text-slate-700 group-hover:text-purple-700">
                    Platform Admin
                  </div>
                </button>
              </div>
            </div>

            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-slate-200"></div>
              <span className="flex-shrink mx-3 text-[10px] uppercase font-black text-slate-400">
                Or Enter Email
              </span>
              <div className="flex-grow border-t border-slate-200"></div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleLogin();
              }}
              className="space-y-3.5"
            >
              <div>
                <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 font-medium"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl text-xs font-black shadow-md shadow-blue-500/20 transition-all cursor-pointer flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                <span>{loading ? 'Signing In...' : 'Sign In'}</span>
              </button>
            </form>
          </>
        ) : (
          <form onSubmit={handleRegister} className="space-y-3">
            <div>
              <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Pravash Singh"
                className="w-full px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 font-medium"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Min 8 chars"
                  className="w-full px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                  Confirm
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat pass"
                  className="w-full px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-blue-600 font-medium"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-1">
                Account Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRegRole('CONSUMER')}
                  className={`py-2 px-3 text-xs font-black rounded-xl border transition-all cursor-pointer ${
                    regRole === 'CONSUMER'
                      ? 'bg-blue-50 text-blue-700 border-blue-300'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  Consumer
                </button>
                <button
                  type="button"
                  onClick={() => setRegRole('BRAND_ADMIN')}
                  className={`py-2 px-3 text-xs font-black rounded-xl border transition-all cursor-pointer ${
                    regRole === 'BRAND_ADMIN'
                      ? 'bg-red-50 text-red-700 border-red-300'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  Brand Admin
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl text-xs font-black shadow-md shadow-blue-500/20 transition-all cursor-pointer flex items-center justify-center gap-2 mt-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              <span>{loading ? 'Creating Account...' : 'Register &amp; Sign In'}</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

