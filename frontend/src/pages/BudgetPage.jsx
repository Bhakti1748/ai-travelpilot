import React from 'react';

import {
  DollarSign,
  TrendingDown,
  PieChart,
  CheckCircle2,
  Sparkles,
  BedDouble,
  Train,
  Ticket,
  Utensils,
  Package,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';
import DisruptionAlertBanner from '../components/DisruptionAlertBanner';

export default function BudgetPage() {
  const {
    activeTrip,
    setCurrentPage,
    simulateDisruption,
    refreshTripData,
  } = useTrip();

  const curr = activeTrip?.currency || 'INR';

  const totalBudget = activeTrip?.budget || 0;
  const spending = activeTrip?.spending || 0;
  const remaining = Math.max(0, totalBudget - spending);

  const percentUsed =
    totalBudget > 0
      ? Math.min(100, Math.round((spending / totalBudget) * 100))
      : 0;

  const b = activeTrip?.budgetBreakdown || {
    accommodation: Math.round(totalBudget * 0.35),
    transportation: Math.round(totalBudget * 0.2),
    activities: Math.round(totalBudget * 0.2),
    food: Math.round(totalBudget * 0.2),
    miscellaneous: Math.round(totalBudget * 0.05),
  };

  const travelersCount = activeTrip?.travelers || 1;

  const destination =
    activeTrip?.destination || 'your selected destination';

  const categories = [
    {
      id: 'accommodation',
      label: 'Accommodation',
      icon: BedDouble,
      allocated: b.accommodation,
      percent:
        totalBudget > 0
          ? Math.round((b.accommodation / totalBudget) * 100)
          : 35,
      color: 'bg-cyan-400',
      badgeColor:
        'text-cyan-300 bg-cyan-400/10 border-cyan-400/20',
      strokeColor: '#22d3ee',
      desc: `Accommodation allocation and lodging costs in ${destination}.`,
      status: 'Reserved',
    },
    {
      id: 'transportation',
      label: 'Transportation',
      icon: Train,
      allocated: b.transportation,
      percent:
        totalBudget > 0
          ? Math.round((b.transportation / totalBudget) * 100)
          : 20,
      color: 'bg-indigo-400',
      badgeColor:
        'text-indigo-300 bg-indigo-400/10 border-indigo-400/20',
      strokeColor: '#818cf8',
      desc: `Local and intercity transportation costs for ${destination}.`,
      status: 'Optimized',
    },
    {
      id: 'activities',
      label: 'Activities & Attractions',
      icon: Ticket,
      allocated: b.activities,
      percent:
        totalBudget > 0
          ? Math.round((b.activities / totalBudget) * 100)
          : 20,
      color: 'bg-purple-400',
      badgeColor:
        'text-purple-300 bg-purple-400/10 border-purple-400/20',
      strokeColor: '#c084fc',
      desc: `Activities and attraction costs selected for your itinerary.`,
      status: 'Verified',
    },
    {
      id: 'food',
      label: 'Food & Dining',
      icon: Utensils,
      allocated: b.food,
      percent:
        totalBudget > 0
          ? Math.round((b.food / totalBudget) * 100)
          : 20,
      color: 'bg-emerald-400',
      badgeColor:
        'text-emerald-300 bg-emerald-400/10 border-emerald-400/20',
      strokeColor: '#34d399',
      desc: `Food and dining allowance based on your trip plan.`,
      status: 'Flexible',
    },
    {
      id: 'miscellaneous',
      label: 'Miscellaneous & Cushion',
      icon: Package,
      allocated: b.miscellaneous,
      percent:
        totalBudget > 0
          ? Math.round((b.miscellaneous / totalBudget) * 100)
          : 5,
      color: 'bg-amber-400',
      badgeColor:
        'text-amber-300 bg-amber-400/10 border-amber-400/20',
      strokeColor: '#fbbf24',
      desc:
        'Disruption buffer, unexpected expenses, and flexible spending reserve.',
      status: 'Safety Net',
    },
  ];

  // Dynamically compute SVG circle arc offsets.
  const circumference = 2 * Math.PI * 40;

  let accumulatedOffset = 0;

  const chartSegments = categories.map((cat) => {
    const strokeDash = Math.max(
      0,
      (cat.percent / 100) * circumference
    );

    const strokeDashoffset = -accumulatedOffset;

    accumulatedOffset += strokeDash;

    return {
      ...cat,
      strokeDasharray: `${strokeDash.toFixed(
        2
      )} ${circumference.toFixed(2)}`,
      strokeDashoffset: strokeDashoffset.toFixed(2),
    };
  });

  // If no trip is selected, show a clean empty state.
  if (!activeTrip) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <DisruptionAlertBanner />

        <div className="min-h-[500px] flex flex-col items-center justify-center text-center">
          <div className="p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 mb-5">
            <DollarSign className="w-10 h-10 text-cyan-400" />
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            Trip Budget & Cost Intelligence
          </h1>

          <p className="text-sm text-slate-400 mt-2 max-w-lg">
            Create or select a trip to view its budget,
            spending, category allocations, and financial
            guardrails.
          </p>

          <button
            type="button"
            onClick={() => setCurrentPage('create')}
            className="mt-6 px-5 py-3 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-semibold transition cursor-pointer"
          >
            Create a Trip
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <DisruptionAlertBanner />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4 mb-8">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-cyan-400 mb-1">
            <DollarSign className="w-3.5 h-3.5" />
            <span>Autonomous Financial Guardrails</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Trip Budget & Cost Intelligence
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Spending allocation for your trip to{' '}
            <span className="text-slate-200 font-medium">
              {destination}
            </span>
            , based on your itinerary and current trip state.
          </p>
        </div>

        <div className="flex items-center space-x-3 flex-wrap gap-2">
          <button
            onClick={() => refreshTripData()}
            className="px-3 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 transition flex items-center space-x-1.5 cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400"
            aria-label="Refresh Budget Data"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Sync Ledger</span>
          </button>

          <button
            onClick={() => {
              const reduction = Math.min(
                15000,
                Math.max(0, totalBudget - 30000)
              );

              if (reduction <= 0) return;

              simulateDisruption({
                type: 'budget_reduced',
                disruption_type: 'budget_reduced',
                title: `Budget Trim Simulation (-${reduction.toLocaleString()} ${curr})`,
                severity: 'warning',
                description: `Traveler requested a ${reduction.toLocaleString()} ${curr} reduction in the total budget ceiling to test dynamic replanning.`,
                cost_delta: -reduction,
                new_budget: Math.max(
                  30000,
                  totalBudget - reduction
                ),
              });

              setCurrentPage('disruptions');
            }}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-amber-300 hover:text-amber-200 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 transition flex items-center space-x-1.5 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400"
            aria-label="Simulate Budget Reduction"
          >
            <TrendingDown className="w-4 h-4" />
            <span>
              Simulate Budget Cut (-15,000 {curr})
            </span>
          </button>
        </div>
      </div>

      {/* Top Stat Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10">
        {/* Total Budget */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase tracking-wider mb-2">
            <span>Total Trip Ceiling</span>

            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>

          <div className="text-3xl font-extrabold text-white">
            {curr} {totalBudget.toLocaleString()}
          </div>

          <div className="text-xs text-slate-400 mt-2 flex items-center justify-between">
            <span>
              For {travelersCount} traveler
              {travelersCount !== 1 ? 's' : ''}
            </span>

            <span className="font-mono text-cyan-400/80 font-medium">
              ~{curr}{' '}
              {Math.round(
                totalBudget / travelersCount
              ).toLocaleString()}
              /person
            </span>
          </div>
        </div>

        {/* Estimated Spending */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase tracking-wider mb-2">
            <span>Committed Bookings</span>

            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>

          <div className="text-3xl font-extrabold text-indigo-300">
            {curr} {spending.toLocaleString()}
          </div>

          <div className="text-xs text-slate-400 mt-2 flex items-center justify-between">
            <span>{percentUsed}% allocated</span>

            <span className="text-emerald-400 font-medium flex items-center space-x-1">
              <CheckCircle2 className="w-3 h-3 inline" />
              <span>Paced</span>
            </span>
          </div>
        </div>

        {/* Remaining Margin */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase tracking-wider mb-2">
            <span>Available Margin</span>

            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>

          <div className="text-3xl font-extrabold text-emerald-400">
            {curr} {remaining.toLocaleString()}
          </div>

          <div className="text-xs text-slate-400 mt-2 flex items-center justify-between">
            <span>Liquid buffer</span>

            <span className="text-slate-300 font-mono">
              ~{curr}{' '}
              {Math.round(
                remaining / 5
              ).toLocaleString()}
              /day reserve
            </span>
          </div>
        </div>
      </div>

      {/* Progress Bar Overall */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 mb-10 shadow-lg">
        <div className="flex items-center justify-between text-xs font-semibold mb-2.5">
          <div className="flex items-center space-x-2">
            <span className="text-white">
              Budget Consumption Pace
            </span>

            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              Normal Velocity
            </span>
          </div>

          <span className="text-cyan-400 font-mono text-sm">
            {percentUsed}% Consumed
          </span>
        </div>

        <div className="w-full bg-slate-950 h-3.5 rounded-full overflow-hidden p-0.5 border border-slate-800/90 shadow-inner">
          <div
            className="h-full bg-gradient-to-r from-cyan-400 via-indigo-400 to-emerald-400 rounded-full transition-all duration-700"
            style={{ width: `${percentUsed}%` }}
          />
        </div>

        <div className="flex justify-between text-[11px] text-slate-400 mt-2.5 font-mono">
          <span>0 {curr} Started</span>

          <span className="text-slate-200 font-medium">
            Spent: {curr} {spending.toLocaleString()}
          </span>

          <span>
            Max Ceiling: {curr}{' '}
            {totalBudget.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Visual Chart & Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
        {/* SVG Circular Donut Chart */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col items-center justify-center text-center shadow-lg">
          <div className="w-full flex items-center justify-between pb-3 mb-2 border-b border-slate-800/80">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <PieChart className="w-4 h-4 text-cyan-400" />
              <span>Allocation Distribution</span>
            </h3>

            <span className="text-[10px] font-mono text-slate-400">
              5 Categories
            </span>
          </div>

          <div className="relative w-52 h-52 my-3">
            <svg
              viewBox="0 0 100 100"
              className="w-full h-full transform -rotate-90"
            >
              {/* Background ring */}
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="transparent"
                stroke="#1e293b"
                strokeWidth="11"
              />

              {/* Dynamic segments */}
              {chartSegments.map((seg) => (
                <circle
                  key={seg.id}
                  cx="50"
                  cy="50"
                  r="40"
                  fill="transparent"
                  stroke={seg.strokeColor}
                  strokeWidth="11"
                  strokeDasharray={seg.strokeDasharray}
                  strokeDashoffset={seg.strokeDashoffset}
                  className="transition-all duration-500 hover:opacity-90"
                />
              ))}
            </svg>

            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Total
              </span>

              <span className="text-base font-extrabold text-white truncate max-w-[130px] mt-0.5">
                {curr} {totalBudget.toLocaleString()}
              </span>

              <span className="text-[10px] text-cyan-400 font-medium mt-0.5">
                100% Guarded
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-left mt-3 w-full text-[11px] pt-3 border-t border-slate-800/60">
            {categories.map((c) => (
              <div
                key={c.id}
                className="flex items-center space-x-1.5"
              >
                <span
                  className={`w-2.5 h-2.5 rounded-full ${c.color} shrink-0`}
                />

                <span className="text-slate-300 truncate font-medium">
                  {c.label}
                </span>

                <span className="text-slate-500 text-[10px] ml-auto font-mono">
                  {c.percent}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Detailed Horizontal Breakdown Bars */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3.5 shadow-lg">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
            <h3 className="text-sm font-bold text-white">
              Category Breakdown Details
            </h3>

            <span className="text-xs text-slate-400">
              Total:{' '}
              <strong className="text-white font-mono">
                {curr} {totalBudget.toLocaleString()}
              </strong>
            </span>
          </div>

          {categories.map((cat) => {
            const Icon = cat.icon;

            const perPersonCost = Math.round(
              cat.allocated / travelersCount
            );

            return (
              <div
                key={cat.id}
                className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition group"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center space-x-2.5">
                    <div className="p-2 rounded-lg bg-slate-900 text-slate-300 border border-slate-800">
                      <Icon className="w-4 h-4 text-cyan-400" />
                    </div>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold text-white">
                          {cat.label}
                        </span>

                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${cat.badgeColor}`}
                        >
                          {cat.status}
                        </span>
                      </div>

                      <p className="text-[11px] text-slate-400 hidden sm:block mt-0.5">
                        {cat.desc}
                      </p>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-sm font-extrabold text-white font-mono">
                      {curr} {cat.allocated.toLocaleString()}
                    </div>

                    <div className="text-[10px] text-slate-400">
                      {cat.percent}% •{' '}
                      <span className="text-slate-300">
                        {curr}{' '}
                        {perPersonCost.toLocaleString()}
                      </span>{' '}
                      / traveler
                    </div>
                  </div>
                </div>

                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden mt-2 p-0.5 border border-slate-800">
                  <div
                    className={`${cat.color} h-full rounded-full transition-all duration-500`}
                    style={{
                      width: `${Math.min(
                        100,
                        cat.percent * 2.5
                      )}%`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI Budget Optimization Insights Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-indigo-950/40 border border-emerald-500/20 p-6 shadow-xl">
        <div className="flex items-start space-x-4">
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shrink-0">
            <Sparkles className="w-6 h-6" />
          </div>

          <div>
            <h4 className="text-base font-bold text-white flex items-center space-x-2">
              <span>AI Smart Spend Guardrails</span>

              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Active
              </span>
            </h4>

            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              TravelPilot dynamically cross-references your
              itinerary, bookings, transportation requirements,
              and current budget state for{' '}
              <span className="text-slate-100 font-medium">
                {destination}
              </span>
              . The budget guardrails help maintain a financial
              buffer while the itinerary adapts to changes.
            </p>

            <div className="mt-3 flex items-center space-x-4 text-xs font-medium text-emerald-300 flex-wrap gap-2">
              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Transportation costs monitored</span>
              </span>

              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Activity costs tracked</span>
              </span>

              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>
                  Safety margin: {curr}{' '}
                  {remaining.toLocaleString()} intact
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}