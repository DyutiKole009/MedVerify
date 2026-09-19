import { useState, useEffect } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { Omnibox } from './components/Omnibox';
import { OrchestratorTrace } from './components/OrchestratorTrace';
import { StatusBanner } from './components/StatusBanner';
import { EvidenceCards } from './components/EvidenceCards';
import { ManufacturerCard } from './components/ManufacturerCard';
import { DeepReasoningView } from './components/DeepReasoningView';
import { FeedbackWidget } from './components/FeedbackWidget';
import { ReportModal } from './components/ReportModal';
import { HistoryDrawer } from './components/HistoryDrawer';
import { submitVerification } from './services/api';
import type { VerificationResponse } from './types/api';

interface HistoryItem {
  query: string;
  result: VerificationResponse;
  timestamp: string;
}

export function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [currentResult, setCurrentResult] = useState<VerificationResponse | null>(null);
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('medverify_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('medverify_history', JSON.stringify(history));
    } catch {
      // Ignore quota errors
    }
  }, [history]);

  const handleSearch = async (text: string, imageFile?: File) => {
    setIsLoading(true);
    setError(null);
    setCurrentQuery(text || (imageFile ? imageFile.name : 'Packaging Check'));

    try {
      const result = await submitVerification({
        text,
        imageFile,
        batchNo: text && text.trim().length <= 15 ? text.trim() : undefined,
      });

      setCurrentResult(result);

      // Save to local history
      const newItem: HistoryItem = {
        query: text || imageFile?.name || 'Inspection',
        result,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setHistory((prev) => [newItem, ...prev.slice(0, 19)]);
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.message || 'Verification could not be completed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setHistory([]);
    localStorage.removeItem('medverify_history');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-sky-500 selection:text-white">
      <Navbar
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenReport={() => setIsReportOpen(true)}
      />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        
        {/* Hero Title & Description */}
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-semibold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-sky-500" />
            <span>AI Multi-Agent Verification Platform</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Verify Any Medicine in Seconds
          </h1>

          <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
            Enter a batch number, snap a photo of the packaging, or describe an adverse reaction.
            Our <strong>intelligent orchestrator</strong> automatically routes your inquiry to the right AI agent.
          </p>
        </div>

        {/* Unified Interactive Omnibox (No separate tabs!) */}
        <Omnibox onSearch={handleSearch} isLoading={isLoading} />

        {/* Loading Stepper / State */}
        {isLoading && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm text-center max-w-md mx-auto space-y-3 animate-in fade-in">
            <Loader2 className="w-8 h-8 animate-spin text-sky-600 mx-auto" />
            <div>
              <h4 className="text-sm font-bold text-slate-800">Orchestrating Verification</h4>
              <p className="text-xs text-slate-500 mt-1">
                Classifying query intent and checking CDSCO regulatory records...
              </p>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-800 text-xs sm:text-sm font-medium flex items-center justify-between max-w-3xl mx-auto">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-xs underline font-semibold ml-2">
              Dismiss
            </button>
          </div>
        )}

        {/* Verification Results View */}
        {currentResult && !isLoading && (
          <div className="space-y-6 animate-in fade-in duration-200">
            
            {/* Orchestrator Decision Trace */}
            <OrchestratorTrace
              tier={currentResult.orchestrator_tier}
              reasoning={currentResult.orchestrator_reasoning}
            />

            {/* Verdict Status Banner (with Mandatory Safety Disclaimer) */}
            <StatusBanner
              status={currentResult.status_category}
              disclaimer={currentResult.disclaimer}
              batchNo={currentResult.official_record?.batch_no || currentQuery}
              summary={currentResult.summary}
            />

            {/* Side-by-Side Signal Separation: CDSCO Official vs Community Reports */}
            <EvidenceCards
              officialRecord={currentResult.official_record}
              communityFlag={currentResult.community_flag}
              communityReportCount={currentResult.community_report_count}
              communityReports={currentResult.community_reports}
              onOpenReportModal={() => setIsReportOpen(true)}
            />

            {/* Manufacturer Dossier if available */}
            {currentResult.manufacturer_record && (
              <ManufacturerCard
                profile={currentResult.manufacturer_record}
                recentBatches={currentResult.recent_manufacturer_batches}
              />
            )}

            {/* Deep / Reactive Autonomous Reasoning Trace & Bedrock Citations */}
            <DeepReasoningView
              reasoningTrace={currentResult.reasoning_trace}
              citations={currentResult.citations}
              extractedFields={currentResult.extracted_fields}
            />

            {/* Interactive Helpful/Not Helpful Feedback (Powers RAG Promotion) */}
            <FeedbackWidget sessionId={currentResult.session_id} />

          </div>
        )}

        {/* Informative Platform Footnotes */}
        {!currentResult && !isLoading && (
          <div className="pt-8 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-slate-500">
            <div className="p-4 rounded-xl bg-white border border-slate-200/70 shadow-sm">
              <span className="font-bold text-slate-800 block mb-1">⚡ Skill Agent (Tier 1)</span>
              Direct DynamoDB index query for clean batch numbers in under 500 milliseconds.
            </div>
            <div className="p-4 rounded-xl bg-white border border-slate-200/70 shadow-sm">
              <span className="font-bold text-slate-800 block mb-1">📷 Reactive Agent (Tier 2)</span>
              Computer vision OCR pipeline extracting typography from medicine strips and packaging.
            </div>
            <div className="p-4 rounded-xl bg-white border border-slate-200/70 shadow-sm">
              <span className="font-bold text-slate-800 block mb-1">🔬 Deep Agent (Tier 3)</span>
              Autonomous Bedrock Knowledge Base retrieval across regulatory precedents and clinical alerts.
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-400">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>MedVerify Platform • Official data sourced from CDSCO National Quality Alerts</span>
          <span className="italic font-medium text-slate-500">
            "Absence of a flag is not proof of safety."
          </span>
        </div>
      </footer>

      {/* Community Report Submission Modal */}
      <ReportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        defaultBatchNo={currentResult?.official_record?.batch_no || currentQuery}
      />

      {/* Verification History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        onSelect={(res) => setCurrentResult(res)}
        onClear={handleClearHistory}
      />
    </div>
  );
}

export default App;
