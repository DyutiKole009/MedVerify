import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { VerificationResponse } from '../../types/api';
import { submitFeedback } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const markdownComponents = {
  table: ({ node, ...props }: any) => (
    <div className="overflow-x-auto my-3 rounded-lg border border-slate-200 shadow-2xs">
      <table className="w-full text-left border-collapse text-xs font-sans" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: any) => (
    <thead className="bg-slate-100/90 border-b border-slate-200 text-slate-700 font-semibold text-[11px] font-mono tracking-wider uppercase" {...props} />
  ),
  tbody: ({ node, ...props }: any) => (
    <tbody className="divide-y divide-slate-100 bg-white" {...props} />
  ),
  tr: ({ node, ...props }: any) => (
    <tr className="even:bg-slate-50/50 hover:bg-sky-50/40 transition-colors" {...props} />
  ),
  th: ({ node, ...props }: any) => (
    <th className="px-3 py-2 border-r border-slate-200 last:border-r-0 font-semibold text-slate-800" {...props} />
  ),
  td: ({ node, ...props }: any) => (
    <td className="px-3 py-2 border-r border-slate-100 last:border-r-0 text-slate-700 leading-relaxed text-xs align-top" {...props} />
  ),
  h1: ({ node, ...props }: any) => (
    <h1 className="text-base font-bold text-slate-900 mt-4 mb-2 pb-1 border-b border-slate-200" {...props} />
  ),
  h2: ({ node, ...props }: any) => (
    <h2 className="text-sm font-bold text-sky-950 mt-3.5 mb-1.5" {...props} />
  ),
  h3: ({ node, ...props }: any) => (
    <h3 className="text-xs font-bold text-sky-800 mt-3 mb-1 uppercase tracking-wide font-mono" {...props} />
  ),
  h4: ({ node, ...props }: any) => (
    <h4 className="text-xs font-semibold text-slate-900 mt-2 mb-1" {...props} />
  ),
  p: ({ node, ...props }: any) => (
    <p className="text-xs text-slate-700 leading-relaxed my-1.5" {...props} />
  ),
  ul: ({ node, ...props }: any) => (
    <ul className="list-disc list-outside pl-4 space-y-1 my-1.5 text-xs text-slate-700" {...props} />
  ),
  ol: ({ node, ...props }: any) => (
    <ol className="list-decimal list-outside pl-4 space-y-1 my-1.5 text-xs text-slate-700" {...props} />
  ),
  li: ({ node, ...props }: any) => (
    <li className="leading-relaxed" {...props} />
  ),
  strong: ({ node, ...props }: any) => (
    <strong className="font-semibold text-slate-900" {...props} />
  ),
  blockquote: ({ node, ...props }: any) => (
    <blockquote className="border-l-2 border-sky-500 pl-3 py-1 my-2 bg-sky-50/60 text-slate-700 italic text-xs rounded-r" {...props} />
  ),
  code: ({ inline, ...props }: any) => (
    <code className="px-1.5 py-0.5 rounded bg-slate-100 text-sky-800 font-mono text-[11px] border border-slate-200" {...props} />
  ),
};

export interface ChatMessageItem {
  id: string;
  sender: 'user' | 'agent';
  timestamp: string;
  text?: string;
  imageUrl?: string;
  imageFileName?: string;
  imageFileSize?: string;
  isThinking?: boolean;
  result?: VerificationResponse;
}

interface ChatMessageProps {
  message: ChatMessageItem;
  onOpenReportModal?: (batchNo?: string, drugName?: string) => void;
  onOpenOcrModal?: () => void;
  onDownloadReport?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onOpenReportModal,
  onOpenOcrModal,
  onDownloadReport,
}) => {
  const { user, isAuthenticated } = useAuth();
  const [traceOpen, setTraceOpen] = useState(false);
  const [feedbackVote, setFeedbackVote] = useState<'up' | 'down' | null>(null);
  const [copied, setCopied] = useState(false);

  const userName = user?.name || user?.email || (isAuthenticated ? 'Customer' : 'You');
  const userInitials = userName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join('') || 'U';

  const handleVote = async (isHelpful: boolean) => {
    if (!message.result?.session_id) return;
    setFeedbackVote(isHelpful ? 'up' : 'down');
    try {
      await submitFeedback(message.result.session_id, isHelpful);
    } catch {
      // ignore
    }
  };

  const handleCopy = () => {
    const textToCopy =
      message.result?.summary ||
      message.text ||
      'MedVerify Verification Record';
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (ts: string) => {
    return new Date(ts).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 1. USER MESSAGE BUBBLE
  if (message.sender === 'user') {
    return (
      <div className="flex items-start gap-3 justify-end select-text">
        <div className="flex flex-col items-end max-w-xl gap-2">
          {/* Header Info */}
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-mono">
            <span className="font-medium text-slate-600">{userName}</span>
            <span>• {formatTime(message.timestamp)}</span>
          </div>

          {/* User Bubble Card */}
          <div className="p-3.5 rounded-2xl rounded-tr-sm bg-white border border-slate-200 text-slate-800 text-[14px] leading-relaxed shadow-xs">
            {message.text && (
              <p className="whitespace-pre-wrap">
                {message.text}
              </p>
            )}

            {/* Attached Thumbnail Card */}
            {message.imageUrl && (
              <div className="mt-3 p-2 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-12 h-12 rounded-lg overflow-hidden relative border border-slate-200 shrink-0 bg-white">
                    <img
                      src={message.imageUrl}
                      alt="Packaging Scan"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="flex flex-col text-left truncate">
                    <span className="font-mono text-xs text-slate-800 font-medium truncate">
                      {message.imageFileName || 'packaging_scan.jpg'}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {message.imageFileSize || 'Image attached'} • OCR Processed
                    </span>
                  </div>
                </div>

                {onOpenOcrModal && (
                  <button
                    type="button"
                    onClick={onOpenOcrModal}
                    className="px-2.5 py-1 rounded-md bg-white hover:bg-slate-100 text-sky-700 text-xs font-semibold border border-slate-200 transition-colors flex items-center gap-1 shadow-2xs shrink-0 cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[14px]">document_scanner</span>
                    <span>Review OCR</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* User Avatar Circle */}
        <div className="w-7 h-7 rounded-full bg-sky-100 border border-sky-200 flex items-center justify-center text-xs font-semibold text-sky-700 shrink-0 mt-6 select-none">
          {userInitials}
        </div>
      </div>
    );
  }

  // 2. AGENT RESPONSE
  const result = message.result;
  const isThinking = message.isThinking;
  const statusCategory = (result?.status_category || 'CLEAR').toUpperCase();
  const isSpurious = statusCategory === 'SPURIOUS';
  const isNsq = statusCategory === 'NSQ';
  const isClear = statusCategory === 'CLEAR';
  const isNoMatch = statusCategory === 'NO_MATCH';
  const isInfoNeeded = statusCategory === 'INFO_NEEDED';

  // Actual extracted or verified data ONLY
  const product =
    result?.official_record?.drug_name ||
    (result?.extracted_fields?.drug_name !== 'Not specified' ? result?.extracted_fields?.drug_name : '') ||
    '';
  const batchNo =
    result?.official_record?.batch_no ||
    (result?.extracted_fields?.batch_no !== 'Not specified' ? result?.extracted_fields?.batch_no : '') ||
    '';
  const maker =
    result?.official_record?.manufacturer_name ||
    (result?.extracted_fields?.manufacturer !== 'Not specified' ? result?.extracted_fields?.manufacturer : '') ||
    '';
  const expiry =
    result?.official_record?.expiry_date ||
    result?.extracted_fields?.expiry_date ||
    '';

  const hasMetadata = Boolean(product || batchNo || maker || expiry);

  return (
    <div className="flex items-start gap-3 justify-start select-text">
      {/* Bot Avatar Icon */}
      <div className="w-7 h-7 rounded-md bg-sky-600 flex items-center justify-center text-white font-bold shrink-0 shadow-xs mt-1 select-none">
        <span className="material-symbols-outlined text-[16px] text-white font-semibold">smart_toy</span>
      </div>

      <div className="flex flex-col flex-1 gap-3 max-w-2xl">
        {/* Bot Identity Header */}
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500 select-none">
          <span className="font-semibold text-slate-800">MedVerify AI Orchestrator</span>
          <span>• {formatTime(message.timestamp)}</span>
          {isThinking && (
            <span className="text-sky-600 font-sans animate-pulse font-medium">Verifying CDSCO database...</span>
          )}
        </div>

        {/* Collapsible Reasoning Chain */}
        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden shadow-2xs">
          <button
            type="button"
            className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-slate-50 transition-colors cursor-pointer"
            onClick={() => setTraceOpen(!traceOpen)}
          >
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[15px] text-sky-600">psychology</span>
              <span className="text-xs font-medium text-slate-700">
                {isThinking
                  ? 'Analyzing regulatory databases & recall records...'
                  : result?.orchestrator_tier
                  ? `Verification trace (${result.orchestrator_tier} Tier Agent)`
                  : 'Verification trace'}
              </span>
            </div>
            <span
              className={`material-symbols-outlined text-[16px] text-slate-400 transition-transform duration-200 ${
                traceOpen ? 'rotate-180' : ''
              }`}
            >
              expand_more
            </span>
          </button>

          {traceOpen && (
            <div className="px-3 pb-3 pt-1 text-xs text-slate-600 font-mono leading-relaxed flex flex-col gap-2 border-t border-slate-200 bg-slate-50">
              {result?.orchestrator_reasoning && (
                <div className="pt-1 text-slate-800">
                  {result.orchestrator_reasoning}
                </div>
              )}
              {result?.reasoning_trace && result.reasoning_trace.length > 0 && (
                <div className="flex flex-col gap-1.5 text-[11px]">
                  {result.reasoning_trace.map((step, idx) => (
                    <div
                      key={idx}
                      className={`flex items-start gap-1.5 ${
                        idx === 0
                          ? 'text-emerald-700'
                          : isSpurious
                          ? 'text-rose-700'
                          : isNsq
                          ? 'text-amber-800'
                          : 'text-slate-700'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[13px] mt-0.5">
                        {idx === 0 ? 'check' : isSpurious ? 'priority_high' : 'info'}
                      </span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Live / Completed Response Content */}
        {!isThinking && result && (
          <>
            {/* Sleek Callout Alert */}
            {isInfoNeeded && (
              <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 flex items-start gap-3">
                <span className="material-symbols-outlined text-[18px] text-sky-600 shrink-0 mt-0.5">
                  help_outline
                </span>
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold font-mono tracking-wide text-sky-700 uppercase">
                    Medicine Details Required for CDSCO Verification
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {result.summary || 'Specific medicine name and batch number are required to search CDSCO recall registers. See clinical guidance and triage details below.'}
                  </p>
                </div>
              </div>
            )}

            {isSpurious && (
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3">
                <span className="material-symbols-outlined text-[18px] text-rose-600 shrink-0 mt-0.5">
                  error_outline
                </span>
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold font-mono tracking-wide text-rose-700 uppercase">
                    Spurious Medicine Alert
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {result.summary || `Batch ${batchNo || 'queried'} is flagged as spurious/counterfeit in CDSCO regulatory records. Do not consume.`}
                  </p>
                </div>
              </div>
            )}

            {isNsq && (
              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3">
                <span className="material-symbols-outlined text-[18px] text-amber-700 shrink-0 mt-0.5">
                  warning
                </span>
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold font-mono tracking-wide text-amber-800 uppercase">
                    Quality Defect (Not of Standard Quality)
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {result.summary || `Batch ${batchNo || 'queried'} failed government laboratory standards. Dispensing halted.`}
                  </p>
                </div>
              </div>
            )}

            {isClear && (
              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
                <span className="material-symbols-outlined text-[18px] text-emerald-600 shrink-0 mt-0.5">
                  verified
                </span>
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold font-mono tracking-wide text-emerald-700 uppercase">
                    No Adverse Regulatory Record Found
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {result.summary || 'No active NSQ quality failure or counterfeit alert found in CDSCO records.'}
                  </p>
                </div>
              </div>
            )}

            {isNoMatch && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3">
                <span className="material-symbols-outlined text-[18px] text-slate-500 shrink-0 mt-0.5">
                  info
                </span>
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold font-mono tracking-wide text-slate-700 uppercase">
                    No Adverse Regulatory Record Found
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {result.summary || 'No active NSQ quality failure or counterfeit alert found in CDSCO records for this batch/medicine.'}
                  </p>
                </div>
              </div>
            )}

            {/* Structured Investigation Plan / Milestones (Deep Agent) */}
            {result.todos && result.todos.length > 0 && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-sky-600">checklist</span>
                    <span>Investigation Plan &amp; Milestones ({result.todos.filter((t) => t.status === 'completed').length}/{result.todos.length} Completed)</span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">DEEP TIER</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {result.todos.map((todo, idx) => {
                    const isCompleted = todo.status === 'completed';
                    const isInProgress = todo.status === 'in_progress';
                    return (
                      <div
                        key={idx}
                        className={`p-2 rounded-lg text-xs flex items-start gap-2 border ${
                          isCompleted
                            ? 'bg-emerald-50/50 border-emerald-200/60 text-slate-800'
                            : isInProgress
                            ? 'bg-sky-50/50 border-sky-200/60 text-sky-900'
                            : 'bg-white border-slate-200 text-slate-600'
                        }`}
                      >
                        <span
                          className={`material-symbols-outlined text-[15px] mt-0.5 shrink-0 ${
                            isCompleted ? 'text-emerald-600' : isInProgress ? 'text-sky-600 animate-spin' : 'text-slate-400'
                          }`}
                        >
                          {isCompleted ? 'check_circle' : isInProgress ? 'sync' : 'radio_button_unchecked'}
                        </span>
                        <div className="flex-1 leading-relaxed">
                          <span className={isCompleted ? 'text-slate-700' : ''}>
                            {todo.content}
                          </span>
                          <span
                            className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ml-2 font-medium ${
                              isCompleted
                                ? 'text-emerald-700 bg-emerald-100/60'
                                : isInProgress
                                ? 'text-sky-700 bg-sky-100/60'
                                : 'text-slate-500 bg-slate-100'
                            }`}
                          >
                            {todo.status.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 4-Card Metadata Grid (Rendered only if actual medicine fields exist) */}
            {hasMetadata && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs flex flex-col">
                  <span className="text-[10px] uppercase font-mono text-slate-400 font-medium">Product</span>
                  <span className="text-[13px] font-semibold text-slate-900 mt-0.5 truncate">
                    {product || 'Not detected'}
                  </span>
                </div>

                <div className={`p-2.5 rounded-lg bg-white shadow-2xs flex flex-col ${isSpurious ? 'border border-rose-200' : 'border border-slate-200'}`}>
                  <span className={`text-[10px] uppercase font-mono font-medium ${isSpurious ? 'text-rose-600' : 'text-slate-400'}`}>
                    Batch Number
                  </span>
                  <span className={`text-[13px] font-mono font-bold mt-0.5 ${isSpurious ? 'text-rose-700' : 'text-slate-900'}`}>
                    {batchNo || 'N/A'}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs flex flex-col">
                  <span className="text-[10px] uppercase font-mono text-slate-400 font-medium">Manufacturer</span>
                  <span className="text-[13px] font-semibold text-slate-900 mt-0.5 truncate">
                    {maker || 'Not specified'}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-2xs flex flex-col">
                  <span className="text-[10px] uppercase font-mono text-slate-400 font-medium">Expiry</span>
                  <span className="text-[13px] font-mono font-semibold text-slate-900 mt-0.5">
                    {expiry || 'N/A'}
                  </span>
                </div>
              </div>
            )}

            {/* Analysis & Summary Card */}
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3 text-xs leading-relaxed text-slate-700 font-sans">
              <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                <span className="material-symbols-outlined text-[18px] text-sky-600">biotech</span>
                <span>Regulatory Findings &amp; Clinical Investigation Dossier</span>
              </div>

              {result.explanation ? (
                <div className="text-slate-800 leading-relaxed font-sans text-xs select-text">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {result.explanation}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-slate-700 whitespace-pre-wrap">
                  {result.summary || 'Direct regulatory query completed across CDSCO repository and community issue flags.'}
                </p>
              )}

              {/* Official disclaimer */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 flex items-start gap-2">
                <span className="material-symbols-outlined text-[16px] text-sky-600 shrink-0 mt-0.5">verified_user</span>
                <span>
                  {result.disclaimer ||
                    'Notice: Absence of a flag is NOT proof of absolute safety. Official CDSCO records track confirmed laboratory test failures and gazette recalls.'}
                </span>
              </div>

              {/* Action Footer */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-1 text-slate-400">
                  <button
                    type="button"
                    onClick={() => handleVote(true)}
                    className={`p-1 rounded hover:bg-slate-100 transition-colors cursor-pointer ${
                      feedbackVote === 'up' ? 'text-emerald-600' : 'hover:text-emerald-600'
                    }`}
                    title="Helpful verification"
                  >
                    <span className="material-symbols-outlined text-[16px]">thumb_up</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleVote(false)}
                    className={`p-1 rounded hover:bg-slate-100 transition-colors cursor-pointer ${
                      feedbackVote === 'down' ? 'text-rose-600' : 'hover:text-rose-600'
                    }`}
                    title="Not helpful"
                  >
                    <span className="material-symbols-outlined text-[16px]">thumb_down</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="p-1 rounded hover:bg-slate-100 hover:text-slate-700 transition-colors ml-1 cursor-pointer"
                    title={copied ? 'Copied!' : 'Copy summary'}
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {copied ? 'check' : 'content_copy'}
                    </span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onDownloadReport}
                    className="px-2.5 py-1 rounded bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium border border-slate-300 shadow-2xs transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[14px] text-slate-500">download</span>
                    <span>Download Dossier</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onOpenReportModal?.(batchNo, product)}
                    className="px-2.5 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold border border-rose-200 transition-colors flex items-center gap-1 shadow-2xs cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[14px]">flag</span>
                    <span>Report Issue</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Source Attribution Chips */}
            {result.sources && result.sources.length > 0 && (
              <SourceChipsPanel sources={result.sources} />
            )}
          </>
        )}
      </div>
    </div>
  );
};

// ─── Source Attribution Panel ────────────────────────────────────────────────

interface SourceChipsPanelProps {
  sources: import('../../types/api').SourceChunk[];
}

const SourceChipsPanel: React.FC<SourceChipsPanelProps> = ({ sources }) => {
  const [expandedIdx, setExpandedIdx] = React.useState<number | null>(null);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400 uppercase tracking-wide select-none">
        <span className="material-symbols-outlined text-[12px]">dataset</span>
        <span>Sources ({sources.length})</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {sources.map((src, idx) => {
          const isDB = src.type === 'DB';
          const isExpanded = expandedIdx === idx;

          return (
            <div key={idx} className="rounded-lg border border-slate-200 bg-white overflow-hidden shadow-2xs">
              {/* Chip Header */}
              <div
                className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50 transition-colors ${isExpanded ? 'border-b border-slate-200' : ''}`}
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
              >
                {/* Type icon */}
                <span
                  className={`material-symbols-outlined text-[14px] shrink-0 ${isDB ? 'text-sky-600' : 'text-violet-600'}`}
                >
                  {isDB ? 'database' : 'auto_stories'}
                </span>

                {/* Label */}
                <span className="text-[11px] font-mono text-slate-700 flex-1 truncate">{src.label}</span>

                {/* Score badge (KB only) */}
                {src.score !== undefined && (
                  <span className="text-[10px] font-mono text-violet-600 bg-violet-50 border border-violet-200 px-1.5 py-0.5 rounded-full shrink-0">
                    {(src.score * 100).toFixed(0)}%
                  </span>
                )}

                {/* External link for DB sources with a PDF URL */}
                {isDB && src.doc_url && (
                  <a
                    href={src.doc_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-0.5 rounded hover:bg-sky-50 text-sky-600 transition-colors shrink-0"
                    title="Open CDSCO PDF"
                  >
                    <span className="material-symbols-outlined text-[13px]">open_in_new</span>
                  </a>
                )}

                {/* Expand chevron */}
                <span
                  className={`material-symbols-outlined text-[14px] text-slate-400 transition-transform duration-150 shrink-0 ${isExpanded ? 'rotate-180' : ''}`}
                >
                  expand_more
                </span>
              </div>

              {/* Expanded content preview */}
              {isExpanded && src.content_preview && (
                <div className="px-3 py-2 bg-slate-50 text-[11px] font-mono text-slate-600 leading-relaxed">
                  {src.content_preview}
                  {isDB && src.doc_url && (
                    <a
                      href={src.doc_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-sky-600 hover:underline inline-flex items-center gap-0.5"
                    >
                      View CDSCO PDF
                      <span className="material-symbols-outlined text-[11px]">open_in_new</span>
                    </a>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
