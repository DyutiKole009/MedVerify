import React from 'react';
import { X, Clock, Trash2, ArrowRight } from 'lucide-react';
import type { VerificationResponse } from '../types/api';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  history: Array<{ query: string; result: VerificationResponse; timestamp: string }>;
  onSelect: (result: VerificationResponse) => void;
  onClear: () => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  history,
  onSelect,
  onClear,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-sm animate-in fade-in">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white shadow-2xl border-l border-slate-200 flex flex-col">
          
          <div className="p-5 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-sky-600" />
              <h3 className="font-bold text-slate-900 text-sm">Recent Verifications</h3>
            </div>
            <div className="flex items-center space-x-2">
              {history.length > 0 && (
                <button
                  type="button"
                  onClick={onClear}
                  className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-slate-100 transition"
                  title="Clear history"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {history.length === 0 ? (
              <div className="py-16 text-center text-xs text-slate-400">
                No recent verifications yet.
              </div>
            ) : (
              history.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    onSelect(item.result);
                    onClose();
                  }}
                  className="p-3.5 rounded-xl border border-slate-200/80 hover:border-sky-300 hover:bg-sky-50/40 transition cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-slate-800 group-hover:text-sky-700">
                      {item.query || 'Image Verification'}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">{item.timestamp}</span>
                  </div>

                  <div className="flex items-center justify-between mt-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.result.status_category === 'CLEAR'
                        ? 'bg-emerald-100 text-emerald-800'
                        : item.result.status_category === 'NSQ'
                        ? 'bg-amber-100 text-amber-800'
                        : item.result.status_category === 'SPURIOUS'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-purple-100 text-purple-800'
                    }`}>
                      {item.result.status_category}
                    </span>

                    <span className="text-[11px] font-medium text-sky-600 flex items-center space-x-0.5 group-hover:translate-x-0.5 transition-transform">
                      <span>View</span>
                      <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

        </div>
      </div>
    </div>
  );
};
