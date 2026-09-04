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

  React.useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setError(null);
    }
  }, [isOpen, initialMode]);
  
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
        setError('Unable to reach backend server. Please check your connection or verify the server is running on port 8000.');
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
      // 1. Register new user
      await authApi.register({
        email: regEmail.trim(),
        password: regPassword,
        full_name: fullName.trim(),
        role_name: regRole,
      });

      // 2. Automatically sign in with the new credentials
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
        setError('Unable to reach backend server. Please check your connection or verify the server is running on port 8000.');
      } else {
        console.error('Registration error:', err);
        setError(err.message || 'An unexpected error occurred during registration.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5">
        {/* Header with Title and Close Button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
              {mode === 'signin' ? <Lock className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            </div>
            <h2 className="text-lg font-bold text-slate-900">
              {mode === 'signin' ? 'Sign In to VeriSure' : 'Create a New Account'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher: Sign In vs Create Account */}
        <div className="grid grid-cols-2 p-1 bg-slate-100 rounded-2xl">
          <button
            type="button"
            onClick={() => {
              setMode('signin');
              setError(null);
            }}
            className={`py-2 text-xs font-bold rounded-xl transition-all ${
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
            className={`py-2 text-xs font-bold rounded-xl transition-all ${
              mode === 'register'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium">
            {error}
          </div>
        )}

        {mode === 'signin' ? (
          <>
            {/* 1-Click Demo Accounts */}
            <div>
              <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                Quick 1-Click Demo Roles
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleLogin('consumer@verisure.ai', 'Consumer@12345')}
                  className="p-2.5 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded-xl text-center transition-all group"
                >
                  <UserIcon className="w-4 h-4 mx-auto text-slate-500 group-hover:text-blue-600 mb-1" />
                  <div className="text-[11px] font-bold text-slate-700 group-hover:text-blue-700">
                    Consumer
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleLogin('amul_admin@verisure.ai', 'Amul@12345')}
                  className="p-2.5 bg-slate-50 hover:bg-red-50 border border-slate-200 hover:border-red-300 rounded-xl text-center transition-all group"
                >
                  <Building2 className="w-4 h-4 mx-auto text-slate-500 group-hover:text-red-600 mb-1" />
                  <div className="text-[11px] font-bold text-slate-700 group-hover:text-red-700">
                    Brand Admin
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleLogin('admin@verisure.ai', 'Admin@12345')}
                  className="p-2.5 bg-slate-50 hover:bg-purple-50 border border-slate-200 hover:border-purple-300 rounded-xl text-center transition-all group"
                >
                  <Shield className="w-4 h-4 mx-auto text-slate-500 group-hover:text-purple-600 mb-1" />
                  <div className="text-[11px] font-bold text-slate-700 group-hover:text-purple-700">
                    Admin
                  </div>
                </button>
              </div>
            </div>

            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-slate-200"></div>
              <span className="flex-shrink mx-3 text-[10px] uppercase font-bold text-slate-400">
                Or sign in with email
              </span>
              <div className="flex-grow border-t border-slate-200"></div>
            </div>

            {/* Sign In Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleLogin();
              }}
              className="space-y-3"
            >
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  required
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !email || !password}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 transition-all flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign In'}
              </button>
            </form>

            <div className="text-center text-xs text-slate-500 pt-1">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('register');
                  setError(null);
                }}
                className="font-bold text-blue-600 hover:underline"
              >
                Create Account
              </button>
            </div>
          </>
        ) : (
          /* Create Account Form */
          <form onSubmit={handleRegister} className="space-y-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Pravash Kumar"
                required
                className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Email Address</label>
              <input
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="pravash@example.com"
                required
                className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Account Role</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRegRole('CONSUMER')}
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all text-center ${
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
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all text-center ${
                    regRole === 'BRAND_ADMIN'
                      ? 'bg-red-50 text-red-700 border-red-300'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  Brand Partner
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Password (min. 8 characters)</label>
              <input
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={8}
                className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={8}
                className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:outline-blue-600"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !fullName || !regEmail || !regPassword || !confirmPassword}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 transition-all flex items-center justify-center gap-2 mt-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Account'}
            </button>

            <div className="text-center text-xs text-slate-500 pt-1">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setError(null);
                }}
                className="font-bold text-blue-600 hover:underline"
              >
                Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
