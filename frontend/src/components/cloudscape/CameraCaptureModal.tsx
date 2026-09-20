import React, { useRef, useState, useEffect } from 'react';

interface CameraCaptureModalProps {
  visible: boolean;
  onDismiss: () => void;
  onCapture: (capturedFile: File) => void;
}

export const CameraCaptureModal: React.FC<CameraCaptureModalProps> = ({
  visible,
  onDismiss,
  onCapture,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);


  useEffect(() => {
    let active = true;

    if (visible) {
      navigator.mediaDevices
        ?.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        })
        .then((stream) => {
          if (!active) {
            stream.getTracks().forEach((track) => track.stop());
            return;
          }
          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.play().catch(() => {});
          }
          setCameraActive(true);
        })
        .catch((err) => {
          console.warn('Camera access error or unsupported:', err);
          setCameraActive(false);
        });
    } else {
      stopCamera();
    }

    return () => {
      active = false;
      stopCamera();
    };
  }, [visible]);

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const handleCapture = () => {
    if (videoRef.current && cameraActive) {
      const video = videoRef.current;
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (blob) => {
            if (!blob) return;
            const file = new File([blob], `packaging-scan-${Date.now()}.jpg`, {
              type: 'image/jpeg',
            });
            stopCamera();
            onCapture(file);
          },
          'image/jpeg',
          0.92
        );
        return;
      }
    }

    // If live camera is not available or mocked, fetch sample scan or generate test blob
    const sampleCanvas = document.createElement('canvas');
    sampleCanvas.width = 640;
    sampleCanvas.height = 480;
    const ctx = sampleCanvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, 640, 480);
      ctx.fillStyle = '#38bdf8';
      ctx.font = '20px monospace';
      ctx.fillText('CIPRODAC 500 - BATCH CP-8821', 40, 240);
      ctx.fillText('EXP 12/2025 - CDSCO LAB SAMPLE', 40, 280);
      sampleCanvas.toBlob((blob) => {
        if (!blob) return;
        const file = new File([blob], 'ciprodac_foil_scan_01.jpg', {
          type: 'image/jpeg',
        });
        stopCamera();
        onCapture(file);
      }, 'image/jpeg');
    }
  };

  const handleClose = () => {
    stopCamera();
    onDismiss();
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-4 select-none">
      <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px] text-emerald-600">videocam</span>
            <span>Live Macro Scanner</span>
          </span>
          <button
            type="button"
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-700 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Viewfinder Frame */}
        <div className="relative w-full h-72 bg-black flex items-center justify-center overflow-hidden">
          {cameraActive ? (
            <video
              ref={videoRef}
              playsInline
              muted
              className="w-full h-full object-cover"
            />
          ) : (
            <img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBnf6iphFEy6nEc5qPbErJ7yigtSLwOZUdBAjeJUbodl_9n_EaO-lGpvgzDtL-SLFAk-lW5ErndjQm2xFUx6Yk15YT9gKc539gDo8_RbPoZRZT8GdrLM1LGXOtoIuo9i-0UzqEMs6gcer_epcNo9OQrxxWdVsgrFnnOSAdyLRjm-tm7iFbHAY2RBUYYKkSNOrOxZCxjAZS8uSDc3-UNU6jzu6AhkJXDYgT_IHtPR5k"
              alt="Macro Scanner Feed"
              className="w-full h-full object-cover opacity-80"
            />
          )}

          {/* Reticle Overlay */}
          <div className="absolute inset-6 border border-dashed border-sky-400/80 rounded-lg flex flex-col justify-between p-2 pointer-events-none">
            <span className="text-[9px] font-mono text-sky-400 bg-black/70 px-1.5 py-0.5 rounded w-fit font-semibold">
              FOCUS: LOCKED
            </span>
            <span className="text-[10px] font-mono text-white/90 text-center bg-black/70 py-1 rounded">
              Align blister packaging details & batch number
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="p-3 border-t border-slate-200 flex items-center justify-between bg-slate-50 px-4">
          <button
            type="button"
            onClick={handleClose}
            className="text-xs text-slate-500 hover:text-slate-800 cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleCapture}
            className="px-5 py-2 rounded-full bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs flex items-center gap-1.5 shadow-md transition cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">camera</span>
            <span>Capture Packaging</span>
          </button>

          <div className="w-10" />
        </div>
      </div>
    </div>
  );
};
