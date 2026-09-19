import React from 'react';
import { AlertTriangle, Sparkles, ArrowRight, CheckCircle2, ShieldAlert } from 'lucide-react';
import { useTrip } from '../hooks/useTrip';

export default function DisruptionAlertBanner() {
  const { activeTrip, setCurrentPage, resolveAlert } = useTrip();

  const unresolvedAlerts = (activeTrip?.activeAlerts || []).filter((a) => !a.resolved);

  if (!unresolvedAlerts.length) return null;

  const topAlert = unresolvedAlerts[0];

  return (
    <aside
      aria-label="Disruption Alert Banner"
      className="relative bg-gradient-to-r from-amber-950/60 via-slate-900/95 to-amber-950/60 border border-amber-500/40 rounded-2xl p-4 sm:p-5 mb-8 shadow-xl shadow-amber-950/30 backdrop-blur-md overflow-hidden animate-in fade-in slide-in-from-top-3 duration-300"
    >
      {/* Decorative ambient amber glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start space-x-3.5">
          <div className="p-2.5 bg-amber-500/15 border border-amber-500/30 rounded-xl text-amber-400 shrink-0 mt-0.5 shadow-sm shadow-amber-500/20">
            <AlertTriangle className="w-5 h-5 animate-pulse" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                Live Disruption Detected
              </span>
              <h4 className="text-sm font-bold text-white tracking-tight">
                {topAlert.title}
              </h4>
              <span className="text-xs text-slate-400 font-mono">
                • {topAlert.timestamp}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              {topAlert.description}
            </p>
            {topAlert.aiResolution && (
              <div className="flex items-center space-x-2 mt-2.5 text-xs font-medium text-cyan-300 bg-cyan-950/50 px-3 py-1.5 rounded-xl border border-cyan-500/30 shadow-inner">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0" aria-hidden="true" />
                <span>
                  <strong className="text-cyan-200">AI Dynamic Resolution:</strong> {topAlert.aiResolution}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 self-end md:self-center shrink-0 w-full sm:w-auto justify-end">
          <button
            type="button"
            onClick={() => resolveAlert(topAlert.id)}
            className="px-3 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/90 hover:bg-slate-700/90 rounded-xl border border-slate-700 transition flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
            <span>Acknowledge</span>
          </button>
          <button
            type="button"
            onClick={() => setCurrentPage('disruptions')}
            className="px-4 py-2 text-xs font-bold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-300 hover:from-amber-300 hover:to-amber-200 rounded-xl shadow-md shadow-amber-500/20 transition flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300"
          >
            <span>Review Replan</span>
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  );
}
