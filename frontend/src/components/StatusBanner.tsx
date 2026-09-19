import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, HelpCircle, ShieldAlert } from 'lucide-react';
import type { StatusCategory } from '../types/api';

interface StatusBannerProps {
  status: StatusCategory;
  disclaimer: string;
  batchNo?: string;
  summary?: string;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({ status, disclaimer, batchNo, summary }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'CLEAR':
        return {
          title: 'NO REGULATORY QUALITY ALERTS FOUND',
          icon: <CheckCircle2 className="w-6 h-6 text-emerald-600" />,
          bgColor: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-950',
          badgeColor: 'bg-emerald-600 text-white',
          desc: 'No official CDSCO quality failure (NSQ) or spurious notice recorded for this batch.',
        };
      case 'NSQ':
        return {
          title: 'OFFICIAL CDSCO REGULATORY ALERT: NOT OF STANDARD QUALITY (NSQ)',
          icon: <AlertTriangle className="w-6 h-6 text-amber-600" />,
          bgColor: 'bg-amber-500/10 border-amber-500/30 text-amber-950',
          badgeColor: 'bg-amber-600 text-white',
          desc: 'This batch was tested by a government drug laboratory and failed standard quality/assay parameters.',
        };
      case 'SPURIOUS':
        return {
          title: 'CRITICAL WARNING: SUSPECTED SPURIOUS / COUNTERFEIT MEDICINE',
          icon: <AlertOctagon className="w-6 h-6 text-red-600" />,
          bgColor: 'bg-red-500/10 border-red-500/30 text-red-950',
          badgeColor: 'bg-red-600 text-white',
          desc: 'Declared spurious or manufactured by a non-existent/fictitious entity according to CDSCO notices.',
        };
      case 'COMMUNITY_FLAGGED':
        return {
          title: 'COMMUNITY FLAGGED: REAL-WORLD SIGNALS REPORTED',
          icon: <ShieldAlert className="w-6 h-6 text-purple-600" />,
          bgColor: 'bg-purple-500/10 border-purple-500/30 text-purple-950',
          badgeColor: 'bg-purple-600 text-white',
          desc: 'Multiple verified consumer or pharmacist issue reports have been logged against this batch.',
        };
      case 'NO_MATCH':
      default:
        return {
          title: 'NO MATCH IN CENTRAL REGULATORY ARCHIVE',
          icon: <HelpCircle className="w-6 h-6 text-slate-600" />,
          bgColor: 'bg-slate-500/10 border-slate-500/30 text-slate-900',
          badgeColor: 'bg-slate-700 text-white',
          desc: 'No indexed CDSCO alert matches the provided search query.',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={`rounded-2xl border p-4 sm:p-5 shadow-sm transition-all ${config.bgColor}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start space-x-3.5">
          <div className="mt-0.5 flex-shrink-0">{config.icon}</div>
          <div>
            <div className="flex items-center space-x-2">
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold tracking-wider uppercase ${config.badgeColor}`}>
                {status}
              </span>
              {batchNo && (
                <span className="text-xs font-mono font-semibold text-slate-700 bg-white/70 px-2 py-0.5 rounded border border-slate-200">
                  Batch: {batchNo}
                </span>
              )}
            </div>
            <h3 className="text-base sm:text-lg font-bold mt-1 tracking-tight text-slate-900">
              {config.title}
            </h3>
            <p className="text-xs sm:text-sm text-slate-700 mt-0.5 leading-relaxed">
              {summary || config.desc}
            </p>
          </div>
        </div>
      </div>

      {/* Mandatory Safety Disclaimer Banner (§1.3) */}
      <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center space-x-2 text-xs font-medium text-slate-600">
        <span className="font-semibold text-slate-800">Mandatory Limitation:</span>
        <span className="italic">{disclaimer}</span>
      </div>
    </div>
  );
};
