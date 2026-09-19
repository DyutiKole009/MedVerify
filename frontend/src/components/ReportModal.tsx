import React, { useState } from 'react';
import { X, AlertCircle, Send, Loader2, Check } from 'lucide-react';
import { submitCommunityReport } from '../services/api';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultBatchNo?: string;
}

export const ReportModal: React.FC<ReportModalProps> = ({ isOpen, onClose, defaultBatchNo = '' }) => {
  const [batchNo, setBatchNo] = useState(defaultBatchNo);
  const [drugName, setDrugName] = useState('');
  const [issueType, setIssueType] = useState('SUSPECTED_COUNTERFEIT');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    setIsSubmitting(true);
    const ok = await submitCommunityReport({
      batch_no: batchNo.trim() || undefined,
      drug_name: drugName.trim() || undefined,
      issue_type: issueType,
      description: description.trim(),
    });
    setIsSubmitting(false);

    if (ok) {
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1800);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-2.5 mb-4">
          <div className="p-2 rounded-xl bg-violet-100 text-violet-700">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-base text-slate-900">File a Community Safety Report</h3>
            <p className="text-xs text-slate-500">Report adverse reactions, quality flaws, or suspected fakes</p>
          </div>
        </div>

        {success ? (
          <div className="py-8 text-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
              <Check className="w-6 h-6" />
            </div>
            <h4 className="font-bold text-slate-900">Report Successfully Logged</h4>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              Your report has been stored in the community registry and will appear on verification queries.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Batch Number
                </label>
                <input
                  type="text"
                  value={batchNo}
                  onChange={(e) => setBatchNo(e.target.value)}
                  placeholder="e.g. B-9021"
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl outline-none focus:border-violet-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Drug Name
                </label>
                <input
                  type="text"
                  value={drugName}
                  onChange={(e) => setDrugName(e.target.value)}
                  placeholder="e.g. Paracetamol 500mg"
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl outline-none focus:border-violet-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Issue Category
              </label>
              <select
                value={issueType}
                onChange={(e) => setIssueType(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl outline-none focus:border-violet-500 bg-white"
              >
                <option value="SUSPECTED_COUNTERFEIT">Suspected Counterfeit / Fake Medicine</option>
                <option value="PACKAGING_DEFECT">Packaging / Label Print Flaw</option>
                <option value="ADVERSE_REACTION">Unexpected Adverse Reaction / Side Effect</option>
                <option value="INEFFECTIVE">Lack of Therapeutic Effect</option>
                <option value="PHYSICAL_DEFECT">Discoloration, Crumbled Tablet, or Odor</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Description & Symptoms *
              </label>
              <textarea
                required
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what occurred, any packaging anomalies, pharmacy details, or symptoms experienced..."
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl outline-none focus:border-violet-500 resize-none"
              />
            </div>

            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !description.trim()}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold rounded-xl disabled:opacity-50 transition flex items-center space-x-1.5 shadow-md shadow-violet-600/20"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Submitting...</span>
                  </>
                ) : (
                  <>
                    <span>Submit Report</span>
                    <Send className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
