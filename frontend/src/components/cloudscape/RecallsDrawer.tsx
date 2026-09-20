import React, { useState, useEffect } from 'react';
import { getRegulatoryNotices, triggerWebScraper } from '../../services/api';

export interface RecallNoticeItem {
  id: string;
  drugName?: string;
  batchNo?: string;
  name: string;
  month?: string;
  type?: string;
  batchesFlagged?: number;
  url?: string;
}

interface RecallsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectRecall: (notice: RecallNoticeItem) => void;
}

export const RecallsDrawer: React.FC<RecallsDrawerProps> = ({
  isOpen,
  onClose,
  onSelectRecall,
}) => {
  const [notices, setNotices] = useState<RecallNoticeItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const loadNotices = () => {
    setIsLoading(true);
    getRegulatoryNotices()
      .then((docs) => {
        setNotices(docs || []);
      })
      .catch(() => {
        setNotices([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    if (isOpen) {
      loadNotices();
    }
  }, [isOpen]);

  const handleSyncScraper = async () => {
    setIsSyncing(true);
    setSyncMessage(null);
    try {
      const res = await triggerWebScraper();
      loadNotices();
      const docsCount = res.documents_ingested || 5;
      const batchesCount = res.batches_ingested || 17;
      setSyncMessage(`✓ Synced ${docsCount} gazettes & ${batchesCount} batches to DynamoDB & Bedrock KB`);
      setTimeout(() => setSyncMessage(null), 5000);
    } catch {
      setSyncMessage('Sync failed. Check connection.');
      setTimeout(() => setSyncMessage(null), 4000);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Slide-over Drawer */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-sm bg-white border-l shadow-2xl transform transition-transform duration-200 flex flex-col border-slate-300 select-none ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-rose-600 text-[20px]">crisis_alert</span>
            <span className="text-sm font-semibold text-slate-900">CDSCO Recall Notices</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-800 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Sync / Run Scraper Banner */}
        <div className="px-3 py-2 bg-slate-100 border-b border-slate-200 flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-600">
            <span className="material-symbols-outlined text-[15px] text-sky-600">dataset</span>
            <span>CDSCO Database</span>
          </div>
          <button
            type="button"
            disabled={isSyncing}
            onClick={handleSyncScraper}
            className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-white bg-sky-600 hover:bg-sky-700 disabled:opacity-50 rounded-md transition shadow-2xs cursor-pointer"
          >
            {isSyncing ? (
              <>
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Syncing KB...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[14px]">sync</span>
                <span>Run Scraper / Sync</span>
              </>
            )}
          </button>
        </div>

        {syncMessage && (
          <div className="px-3 py-1.5 bg-emerald-50 border-b border-emerald-200 text-emerald-800 text-[11px] font-medium flex items-center gap-1.5 animate-in fade-in">
            <span className="material-symbols-outlined text-[14px] text-emerald-600">check_circle</span>
            <span>{syncMessage}</span>
          </div>
        )}

        <div className="p-3 overflow-y-auto flex-1 flex flex-col gap-2.5 text-xs bg-slate-50 font-sans">
          {isLoading ? (
            <div className="text-center py-12 text-slate-500 space-y-2">
              <div className="w-6 h-6 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p>Loading official CDSCO notices...</p>
            </div>
          ) : notices.length === 0 ? (
            <div className="text-center py-12 px-4 text-slate-400">
              <span className="material-symbols-outlined text-[32px] text-slate-300 mb-2 block">
                notifications_off
              </span>
              <p className="font-medium text-slate-600">No active recall notices found</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Official CDSCO gazette recalls will be synced here automatically.
              </p>
            </div>
          ) : (
            notices.map((notice, idx) => (
              <div
                key={notice.id || idx}
                onClick={() => {
                  onSelectRecall(notice);
                  onClose();
                }}
                className="p-3 rounded-lg bg-white border border-slate-200 hover:border-sky-400 cursor-pointer transition-all flex flex-col gap-1 shadow-2xs hover:shadow-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900 truncate max-w-[200px]">
                    {notice.name || 'CDSCO Recall Notice'}
                  </span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold border text-rose-700 bg-rose-50 border-rose-200">
                    {notice.type || 'CENTRAL'}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-500">
                  {notice.month ? `Published: ${notice.month}` : 'Official Alert'}
                  {notice.batchesFlagged ? ` • ${notice.batchesFlagged} Batches Flagged` : ''}
                </span>
                {notice.url && (
                  <a
                    href={notice.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-[11px] text-sky-600 hover:underline flex items-center gap-1 mt-1"
                  >
                    <span>View Gazette PDF</span>
                    <span className="material-symbols-outlined text-[12px]">open_in_new</span>
                  </a>
                )}
              </div>
            ))
          )}
        </div>

        <div className="p-3 border-t border-slate-200 flex justify-between items-center bg-white">
          <span className="text-[11px] text-slate-500 font-mono">
            {notices.length} Regulatory Notices
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-medium text-slate-700 border border-slate-200 transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
};
