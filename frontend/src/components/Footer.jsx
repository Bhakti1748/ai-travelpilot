import { Plane, Sparkles, ShieldCheck, Zap } from 'lucide-react';
import { useTrip } from '../hooks/useTrip';

export default function Footer() {
  const { setCurrentPage } = useTrip();

  return (
    <footer className="mt-20 border-t border-slate-900 bg-slate-950/60 backdrop-blur-sm text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-slate-950 shadow-md">
              <Plane className="w-4 h-4 transform -rotate-45 text-white" />
            </div>
            <div>
              <span className="font-bold text-white tracking-tight text-sm">
                TravelPilot
              </span>
              <p className="text-[11px] text-slate-400">
                Autonomous AI Travel Planning & Dynamic Disruption Management
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-6">
            <button
              onClick={() => setCurrentPage('landing')}
              className="hover:text-cyan-400 transition"
            >
              Home
            </button>
            <button
              onClick={() => setCurrentPage('create')}
              className="hover:text-cyan-400 transition"
            >
              Trip Planner
            </button>
            <button
              onClick={() => setCurrentPage('dashboard')}
              className="hover:text-cyan-400 transition"
            >
              Dashboard
            </button>
            <button
              onClick={() => setCurrentPage('disruptions')}
              className="hover:text-cyan-400 transition"
            >
              Disruption Center
            </button>
            <button
              onClick={() => setCurrentPage('assistant')}
              className="hover:text-cyan-400 transition flex items-center space-x-1"
            >
              <Sparkles className="w-3 h-3 text-cyan-400" />
              <span>AI Co-pilot</span>
            </button>
          </div>

          <div className="flex items-center space-x-2 text-slate-400 text-[11px]">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
              <Zap className="w-3 h-3 text-cyan-400 mr-1" />
              Hackathon Ready
            </span>
            <span>•</span>
            <span>React + Vite + FastAPI</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
