import React, { useState } from 'react';
import type { CaseRecord } from './DashboardView';

interface ChatSidebarProps {
  sessions: CaseRecord[];
  activeSessionId?: string;
  onSelectSession: (session: CaseRecord) => void;
  onNewVerification: () => void;
  onOpenReportModal: (batchNo?: string, drugName?: string) => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewVerification,
  onOpenReportModal,
}) => {
  const [filterQuery, setFilterQuery] = useState('');

  // Filter ONLY real user sessions
  const filteredSessions = sessions.filter((s) => {
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase();
    return (
      s.batchNo?.toLowerCase().includes(q) ||
      s.drugName?.toLowerCase().includes(q) ||
      s.query?.toLowerCase().includes(q)
    );
  });

  // Group sessions by Today, Yesterday, Previous
  const todaySessions: CaseRecord[] = [];
  const yesterdaySessions: CaseRecord[] = [];
  const previousSessions: CaseRecord[] = [];

  const now = new Date().getTime();
  const oneDay = 24 * 60 * 60 * 1000;

  filteredSessions.forEach((s) => {
    const sTime = new Date(s.timestamp).getTime();
    const diffDays = Math.floor((now - sTime) / oneDay);
    if (diffDays === 0) {
      todaySessions.push(s);
    } else if (diffDays === 1) {
      yesterdaySessions.push(s);
    } else {
      previousSessions.push(s);
    }
  });

  const renderBadge = (status?: string) => {
    const s = (status || 'CLEAR').toUpperCase();
    if (s === 'SPURIOUS' || s === 'FLAGGED') {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-50 text-rose-700 border border-rose-200 shrink-0">
          SPURIOUS
        </span>
      );
    }
    if (s === 'NSQ' || s === 'NSQ DEFECT') {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-50 text-amber-800 border border-amber-200 shrink-0">
          NSQ DEFECT
        </span>
      );
    }
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
        VERIFIED
      </span>
    );
  };

  const renderSessionCard = (item: CaseRecord) => {
    const isSelected = item.id === activeSessionId;
    const timeDisplay = new Date(item.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    return (
      <div
        key={item.id}
        onClick={() => onSelectSession(item)}
        className={`session-item group relative p-2.5 rounded-lg cursor-pointer transition-all flex flex-col gap-1 select-none ${
          isSelected
            ? 'active bg-white border border-sky-300 shadow-xs'
            : 'bg-transparent hover:bg-white border border-transparent hover:border-slate-200 text-slate-600 hover:text-slate-900'
        }`}
      >
        <div className="flex items-center justify-between">
          <span
            className={`text-[13px] truncate max-w-[150px] ${
              isSelected ? 'font-semibold text-slate-900' : 'font-medium text-slate-800'
            }`}
          >
            {item.drugName || item.query || 'Verification Scan'}
          </span>
          {renderBadge(item.status)}
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>Batch {item.batchNo && item.batchNo !== 'N/A' ? item.batchNo : 'Unspecified'}</span>
          <span>{timeDisplay}</span>
        </div>
      </div>
    );
  };

  return (
    <aside
      className="w-72 bg-slate-50 border-r flex flex-col justify-between shrink-0 select-text border-slate-300 shadow-xs h-full"
      style={{ borderRightWidth: '2px' }}
    >
      <div className="p-3 flex flex-col gap-3 overflow-y-auto flex-1">
        {/* + New Verification Button */}
        <button
          type="button"
          onClick={onNewVerification}
          className="w-full h-9 rounded-lg bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 text-[13px] font-medium flex items-center justify-between px-3 transition-all group shadow-xs cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[17px] text-sky-600 group-hover:rotate-90 transition-transform">
              add
            </span>
            <span className="font-medium">New Verification</span>
          </span>
          <kbd className="font-mono text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            ⌘K
          </kbd>
        </button>

        {/* Search Input */}
        <div className="relative">
          <span className="material-symbols-outlined absolute left-2.5 top-2 text-[16px] text-slate-400">
            search
          </span>
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Search verifications..."
            className="w-full h-8 pl-8 pr-3 text-xs rounded-md bg-white text-slate-800 placeholder-slate-400 border border-slate-200 focus:border-sky-500 focus:outline-none transition-colors shadow-2xs font-sans"
          />
        </div>

        {/* Sessions List or Empty State */}
        <div className="flex flex-col gap-3 pt-1">
          {filteredSessions.length === 0 ? (
            <div className="text-center py-8 px-2 text-xs text-slate-400 font-sans">
              <span className="material-symbols-outlined text-slate-300 text-[28px] mb-1 block">
                history
              </span>
              No previous verifications yet.
              <p className="text-[11px] text-slate-400 mt-1">
                Your medicine verification history will appear here.
              </p>
            </div>
          ) : (
            <>
              {todaySessions.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 px-2 py-1 block uppercase tracking-wider font-mono">
                    Today
                  </span>
                  <div className="flex flex-col gap-1 mt-1">
                    {todaySessions.map(renderSessionCard)}
                  </div>
                </div>
              )}

              {yesterdaySessions.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 px-2 py-1 block uppercase tracking-wider font-mono">
                    Yesterday
                  </span>
                  <div className="flex flex-col gap-1 mt-1">
                    {yesterdaySessions.map(renderSessionCard)}
                  </div>
                </div>
              )}

              {previousSessions.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 px-2 py-1 block uppercase tracking-wider font-mono">
                    Previous
                  </span>
                  <div className="flex flex-col gap-1 mt-1">
                    {previousSessions.map(renderSessionCard)}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer Bar */}
      <div className="p-3 border-t border-slate-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px] text-emerald-600">verified</span>
          <span className="text-[11px] text-slate-600 font-mono">
            Safety Node: <span className="text-slate-900 font-semibold">Online</span>
          </span>
        </div>
        <button
          type="button"
          onClick={() => onOpenReportModal()}
          className="text-[11px] text-sky-700 font-medium hover:underline flex items-center gap-1 cursor-pointer"
        >
          <span className="material-symbols-outlined text-[14px]">flag</span> Report Issue
        </button>
      </div>
    </aside>
  );
};
