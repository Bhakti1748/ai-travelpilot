import React from 'react';
import { CheckCircle2, Loader2, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';

const PLANNING_STEPS = [
  { id: 'preferences', label: 'Understanding preferences' },
  { id: 'activities', label: 'Finding activities' },
  { id: 'timings', label: 'Checking timings' },
  { id: 'locations', label: 'Optimizing locations' },
  { id: 'budget', label: 'Checking budget' },
  { id: 'validation', label: 'Validating itinerary' },
  { id: 'ready', label: 'Trip ready' },
];

export default function AIPlanningProgressModal({
  isOpen,
  currentStepIndex,
  destination,
  error,
  onRetry,
  onClose,
}) {
  if (!isOpen) return null;

  const totalSteps = PLANNING_STEPS.length;
  const progressPercent = Math.min(100, Math.round(((currentStepIndex + 1) / totalSteps) * 100));

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-20 -right-20 w-60 h-60 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="relative z-10 text-center mb-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5 animate-spin" />
            <span>AI Planning Pipeline</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Synthesizing Journey
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Grounded in Paris real-world catalog & deterministic constraint solvers for{' '}
            <span className="text-cyan-300 font-semibold">{destination || 'your destination'}</span>.
          </p>
        </div>

        {/* Progress Bar */}
        <div className="relative z-10 mb-6">
          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5">
            <span>Progress</span>
            <span className="text-cyan-400 font-bold">{progressPercent}%</span>
          </div>
          <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden p-0.5 border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 via-teal-400 to-indigo-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Step List */}
        <div className="relative z-10 space-y-3 mb-6 bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
          {PLANNING_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex && !error;
            const isPending = idx > currentStepIndex;

            return (
              <div
                key={step.id}
                className={`flex items-center space-x-3 p-2 rounded-xl transition-all ${
                  isCurrent
                    ? 'bg-slate-900 border border-cyan-500/30 shadow-md shadow-cyan-500/10'
                    : isCompleted
                    ? 'text-slate-300'
                    : 'text-slate-600'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 stroke-[2.5]" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-800 flex items-center justify-center shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-700" />
                  </div>
                )}

                <span
                  className={`text-xs font-medium ${
                    isCurrent
                      ? 'text-cyan-300 font-semibold'
                      : isCompleted
                      ? 'text-slate-200'
                      : 'text-slate-500'
                  }`}
                >
                  {isCompleted ? `✓ ${step.label}` : step.label}
                </span>

                {isCurrent && (
                  <span className="text-[10px] text-cyan-400 font-mono ml-auto animate-pulse">
                    Processing...
                  </span>
                )}
                {isCompleted && (
                  <span className="text-[10px] text-emerald-400 font-mono ml-auto">
                    Done
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Error Notification */}
        {error && (
          <div className="relative z-10 mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-start space-x-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block text-rose-200">Planning Failed</span>
              <p className="mt-0.5 leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        {/* Action Controls */}
        <div className="relative z-10 flex items-center justify-end space-x-3">
          {error && (
            <>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onRetry}
                className="px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-xl transition flex items-center space-x-1.5 shadow-md"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Generation</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
