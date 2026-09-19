import React from 'react';
import { ShieldCheck, Sparkles, Activity } from 'lucide-react';
import { getAnonymousId } from '../services/session';

interface NavbarProps {
  onOpenHistory?: () => void;
  onOpenReport?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenHistory, onOpenReport }) => {
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

        <div className="flex items-center space-x-3">
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

          <div className="flex items-center space-x-1.5 bg-slate-100 px-2.5 py-1 rounded-full text-xs font-mono text-slate-600" title="Anonymous Client ID">
            <Sparkles className="w-3 h-3 text-sky-500" />
            <span>{anonId}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
