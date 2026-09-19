import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check, Send, Sparkles } from 'lucide-react';
import { submitFeedback } from '../services/api';

interface FeedbackWidgetProps {
  sessionId: string;
}

export const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ sessionId }) => {
  const [voted, setVoted] = useState<boolean | null>(null);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleVote = async (isHelpful: boolean) => {
    setVoted(isHelpful);
    setIsSubmitting(true);
    await submitFeedback(sessionId, isHelpful);
    setIsSubmitting(false);
  };

  const handleSendComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (voted === null) return;
    setIsSubmitting(true);
    await submitFeedback(sessionId, voted, comment);
    setIsSubmitting(false);
    setSubmitted(true);
  };

  return (
    <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 sm:p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800">
            <Sparkles className="w-3.5 h-3.5 text-sky-600" />
            <span>Was this verification result clear and helpful?</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Positive user feedback gates model promotion into the MedVerify Knowledge Base (§6.4).
          </p>
        </div>

        {voted === null ? (
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => handleVote(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:text-emerald-700 hover:border-emerald-300 hover:bg-emerald-50 transition shadow-sm"
            >
              <ThumbsUp className="w-3.5 h-3.5 text-emerald-600" />
              <span>Helpful</span>
            </button>
            <button
              type="button"
              onClick={() => handleVote(false)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:text-red-700 hover:border-red-300 hover:bg-red-50 transition shadow-sm"
            >
              <ThumbsDown className="w-3.5 h-3.5 text-red-600" />
              <span>Not Helpful</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 bg-emerald-100/70 px-3 py-1.5 rounded-xl">
            <Check className="w-3.5 h-3.5" />
            <span>Feedback Recorded ({voted ? 'Helpful' : 'Needs Improvement'})</span>
          </div>
        )}
      </div>

      {voted !== null && !submitted && (
        <form onSubmit={handleSendComment} className="mt-3 pt-3 border-t border-slate-200/60 flex items-center space-x-2">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Add optional notes (e.g. tablet texture, pharmacy location)..."
            className="flex-1 bg-white border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-sky-500"
          />
          <button
            type="submit"
            disabled={isSubmitting || !comment.trim()}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold disabled:opacity-40 transition flex items-center space-x-1"
          >
            <span>Send</span>
            <Send className="w-3 h-3" />
          </button>
        </form>
      )}

      {submitted && (
        <p className="mt-2 text-[11px] text-emerald-700 font-medium">
          ✓ Additional notes submitted. Thank you for contributing to national medicine safety intelligence.
        </p>
      )}
    </div>
  );
};
