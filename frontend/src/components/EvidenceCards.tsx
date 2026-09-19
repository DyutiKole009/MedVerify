import React from 'react';
import { Landmark, Users, FileText, CheckCircle, ExternalLink } from 'lucide-react';
import type { OfficialRecord, CommunityReport } from '../types/api';

interface EvidenceCardsProps {
  officialRecord?: OfficialRecord | null;
  communityFlag: boolean;
  communityReportCount?: number;
  communityReports?: CommunityReport[];
  onOpenReportModal?: () => void;
}

export const EvidenceCards: React.FC<EvidenceCardsProps> = ({
  officialRecord,
  communityFlag,
  communityReportCount = 0,
  communityReports = [],
  onOpenReportModal,
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
      
      {/* Card 1: Official CDSCO Regulatory Record */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-lg bg-sky-50 text-sky-700">
                <Landmark className="w-5 h-5" />
              </div>
              <div>
                <h4 className="font-bold text-sm text-slate-900">Official CDSCO Record</h4>
                <p className="text-[11px] text-slate-500">Central Drugs Standard Control Organisation</p>
              </div>
            </div>

            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
              officialRecord
                ? officialRecord.alert_status === 'SPURIOUS'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-800'
                : 'bg-emerald-100 text-emerald-800'
            }`}>
              {officialRecord ? officialRecord.alert_status : 'CLEAR'}
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {officialRecord ? (
              <>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-400">Drug Composition:</span>
                    <p className="font-semibold text-slate-800">{officialRecord.drug_name || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Batch ID:</span>
                    <p className="font-mono font-semibold text-slate-800">{officialRecord.batch_no}</p>
                  </div>
                </div>

                <div>
                  <span className="text-xs text-slate-400">Manufacturer & Address:</span>
                  <p className="text-xs font-medium text-slate-800 leading-snug">
                    {officialRecord.manufacturer_name || 'Unspecified Manufacturer'}
                  </p>
                </div>

                <div className="p-3 bg-amber-50/70 border border-amber-200/70 rounded-xl text-xs">
                  <span className="font-bold text-amber-900 block mb-0.5">Reason for Regulatory Alert:</span>
                  <p className="text-amber-800">
                    {officialRecord.nsq_reason || 'Identified as Not of Standard Quality (NSQ) by CDSCO laboratory'}
                  </p>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                  <span>Source Month: <strong>{officialRecord.source_month || 'Recent Alert'}</strong></span>
                  {officialRecord.source_document_s3_key && (
                    <span className="flex items-center space-x-1 text-sky-600 hover:underline cursor-pointer">
                      <FileText className="w-3.5 h-3.5" />
                      <span>Official Notice S3</span>
                    </span>
                  )}
                </div>
              </>
            ) : (
              <div className="py-6 text-center space-y-2">
                <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto" />
                <p className="text-xs font-medium text-slate-700">
                  No regulatory NSQ or spurious alerts recorded in CDSCO repository.
                </p>
                <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                  Checked against all central and state drug testing laboratory monthly gazettes.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400">
          Source: Government of India CDSCO Central Notifications
        </div>
      </div>

      {/* Card 2: Crowd-Sourced Real-World Community Signals */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-lg bg-violet-50 text-violet-700">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h4 className="font-bold text-sm text-slate-900">Community Signals</h4>
                <p className="text-[11px] text-slate-500">Real-World Adverse Reports & Patient Signals</p>
              </div>
            </div>

            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
              communityFlag ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-600'
            }`}>
              {communityFlag ? 'FLAGGED' : 'NORMAL'}
            </span>
          </div>

          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <div>
                <span className="text-xs text-slate-500 block">Logged Reports</span>
                <span className="text-lg font-bold text-slate-900 font-mono">
                  {communityReportCount} {communityReportCount === 1 ? 'Report' : 'Reports'}
                </span>
              </div>

              <div className="text-right">
                <span className="text-xs text-slate-500 block">Community Status</span>
                <span className={`text-xs font-bold ${communityFlag ? 'text-purple-600' : 'text-slate-600'}`}>
                  {communityFlag ? '⚠️ Active User Flags' : '✓ No Suspicious Anomalies'}
                </span>
              </div>
            </div>

            {communityReports.length > 0 ? (
              <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                {communityReports.map((rep) => (
                  <div key={rep.report_id} className="p-2.5 rounded-lg bg-purple-50/50 border border-purple-100 text-xs">
                    <div className="flex items-center justify-between font-medium text-purple-900 mb-0.5">
                      <span>{rep.issue_type || 'User Concern'}</span>
                      <span className="text-[10px] text-purple-600">{rep.created_at?.slice(0, 10)}</span>
                    </div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">{rep.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-4 text-center text-xs text-slate-500">
                No adverse event or suspected fake complaints filed by consumers or pharmacists for this batch.
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
          <span className="text-[11px] text-slate-400">Crowd-sourced patient feedback</span>
          <button
            type="button"
            onClick={onOpenReportModal}
            className="text-xs font-semibold text-violet-600 hover:text-violet-700 hover:underline flex items-center space-x-1"
          >
            <span>Report an issue</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>

    </div>
  );
};
