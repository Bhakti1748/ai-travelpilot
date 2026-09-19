import React, { useMemo, useState } from 'react';

import {
  AlertTriangle,
  Play,
  Sparkles,
  Zap,
  CheckCircle2,
  ClockAlert,
  CalendarX,
  TrendingDown,
  Wand2,
  RefreshCw,
  ShieldCheck,
  MapPin,
  Clock,
  Check,
  Route,
  Wallet,
  Navigation,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';
import DisruptionAlertBanner from '../components/DisruptionAlertBanner';

/* ========================================================================== */
/* DISRUPTION PRESETS                                                         */
/* ========================================================================== */

const DISRUPTION_PRESETS = [
  {
    id: 'activity-cancelled',
    disruption_type: 'activity_cancelled',
    title: 'Scheduled Activity Cancelled',
    label: 'Activity Cancelled',
    icon: 'CalendarX',
    severity: 'critical',
    description:
      'The scheduled activity has suddenly been cancelled or the venue has temporarily closed.',
    defaultImpact:
      'The affected activity must be removed and a suitable replacement should be found.',
    defaultAiAction:
      'Search available activities near the affected location and rebuild the schedule.',
  },
  {
    id: 'transport-delay',
    disruption_type: 'transportation_delayed',
    title: 'Transportation Delay',
    delay_minutes: 45,
    label: 'Transportation Delayed (+45 mins)',
    icon: 'ClockAlert',
    severity: 'warning',
    description:
      'A transportation disruption causes an unexpected 45-minute delay.',
    defaultImpact:
      'Downstream activities may overlap or become difficult to reach on time.',
    defaultAiAction:
      'Shift the affected schedule and recalculate travel-time constraints.',
  },
  {
    id: 'budget-reduced',
    disruption_type: 'budget_reduced',
    label: 'Travel Budget Reduced',
    icon: 'TrendingDown',
    severity: 'warning',
    description:
      'The traveler has less money available for the remaining journey.',
    defaultImpact:
      'Higher-cost activities may need to be replaced with lower-cost alternatives.',
    defaultAiAction:
      'Recalculate the remaining budget and find lower-cost activities.',
  },
  {
    id: 'interests-changed',
    disruption_type: 'user_interests_changed',
    label: 'Traveler Interests Changed',
    icon: 'Sparkles',
    severity: 'info',
    description:
      'The traveler has changed their interests and wants the remaining itinerary adapted.',
    defaultImpact:
      'Existing activities may no longer match the traveler preferences.',
    defaultAiAction:
      'Re-rank available activities using the updated interests.',
  },
];

/* ========================================================================== */
/* HELPERS                                                                    */
/* ========================================================================== */

function formatCurrency(value, currency = 'INR') {
  const amount = Number(value || 0);

  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

function getDestinationName(activeTrip) {
  return (
    activeTrip?.destination ||
    activeTrip?.destination_name ||
    activeTrip?.city ||
    'your destination'
  );
}

function getTripCurrency(activeTrip) {
  return (
    activeTrip?.currency ||
    activeTrip?.currency_code ||
    'INR'
  );
}

/* ========================================================================== */
/* COMPONENT                                                                  */
/* ========================================================================== */

export default function DisruptionPage() {
  const {
    activeTrip,
    simulateDisruption,
    applyReplan,
    proposedReplan,
    setProposedReplan,
    isSimulating,
    isReplanning,
    resolveAlert,
    setCurrentPage,
  } = useTrip();

  const destination = getDestinationName(activeTrip);
  const currency = getTripCurrency(activeTrip);

  /* ------------------------------------------------------------------------ */
  /* CUSTOM DISRUPTION FORM                                                   */
  /* ------------------------------------------------------------------------ */

  const [customType, setCustomType] = useState('activity_cancelled');
  const [customTitle, setCustomTitle] = useState('');
  const [customTime, setCustomTime] = useState('14:30');
  const [customDesc, setCustomDesc] = useState('');
  const [customSeverity, setCustomSeverity] = useState('warning');

  /* ------------------------------------------------------------------------ */
  /* SUGGESTED ACTIVITY                                                       */
  /* ------------------------------------------------------------------------ */

  const suggestedActivity =
    activeTrip?.itinerary?.[0]?.activity_name ||
    activeTrip?.itinerary?.[0]?.title ||
    activeTrip?.itinerary?.[0]?.name ||
    '';

  /* ------------------------------------------------------------------------ */
  /* SIMULATE PRESET                                                          */
  /* ------------------------------------------------------------------------ */

  const handleSimulatePreset = async (preset) => {
    await simulateDisruption({
      disruption_type: preset.disruption_type,

      title:
        suggestedActivity ||
        preset.title ||
        preset.label,

      time:
        activeTrip?.itinerary?.[0]?.start_time ||
        activeTrip?.itinerary?.[0]?.startTime ||
        '09:00',

      delay_minutes: preset.delay_minutes || 0,

      cost_delta: preset.cost_delta || 0,

      new_budget:
        preset.new_budget !== undefined
          ? preset.new_budget
          : undefined,

      new_interests:
        preset.new_interests !== undefined
          ? preset.new_interests
          : undefined,

      description: preset.description,

      severity: preset.severity,
    });
  };

  /* ------------------------------------------------------------------------ */
  /* CUSTOM DISRUPTION                                                        */
  /* ------------------------------------------------------------------------ */

  const handleCustomSubmit = async (e) => {
    e.preventDefault();

    const title = customTitle.trim();
    const description = customDesc.trim();

    if (!title || !description) {
      return;
    }

    await simulateDisruption({
      disruption_type: customType,
      title,
      time: customTime,
      description,
      severity: customSeverity,
    });
  };

  /* ------------------------------------------------------------------------ */
  /* APPLY REPLAN                                                             */
  /* ------------------------------------------------------------------------ */

  const handleApplyProposedReplan = async () => {
    if (!proposedReplan) {
      return;
    }

    await applyReplan();
  };

  /* ------------------------------------------------------------------------ */
  /* BEFORE ACTIVITY                                                           */
  /* ------------------------------------------------------------------------ */

  const originalItem = useMemo(() => {
    const affected =
      proposedReplan?.affected_items?.[0] ||
      proposedReplan?.affected_activity ||
      proposedReplan?.original_activity ||
      null;

    if (affected) {
      return affected;
    }

    return {
      activity_name:
        proposedReplan?.title ||
        'Affected Activity',

      start_time:
        proposedReplan?.time ||
        'Not specified',

      estimated_cost:
        proposedReplan?.estimated_cost ??
        proposedReplan?.cost ??
        0,

      category:
        proposedReplan?.category ||
        'Activity',

      location:
        proposedReplan?.location ||
        destination,
    };
  }, [proposedReplan, destination]);

  /* ------------------------------------------------------------------------ */
  /* SUBSTITUTE                                                               */
  /* ------------------------------------------------------------------------ */

  const substituteItem =
    proposedReplan?.recommended_alternative ||
    proposedReplan?.alternative ||
    proposedReplan?.replacement_activity ||
    null;

  /* ------------------------------------------------------------------------ */
  /* ACTIVE ALERTS                                                            */
  /* ------------------------------------------------------------------------ */

  const activeAlerts = activeTrip?.activeAlerts || [];

  /* ------------------------------------------------------------------------ */
  /* NO ACTIVE TRIP                                                           */
  /* ------------------------------------------------------------------------ */

  if (!activeTrip) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <DisruptionAlertBanner />

        <div className="min-h-[60vh] flex items-center justify-center">
          <div className="max-w-xl text-center p-8 rounded-3xl bg-slate-900/70 border border-slate-800 shadow-xl">
            <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
              <AlertTriangle
                className="w-7 h-7 text-cyan-400"
                aria-hidden="true"
              />
            </div>

            <h1 className="text-xl font-bold text-white mb-2">
              No Active Trip
            </h1>

            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Create or select a trip before using the disruption simulator
              and AI replan engine.
            </p>

            <button
              type="button"
              onClick={() => setCurrentPage('create')}
              className="px-5 py-3 rounded-xl text-sm font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition cursor-pointer"
            >
              Create a Trip
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ======================================================================== */
  /* RENDER                                                                   */
  /* ======================================================================== */

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      <DisruptionAlertBanner />

      {/* ================================================================== */}
      {/* HEADER                                                             */}
      {/* ================================================================== */}

      <section className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5">

          <div>
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-2">
              <Zap
                className="w-4 h-4"
                aria-hidden="true"
              />

              <span>
                Autonomous Disruption Center
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Real-Time Disruption Simulator &amp; Replan Engine
            </h1>

            <p className="text-sm text-slate-400 mt-2 max-w-3xl leading-relaxed">
              Simulate unexpected travel incidents and let TravelPilot
              evaluate conflicts, costs, travel time, availability, and
              alternative activities before rebuilding the itinerary.
            </p>
          </div>

          <div className="shrink-0 px-4 py-3 rounded-2xl bg-slate-900/80 border border-slate-800">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">
              Current Trip Destination
            </div>

            <div className="text-sm font-bold text-cyan-300 flex items-center gap-2">
              <MapPin
                className="w-4 h-4"
                aria-hidden="true"
              />

              {destination}
            </div>
          </div>

        </div>
      </section>

      {/* ================================================================== */}
      {/* PROPOSED REPLAN                                                    */}
      {/* ================================================================== */}

      {proposedReplan && (
        <section
          aria-label="Disruption Replan Comparison"
          className="mb-10"
        >

          <div className="p-5 sm:p-6 rounded-3xl bg-slate-900/80 border border-cyan-500/20 shadow-2xl">

            {/* HEADER */}

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">

              <div>
                <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-1">
                  <Sparkles
                    className="w-4 h-4"
                    aria-hidden="true"
                  />

                  <span>
                    Disruption Simulation Analysis
                  </span>
                </div>

                <h2 className="text-lg font-bold text-white">
                  Compare Schedule Changes &amp; Apply Replan
                </h2>
              </div>

              <button
                type="button"
                onClick={() => setProposedReplan(null)}
                className="px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 transition cursor-pointer"
              >
                Dismiss Review
              </button>

            </div>

            {/* BEFORE / AFTER */}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

              {/* ========================================================== */}
              {/* BEFORE                                                      */}
              {/* ========================================================== */}

              <div className="rounded-2xl border border-rose-500/20 bg-rose-500/[0.03] p-5">

                <div className="flex items-center justify-between gap-3 mb-4">

                  <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">
                    🔴 BEFORE: Original Scheduled Plan
                  </span>

                  <span className="text-xs text-slate-400 font-mono">
                    Time: {originalItem.start_time || 'Not specified'}
                  </span>

                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">

                  <h3 className="text-base font-bold text-white">
                    {originalItem.activity_name ||
                      originalItem.title ||
                      originalItem.name ||
                      'Affected Activity'}
                  </h3>

                  <p className="text-xs text-slate-400 mt-1">
                    {originalItem.category || 'Activity'}
                    {' • '}
                    {originalItem.location || destination}
                  </p>

                  <div className="mt-4 pt-3 border-t border-slate-800">

                    <span className="text-xs text-slate-500 block">
                      Original Cost:
                    </span>

                    <span className="text-sm font-bold text-rose-400">
                      {formatCurrency(
                        originalItem.estimated_cost ??
                          originalItem.cost ??
                          0,
                        currency
                      )}
                    </span>

                  </div>

                  <div className="mt-4 p-3 rounded-xl bg-rose-950/30 border border-rose-500/20 text-xs text-rose-200">

                    <span className="break-words">
                      <strong>DISRUPTION:</strong>{' '}
                      {proposedReplan.reason_for_disruption ||
                        proposedReplan.description ||
                        'Travel disruption detected'}
                    </span>

                  </div>

                </div>

              </div>

              {/* ========================================================== */}
              {/* AFTER                                                       */}
              {/* ========================================================== */}

              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.03] p-5">

                <div className="flex items-center justify-between gap-3 mb-4">

                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                    🟢 AFTER: AI Replanned Schedule
                  </span>

                  <span className="text-xs font-semibold text-emerald-400">
                    Validated &amp; Optimized
                  </span>

                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">

                  {substituteItem ? (

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-2">

                      <div>

                        <h3 className="text-base font-bold text-white">

                          <span>
                            {substituteItem.name ||
                              substituteItem.title ||
                              substituteItem.activity_name ||
                              'Replacement Activity'}
                          </span>

                          {substituteItem.category && (
                            <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                              {substituteItem.category}
                            </span>
                          )}

                        </h3>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300 mt-1.5">

                          {(substituteItem.distance_km !== undefined ||
                            substituteItem.distance_from_original_km !== undefined) && (
                            <span className="flex items-center gap-1">
                              <MapPin
                                className="w-3.5 h-3.5 text-cyan-400"
                                aria-hidden="true"
                              />

                              {substituteItem.distance_km ??
                                substituteItem.distance_from_original_km}

                              {' km from original'}
                            </span>
                          )}

                          {substituteItem.estimated_duration !== undefined ||
                          substituteItem.duration_minutes !== undefined ? (
                            <>
                              <span>•</span>

                              <span className="flex items-center gap-1">
                                <Clock
                                  className="w-3.5 h-3.5 text-cyan-400"
                                  aria-hidden="true"
                                />

                                {substituteItem.estimated_duration ??
                                  `${substituteItem.duration_minutes} mins`}
                              </span>
                            </>
                          ) : null}

                          {substituteItem.rating !== undefined &&
                            substituteItem.rating !== null && (
                              <>
                                <span>•</span>

                                <span>
                                  Rating: {substituteItem.rating}
                                </span>
                              </>
                            )}

                        </div>

                        {substituteItem.recommendation_reason && (
                          <p className="text-xs text-cyan-300 mt-2 bg-cyan-950/40 p-2.5 rounded-xl border border-cyan-500/20">

                            <strong>
                              AI Rationale:
                            </strong>{' '}

                            {substituteItem.recommendation_reason}

                          </p>
                        )}

                      </div>

                      <div className="text-right sm:self-center shrink-0">

                        <span className="text-xs text-slate-400 block">
                          New Venue Cost:
                        </span>

                        <span className="text-sm font-bold text-emerald-400">

                          {substituteItem.cost !== undefined
                            ? formatCurrency(
                                substituteItem.cost,
                                currency
                              )
                            : substituteItem.estimated_cost !== undefined
                            ? formatCurrency(
                                substituteItem.estimated_cost,
                                currency
                              )
                            : 'Cost unavailable'}

                        </span>

                      </div>

                    </div>

                  ) : (

                    <div className="text-xs text-slate-300 mt-2">

                      {proposedReplan.changes_made?.length
                        ? 'TravelPilot dynamically adjusted the itinerary to absorb the disruption.'
                        : 'TravelPilot recalculated the schedule without requiring a venue replacement.'}

                    </div>

                  )}

                </div>

              </div>

            </div>

            {/* ============================================================ */}
            {/* CHANGE SUMMARY                                                */}
            {/* ============================================================ */}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 mb-6">

              <div className="md:col-span-2 p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-xs">

                <span className="font-semibold text-white block mb-2">
                  Summary of Schedule Modifications (
                  {proposedReplan.changes_made?.length || 0}
                  ):
                </span>

                <ul className="space-y-1.5 text-slate-300">

                  {(proposedReplan.changes_made || []).map(
                    (change, index) => (

                      <li
                        key={index}
                        className="flex items-start space-x-2"
                      >

                        <CheckCircle2
                          className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"
                          aria-hidden="true"
                        />

                        <span>
                          {change}
                        </span>

                      </li>

                    )
                  )}

                  {(!proposedReplan.changes_made ||
                    proposedReplan.changes_made.length === 0) && (

                    <li className="text-slate-500 italic">
                      No schedule changes were returned by the
                      replanning engine.
                    </li>

                  )}

                </ul>

              </div>

              {/* ========================================================== */}
              {/* IMPACT                                                      */}
              {/* ========================================================== */}

              <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-xs space-y-3">

                <span className="font-semibold text-white block">
                  Projected Impact:
                </span>

                <div>

                  <span className="text-slate-400 flex items-center gap-1">

                    <Wallet
                      className="w-3.5 h-3.5"
                      aria-hidden="true"
                    />

                    Budget Impact:

                  </span>

                  <div className="text-sm font-bold text-emerald-400 mt-0.5">

                    {proposedReplan.budget_impact?.spending_delta !==
                    undefined
                      ? formatCurrency(
                          proposedReplan.budget_impact.spending_delta,
                          currency
                        )
                      : formatCurrency(0, currency)}

                  </div>

                </div>

                <div>

                  <span className="text-slate-400 flex items-center gap-1">

                    <Route
                      className="w-3.5 h-3.5"
                      aria-hidden="true"
                    />

                    Route Distance Change:

                  </span>

                  <div className="text-sm font-bold text-cyan-400 mt-0.5">

                    {proposedReplan.travel_impact
                      ?.distance_delta_km !== undefined
                      ? `${proposedReplan.travel_impact.distance_delta_km} km`
                      : '0 km'}

                  </div>

                </div>

              </div>

            </div>

            {/* ============================================================ */}
            {/* APPLY                                                          */}
            {/* ============================================================ */}

            <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">

              <span className="text-xs text-slate-300">
                Review the proposed changes before committing them to the
                live trip.
              </span>

              <div className="flex items-center space-x-3 w-full sm:w-auto">

                <button
                  type="button"
                  onClick={() => setCurrentPage('itinerary')}
                  className="w-full sm:w-auto px-4 py-3 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition cursor-pointer"
                >
                  View Itinerary Timeline
                </button>

                <button
                  type="button"
                  onClick={handleApplyProposedReplan}
                  disabled={isReplanning}
                  className="w-full sm:w-auto px-8 py-3.5 rounded-xl text-sm font-extrabold text-slate-950 bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 hover:from-emerald-300 hover:to-cyan-300 transition shadow-xl shadow-emerald-500/25 flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >

                  {isReplanning ? (
                    <>
                      <RefreshCw
                        className="w-4 h-4 animate-spin"
                        aria-hidden="true"
                      />

                      <span>
                        Applying to Database...
                      </span>
                    </>
                  ) : (
                    <>
                      <Check
                        className="w-4 h-4 stroke-[3]"
                        aria-hidden="true"
                      />

                      <span>
                        Apply Changes to Live Trip
                      </span>
                    </>
                  )}

                </button>

              </div>

            </div>

          </div>

        </section>
      )}

      {/* ================================================================== */}
      {/* GENERIC DISRUPTION SCENARIOS                                       */}
      {/* ================================================================== */}

      <div className="mb-12">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">

          <h2 className="text-sm font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-2">

            <Play
              className="w-4 h-4"
              aria-hidden="true"
            />

            <span>
              Disruption Scenarios
            </span>

          </h2>

          <span className="text-xs text-slate-500">
            Destination: {destination}
          </span>

        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

          {DISRUPTION_PRESETS.map((preset) => {

            const isCritical =
              preset.severity === 'critical';

            return (

              <div
                key={preset.id}
                className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between group shadow-lg"
              >

                <div>

                  <div className="flex items-center justify-between mb-3">

                    <div
                      className={`p-2 rounded-xl ${
                        isCritical
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}
                    >

                      {preset.icon === 'CalendarX' ? (

                        <CalendarX
                          className="w-5 h-5"
                          aria-hidden="true"
                        />

                      ) : preset.icon === 'ClockAlert' ? (

                        <ClockAlert
                          className="w-5 h-5"
                          aria-hidden="true"
                        />

                      ) : preset.icon === 'TrendingDown' ? (

                        <TrendingDown
                          className="w-5 h-5"
                          aria-hidden="true"
                        />

                      ) : (

                        <Sparkles
                          className="w-5 h-5"
                          aria-hidden="true"
                        />

                      )}

                    </div>

                    <span
                      className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full border ${
                        isCritical
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}
                    >
                      {preset.severity}
                    </span>

                  </div>

                  <h3 className="text-sm font-bold text-white mb-1.5 group-hover:text-cyan-300 transition">
                    {preset.label}
                  </h3>

                  <p className="text-xs text-slate-400 leading-relaxed mb-3">
                    {preset.description}
                  </p>

                  <div className="text-[11px] text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 space-y-1">

                    <div>
                      <span className="text-slate-400 font-medium">
                        Impact:
                      </span>{' '}
                      {preset.defaultImpact}
                    </div>

                    <div>
                      <span className="text-cyan-400 font-medium">
                        AI Action:
                      </span>{' '}
                      {preset.defaultAiAction}
                    </div>

                  </div>

                </div>

                <button
                  type="button"
                  onClick={() => handleSimulatePreset(preset)}
                  disabled={isSimulating}
                  className="mt-4 w-full py-2.5 px-4 rounded-xl text-xs font-bold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-300 hover:from-amber-300 hover:to-amber-200 transition shadow-md shadow-amber-500/20 flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >

                  {isSimulating ? (

                    <RefreshCw
                      className="w-3.5 h-3.5 animate-spin"
                      aria-hidden="true"
                    />

                  ) : (

                    <Play
                      className="w-3.5 h-3.5 fill-current"
                      aria-hidden="true"
                    />

                  )}

                  <span>
                    {isSimulating
                      ? 'Simulating...'
                      : 'Simulate this Disruption'}
                  </span>

                </button>

              </div>

            );
          })}

        </div>

      </div>

      {/* ================================================================== */}
      {/* CUSTOM DISRUPTION BUILDER                                          */}
      {/* ================================================================== */}

      <div
        id="custom-form"
        className="mb-12 p-6 sm:p-8 rounded-3xl bg-slate-900/60 border border-slate-800 shadow-xl"
      >

        <div className="flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-2">

          <Wand2
            className="w-4 h-4"
            aria-hidden="true"
          />

          <span>
            Custom Disruption Builder
          </span>

        </div>

        <h3 className="text-lg font-bold text-white mb-1">
          Create a Custom Travel Incident
        </h3>

        <p className="text-xs text-slate-400 mb-6">
          Describe what actually happened. TravelPilot will send the
          incident details to the disruption engine and generate a
          destination-aware replan.
        </p>

        <form
          onSubmit={handleCustomSubmit}
          className="space-y-4 text-xs"
        >

          {/* ============================================================ */}
          {/* TITLE + TYPE                                                  */}
          {/* ============================================================ */}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            <div className="md:col-span-2">

              <label className="block text-slate-300 mb-1 font-medium">
                Activity or Venue Name
              </label>

              <input
                type="text"
                required
                value={customTitle}
                onChange={(e) =>
                  setCustomTitle(e.target.value)
                }
                placeholder={
                  suggestedActivity ||
                  `e.g. ${destination} Museum`
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-400"
              />

            </div>

            <div>

              <label className="block text-slate-300 mb-1 font-medium">
                Disruption Type
              </label>

              <select
                value={customType}
                onChange={(e) =>
                  setCustomType(e.target.value)
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-400"
              >

                <option value="activity_cancelled">
                  Activity Cancelled
                </option>

                <option value="transportation_delayed">
                  Transportation Delayed
                </option>

                <option value="activity_unavailable">
                  Sold Out / Unavailable
                </option>

                <option value="budget_reduced">
                  Budget Reduced
                </option>

                <option value="user_interests_changed">
                  Interests Changed
                </option>

              </select>

            </div>

          </div>

          {/* ============================================================ */}
          {/* TIME + SEVERITY                                               */}
          {/* ============================================================ */}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            <div>

              <label className="block text-slate-300 mb-1 font-medium">
                Affected Time
              </label>

              <input
                type="time"
                value={customTime}
                onChange={(e) =>
                  setCustomTime(e.target.value)
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-400"
              />

            </div>

            <div>

              <label className="block text-slate-300 mb-1 font-medium">
                Severity
              </label>

              <select
                value={customSeverity}
                onChange={(e) =>
                  setCustomSeverity(e.target.value)
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-400"
              >

                <option value="info">
                  Informational
                </option>

                <option value="warning">
                  Warning
                </option>

                <option value="critical">
                  Critical
                </option>

              </select>

            </div>

          </div>

          {/* ============================================================ */}
          {/* INCIDENT DESCRIPTION                                          */}
          {/* ============================================================ */}

          <div>

            <label className="block text-slate-300 mb-1 font-medium">
              Incident Description
            </label>

            <textarea
              rows={4}
              required
              value={customDesc}
              onChange={(e) =>
                setCustomDesc(e.target.value)
              }
              placeholder="Describe exactly what happened. Example: The venue is closed today because of an unexpected staff strike."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-400 resize-y"
            />

            <p className="mt-1.5 text-[11px] text-slate-500">
              This description is sent directly to the backend
              disruption engine and should appear in the resulting
              incident/replan explanation.
            </p>

          </div>

          {/* ============================================================ */}
          {/* SUBMIT                                                        */}
          {/* ============================================================ */}

          <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-2">

            <div className="text-[11px] text-slate-500 flex items-center gap-2">

              <Navigation
                className="w-3.5 h-3.5"
                aria-hidden="true"
              />

              <span>
                Destination-aware replanning:
              </span>

              <span className="text-cyan-400 font-semibold">
                {destination}
              </span>

            </div>

            <button
              type="submit"
              disabled={
                isSimulating ||
                !customTitle.trim() ||
                !customDesc.trim()
              }
              className="px-6 py-3 rounded-xl text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition shadow-lg shadow-cyan-500/20 flex items-center space-x-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >

              {isSimulating ? (

                <RefreshCw
                  className="w-3.5 h-3.5 animate-spin"
                  aria-hidden="true"
                />

              ) : (

                <Play
                  className="w-3.5 h-3.5 fill-current"
                  aria-hidden="true"
                />

              )}

              <span>
                {isSimulating
                  ? 'Processing Disruption...'
                  : 'Fire Custom Disruption'}
              </span>

            </button>

          </div>

        </form>

      </div>

      {/* ================================================================== */}
      {/* LIVE ALERT FEED                                                    */}
      {/* ================================================================== */}

      <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800 mb-4">

          <div className="flex items-center space-x-2">

            <ShieldCheck
              className="w-5 h-5 text-emerald-400"
              aria-hidden="true"
            />

            <h3 className="text-base font-bold text-white">
              Live Alert Triage &amp; Incident Log ({activeAlerts.length})
            </h3>

          </div>

          <span className="text-xs text-slate-400">
            {destination} • Real-time synchronization active
          </span>

        </div>

        <div className="space-y-4">

          {activeAlerts.length === 0 ? (

            <div className="py-10 text-center">

              <CheckCircle2
                className="w-10 h-10 mx-auto text-emerald-400 mb-3"
                aria-hidden="true"
              />

              <p className="text-sm font-semibold text-white">
                No active disruptions
              </p>

              <p className="text-xs text-slate-500 mt-1">
                Your current trip has no unresolved travel incidents.
              </p>

            </div>

          ) : (

            activeAlerts.map((alert) => {

              const isResolved = alert.resolved;

              return (

                <div
                  key={alert.id}
                  className={`p-4 rounded-xl border transition ${
                    isResolved
                      ? 'bg-slate-950/40 border-slate-800/60 opacity-60'
                      : 'bg-slate-950 border-amber-500/30 shadow-md'
                  }`}
                >

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">

                    <div className="flex flex-wrap items-center gap-2">

                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${
                          alert.severity === 'critical'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            : alert.severity === 'warning'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                        }`}
                      >
                        {alert.severity || 'info'}
                      </span>

                      <h4 className="text-sm font-bold text-white">
                        {alert.title ||
                          alert.activity_name ||
                          'Travel Disruption'}
                      </h4>

                      {alert.timestamp && (
                        <span className="text-xs text-slate-500">
                          • {alert.timestamp}
                        </span>
                      )}

                    </div>

                    {!isResolved ? (

                      <button
                        type="button"
                        onClick={() =>
                          resolveAlert(alert.id)
                        }
                        className="px-3 py-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition self-start sm:self-auto flex items-center space-x-1 cursor-pointer"
                      >

                        <CheckCircle2
                          className="w-3.5 h-3.5"
                          aria-hidden="true"
                        />

                        <span>
                          Mark Resolved
                        </span>

                      </button>

                    ) : (

                      <span className="text-xs text-slate-500 flex items-center space-x-1">

                        <CheckCircle2
                          className="w-3.5 h-3.5 text-slate-500"
                          aria-hidden="true"
                        />

                        <span>
                          Resolved
                        </span>

                      </span>

                    )}

                  </div>

                  {/* INCIDENT DESCRIPTION */}

                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">

                    {alert.description ||
                      alert.reason_for_disruption ||
                      alert.reason ||
                      'No incident description provided.'}

                  </p>

                  {/* AI RESOLUTION */}

                  {alert.aiResolution && (

                    <div className="mt-3 text-xs text-cyan-300 bg-cyan-950/40 p-2.5 rounded-lg border border-cyan-500/20 flex items-start space-x-2">

                      <Sparkles
                        className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5"
                        aria-hidden="true"
                      />

                      <span>

                        <strong>
                          AI Dynamic Countermeasure:
                        </strong>{' '}

                        {alert.aiResolution}

                      </span>

                    </div>

                  )}

                </div>

              );
            })

          )}

        </div>

      </div>

    </div>
  );
}