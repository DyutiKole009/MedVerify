import React, { useState, useRef, useEffect } from 'react';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessage } from './ChatMessage';
import type { ChatMessageItem } from './ChatMessage';
import { ChatOmnibox } from './ChatOmnibox';
import { OcrReviewModal } from './OcrReviewModal';
import type { ExtractedMedicineFields } from './OcrReviewModal';
import { IncidentModal } from './IncidentModal';
import { RecallsDrawer } from './RecallsDrawer';
import type { RecallNoticeItem } from './RecallsDrawer';
import type { CaseRecord } from './DashboardView';
import type { VerificationResponse } from '../../types/api';
import { useAuth } from '../../context/AuthContext';
import {
  submitVerification,
  uploadImageFile,
  extractPackagingOcr,
  fetchUserSessions,
  saveSessionToBackend,
} from '../../services/api';
import {
  getStoredVerificationSessions,
  saveStoredVerificationSession,
} from '../../services/session';

interface ChatInterfaceProps {
  initialCases?: CaseRecord[];
  isRecallsDrawerOpen?: boolean;
  onCloseRecallsDrawer?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  initialCases = [],
  isRecallsDrawerOpen = false,
  onCloseRecallsDrawer,
}) => {
  // Load real previous user sessions from client storage or initialCases
  const [sessions, setSessions] = useState<CaseRecord[]>(() => {
    const stored = getStoredVerificationSessions();
    if (stored.length > 0) return stored;
    return initialCases;
  });

  const { user, isAuthenticated } = useAuth();

  // Load sessions from DynamoDB whenever authentication state or user changes
  useEffect(() => {
    let isMounted = true;
    const loadBackendSessions = async () => {
      try {
        const backendSessions = await fetchUserSessions();
        if (isMounted && backendSessions.length > 0) {
          setSessions(backendSessions);
          backendSessions.forEach((s) => saveStoredVerificationSession(s));
        } else if (isMounted) {
          const stored = getStoredVerificationSessions();
          if (stored.length > 0) setSessions(stored);
        }
      } catch (err) {
        console.warn('Could not load sessions from backend:', err);
      }
    };
    loadBackendSessions();
    return () => {
      isMounted = false;
    };
  }, [user?.user_id, isAuthenticated]);

  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined);
  const [activeSessionLabel, setActiveSessionLabel] = useState<string>('NEW-VERIFICATION');
  const [activeSessionStatus, setActiveSessionStatus] = useState<string>('READY');

  // Messages in current stream - start clean and empty like ChatGPT
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Modals & Drawers state
  const [ocrModalVisible, setOcrModalVisible] = useState(false);
  const [pendingOcrFields, setPendingOcrFields] = useState<ExtractedMedicineFields>({});
  const [pendingImageUrl, setPendingImageUrl] = useState<string | undefined>(undefined);
  const [pendingImageS3Key, setPendingImageS3Key] = useState<string | undefined>(undefined);
  const [pendingUserText, setPendingUserText] = useState<string>('');

  const [incidentModalVisible, setIncidentModalVisible] = useState(false);
  const [incidentDrug, setIncidentDrug] = useState('');
  const [incidentBatch, setIncidentBatch] = useState('');

  const [recallsOpen, setRecallsOpen] = useState(isRecallsDrawerOpen);

  // Toast notifications
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setRecallsOpen(isRecallsDrawerOpen);
  }, [isRecallsDrawerOpen]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3000);
  };

  useEffect(() => {
    if (messages.length > 0) {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isLoading]);

  // Handle new prompt or attachment
  const handleSendMessage = async (text: string, file?: File) => {
    if (!text && !file) return;

    const userMsgId = `user-${Date.now()}`;
    const localUrl = file ? URL.createObjectURL(file) : undefined;

    const userMsg: ChatMessageItem = {
      id: userMsgId,
      sender: 'user',
      timestamp: new Date().toISOString(),
      text: text || undefined,
      imageUrl: localUrl,
      imageFileName: file?.name,
      imageFileSize: file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : undefined,
    };

    setMessages((prev) => [...prev, userMsg]);

    if (file) {
      setIsLoading(true);
      try {
        const uploadResult = await uploadImageFile(file);
        // Prefer the presigned GET URL (durable, works after reload) over the local blob
        setPendingImageUrl(uploadResult.image_url || localUrl);
        setPendingImageS3Key(uploadResult.s3_key);  // Preserve S3 key for OCR → REACTIVE routing
        setPendingUserText(text);

        const ocrData = await extractPackagingOcr(uploadResult.s3_key);
        const extracted = ocrData.extracted_fields || {};

        setPendingOcrFields({
          drug_name: extracted.drug_name || '',
          batch_no: extracted.batch_no !== 'Not visible in photo' ? extracted.batch_no : '',
          manufacturer: extracted.manufacturer !== 'Not visible in photo' ? extracted.manufacturer : '',
          mfg_date: extracted.mfg_date !== 'Not visible in photo' ? extracted.mfg_date : '',
          expiry_date: extracted.expiry_date !== 'Not visible in photo' ? extracted.expiry_date : '',
          ocr_confidence: extracted.ocr_confidence ?? 0.95,
        });

        setOcrModalVisible(true);
      } catch (err) {
        console.warn('OCR upload preparation failed, falling back to direct verification:', err);
        await executeVerification(text, file);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    await executeVerification(text);
  };

  const executeVerification = async (
    textQuery: string,
    file?: File,
    overrideFields?: ExtractedMedicineFields,
    imageS3Key?: string
  ) => {
    setIsLoading(true);
    const thinkingMsgId = `thinking-${Date.now()}`;

    const thinkingMsg: ChatMessageItem = {
      id: thinkingMsgId,
      sender: 'agent',
      timestamp: new Date().toISOString(),
      isThinking: true,
      result: {
        session_id: thinkingMsgId,
        status_category: 'CLEAR',
        disclaimer: 'Absence of a flag is not proof of safety.',
        orchestrator_tier: (file || imageS3Key) ? 'REACTIVE' : 'SKILL',
        orchestrator_reasoning: (file || imageS3Key)
          ? 'Packaging photograph routed to Vision Verification Agent.'
          : 'Query dispatched to Orchestrator for classification.',
        reasoning_trace: [
          'Step 1: Parsing input query parameters.',
          'Step 2: Cross-referencing CDSCO official batches master database.',
          'Step 3: Checking national NSQ and spurious recall lists.',
          'Step 4: Evaluating community safety flags.',
        ],
        community_flag: false,
      },
    };

    setMessages((prev) => [...prev, thinkingMsg]);

    try {
      const response: VerificationResponse = await submitVerification({
        text: textQuery,
        imageFile: file,
        imageS3Key: imageS3Key,
        batchNo: overrideFields?.batch_no,
        drugName: overrideFields?.drug_name,
        manufacturer: overrideFields?.manufacturer,
      });

      const finalAgentMsg: ChatMessageItem = {
        id: `agent-${response.session_id}`,
        sender: 'agent',
        timestamp: new Date().toISOString(),
        isThinking: false,
        result: response,
      };

      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingMsgId ? finalAgentMsg : m))
      );

      const targetBatch =
        response.official_record?.batch_no ||
        overrideFields?.batch_no ||
        (textQuery.length <= 15 ? textQuery : 'N/A');
      const targetDrug =
        response.official_record?.drug_name ||
        overrideFields?.drug_name ||
        (response.status_category === 'INFO_NEEDED' || textQuery.split(' ').length > 3
          ? 'Clinical Inquiry'
          : textQuery || 'Verification Query');

      const sessionCode =
        response.status_category === 'INFO_NEEDED'
          ? `CLINICAL-TRIAGE-${response.session_id.slice(0, 8).toUpperCase()}`
          : `${targetDrug.toUpperCase().replace(/\s+/g, '-').slice(0, 16)}-${targetBatch}`;
      setActiveSessionId(response.session_id);
      setActiveSessionLabel(sessionCode);
      setActiveSessionStatus(response.status_category);

      const newRecord: CaseRecord = {
        id: response.session_id,
        query: textQuery || file?.name || 'Inspection',
        batchNo: targetBatch,
        drugName: targetDrug,
        status: response.status_category,
        tier: response.orchestrator_tier,
        timestamp: new Date().toISOString(),
        imageUrl: pendingImageUrl || (file ? URL.createObjectURL(file) : undefined),
        result: response,
        messages: [
          {
            id: `usr-${Date.now()}`,
            sender: 'user',
            timestamp: new Date().toISOString(),
            text: textQuery,
            imageUrl: pendingImageUrl || (file ? URL.createObjectURL(file) : undefined),
          },
          finalAgentMsg,
        ],
      };

      setSessions((prev) => [newRecord, ...prev.filter((s) => s.id !== newRecord.id)]);
      saveStoredVerificationSession(newRecord);
      saveSessionToBackend(newRecord);
    } catch (err: any) {
      console.error('Verification query error:', err);
      const errorMsg: ChatMessageItem = {
        id: `err-${Date.now()}`,
        sender: 'agent',
        timestamp: new Date().toISOString(),
        isThinking: false,
        result: {
          session_id: 'error',
          status_category: 'CLEAR',
          summary: `Verification query encountered an error: ${err?.message || 'Network error'}. Please check your connection.`,
          disclaimer: 'Absence of an adverse flag is not proof of absolute quality.',
          orchestrator_tier: 'SKILL',
          community_flag: false,
        },
      };

      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingMsgId ? errorMsg : m))
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveOcr = async (approved: ExtractedMedicineFields) => {
    setOcrModalVisible(false);
    showToast(`Approved details: ${approved.drug_name || 'Medicine'} (${approved.batch_no || 'No batch'})`);
    const s3Key = pendingImageS3Key;
    setPendingImageS3Key(undefined);  // Clear before async call to avoid stale state
    await executeVerification(
      pendingUserText || approved.drug_name || 'Packaging Scan',
      undefined,
      approved,
      s3Key  // Forward the pre-uploaded S3 key → routes to POST /investigate → REACTIVE Agent
    );
  };

  const handleSelectSession = (s: CaseRecord) => {
    setActiveSessionId(s.id);
    setActiveSessionLabel(`${s.drugName.toUpperCase().replace(/\s+/g, '-').slice(0, 16)}-${s.batchNo}`);
    setActiveSessionStatus(s.status);

    if (s.messages && s.messages.length > 0) {
      setMessages(s.messages as ChatMessageItem[]);
    } else if (s.result) {
      setMessages([
        {
          id: `hist-user-${s.id}`,
          sender: 'user',
          timestamp: s.timestamp,
          text: s.query || `Inspect ${s.drugName} (Batch: ${s.batchNo})`,
          imageUrl: s.imageUrl,
        },
        {
          id: `hist-agent-${s.id}`,
          sender: 'agent',
          timestamp: s.timestamp,
          isThinking: false,
          result: s.result,
        },
      ]);
    }
    showToast(`Loaded session: ${s.drugName} (${s.batchNo})`);
  };

  const handleNewVerification = () => {
    setActiveSessionId(undefined);
    setActiveSessionLabel('NEW-VERIFICATION');
    setActiveSessionStatus('READY');
    setMessages([]);
    showToast('New verification session ready.');
  };

  const handleOpenReportModal = (batch?: string, drug?: string) => {
    setIncidentDrug(drug || '');
    setIncidentBatch(batch || '');
    setIncidentModalVisible(true);
  };

  const handleSelectRecall = (notice: RecallNoticeItem) => {
    const query = notice.batchNo
      ? `Verify batch ${notice.batchNo}`
      : `Check CDSCO alert ${notice.name}`;
    handleSendMessage(query);
  };

  const handleExportReport = () => {
    showToast('Generating official Verification Report...');
    setTimeout(() => {
      const content = `
MEDVERIFY MEDICINE SAFETY VERIFICATION RECORD
Central Drugs Standard Control Organisation (CDSCO) Integration Gateway
============================================================
SESSION:          ${activeSessionLabel}
STATUS:           ${activeSessionStatus}
GENERATED AT:     ${new Date().toISOString()}

DETAILS:
Drug Name:        ${incidentDrug || 'Queried Medicine'}
Batch Number:     ${incidentBatch || 'Queried Batch'}
Summary:          Verified against CDSCO gazette recalls and community reports.
Notice:           Absence of a flag is not proof of absolute quality.
============================================================
MedVerify Official Safety Record
      `;
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `MEDVERIFY-${activeSessionLabel}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`Downloaded MEDVERIFY-${activeSessionLabel}.txt`);
    }, 600);
  };

  const renderStatusPill = () => {
    const s = activeSessionStatus.toUpperCase();
    if (s === 'READY') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200">
          Ready
        </span>
      );
    }
    if (s === 'INFO_NEEDED') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-sky-50 text-sky-800 border border-sky-200">
          Clinical Guidance Needed
        </span>
      );
    }
    if (s === 'SPURIOUS') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-rose-50 text-rose-700 border border-rose-200">
          Spurious Medicine Alert
        </span>
      );
    }
    if (s === 'NSQ' || s === 'NSQ DEFECT') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-50 text-amber-800 border border-amber-200">
          NSQ Quality Defect
        </span>
      );
    }
    if (s === 'COMMUNITY_FLAGGED') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-purple-50 text-purple-800 border border-purple-200">
          Community Safety Signal
        </span>
      );
    }
    if (s === 'NO_MATCH') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
          No Adverse Notice
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        Standard Quality
      </span>
    );
  };

  return (
    <div className="flex-1 flex overflow-hidden h-[calc(100vh-53px)]">
      {/* 1. Sidebar with real session history */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewVerification={handleNewVerification}
        onOpenReportModal={handleOpenReportModal}
      />

      {/* 2. Main Chat Stream Workspace */}
      <main className="flex-1 flex flex-col bg-[#f8fafc] relative overflow-hidden select-text">
        {/* Sub-Bar (Real Session Context) */}
        <div className="h-9 px-6 bg-white/70 backdrop-blur border-b border-slate-200 flex items-center justify-between text-xs text-slate-500 shrink-0">
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span className="text-slate-400 font-normal">Session:</span>
            <span className="text-slate-800 font-semibold">{activeSessionLabel}</span>
            <span className="text-slate-300">•</span>
            {renderStatusPill()}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleExportReport}
              className="flex items-center gap-1 text-[11px] hover:text-slate-900 text-slate-600 transition-colors py-1 px-2.5 rounded bg-white hover:bg-slate-50 border border-slate-200 shadow-2xs font-medium cursor-pointer"
            >
              <span className="material-symbols-outlined text-[14px] text-slate-500">download</span>
              <span>Export Report</span>
            </button>
          </div>
        </div>

        {/* Chat Stream: Dynamic layout (centered welcome when empty, top-aligned natural scroll when active) */}
        <div
          className={`flex-1 overflow-y-auto px-4 md:px-8 py-6 flex flex-col ${
            messages.length === 0 ? 'items-center justify-center' : 'justify-start'
          }`}
        >
          {messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center max-w-xl mx-auto px-4 text-center select-none py-12">
              <div className="w-12 h-12 rounded-xl bg-sky-600 text-white flex items-center justify-center mb-4 shadow-sm">
                <span className="material-symbols-outlined text-[28px]">verified_user</span>
              </div>
              <h1 className="text-xl font-semibold text-slate-900 tracking-tight font-sans">
                What medicine would you like to verify?
              </h1>
              <p className="text-xs text-slate-500 max-w-md mt-1.5 leading-relaxed font-sans">
                Verify authenticity, laboratory test failures, and recall notices from the Central Drugs Standard Control Organisation (CDSCO).
              </p>

              {/* Starter Action Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full mt-8 text-left">
                <button
                  type="button"
                  onClick={() => handleSendMessage('PD-602')}
                  className="p-3 rounded-xl bg-white border border-slate-200 hover:border-sky-400 hover:shadow-xs transition-all text-xs group cursor-pointer"
                >
                  <div className="font-semibold text-slate-800 group-hover:text-sky-700 flex items-center justify-between">
                    <span>Check Batch PD-602</span>
                    <span className="material-symbols-outlined text-[15px] text-slate-400 group-hover:text-sky-600">arrow_forward</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Test CDSCO spurious alert batch</p>
                </button>

                <button
                  type="button"
                  onClick={() => handleSendMessage('T-2401')}
                  className="p-3 rounded-xl bg-white border border-slate-200 hover:border-sky-400 hover:shadow-xs transition-all text-xs group cursor-pointer"
                >
                  <div className="font-semibold text-slate-800 group-hover:text-sky-700 flex items-center justify-between">
                    <span>Check Batch T-2401</span>
                    <span className="material-symbols-outlined text-[15px] text-slate-400 group-hover:text-sky-600">arrow_forward</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Test standard quality batch</p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    const input = document.getElementById('omniboxFileInput');
                    input?.click();
                  }}
                  className="p-3 rounded-xl bg-white border border-slate-200 hover:border-sky-400 hover:shadow-xs transition-all text-xs group cursor-pointer"
                >
                  <div className="font-semibold text-slate-800 group-hover:text-sky-700 flex items-center justify-between">
                    <span>Scan Packaging Photo</span>
                    <span className="material-symbols-outlined text-[15px] text-slate-400 group-hover:text-sky-600">arrow_forward</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Multimodal vision OCR extraction</p>
                </button>

                <button
                  type="button"
                  onClick={() => setRecallsOpen(true)}
                  className="p-3 rounded-xl bg-white border border-slate-200 hover:border-sky-400 hover:shadow-xs transition-all text-xs group cursor-pointer"
                >
                  <div className="font-semibold text-slate-800 group-hover:text-sky-700 flex items-center justify-between">
                    <span>Explore CDSCO Recalls</span>
                    <span className="material-symbols-outlined text-[15px] text-slate-400 group-hover:text-sky-600">arrow_forward</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Browse national gazette notices</p>
                </button>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto w-full flex flex-col gap-6 pb-12">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onOpenReportModal={handleOpenReportModal}
                  onOpenOcrModal={() => setOcrModalVisible(true)}
                  onDownloadReport={handleExportReport}
                />
              ))}
              <div ref={scrollRef} className="h-2 shrink-0" />
            </div>
          )}
        </div>

        {/* Floating Omnibox */}
        <ChatOmnibox
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onOpenOcrModal={() => setOcrModalVisible(true)}
          onOpenRecallsDrawer={() => setRecallsOpen(true)}
          onShowToast={showToast}
        />
      </main>

      {/* OCR Preview & Correction Modal */}
      <OcrReviewModal
        visible={ocrModalVisible}
        initialFields={pendingOcrFields}
        imageUrl={pendingImageUrl}
        onDismiss={() => setOcrModalVisible(false)}
        onApproveAndVerify={handleApproveOcr}
      />

      {/* Incident / Quality Report Modal */}
      <IncidentModal
        visible={incidentModalVisible}
        defaultDrug={incidentDrug}
        defaultBatch={incidentBatch}
        onDismiss={() => setIncidentModalVisible(false)}
        onSubmitted={showToast}
      />

      {/* CDSCO Active Recalls Drawer */}
      <RecallsDrawer
        isOpen={recallsOpen}
        onClose={() => {
          setRecallsOpen(false);
          onCloseRecallsDrawer?.();
        }}
        onSelectRecall={handleSelectRecall}
      />

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-16 right-6 z-50 px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white shadow-xl flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-150 font-sans">
          <span className="material-symbols-outlined text-sky-400 text-[16px]">info</span>
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
};
