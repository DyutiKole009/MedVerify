import React, { useState } from 'react';
import {
  ShieldCheck,
  Mail,
  Lock,
  User,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Building2,
  UserCheck,
  FileCheck
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { resendConfirmationApi } from '../services/auth';

interface AuthPageProps {
  onContinueAsGuest?: () => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({ onContinueAsGuest }) => {
  const { login, signup, confirm } = useAuth();

  const [tab, setTab] = useState<'login' | 'signup' | 'confirm'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<'consumer' | 'pharmacist'>('consumer');
  const [confirmationCode, setConfirmationCode] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err?.message || 'Invalid email or password. Please verify your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signup(email, password, role, name);
      setSuccess(`Account registered! Verification code sent to ${email}.`);
      setTab('confirm');
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await confirm(email, confirmationCode);
      setSuccess('Email verified successfully! Please sign in with your credentials.');
      setTab('login');
    } catch (err: any) {
      setError(err?.message || 'Invalid or expired confirmation code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendCode = async () => {
    if (!email) {
      setError('Please enter your email address first.');
      return;
    }
    try {
      await resendConfirmationApi(email);
      setSuccess(`A fresh verification code was sent to ${email}.`);
    } catch (err: any) {
      setError(err?.message || 'Failed to resend confirmation code.');
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-[#0f172a] flex flex-col justify-between py-10 px-4 sm:px-6 lg:px-8 relative font-sans">
      {/* Top institutional header band */}
      <div className="max-w-md mx-auto w-full text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-sky-700 text-white shadow-xs mb-3 border border-sky-800">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div className="flex items-center justify-center space-x-2">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">MedVerify</h1>
          <span className="font-mono text-[10px] text-slate-600 font-semibold px-1.5 py-0.5 rounded bg-slate-100 border border-slate-300">
            CDSCO AI GATEWAY
          </span>
        </div>
        <p className="mt-1.5 text-xs text-slate-500 font-medium">
          Central Drugs Standard Control Organisation • Surveillance & Safety Node
        </p>
      </div>

      {/* Main card panel - crisp institutional paper design */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md mt-6">
        <div className="bg-white py-6 px-6 sm:px-8 border border-slate-200 rounded-xl shadow-xs">
          {/* Tab Switcher */}
          <div className="flex bg-slate-100 p-1 rounded-lg mb-5 border border-slate-200">
            <button
              type="button"
              onClick={() => {
                setTab('login');
                setError(null);
                setSuccess(null);
              }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                tab === 'login'
                  ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setTab('signup');
                setError(null);
                setSuccess(null);
              }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                tab === 'signup'
                  ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Create Account
            </button>
            {tab === 'confirm' && (
              <button
                type="button"
                className="flex-1 py-1.5 text-xs font-semibold rounded-md bg-white text-slate-900 shadow-2xs border border-slate-200"
              >
                Verify Code
              </button>
            )}
          </div>

          {/* Alert messages */}
          {error && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start space-x-2 text-rose-800 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start space-x-2 text-emerald-800 text-xs">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}

          {/* 1. SIGN IN FORM */}
          {tab === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600 transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-2 px-4 bg-sky-700 hover:bg-sky-800 text-white font-medium text-xs rounded-md shadow-xs transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <span>Sign In</span>}
                {!isSubmitting && <ArrowRight className="w-3.5 h-3.5" />}
              </button>

              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center text-[10px]">
                  <span className="bg-white px-2 text-slate-400 uppercase font-mono">Or Quick Access</span>
                </div>
              </div>

              <button
                type="button"
                onClick={onContinueAsGuest}
                className="w-full py-2 px-3 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs rounded-md border border-slate-200 transition flex items-center justify-center space-x-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-sky-600" />
                <span>Continue as Guest / Anonymous Verification</span>
              </button>
            </form>
          )}

          {/* 2. REGISTER / SIGN UP FORM */}
          {tab === 'signup' && (
            <form onSubmit={handleSignup} className="space-y-3.5">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your Name"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Password (min 8 chars)
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600 transition"
                  />
                </div>
              </div>

              {/* Role Selection */}
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Account Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRole('consumer')}
                    className={`p-2.5 rounded-md border text-left transition ${
                      role === 'consumer'
                        ? 'border-sky-600 bg-sky-50 text-sky-900 ring-1 ring-sky-600'
                        : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <UserCheck className="w-4 h-4 text-sky-700 mb-1" />
                    <div className="font-semibold text-xs">Citizen / Consumer</div>
                    <div className="text-[10px] text-slate-500">Fast batch authentication</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setRole('pharmacist')}
                    className={`p-2.5 rounded-md border text-left transition ${
                      role === 'pharmacist'
                        ? 'border-sky-600 bg-sky-50 text-sky-900 ring-1 ring-sky-600'
                        : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <Building2 className="w-4 h-4 text-sky-700 mb-1" />
                    <div className="font-semibold text-xs">Licensed Pharmacist</div>
                    <div className="text-[10px] text-slate-500">Official verification & reporting</div>
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-2 px-4 bg-sky-700 hover:bg-sky-800 text-white font-medium text-xs rounded-md shadow-xs transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <span>Create Account</span>}
                {!isSubmitting && <ArrowRight className="w-3.5 h-3.5" />}
              </button>

              <div className="text-center pt-1">
                <button
                  type="button"
                  onClick={() => setTab('login')}
                  className="text-xs text-sky-700 hover:underline font-medium"
                >
                  Already registered? Sign In
                </button>
              </div>
            </form>
          )}

          {/* 3. CONFIRM EMAIL / OTP TAB */}
          {tab === 'confirm' && (
            <form onSubmit={handleConfirm} className="space-y-4">
              <div className="text-center mb-3">
                <div className="w-8 h-8 bg-sky-100 rounded-full flex items-center justify-center mx-auto mb-1.5 text-sky-700">
                  <FileCheck className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-bold text-slate-900">Verify Security Token</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Enter the 6-digit confirmation code Cognito sent to:
                  <br />
                  <strong className="text-slate-800 font-mono">{email}</strong>
                </p>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  6-Digit Verification Code
                </label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={confirmationCode}
                  onChange={(e) => setConfirmationCode(e.target.value.trim())}
                  placeholder="123456"
                  className="w-full px-3 py-2 text-center text-lg font-mono tracking-widest bg-slate-50 border border-slate-300 rounded-md focus:bg-white focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600 transition"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2 px-4 bg-sky-700 hover:bg-sky-800 text-white font-medium text-xs rounded-md shadow-xs transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <span>Confirm & Activate Account</span>}
              </button>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                <button
                  type="button"
                  onClick={handleResendCode}
                  className="text-sky-700 hover:underline font-medium"
                >
                  Resend Code
                </button>
                <button
                  type="button"
                  onClick={() => setTab('login')}
                  className="hover:text-slate-800"
                >
                  Back to Sign In
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer info */}
        <p className="text-center font-mono text-[10px] text-slate-400 mt-4">
          Statutory Drug Quality System • CDSCO Rule 105E Compliance
        </p>
      </div>

      <div className="text-center text-[10px] text-slate-400 font-mono">
        CDSCO Regional Drug Testing Laboratories & AWS Cognito Identity Services
      </div>
    </div>
  );
};
