import React from 'react';
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Compass,
  Cpu,
  Clock,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  MapPin,
  Calendar,
  Layers,
  Zap,
} from 'lucide-react';
import { useTrip } from '../hooks/useTrip';

export default function LandingPage() {
  const { setCurrentPage } = useTrip();

  return (
    <div className="relative overflow-hidden">
      {/* Background Decorative Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-cyan-500/15 via-indigo-500/10 to-transparent blur-3xl pointer-events-none" />

      <div className="absolute top-1/3 right-0 w-[400px] h-[350px] bg-purple-500/10 blur-3xl pointer-events-none" />

      {/* ================================================================== */}
      {/* HERO SECTION                                                       */}
      {/* ================================================================== */}

      <section className="relative pt-20 pb-20 md:pt-28 md:pb-28 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">

        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-slate-700/60 shadow-inner mb-8 text-xs font-medium text-slate-300">

          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
          </span>

          <span className="bg-gradient-to-r from-cyan-400 to-indigo-300 bg-clip-text text-transparent font-semibold">
            Next-Gen Autonomous Travel Agent
          </span>

          <span className="text-slate-400">|</span>

          <span className="text-slate-400">
            Real-Time Disruption Recovery
          </span>

        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-[1.12]">

          Your trip changes.{' '}

          <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent underline decoration-cyan-500/30 decoration-wavy">
            TravelPilot adapts.
          </span>

        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
          An AI travel co-pilot that plans, manages and dynamically replans
          your journey. Never get stranded by delayed transport, closed
          venues, or unexpected disruptions again.
        </p>

        {/* CTA Group */}

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">

          <button
            onClick={() => setCurrentPage('create')}
            className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 via-teal-300 to-cyan-300 hover:from-cyan-300 hover:to-teal-200 shadow-xl shadow-cyan-500/25 transition-all transform hover:-translate-y-0.5 flex items-center justify-center space-x-2 group cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400"
            aria-label="Start Planning a New Trip"
          >

            <span>
              Start Planning
            </span>

            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />

          </button>

          <button
            onClick={() => setCurrentPage('dashboard')}
            className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold text-slate-200 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-700/80 shadow-lg transition flex items-center justify-center space-x-2 cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400"
            aria-label="Explore TravelPilot Dashboard"
          >

            <Sparkles className="w-4 h-4 text-cyan-400" />

            <span>
              Explore Live Dashboard
            </span>

          </button>

        </div>

        {/* Quick Highlights Strip */}

        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">

            <div className="text-2xl font-bold text-white">
              0.3 sec
            </div>

            <div className="text-xs text-slate-400 mt-1">
              Autonomous Replanning Latency
            </div>

          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">

            <div className="text-2xl font-bold text-cyan-400">
              100%
            </div>

            <div className="text-xs text-slate-400 mt-1">
              Budget-Locked Schedule Guard
            </div>

          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">

            <div className="text-2xl font-bold text-indigo-400">
              24/7
            </div>

            <div className="text-xs text-slate-400 mt-1">
              Active Disruption Radar
            </div>

          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">

            <div className="text-2xl font-bold text-emerald-400">
              Deterministic
            </div>

            <div className="text-xs text-slate-400 mt-1">
              Grounded Local Constraint Engine
            </div>

          </div>

        </div>

      </section>

      {/* ================================================================== */}
      {/* INTERACTIVE MOCK AGENT TEASER                                      */}
      {/* ================================================================== */}

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">

        <div className="rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-800 p-6 md:p-8 shadow-2xl relative overflow-hidden">

          <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">

            <Cpu className="w-64 h-64 text-cyan-400" />

          </div>

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800 gap-4">

            <div className="flex items-center space-x-3">

              <div className="w-3 h-3 rounded-full bg-rose-500" />
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <div className="w-3 h-3 rounded-full bg-emerald-500" />

              <span className="text-xs font-mono text-slate-400 ml-2">
                travelpilot-agent-engine // active session
              </span>

            </div>

            <div className="flex items-center space-x-2 text-xs text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-500/20">

              <Sparkles className="w-3.5 h-3.5" />

              <span>
                Simulated Real-Time Re-Route Engine
              </span>

            </div>

          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">

            {/* ============================================================ */}
            {/* STEP 1                                                        */}
            {/* ============================================================ */}

            <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800/80 flex flex-col justify-between">

              <div>

                <div className="flex items-center space-x-2 text-amber-400 text-xs font-semibold mb-2">

                  <AlertTriangle className="w-4 h-4" />

                  <span>
                    STEP 1: DISRUPTION DETECTED
                  </span>

                </div>

                <h4 className="text-base font-semibold text-white">
                  Unexpected Travel Disruption
                </h4>

                <p className="text-xs text-slate-400 mt-2">
                  A delay, closure, cancellation, or other travel incident
                  affects the current itinerary.
                </p>

              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400">
                Incident details are passed to the disruption management
                engine.
              </div>

            </div>

            {/* ============================================================ */}
            {/* STEP 2                                                        */}
            {/* ============================================================ */}

            <div className="p-5 rounded-xl bg-slate-950/80 border border-cyan-500/30 flex flex-col justify-between shadow-lg shadow-cyan-950/20">

              <div>

                <div className="flex items-center space-x-2 text-cyan-400 text-xs font-semibold mb-2">

                  <Cpu className="w-4 h-4 animate-spin" />

                  <span>
                    STEP 2: AI REASONING &amp; OPTIMIZATION
                  </span>

                </div>

                <h4 className="text-base font-semibold text-white">
                  Dynamic Constraint Solving
                </h4>

                <p className="text-xs text-slate-300 mt-2">
                  TravelPilot evaluates downstream activities, opening
                  hours, travel time, budget constraints, preferences,
                  and possible alternatives.
                </p>

              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-cyan-300">
                Constraints validated before the revised itinerary is proposed.
              </div>

            </div>

            {/* ============================================================ */}
            {/* STEP 3                                                        */}
            {/* ============================================================ */}

            <div className="p-5 rounded-xl bg-slate-950/80 border border-emerald-500/30 flex flex-col justify-between shadow-lg shadow-emerald-950/20">

              <div>

                <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold mb-2">

                  <CheckCircle className="w-4 h-4" />

                  <span>
                    STEP 3: DEPLOYED ADAPTATION
                  </span>

                </div>

                <h4 className="text-base font-semibold text-white">
                  Seamless Replan Active
                </h4>

                <p className="text-xs text-slate-300 mt-2">
                  A revised schedule is generated with replacement options,
                  updated timings, route changes, and budget impact.
                </p>

              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-emerald-300">
                The traveler reviews the proposed changes before applying them.
              </div>

            </div>

          </div>

        </div>

      </section>

      {/* ================================================================== */}
      {/* CORE FEATURES                                                       */}
      {/* ================================================================== */}

      <section className="py-20 bg-slate-900/40 border-y border-slate-800/80">

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

          <div className="text-center max-w-3xl mx-auto mb-16">

            <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 mb-2">
              Comprehensive Travel Intelligence
            </h2>

            <p className="text-3xl sm:text-4xl font-bold text-white">
              Engineered for seamless journeys from departure to return.
            </p>

          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">

            {/* ============================================================ */}
            {/* 1. HOW IT WORKS                                               */}
            {/* ============================================================ */}

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 hover:border-cyan-500/40 transition group">

              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-5 group-hover:scale-110 transition">

                <Compass className="w-6 h-6" />

              </div>

              <h3 className="text-lg font-bold text-white mb-2">
                How It Works
              </h3>

              <p className="text-sm text-slate-400 leading-relaxed">
                Provide your destination, budget, dates, and interests.
                TravelPilot generates a realistic day-by-day journey
                structured around travel time and scheduling constraints.
              </p>

              <ul className="mt-4 space-y-1.5 text-xs text-slate-300">

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mr-2" />

                  Instant constraint-based synthesis

                </li>

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mr-2" />

                  Realistic travel-time estimation

                </li>

              </ul>

            </div>

            {/* ============================================================ */}
            {/* 2. AI PLANNING                                                */}
            {/* ============================================================ */}

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 hover:border-indigo-500/40 transition group">

              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-5 group-hover:scale-110 transition">

                <Sparkles className="w-6 h-6" />

              </div>

              <h3 className="text-lg font-bold text-white mb-2">
                AI Planning
              </h3>

              <p className="text-sm text-slate-400 leading-relaxed">
                TravelPilot reasons over activities, schedules, travel
                distances, opening hours, preferences, and available
                constraints to build a practical itinerary.
              </p>

              <ul className="mt-4 space-y-1.5 text-xs text-slate-300">

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mr-2" />

                  Personalized interest weighting

                </li>

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mr-2" />

                  Constraint-aware activity selection

                </li>

              </ul>

            </div>

            {/* ============================================================ */}
            {/* 3. SMART OPTIMIZATION                                         */}
            {/* ============================================================ */}

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 hover:border-emerald-500/40 transition group">

              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-5 group-hover:scale-110 transition">

                <DollarSign className="w-6 h-6" />

              </div>

              <h3 className="text-lg font-bold text-white mb-2">
                Smart Optimization
              </h3>

              <p className="text-sm text-slate-400 leading-relaxed">
                Automated budget allocation across accommodation, transit,
                activities, dining, and other trip expenses with
                constraint-aware adjustments.
              </p>

              <ul className="mt-4 space-y-1.5 text-xs text-slate-300">

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-2" />

                  Real-time spending projection

                </li>

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-2" />

                  Budget-aware itinerary adjustments

                </li>

              </ul>

            </div>

            {/* ============================================================ */}
            {/* 4. DISRUPTION MANAGEMENT                                      */}
            {/* ============================================================ */}

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 hover:border-amber-500/40 transition group">

              <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mb-5 group-hover:scale-110 transition">

                <AlertTriangle className="w-6 h-6" />

              </div>

              <h3 className="text-lg font-bold text-white mb-2">
                Disruption Management
              </h3>

              <p className="text-sm text-slate-400 leading-relaxed">
                When transport is delayed, an activity becomes unavailable,
                or the traveler changes plans, TravelPilot evaluates the
                downstream impact and proposes alternatives.
              </p>

              <ul className="mt-4 space-y-1.5 text-xs text-slate-300">

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mr-2" />

                  Live disruption simulations

                </li>

                <li className="flex items-center">

                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mr-2" />

                  Automated schedule adjustments

                </li>

              </ul>

            </div>

          </div>

        </div>

      </section>

      {/* ================================================================== */}
      {/* CALL TO ACTION                                                      */}
      {/* ================================================================== */}

      <section className="py-20 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">

        <div className="rounded-3xl bg-gradient-to-r from-cyan-950/60 via-slate-900 to-indigo-950/60 border border-cyan-500/30 p-8 sm:p-12 shadow-2xl relative">

          <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
            Ready to experience effortless, adaptive travel?
          </h2>

          <p className="mt-4 text-base text-slate-300 max-w-xl mx-auto">
            Create a trip, generate an AI-powered itinerary, and test how
            TravelPilot adapts when your plans change.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">

            <button
              onClick={() => setCurrentPage('create')}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition shadow-lg shadow-cyan-500/20 cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400"
              aria-label="Start Planning Now"
            >
              Start Planning Now
            </button>

            <button
              onClick={() => setCurrentPage('disruptions')}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition border border-slate-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan-400"
              aria-label="Test Disruption Simulator"
            >
              Test Disruption Simulator
            </button>

          </div>

        </div>

      </section>

    </div>
  );
}