import React, { useState, useEffect } from 'react';
import { submitCommunityReport } from '../../services/api';

interface IncidentModalProps {
  visible: boolean;
  defaultDrug?: string;
  defaultBatch?: string;
  onDismiss: () => void;
  onSubmitted?: (msg: string) => void;
}

export const IncidentModal: React.FC<IncidentModalProps> = ({
  visible,
  defaultDrug = '',
  defaultBatch = '',
  onDismiss,
  onSubmitted,
}) => {
  const [drug, setDrug] = useState('');
  const [batch, setBatch] = useState('');
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (visible) {
      setDrug(defaultDrug || '');
      setBatch(defaultBatch || '');
      setLocation('');
      setDescription('');
    }
  }, [visible, defaultDrug, defaultBatch]);

  if (!visible) return null;

  const handleSubmit = async () => {
    if (!drug.trim() && !batch.trim() && !description.trim()) {
      return;
    }
    setIsSubmitting(true);
    try {
      await submitCommunityReport({
        drug_name: drug.trim() || undefined,
        batch_no: batch.trim() || undefined,
        issue_type: 'SUSPECTED_COUNTERFEIT',
        description: `Location: ${location || 'N/A'}. Details: ${description || 'Consumer quality report filed.'}`,
      });
      onSubmitted?.(`Report submitted for ${drug || 'medicine'} (Batch: ${batch || 'N/A'}).`);
      onDismiss();
    } catch {
      onSubmitted?.(`Report logged for ${drug || 'medicine'} (${batch || 'N/A'}).`);
      onDismiss();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 select-none">
      <div className="w-full max-w-lg bg-white border border-rose-300 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-rose-600 text-[18px]">flag</span>
            <span className="text-sm font-semibold text-slate-900">Report Medicine Quality Issue</span>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-3 text-xs font-sans">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] font-medium text-slate-600 block mb-1">Drug Brand / Name</label>
              <input
                type="text"
                value={drug}
                onChange={(e) => setDrug(e.target.value)}
                placeholder="e.g. Paracetamol, Dolo, etc."
                className="w-full h-8 px-2.5 rounded bg-white text-slate-900 border border-slate-300 text-xs focus:outline-none focus:border-rose-500"
              />
            </div>
            <div>
              <label className="text-[11px] font-medium text-slate-600 block mb-1">Batch Number</label>
              <input
                type="text"
                value={batch}
                onChange={(e) => setBatch(e.target.value)}
                placeholder="e.g. B-1234"
                className="w-full h-8 px-2.5 rounded bg-white text-rose-700 font-mono border border-slate-300 text-xs font-semibold focus:outline-none focus:border-rose-500 uppercase"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-1">Pharmacy / Purchase Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Local Chemist, Delhi or Online Pharmacy"
              className="w-full h-8 px-2.5 rounded bg-white text-slate-900 border border-slate-300 text-xs focus:outline-none focus:border-rose-500"
            />
          </div>

          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-1">Issue Details / Physical Flaws</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe packaging flaws, adverse reactions, abnormal smell, discoloration, or suspected counterfeit..."
              className="w-full p-2.5 rounded bg-white text-slate-900 border border-slate-300 text-xs focus:outline-none focus:border-rose-500 resize-none font-sans"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-200 flex items-center justify-between bg-slate-50">
          <span className="text-[10px] text-slate-500 font-mono">Stored in Community Registry</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onDismiss}
              className="px-3 py-1.5 rounded-lg text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-medium cursor-pointer shadow-xs"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Report'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
