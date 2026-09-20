import React, { useRef, useState } from 'react';
import { CameraCaptureModal } from './CameraCaptureModal';

interface ChatOmniboxProps {
  onSendMessage: (text: string, attachedFile?: File) => void;
  isLoading: boolean;
  onOpenOcrModal?: () => void;
  onOpenRecallsDrawer?: () => void;
  onShowToast?: (msg: string) => void;
}

export const ChatOmnibox: React.FC<ChatOmniboxProps> = ({
  onSendMessage,
  isLoading,
  onOpenRecallsDrawer,
  onShowToast,
}) => {
  const [text, setText] = useState('');
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [cameraModalVisible, setCameraModalVisible] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const recognitionRef = useRef<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile(file);
      onShowToast?.(`Attached ${file.name}`);
    }
  };

  const handleCameraCapture = (file: File) => {
    setAttachedFile(file);
    setCameraModalVisible(false);
    onShowToast?.(`Photo captured (${(file.size / 1024).toFixed(1)} KB)`);
  };

  const handleRemoveAttachment = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed && !attachedFile) return;
    if (isLoading) return;

    onSendMessage(trimmed, attachedFile || undefined);
    setText('');
    handleRemoveAttachment();
  };

  const handleKeydown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (prompt: string) => {
    setText(prompt);
    textareaRef.current?.focus();
  };

  // Real Web Speech API voice dictation
  const toggleVoice = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      onShowToast?.('Voice dictation is not supported by your browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      onShowToast?.('Voice dictation ended.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-IN';

      recognition.onstart = () => {
        setIsListening(true);
        onShowToast?.('Listening... Speak medicine name or batch number.');
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
        onShowToast?.(`Recognized: "${transcript}"`);
      };

      recognition.onerror = () => {
        setIsListening(false);
        onShowToast?.('Voice recognition failed or microphone not accessible.');
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setIsListening(false);
      onShowToast?.('Microphone permission denied.');
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 shrink-0 select-none">
      {/* Quick Action Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 no-scrollbar text-xs">
        <button
          type="button"
          onClick={() => handleChipClick('Verify batch: ')}
          className="px-2.5 py-1 rounded-full bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 whitespace-nowrap transition-colors shadow-2xs font-medium cursor-pointer"
        >
          Verify Batch Number
        </button>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="px-2.5 py-1 rounded-full bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 whitespace-nowrap transition-colors shadow-2xs font-medium cursor-pointer"
        >
          Upload Packaging Photo
        </button>

        <button
          type="button"
          onClick={() => onOpenRecallsDrawer?.()}
          className="px-2.5 py-1 rounded-full bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 whitespace-nowrap transition-colors shadow-2xs font-medium cursor-pointer"
        >
          View CDSCO Recalls
        </button>
      </div>

      {/* Input Shell */}
      <div className="rounded-2xl bg-white border border-slate-300 focus-within:border-sky-600 focus-within:ring-2 focus-within:ring-sky-100 transition-all p-2.5 shadow-sm">
        {/* Staged Attachment Chip */}
        {attachedFile && (
          <div className="flex items-center justify-between px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 mb-1.5 w-fit">
            <span className="material-symbols-outlined text-[16px] text-sky-600 mr-1.5">image</span>
            <span className="truncate max-w-[220px]">{attachedFile.name}</span>
            <button
              type="button"
              onClick={handleRemoveAttachment}
              className="ml-2 text-slate-400 hover:text-slate-700 cursor-pointer"
              title="Remove attachment"
            >
              <span className="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeydown}
          rows={2}
          placeholder="Ask about a medicine, enter a batch number, or upload packaging..."
          className="w-full bg-transparent resize-none text-[14px] text-slate-900 placeholder-slate-400 focus:outline-none px-2 py-1 leading-normal font-sans"
        />

        {/* Bottom Bar Controls */}
        <div className="flex items-center justify-between pt-1 border-t border-slate-100 px-1">
          <div className="flex items-center gap-1">
            {/* Hidden native file input */}
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              onChange={handleFileChange}
              className="hidden"
            />

            {/* Attach File Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-1.5 rounded-lg text-slate-400 hover:text-sky-700 hover:bg-slate-100 transition-colors cursor-pointer"
              title="Attach packaging photo"
            >
              <span className="material-symbols-outlined text-[18px]">attach_file</span>
            </button>

            {/* Camera Button */}
            <button
              type="button"
              onClick={() => setCameraModalVisible(true)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-sky-700 hover:bg-slate-100 transition-colors cursor-pointer"
              title="Open camera scanner"
            >
              <span className="material-symbols-outlined text-[18px]">photo_camera</span>
            </button>

            {/* Voice Dictation Button */}
            <button
              type="button"
              onClick={toggleVoice}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                isListening ? 'text-rose-500 bg-rose-50 animate-pulse' : 'text-slate-400 hover:text-sky-700 hover:bg-slate-100'
              }`}
              title={isListening ? 'Listening...' : 'Voice input'}
            >
              <span className="material-symbols-outlined text-[18px]">
                {isListening ? 'settings_voice' : 'mic'}
              </span>
            </button>
          </div>

          {/* Primary Verify Button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || (!text.trim() && !attachedFile)}
            className="h-8 px-3.5 rounded-lg bg-sky-600 hover:bg-sky-700 disabled:opacity-40 disabled:hover:bg-sky-600 text-white font-medium text-xs flex items-center gap-1.5 transition-all shadow-xs active:scale-95 cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Verifying...</span>
              </>
            ) : (
              <>
                <span>Verify</span>
                <span className="material-symbols-outlined text-[16px]">arrow_upward</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Footer Caption */}
      <p className="text-center font-mono text-[10px] text-slate-400 mt-2 font-medium">
        MedVerify National Medicine Safety Gateway • Consumer Verification Portal
      </p>

      {/* Camera Capture Modal */}
      <CameraCaptureModal
        visible={cameraModalVisible}
        onDismiss={() => setCameraModalVisible(false)}
        onCapture={handleCameraCapture}
      />
    </div>
  );
};
