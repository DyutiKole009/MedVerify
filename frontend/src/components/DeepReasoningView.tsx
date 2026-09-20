import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Bot, BookOpen, Layers, CheckCircle } from 'lucide-react';

interface DeepReasoningViewProps {
  reasoningTrace?: string[];
  citations?: Array<{ title?: string; source_url: string; text?: string }>;
  extractedFields?: {
    drug_name?: string;
    batch_no?: string;
    manufacturer?: string;
    expiry_date?: string;
    mfg_date?: string;
    ocr_confidence?: number;
  };
}

export const DeepReasoningView: React.FC<DeepReasoningViewProps> = ({
  reasoningTrace = [],
  citations = [],
  extractedFields,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (reasoningTrace.length === 0 && citations.length === 0 && !extractedFields) {
    return null;
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-3.5 bg-slate-50/70 hover:bg-slate-50 transition flex items-center justify-between text-left"
      >
        <div className="flex items-center space-x-2.5">
          <div className="p-1 rounded bg-indigo-100 text-indigo-700">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-800 tracking-tight block">
              Autonomous Agent Reasoning & Trace
            </span>
            <span className="text-[11px] text-slate-500">
              Inspection trajectory, Knowledge Base citations, and entity extraction
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-1 text-xs font-semibold text-slate-500">
          <span>{isOpen ? 'Collapse' : 'Inspect'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-5 border-t border-slate-200 space-y-4">
          
          {/* OCR Extracted Fields if available */}
          {extractedFields && (
            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2 flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-sky-600" />
                <span>Extracted Packaging Metadata (OCR Vision)</span>
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200/60 text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px]">Detected Batch</span>
                  <span className="font-mono font-bold text-slate-800">{extractedFields.batch_no || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Drug Name</span>
                  <span className="font-semibold text-slate-800 truncate block">{extractedFields.drug_name || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Manufacturer</span>
                  <span className="font-medium text-slate-800 truncate block">{extractedFields.manufacturer || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">OCR Confidence</span>
                  <span className="font-mono font-bold text-emerald-600">
                    {extractedFields.ocr_confidence ? `${Math.round(extractedFields.ocr_confidence * 100)}%` : 'High'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Reasoning Steps */}
          {reasoningTrace.length > 0 && (
            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2 flex items-center space-x-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-indigo-600" />
                <span>Multi-Step Agent Reasoning Trajectory</span>
              </span>
              <div className="space-y-2">
                {reasoningTrace.map((step, index) => (
                  <div key={index} className="flex items-start space-x-2.5 text-xs text-slate-700">
                    <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-700 font-mono font-bold text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-100">
                      {index + 1}
                    </span>
                    <p className="leading-relaxed bg-slate-50 p-2 rounded-lg border border-slate-100 flex-1">
                      {step}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bedrock Citations */}
          {citations.length > 0 && (
            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2 flex items-center space-x-1.5">
                <BookOpen className="w-3.5 h-3.5 text-amber-600" />
                <span>Bedrock Knowledge Base Citations</span>
              </span>
              <div className="space-y-1.5">
                {citations.map((cit, index) => (
                  <div key={index} className="p-2.5 rounded-lg bg-amber-50/50 border border-amber-200/60 text-xs">
                    <span className="font-mono text-[11px] text-amber-900 block font-semibold truncate">
                      {cit.source_url}
                    </span>
                    {cit.text && <p className="text-slate-600 text-[11px] mt-1 italic leading-relaxed">"{cit.text}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
};
