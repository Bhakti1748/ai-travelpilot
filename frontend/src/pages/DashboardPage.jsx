import React from 'react';

import {
  MapPin,
  Calendar,
  DollarSign,
  TrendingDown,
  Clock,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  ChevronRight,
  Train,
  CheckCircle2,
  Users,
  Compass,
  RefreshCw,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';
import DisruptionAlertBanner from '../components/DisruptionAlertBanner';

export default function DashboardPage() {
  const {
    activeTrip,
    setCurrentPage,
    resolveAlert,
    refreshTripData,
    isLoading,
  } = useTrip();

  const curr = activeTrip?.currency || 'INR';
  const totalBudget = activeTrip?.budget || 0;
  const spending = activeTrip?.spending || 0;

  const remainingBudget = Math.max(
    0,
    totalBudget - spending
  );

  const budgetPercentUsed =
    totalBudget > 0
      ? Math.min(
          100,
          Math.round((spending / totalBudget) * 100)
        )
      : 0;

  const itinerary = activeTrip?.itinerary || [];
  const todayPlan = itinerary[0] || null;
  const tomorrowPlan = itinerary[1] || null;

  const unresolvedAlerts = (
    activeTrip?.activeAlerts || []
  ).filter((a) => !a.resolved);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center animate-in fade-in duration-300">
        <div className="inline-flex p-4 rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl mb-4">
          <RefreshCw
            className="w-8 h-8 text-cyan-400 animate-spin"
            aria-hidden="true"
          />
        </div>

        <h2 className="text-xl font-bold text-white">
          Synchronizing Trip State...
        </h2>

        <p className="text-xs text-slate-400 mt-1">
          Loading live schedule and financial metrics from SQLite database.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* Disruption Alert Banner */}
      <DisruptionAlertBanner />

      {/* Hero Header Banner */}
      <div className="relative rounded-3xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/50 border border-slate-800/90 p-6 sm:p-8 mb-8 overflow-hidden shadow-2xl">

        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">

          <div>
            <div className="flex items-center space-x-2 text-xs font-semibold text-cyan-400 mb-2">

              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>

              <span className="tracking-wider uppercase text-[11px] font-mono font-bold">
                Active Journey Dashboard
              </span>
            </div>

            <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              {activeTrip?.destination || 'No trip selected'}
            </h1>

            <div className="flex flex-wrap items-center gap-4 mt-3 text-xs sm:text-sm text-slate-300">

              <div className="flex items-center space-x-1.5">
                <Calendar
                  className="w-4 h-4 text-cyan-400"
                  aria-hidden="true"
                />

                <span>
                  {activeTrip?.startDate || 'Start date not set'}
                  {' → '}
                  {activeTrip?.endDate || 'End date not set'}
                </span>
              </div>

              <span className="text-slate-600 hidden sm:inline">
                •
              </span>

              <div className="flex items-center space-x-1.5">
                <Users
                  className="w-4 h-4 text-indigo-400"
                  aria-hidden="true"
                />

                <span>
                  {activeTrip?.travelers || 0} Travelers
                </span>
              </div>

              <span className="text-slate-600 hidden sm:inline">
                •
              </span>

              <div className="flex items-center space-x-1.5">
                <Compass
                  className="w-4 h-4 text-purple-400"
                  aria-hidden="true"
                />

                <span>
                  {activeTrip?.travelStyle || 'Not specified'} Style
                </span>
              </div>

              <span className="text-slate-600 hidden sm:inline">
                •
              </span>

              <button
                type="button"
                onClick={() => refreshTripData(activeTrip?.id)}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 cursor-pointer font-medium"
                title="Refresh from backend"
                aria-label="Synchronize trip data"
              >
                <RefreshCw
                  className="w-3.5 h-3.5"
                  aria-hidden="true"
                />

                <span>
                  Sync with Backend
                </span>
              </button>
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap items-center gap-3">

            <button
              type="button"
              onClick={() => setCurrentPage('itinerary')}
              className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition shadow-md shadow-cyan-500/20 flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              <span>
                Full Itinerary
              </span>

              <ArrowRight
                className="w-3.5 h-3.5"
                aria-hidden="true"
              />
            </button>

            <button
              type="button"
              onClick={() => setCurrentPage('disruptions')}
              className="px-4 py-2.5 rounded-xl text-xs font-bold text-amber-300 hover:text-amber-200 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 transition flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300"
            >
              <AlertTriangle
                className="w-3.5 h-3.5"
                aria-hidden="true"
              />

              <span>
                Simulate Disruption
              </span>
            </button>

            <button
              type="button"
              onClick={() => setCurrentPage('assistant')}
              className="px-4 py-2.5 rounded-xl text-xs font-bold text-indigo-300 hover:text-indigo-200 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 transition flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
            >
              <Sparkles
                className="w-3.5 h-3.5"
                aria-hidden="true"
              />

              <span>
                Ask Co-pilot
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Key Metric Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">

        {/* Total Budget */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider font-mono">
              Total Budget
            </span>

            <DollarSign
              className="w-4 h-4 text-cyan-400"
              aria-hidden="true"
            />
          </div>

          <div className="text-2xl font-bold text-white tracking-tight">
            {curr} {totalBudget.toLocaleString()}
          </div>

          <p className="text-[11px] text-slate-400 mt-1">
            Allocated across {itinerary.length} days
          </p>
        </div>

        {/* Current Spending */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider font-mono">
              Committed Spend
            </span>

            <TrendingDown
              className="w-4 h-4 text-indigo-400"
              aria-hidden="true"
            />
          </div>

          <div className="text-2xl font-bold text-white tracking-tight">
            {curr} {spending.toLocaleString()}
          </div>

          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-cyan-400 to-indigo-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${budgetPercentUsed}%` }}
            />
          </div>

          <span className="text-[10px] text-slate-400 mt-1 block font-medium">
            {budgetPercentUsed}% of total budget utilized
          </span>
        </div>

        {/* Remaining Budget */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider font-mono">
              Remaining Buffer
            </span>

            <CheckCircle2
              className="w-4 h-4 text-emerald-400"
              aria-hidden="true"
            />
          </div>

          <div className="text-2xl font-bold text-emerald-400 tracking-tight">
            {curr} {remainingBudget.toLocaleString()}
          </div>

          <p className="text-[11px] text-slate-400 mt-1">
            ~{curr}{' '}
            {Math.round(
              remainingBudget / Math.max(1, itinerary.length)
            ).toLocaleString()}{' '}
            / day reserve
          </p>
        </div>

        {/* Real-time Status */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider font-mono">
              Agent Health
            </span>

            <ShieldAlert
              className="w-4 h-4 text-amber-400"
              aria-hidden="true"
            />
          </div>

          <div className="flex items-center space-x-2">
            <span
              className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"
              aria-hidden="true"
            />

            <span className="text-base font-bold text-white">
              {unresolvedAlerts.length > 0
                ? `${unresolvedAlerts.length} Action Needed`
                : 'Synchronized'}
            </span>
          </div>

          <p className="text-[11px] text-slate-400 mt-1">
            Dynamic replanning engine standing by
          </p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left 2 Columns */}
        <div className="lg:col-span-2 space-y-8">

          {/* Today's Schedule */}
          <div className="p-6 sm:p-7 rounded-3xl bg-slate-900/60 border border-slate-800 shadow-xl">

            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">

              <div>
                <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider">
                  Live Agenda
                </span>

                <h2 className="text-lg font-bold text-white tracking-tight">
                  Today's Schedule:{' '}
                  {todayPlan?.title || 'No schedule generated'}
                </h2>
              </div>

              <button
                type="button"
                onClick={() => setCurrentPage('itinerary')}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 cursor-pointer"
              >
                <span>
                  View Timeline
                </span>

                <ChevronRight
                  className="w-4 h-4"
                  aria-hidden="true"
                />
              </button>
            </div>

            {(!todayPlan ||
              todayPlan.activities.length === 0) ? (
              <div className="p-10 rounded-2xl bg-slate-950/60 border border-slate-800 text-center text-xs text-slate-400">

                <p className="text-slate-300 font-medium">
                  No activities scheduled for today.
                </p>

                <button
                  type="button"
                  onClick={() => setCurrentPage('create')}
                  className="mt-3 px-4 py-2 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded-xl hover:bg-cyan-500/20 transition cursor-pointer font-semibold"
                >
                  Generate Adaptive Schedule
                </button>
              </div>
            ) : (
              <div className="space-y-4">

                {todayPlan.activities.map((act) => (
                  <div
                    key={act.id}
                    className="p-4 sm:p-5 rounded-2xl bg-slate-950/80 border border-slate-800/90 hover:border-slate-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md"
                  >
                    <div className="flex items-start space-x-3.5">

                      <div className="px-2.5 py-1 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono font-bold text-cyan-400 shrink-0 mt-0.5 shadow-inner">
                        {act.time}
                      </div>

                      <div>
                        <div className="flex items-center space-x-2 flex-wrap">

                          <h4 className="text-sm font-bold text-white">
                            {act.title}
                          </h4>

                          <span
                            className={`px-2 py-0.5 text-[10px] font-bold rounded-full border uppercase tracking-wider ${
                              act.status === 'Confirmed'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : act.status === 'Delayed'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse'
                                : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                            }`}
                          >
                            {act.status}
                          </span>
                        </div>

                        <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1.5 flex-wrap">

                          <span className="flex items-center">
                            <MapPin className="w-3.5 h-3.5 mr-1 text-slate-500" />
                            {act.location}
                          </span>

                          <span>•</span>

                          <span className="flex items-center">
                            <Clock className="w-3.5 h-3.5 mr-1 text-slate-500" />
                            {act.duration}
                          </span>

                          {act.cost > 0 && (
                            <>
                              <span>•</span>

                              <span className="text-emerald-400 font-semibold">
                                {curr} {act.cost.toLocaleString()}
                              </span>
                            </>
                          )}
                        </div>

                        {act.notes && (
                          <p className="text-[11px] text-slate-400 mt-2 bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
                            {act.notes}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-slate-300 shrink-0 self-end sm:self-center flex items-center space-x-1.5 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
                      <Train className="w-3.5 h-3.5 text-cyan-400" />
                      <span>
                        {act.transportation}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tomorrow's Preview */}
          {tomorrowPlan &&
            tomorrowPlan.activities.length > 0 && (
              <div className="p-6 sm:p-7 rounded-3xl bg-slate-900/60 border border-slate-800 shadow-xl">

                <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">

                  <div>
                    <span className="text-[10px] font-mono font-bold text-indigo-400 uppercase tracking-wider">
                      Next Up
                    </span>

                    <h2 className="text-base font-bold text-white">
                      Tomorrow Preview: {tomorrowPlan.title}
                    </h2>
                  </div>

                  <span className="text-xs text-slate-400 font-mono">
                    {tomorrowPlan.activities.length} planned stops
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                  {tomorrowPlan.activities
                    .slice(0, 4)
                    .map((act) => (
                      <div
                        key={act.id}
                        className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-indigo-500/30 transition shadow-sm"
                      >
                        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">

                          <span className="font-mono text-cyan-400 font-bold">
                            {act.time}
                          </span>

                          <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-900 text-slate-300">
                            {act.category || 'Activity'}
                          </span>
                        </div>

                        <div className="text-xs font-semibold text-white truncate">
                          {act.title}
                        </div>

                        <div className="text-[11px] text-slate-400 truncate mt-0.5">
                          {act.location}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
        </div>

        {/* Right Column */}
        <div className="space-y-6">

          {/* AI Insights */}
          <div className="p-6 sm:p-7 rounded-3xl bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border border-cyan-500/25 shadow-2xl relative overflow-hidden">

            <div className="flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-4 font-mono">
              <Sparkles className="w-4 h-4" />
              <span>
                AI Co-Pilot Insights
              </span>
            </div>

            <div className="space-y-3">
              {(activeTrip?.aiInsights || []).map(
                (insight, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 text-xs text-slate-300 leading-relaxed flex items-start space-x-2.5 shadow-sm"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0 mt-1.5" />
                    <span>
                      {insight}
                    </span>
                  </div>
                )
              )}
            </div>

            {(!activeTrip?.aiInsights ||
              activeTrip.aiInsights.length === 0) && (
              <p className="text-xs text-slate-500">
                AI insights will appear after your itinerary is generated.
              </p>
            )}

            <button
              type="button"
              onClick={() => setCurrentPage('assistant')}
              className="mt-5 w-full py-3 px-4 rounded-xl text-xs font-bold text-slate-900 bg-cyan-400 hover:bg-cyan-300 transition shadow-lg shadow-cyan-500/20 flex items-center justify-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              <span>
                Consult AI Assistant
              </span>

              <ArrowRight
                className="w-3.5 h-3.5"
                aria-hidden="true"
              />
            </button>
          </div>

          {/* Active Alerts */}
          <div className="p-6 sm:p-7 rounded-3xl bg-slate-900/60 border border-slate-800 shadow-xl">

            <div className="flex items-center justify-between mb-4">

              <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-1.5 font-mono">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>
                  Active Disruptions ({unresolvedAlerts.length})
                </span>
              </span>

              <button
                type="button"
                onClick={() => setCurrentPage('disruptions')}
                className="text-xs text-slate-400 hover:text-white cursor-pointer font-medium"
              >
                Manage
              </button>
            </div>

            {unresolvedAlerts.length === 0 ? (
              <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 text-center text-xs text-slate-400">

                <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-1.5" />

                No unhandled travel disruptions.
              </div>
            ) : (
              <div className="space-y-3">

                {unresolvedAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="p-4 rounded-2xl bg-slate-950 border border-amber-500/30 text-xs shadow-md"
                  >
                    <div className="flex items-center justify-between font-bold text-white">

                      <span>
                        {alert.title}
                      </span>

                      <button
                        type="button"
                        onClick={() => resolveAlert(alert.id)}
                        className="text-[11px] text-cyan-400 hover:underline cursor-pointer font-medium"
                      >
                        Resolve
                      </button>
                    </div>

                    <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                      {alert.description}
                    </p>

                    {alert.aiResolution && (
                      <div className="mt-2 text-[11px] text-cyan-300 bg-cyan-950/40 p-2 rounded-xl border border-cyan-500/20">
                        {alert.aiResolution}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}