import React from 'react';
import { TripProvider, useTrip } from './hooks/useTrip';
import Navbar from './components/Navbar';
import Footer from './components/Footer';

// Pages
import LandingPage from './pages/LandingPage';
import TripCreatePage from './pages/TripCreatePage';
import DashboardPage from './pages/DashboardPage';
import ItineraryPage from './pages/ItineraryPage';
import BudgetPage from './pages/BudgetPage';
import DisruptionPage from './pages/DisruptionPage';
import AIAssistantPage from './pages/AIAssistantPage';

import { Sparkles, X, AlertTriangle, CheckCircle2, Info } from 'lucide-react';

function MainContent() {
  const { currentPage, toastMessage, setToastMessage, backendError, refreshTripData } = useTrip();

  const renderPage = () => {
    switch (currentPage) {
      case 'landing':
        return <LandingPage />;
      case 'create':
        return <TripCreatePage />;
      case 'dashboard':
        return <DashboardPage />;
      case 'itinerary':
        return <ItineraryPage />;
      case 'budget':
        return <BudgetPage />;
      case 'disruptions':
        return <DisruptionPage />;
      case 'assistant':
        return <AIAssistantPage />;
      default:
        return <LandingPage />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      <Navbar />

      {/* Backend Offline / Availability Notice */}
      {backendError && (
        <div className="bg-amber-950/80 border-b border-amber-500/30 px-4 py-2 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Backend Offline:</strong> Unable to connect to TravelPilot API at http://127.0.0.1:8000. Running with cached state.
            </span>
          </div>
          <button
            onClick={() => refreshTripData()}
            className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-semibold border border-amber-500/40 text-[11px] transition cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Main Page Body */}
      <main className="flex-1">{renderPage()}</main>

      {/* Floating Global Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-slate-900 border border-slate-700/80 rounded-2xl p-4 shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-5 duration-300">
          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
              {toastMessage.type === 'warning' ? (
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              ) : toastMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <Sparkles className="w-4 h-4 text-cyan-400" />
              )}
            </div>
            <div className="flex-1 pr-2">
              <h4 className="text-xs font-bold text-white">
                {toastMessage.title}
              </h4>
              <p className="text-xs text-slate-300 mt-0.5 leading-snug">
                {toastMessage.message}
              </p>
            </div>
            <button
              onClick={() => setToastMessage(null)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <TripProvider>
      <MainContent />
    </TripProvider>
  );
}
