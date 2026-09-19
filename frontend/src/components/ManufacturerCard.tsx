import React from 'react';
import { Building2 } from 'lucide-react';
import type { ManufacturerProfile, OfficialRecord } from '../types/api';

interface ManufacturerCardProps {
  profile?: ManufacturerProfile | null;
  recentBatches?: OfficialRecord[];
}

export const ManufacturerCard: React.FC<ManufacturerCardProps> = ({ profile, recentBatches = [] }) => {
  if (!profile && recentBatches.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
        <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700">
          <Building2 className="w-5 h-5" />
        </div>
        <div>
          <h4 className="font-bold text-sm text-slate-900">
            {profile?.manufacturer_name || 'Manufacturer Profile'}
          </h4>
          <p className="text-[11px] text-slate-500">Regulatory Compliance History & Risk Indicators</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-slate-50 rounded-xl p-3 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 block">Total Flagged Batches</span>
          <span className="text-xl font-bold font-mono text-slate-800">
            {profile?.total_flags ?? 0}
          </span>
        </div>

        <div className="bg-slate-50 rounded-xl p-3 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 block">Spurious / Counterfeit Flags</span>
          <span className={`text-xl font-bold font-mono ${(profile?.spurious_count ?? 0) > 0 ? 'text-red-600' : 'text-slate-800'}`}>
            {profile?.spurious_count ?? 0}
          </span>
        </div>

        <div className="bg-slate-50 rounded-xl p-3 border border-slate-200/60">
          <span className="text-[11px] text-slate-500 block">Last Flagged Date</span>
          <span className="text-sm font-semibold font-mono text-slate-700 mt-1 block">
            {profile?.last_flagged_date || 'None'}
          </span>
        </div>
      </div>

      {recentBatches.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-100">
          <span className="text-xs font-semibold text-slate-700 block mb-2">
            Recent Regulatory Alerts for this Manufacturer:
          </span>
          <div className="space-y-1.5 max-h-32 overflow-y-auto">
            {recentBatches.map((b, i) => (
              <div key={i} className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-200/60">
                <span className="font-mono font-medium text-slate-800">{b.batch_no}</span>
                <span className="text-slate-600 truncate max-w-xs">{b.drug_name || 'Drug'}</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                  {b.alert_status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
