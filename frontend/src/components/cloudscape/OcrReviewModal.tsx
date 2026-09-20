import React, { useState, useEffect } from 'react';

export interface ExtractedMedicineFields {
  drug_name?: string;
  batch_no?: string;
  manufacturer?: string;
  mfg_date?: string;
  expiry_date?: string;
  ocr_confidence?: number;
  unreadable_fields?: string[];
}

interface OcrReviewModalProps {
  visible: boolean;
  initialFields: ExtractedMedicineFields;
  imageUrl?: string;
  onDismiss: () => void;
  onApproveAndVerify: (fields: ExtractedMedicineFields) => void;
}

export const OcrReviewModal: React.FC<OcrReviewModalProps> = ({
  visible,
  initialFields,
  imageUrl,
  onDismiss,
  onApproveAndVerify,
}) => {
  const [isEditing, setIsEditing] = useState(false);

  // Form states initialized dynamically from actual OCR output
  const [drugName, setDrugName] = useState('');
  const [batchNo, setBatchNo] = useState('');
  const [manufacturer, setManufacturer] = useState('');
  const [expiryDate, setExpiryDate] = useState('');

  useEffect(() => {
    if (visible) {
      setIsEditing(false);
      setDrugName(initialFields.drug_name || '');
      setBatchNo(initialFields.batch_no || '');
      setManufacturer(initialFields.manufacturer || '');
      setExpiryDate(initialFields.expiry_date || '');
    }
  }, [visible, initialFields]);

  if (!visible) return null;

  const confidenceValue = Math.round((initialFields.ocr_confidence ?? 0.9) * 100);

  const handleApprove = () => {
    onApproveAndVerify({
      drug_name: drugName.trim(),
      batch_no: batchNo.trim(),
      manufacturer: manufacturer.trim(),
      expiry_date: expiryDate.trim(),
      ocr_confidence: initialFields.ocr_confidence,
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col select-none">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-sky-600 text-[18px]">document_scanner</span>
            <span className="text-sm font-semibold text-slate-900">
              {isEditing ? 'Edit Medicine Fields' : 'OCR Extraction Review'}
            </span>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 flex flex-col gap-4 text-xs font-sans">
          {!isEditing ? (
            /* State 1: Review Panel */
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                <span>Model Confidence</span>
                <span className="text-emerald-700 font-semibold">{confidenceValue}% Precision</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-sky-600 h-full rounded-full" style={{ width: `${confidenceValue}%` }} />
              </div>

              <div className="grid grid-cols-2 gap-2 mt-1 font-mono">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Brand Name</span>
                  <span className="block text-slate-900 text-xs font-semibold mt-0.5">
                    {drugName || 'Not detected'}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Batch Code</span>
                  <span className="block text-sky-700 text-xs font-bold mt-0.5">
                    {batchNo || 'Not detected'}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Manufacturer</span>
                  <span className="block text-slate-900 text-xs mt-0.5">
                    {manufacturer || 'Not detected'}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Expiry Date</span>
                  <span className="block text-slate-900 text-xs mt-0.5">
                    {expiryDate || 'Not detected'}
                  </span>
                </div>
              </div>

              {imageUrl && (
                <div className="mt-1">
                  <span className="text-[11px] font-mono text-slate-400 block mb-1">Source Packaging Image:</span>
                  <div className="h-28 rounded-lg overflow-hidden border border-slate-200 bg-slate-100 flex items-center justify-center">
                    <img src={imageUrl} alt="Packaging Preview" className="h-full object-contain" />
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* State 2: Manual Edit Form */
            <div className="flex flex-col gap-3 font-sans">
              <div>
                <label className="text-[11px] font-medium text-slate-600 block mb-1">Brand Name / Formulation</label>
                <input
                  type="text"
                  value={drugName}
                  onChange={(e) => setDrugName(e.target.value)}
                  placeholder="e.g. Paracetamol 500mg"
                  className="w-full h-8 px-2.5 rounded bg-white text-slate-900 border border-slate-300 focus:outline-none focus:border-sky-600 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-medium text-slate-600 block mb-1">Batch Number</label>
                  <input
                    type="text"
                    value={batchNo}
                    onChange={(e) => setBatchNo(e.target.value)}
                    placeholder="e.g. B-1234"
                    className="w-full h-8 px-2.5 rounded bg-white text-slate-900 border border-slate-300 focus:outline-none focus:border-sky-600 text-xs font-mono uppercase"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-600 block mb-1">Expiry Date</label>
                  <input
                    type="text"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                    placeholder="MM/YYYY"
                    className="w-full h-8 px-2.5 rounded bg-white text-slate-900 border border-slate-300 focus:outline-none focus:border-sky-600 text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-medium text-slate-600 block mb-1">Manufacturer</label>
                <input
                  type="text"
                  value={manufacturer}
                  onChange={(e) => setManufacturer(e.target.value)}
                  placeholder="e.g. Cipla, Sun Pharma, etc."
                  className="w-full h-8 px-2.5 rounded bg-white text-slate-900 border border-slate-300 focus:outline-none focus:border-sky-600 text-xs"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-200 flex items-center justify-between bg-slate-50">
          <button
            type="button"
            onClick={() => setIsEditing(!isEditing)}
            className="text-xs text-sky-700 font-medium hover:underline cursor-pointer"
          >
            {isEditing ? 'Back to Summary' : 'Manual Edit'}
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onDismiss}
              className="px-3 py-1.5 rounded-lg text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleApprove}
              className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium transition cursor-pointer shadow-xs"
            >
              Verify Medicine
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
