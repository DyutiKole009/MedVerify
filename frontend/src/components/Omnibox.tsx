import React, { useState, useRef } from 'react';
import { Search, Camera, X, ArrowRight, Loader2 } from 'lucide-react';

interface OmniboxProps {
  onSearch: (text: string, imageFile?: File) => void;
  isLoading: boolean;
}

export const Omnibox: React.FC<OmniboxProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
    }
  };

  const handleRemoveImage = () => {
    setImageFile(null);
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() && !imageFile) return;
    onSearch(query.trim(), imageFile || undefined);
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-slate-200 focus-within:border-sky-500 focus-within:ring-4 focus-within:ring-sky-500/10 transition-all p-2 sm:p-3">
          
          {/* Image Preview Thumbnail if attached */}
          {imagePreview && (
            <div className="mb-3 px-2 flex items-center space-x-3 bg-slate-50 p-2 rounded-xl border border-slate-200">
              <div className="relative w-14 h-14 rounded-lg overflow-hidden border border-slate-300 flex-shrink-0 bg-slate-200">
                <img src={imagePreview} alt="Attached Packaging" className="w-full h-full object-cover" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-800 truncate">
                  {imageFile?.name || 'packaging_photo.jpg'}
                </p>
                <p className="text-[11px] text-slate-500">
                  Ready for AI Optical Extraction & Verification
                </p>
              </div>
              <button
                type="button"
                onClick={handleRemoveImage}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition"
                title="Remove photo"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="flex items-center space-x-2">
            <div className="pl-2 text-slate-400">
              <Search className="w-5 h-5" />
            </div>

            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter batch number (e.g. B-9021), medicine name, or describe an issue..."
              className="flex-1 bg-transparent border-none outline-none text-slate-900 placeholder-slate-400 text-sm sm:text-base px-2 py-1.5"
              disabled={isLoading}
            />

            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageChange}
              accept="image/*"
              className="hidden"
            />

            {/* Photo upload trigger */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className={`p-2.5 rounded-xl border transition flex items-center space-x-1.5 text-xs font-medium ${
                imageFile
                  ? 'bg-sky-50 text-sky-600 border-sky-200'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:text-slate-900'
              }`}
              title="Upload medicine packaging photo"
              disabled={isLoading}
            >
              <Camera className="w-4 h-4" />
              <span className="hidden sm:inline">{imageFile ? 'Photo Attached' : 'Attach Photo'}</span>
            </button>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading || (!query.trim() && !imageFile)}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-medium text-sm shadow-md shadow-sky-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center space-x-1.5"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="hidden sm:inline">Verifying...</span>
                </>
              ) : (
                <>
                  <span>Verify</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </form>

    </div>
  );
};
