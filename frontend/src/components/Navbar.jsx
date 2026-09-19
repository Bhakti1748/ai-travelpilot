import React, { useState } from 'react';

import {
  Compass,
  Plane,
  LayoutDashboard,
  Calendar,
  DollarSign,
  AlertTriangle,
  Bot,
  PlusCircle,
  Menu,
  X,
  RotateCcw,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';

export default function Navbar() {
  const {
    currentPage,
    setCurrentPage,
    activeTrip,
    resetToDemoTrip,
  } = useTrip();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const unresolvedAlertsCount = (activeTrip?.activeAlerts || []).filter(
    (a) => !a.resolved
  ).length;

  const navLinks = [
    { id: 'landing', label: 'Home', icon: Compass },
    { id: 'create', label: 'Plan Trip', icon: PlusCircle },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'itinerary', label: 'Itinerary', icon: Calendar },
    { id: 'budget', label: 'Budget', icon: DollarSign },
    {
      id: 'disruptions',
      label: 'Disruptions',
      icon: AlertTriangle,
      badge: unresolvedAlertsCount > 0 ? unresolvedAlertsCount : null,
    },
    {
      id: 'assistant',
      label: 'AI Co-pilot',
      icon: Bot,
      pulse: true,
    },
  ];

  const handleNav = (id) => {
    setCurrentPage(id);
    setMobileMenuOpen(false);
  };

  const handleClearTrip = () => {
    resetToDemoTrip();
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/85 border-b border-slate-800/80 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Brand Logo */}
          <div
            onClick={() => handleNav('landing')}
            className="flex items-center space-x-3 cursor-pointer group select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-xl"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                handleNav('landing');
              }
            }}
            aria-label="TravelPilot Home"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-purple-500 p-0.5 shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Plane
                  className="w-5 h-5 text-cyan-400 transform -rotate-45 group-hover:scale-110 transition"
                  aria-hidden="true"
                />
              </div>
            </div>

            <div className="flex flex-col">
              <div className="flex items-center space-x-1.5">
                <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                  TravelPilot
                </span>

                <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 rounded-full">
                  AI AGENT
                </span>
              </div>

              <span className="text-[10px] text-slate-400 hidden sm:inline font-medium">
                Autonomous Travel & Disruption Co-Pilot
              </span>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav
            className="hidden md:flex items-center space-x-1"
            aria-label="Main Navigation"
          >
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = currentPage === link.id;

              return (
                <button
                  key={link.id}
                  onClick={() => handleNav(link.id)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`relative flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                    isActive
                      ? 'bg-slate-900 text-cyan-400 shadow-sm border border-cyan-500/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-900/60'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? 'text-cyan-400' : 'text-slate-400'
                    } ${
                      link.pulse
                        ? 'animate-pulse text-indigo-400'
                        : ''
                    }`}
                    aria-hidden="true"
                  />

                  <span>{link.label}</span>

                  {link.badge && (
                    <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold bg-amber-400 text-slate-950 rounded-full shadow-sm">
                      {link.badge}
                    </span>
                  )}

                  {isActive && (
                    <span className="absolute bottom-0 left-3 right-3 h-0.5 bg-cyan-400 rounded-full shadow-sm shadow-cyan-400/50" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Trip Destination Pill & Clear Button */}
          <div className="hidden lg:flex items-center space-x-3">
            <div
              className="flex items-center space-x-2 px-3 py-1.5 bg-slate-900/90 border border-slate-800 rounded-full text-xs text-slate-300 shadow-sm"
              title={
                activeTrip?.destination
                  ? `Active trip: ${activeTrip.destination}`
                  : 'No trip selected'
              }
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  activeTrip
                    ? 'bg-emerald-400 animate-pulse'
                    : 'bg-slate-500'
                }`}
                aria-hidden="true"
              />

              <span className="text-slate-400 font-medium">
                Trip:
              </span>

              <span className="font-semibold text-white truncate max-w-[140px]">
                {activeTrip?.destination || 'No trip selected'}
              </span>
            </div>

            {activeTrip && (
              <button
                onClick={handleClearTrip}
                title="Clear current trip"
                aria-label="Clear current trip"
                className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl border border-slate-800 transition text-xs flex items-center space-x-1 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                <RotateCcw
                  className="w-3.5 h-3.5"
                  aria-hidden="true"
                />

                <span className="text-[11px] font-medium">
                  Clear Trip
                </span>
              </button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center space-x-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              aria-label={
                mobileMenuOpen
                  ? 'Close Navigation Menu'
                  : 'Open Navigation Menu'
              }
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-950/95 border-b border-slate-800 px-4 pt-2 pb-5 space-y-1.5 backdrop-blur-2xl animate-in fade-in slide-in-from-top-2 duration-200">

          <div className="pb-2 border-b border-slate-800 mb-2 flex items-center justify-between">
            <div className="min-w-0">
              <span className="text-xs text-slate-400 font-medium">
                Active trip:
              </span>

              <div className="text-xs font-semibold text-white truncate max-w-[220px]">
                {activeTrip?.destination || 'No trip selected'}
              </div>
            </div>

            {activeTrip && (
              <button
                onClick={handleClearTrip}
                className="text-xs text-cyan-400 hover:underline flex items-center space-x-1 cursor-pointer ml-3"
                aria-label="Clear current trip"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Clear Trip</span>
              </button>
            )}
          </div>

          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = currentPage === link.id;

            return (
              <button
                key={link.id}
                onClick={() => handleNav(link.id)}
                className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                    : 'text-slate-300 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className="w-4 h-4" />
                  <span>{link.label}</span>
                </div>

                {link.badge && (
                  <span className="px-2 py-0.5 text-xs font-bold bg-amber-400 text-slate-950 rounded-full">
                    {link.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </header>
  );
}