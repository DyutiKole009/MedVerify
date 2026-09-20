import React from 'react';
import { ShieldCheck, Sparkles, Activity, LogIn, UserPlus, LogOut, UserCheck } from 'lucide-react';
import { getAnonymousId } from '../services/session';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  onOpenHistory?: () => void;
  onOpenReport?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenHistory, onOpenReport }) => {
  const { user, isAuthenticated, logout, openModal } = useAuth();
  const anonId = getAnonymousId().slice(0, 13) + '...';

  return (
    <header className="sticky top-0 z-40 bg-white/85 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-600/20 text-white">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-slate-900">MedVerify</span>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-sky-100 text-sky-700">v2.0</span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">National Medicine Quality & Authenticity Intelligence</p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={onOpenReport}
            className="text-xs sm:text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition flex items-center space-x-1.5"
          >
            <Activity className="w-4 h-4 text-violet-500" />
            <span className="hidden sm:inline">Report Issue</span>
          </button>

          <button
            onClick={onOpenHistory}
            className="text-xs sm:text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition"
          >
            History
          </button>

          <div className="h-4 w-px bg-slate-200" />

          {/* Authentication State */}
          {!isAuthenticated ? (
            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => openModal('login')}
                className="text-xs sm:text-sm font-semibold text-slate-700 hover:text-indigo-600 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition flex items-center space-x-1"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
              <button
                onClick={() => openModal('signup')}
                className="text-xs sm:text-sm font-semibold text-white bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 px-3 py-1.5 rounded-lg shadow-sm transition flex items-center space-x-1"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Register</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-1 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-xs text-indigo-900 font-medium">
                <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
                <span className="max-w-[120px] truncate">{user?.name || user?.email}</span>
                <span className="px-1.5 py-0.2 bg-indigo-200/60 rounded text-[10px] uppercase font-bold text-indigo-800 ml-1">
                  {user?.role}
                </span>
              </div>
              <button
                onClick={logout}
                title="Log Out"
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="hidden md:flex items-center space-x-1.5 bg-slate-100 px-2 py-1 rounded-full text-[11px] font-mono text-slate-500" title="Anonymous Client ID">
            <Sparkles className="w-3 h-3 text-sky-500" />
            <span>{anonId}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
