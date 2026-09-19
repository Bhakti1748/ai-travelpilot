import React, { useState } from 'react';
import {
  Calendar,
  Clock,
  MapPin,
  DollarSign,
  Train,
  AlertTriangle,
  Sparkles,
  Plus,
  Compass,
  ArrowDown,
  Filter,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';
import { api } from '../services/api';
import DisruptionAlertBanner from '../components/DisruptionAlertBanner';

export default function ItineraryPage() {
  const {
    activeTrip,
    setCurrentPage,
    refreshTripData,
    showToast,
  } = useTrip();

  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [showAddModal, setShowAddModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // New activity modal state
  const [newTime, setNewTime] = useState('17:00');
  const [newTitle, setNewTitle] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [newDuration, setNewDuration] = useState('1h 30m');
  const [newCost, setNewCost] = useState(0);
  const [newTransport, setNewTransport] = useState('Public Transit');
  const [newCategory, setNewCategory] = useState('Sightseeing');

  const curr = activeTrip?.currency || 'INR';
  const itinerary = activeTrip?.itinerary || [];

  const currentDay = itinerary[selectedDayIndex] || itinerary[0] || {
    dayNumber: 1,
    date: activeTrip?.startDate || '',
    title: 'Plan for this day',
    activities: [],
  };

  const activities = currentDay.activities || [];

  const filteredActivities = activities.filter((act) => {
    if (categoryFilter === 'All') return true;

    return (
      (act.category || '').toLowerCase() ===
      categoryFilter.toLowerCase()
    );
  });

  const dayTotalCost = activities.reduce(
    (sum, act) => sum + (Number(act.cost) || 0),
    0
  );

  const handleAddActivity = async (e) => {
    e.preventDefault();

    if (!activeTrip) {
      showToast(
        'No Active Trip',
        'Create or select a trip before adding an activity.',
        'warning'
      );
      return;
    }

    if (!newTitle.trim()) return;

    setIsSaving(true);

    try {
      const newAct = {
        id: `act-custom-${Date.now()}`,
        day_number: currentDay.dayNumber,
        date: currentDay.date,
        time: newTime,
        title: newTitle.trim(),
        duration: newDuration,
        location: newLocation.trim() || 'Location not specified',
        cost: Number(newCost) || 0,
        currency: curr,
        transportation: newTransport.trim() || 'Public Transit',
        status: 'Confirmed',
        category: newCategory || 'Sightseeing',
        notes: 'Custom traveler addition.',
      };

      const allItems = [];

      itinerary.forEach((day) => {
        const acts =
          day.dayNumber === currentDay.dayNumber
            ? [...day.activities, newAct]
            : [...day.activities];

        acts.sort((a, b) =>
          (a.time || '').localeCompare(b.time || '')
        );

        acts.forEach((act) => {
          allItems.push({
            day_number: day.dayNumber,
            date: day.date,
            time: act.time,
            title: act.title,
            category: act.category,
            duration: act.duration,
            location: act.location,
            cost: Number(act.cost) || 0,
            currency: act.currency || curr,
            transportation:
              act.transportation || 'Public Transit',
            status: act.status || 'Confirmed',
            notes: act.notes || '',
          });
        });
      });

      await api.updateItinerary(activeTrip.id, allItems);
      await refreshTripData(activeTrip.id);

      setShowAddModal(false);
      setNewTitle('');
      setNewLocation('');
      setNewCost(0);
      setNewTime('17:00');
      setNewDuration('1h 30m');
      setNewTransport('Public Transit');
      setNewCategory('Sightseeing');

      showToast(
        'Activity Saved',
        `Added "${newTitle.trim()}" to Day ${currentDay.dayNumber}.`,
        'success'
      );
    } catch (err) {
      console.error('Failed to save activity:', err);

      showToast(
        'Save Failed',
        err?.message || 'Unable to save the activity.',
        'warning'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <DisruptionAlertBanner />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4 mb-6">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-cyan-400 mb-1">
            <Sparkles
              className="w-3.5 h-3.5"
              aria-hidden="true"
            />

            <span>Autonomous Dynamic Timeline</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Itinerary
            {activeTrip?.destination
              ? ` • ${activeTrip.destination}`
              : ''}
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Each activity is coordinated with transit buffers,
            opening hours, budget constraints, and disruption
            alternatives.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            disabled={!activeTrip}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition shadow-md shadow-cyan-500/20 flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Plus
              className="w-4 h-4"
              aria-hidden="true"
            />

            <span>Add Activity</span>
          </button>

          <button
            type="button"
            onClick={() => setCurrentPage('disruptions')}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold text-amber-300 hover:text-amber-200 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 transition flex items-center space-x-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300"
          >
            <AlertTriangle
              className="w-4 h-4"
              aria-hidden="true"
            />

            <span>Simulate Disruption</span>
          </button>
        </div>
      </div>

      {/* No active trip */}
      {!activeTrip ? (
        <div className="my-12 p-8 rounded-3xl bg-slate-900/60 border border-slate-800 text-center max-w-lg mx-auto">
          <Compass
            className="w-12 h-12 text-slate-600 mx-auto mb-4"
          />

          <h3 className="text-lg font-bold text-white">
            No active trip
          </h3>

          <p className="text-sm text-slate-400 mt-2 mb-5">
            Create a trip to generate and manage your adaptive
            itinerary.
          </p>

          <button
            type="button"
            onClick={() => setCurrentPage('create')}
            className="px-5 py-2.5 bg-cyan-400 text-slate-950 font-semibold text-xs rounded-xl hover:bg-cyan-300 transition shadow-md cursor-pointer"
          >
            Create Trip
          </button>
        </div>
      ) : itinerary.length === 0 ? (
        /* No itinerary */
        <div className="my-12 p-8 rounded-3xl bg-slate-900/60 border border-slate-800 text-center max-w-md mx-auto">
          <Calendar
            className="w-10 h-10 text-slate-600 mx-auto mb-3"
          />

          <h3 className="text-base font-bold text-white">
            No itinerary generated yet
          </h3>

          <p className="text-xs text-slate-400 mt-1 mb-4">
            Create a plan with the AI trip planner to generate
            an adaptive and optimized schedule.
          </p>

          <button
            type="button"
            onClick={() => setCurrentPage('create')}
            className="px-5 py-2.5 bg-cyan-400 text-slate-950 font-semibold text-xs rounded-xl hover:bg-cyan-300 transition shadow-md cursor-pointer"
          >
            Generate Adaptive Itinerary
          </button>
        </div>
      ) : (
        <>
          {/* Day Selector Navigation Tabs */}
          <div
            className="flex items-center space-x-2.5 overflow-x-auto pb-4 scrollbar-none"
            role="tablist"
          >
            {itinerary.map((day, idx) => {
              const isSelected = selectedDayIndex === idx;

              return (
                <button
                  key={day.dayNumber}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  onClick={() => setSelectedDayIndex(idx)}
                  className={`px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer flex items-center space-x-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                    isSelected
                      ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/25 scale-[1.02]'
                      : 'bg-slate-900/90 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <Calendar
                    className="w-3.5 h-3.5"
                    aria-hidden="true"
                  />

                  <span>Day {day.dayNumber}</span>

                  <span
                    className={`text-[11px] ${
                      isSelected
                        ? 'text-slate-950/80 font-mono'
                        : 'text-slate-500 font-mono'
                    }`}
                  >
                    ({day.date})
                  </span>
                </button>
              );
            })}
          </div>

          {/* Selected Day Focus Banner */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-md">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider font-bold">
                Day {currentDay.dayNumber} Overview
              </span>

              <h2 className="text-lg sm:text-xl font-bold text-white mt-0.5">
                {currentDay.title || 'Daily Plan'}
              </h2>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <div className="px-3.5 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 shadow-inner">
                <span className="text-slate-400">
                  Scheduled Stops:
                </span>{' '}
                <span className="font-bold text-white">
                  {activities.length}
                </span>
              </div>

              <div className="px-3.5 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 shadow-inner">
                <span className="text-slate-400">
                  Day Budget:
                </span>{' '}
                <span className="font-bold text-emerald-400">
                  {curr} {dayTotalCost.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Category Filter Chips */}
          <div className="flex items-center space-x-2 mb-6 text-xs overflow-x-auto pb-1">
            <span className="text-slate-400 flex items-center mr-1 text-[11px] font-medium">
              <Filter
                className="w-3 h-3 mr-1"
                aria-hidden="true"
              />
              Filter by:
            </span>

            {[
              'All',
              'Sightseeing',
              'Historical',
              'Museum',
              'Food',
              'Photography',
              'Nature',
              'Walking',
            ].map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={`px-3 py-1 rounded-lg text-xs transition cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400 ${
                  categoryFilter.toLowerCase() ===
                  cat.toLowerCase()
                    ? 'bg-slate-800 text-cyan-400 border border-slate-700 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Timeline List */}
          {filteredActivities.length === 0 ? (
            <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
              <Compass
                className="w-8 h-8 text-slate-600 mx-auto mb-2"
              />

              <p>
                No activities match the "{categoryFilter}" filter
                on this day.
              </p>

              <button
                type="button"
                onClick={() => setCategoryFilter('All')}
                className="mt-2 text-cyan-400 hover:underline text-xs"
              >
                Reset filter
              </button>
            </div>
          ) : (
            <div className="relative pl-6 sm:pl-8 space-y-8 before:absolute before:left-3 sm:before:left-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-gradient-to-b before:from-cyan-500 before:via-indigo-500 before:to-slate-800">
              {filteredActivities.map((activity, idx) => {
                const isDelayed =
                  activity.status === 'Delayed';

                const isRerouted =
                  activity.status === 'Rerouted' ||
                  activity.status === 'Substituted';

                return (
                  <div
                    key={activity.id || idx}
                    className="relative group"
                  >
                    {/* Timeline Node */}
                    <div
                      className={`absolute -left-6 sm:-left-8 top-5 w-4 h-4 rounded-full border-2 transition-transform duration-300 group-hover:scale-125 ${
                        isDelayed
                          ? 'bg-amber-500 border-slate-950 shadow-md shadow-amber-500/50 animate-pulse'
                          : isRerouted
                          ? 'bg-indigo-400 border-slate-950 shadow-md shadow-indigo-500/50'
                          : 'bg-cyan-400 border-slate-950 shadow-md shadow-cyan-500/50'
                      }`}
                      aria-hidden="true"
                    />

                    {/* Activity Card */}
                    <article className="p-5 sm:p-6 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700/90 transition shadow-lg backdrop-blur-sm group-hover:shadow-cyan-500/5">
                      {/* Top Bar */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3.5 border-b border-slate-800/80 mb-3.5">
                        <div className="flex items-center space-x-3 flex-wrap">
                          <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono font-bold text-cyan-400 shadow-inner">
                            {activity.time || 'Time TBD'}
                          </span>

                          <h3 className="text-base font-bold text-white tracking-tight">
                            {activity.title ||
                              'Untitled Activity'}
                          </h3>

                          {activity.category && (
                            <span className="px-2 py-0.5 text-[10px] font-semibold rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                              {activity.category}
                            </span>
                          )}
                        </div>

                        {/* Status */}
                        <div className="flex items-center space-x-2 self-start sm:self-auto">
                          <span
                            className={`px-2.5 py-0.5 text-[11px] font-bold rounded-full border tracking-wide uppercase ${
                              isDelayed
                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30 animate-pulse'
                                : isRerouted
                                ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                                : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                            }`}
                          >
                            {activity.status ||
                              'Planned'}
                          </span>
                        </div>
                      </div>

                      {/* Key Attributes */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                        {/* Duration */}
                        <div className="flex items-center space-x-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                          <Clock
                            className="w-4 h-4 text-cyan-400 shrink-0"
                            aria-hidden="true"
                          />

                          <div>
                            <span className="text-[10px] uppercase font-mono text-slate-400 block leading-tight">
                              Duration
                            </span>

                            <span className="font-semibold text-white">
                              {activity.duration ||
                                'Duration TBD'}
                            </span>
                          </div>
                        </div>

                        {/* Location */}
                        <div className="flex items-center space-x-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                          <MapPin
                            className="w-4 h-4 text-rose-400 shrink-0"
                            aria-hidden="true"
                          />

                          <div className="truncate">
                            <span className="text-[10px] uppercase font-mono text-slate-400 block leading-tight">
                              Location
                            </span>

                            <span
                              className="font-semibold text-white truncate block"
                              title={activity.location}
                            >
                              {activity.location ||
                                'Location not specified'}
                            </span>
                          </div>
                        </div>

                        {/* Transportation */}
                        <div className="flex items-center space-x-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                          <Train
                            className="w-4 h-4 text-indigo-400 shrink-0"
                            aria-hidden="true"
                          />

                          <div className="truncate">
                            <span className="text-[10px] uppercase font-mono text-slate-400 block leading-tight">
                              Travel Transit
                            </span>

                            <span
                              className="font-semibold text-white truncate block"
                              title={
                                activity.transportation
                              }
                            >
                              {activity.transportation ||
                                'Public Transit'}
                            </span>
                          </div>
                        </div>

                        {/* Cost */}
                        <div className="flex items-center space-x-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
                          <DollarSign
                            className="w-4 h-4 text-emerald-400 shrink-0"
                            aria-hidden="true"
                          />

                          <div>
                            <span className="text-[10px] uppercase font-mono text-slate-400 block leading-tight">
                              Est. Cost
                            </span>

                            <span className="font-bold text-emerald-400">
                              {Number(activity.cost) > 0
                                ? `${activity.currency || curr} ${Number(
                                    activity.cost
                                  ).toLocaleString()}`
                                : 'Free Admission'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Notes */}
                      {activity.notes && (
                        <div className="mt-3.5 text-xs text-slate-300 bg-slate-950/70 p-3 rounded-xl border border-slate-800 flex items-start space-x-2.5">
                          <Sparkles
                            className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5"
                            aria-hidden="true"
                          />

                          <span className="leading-relaxed">
                            <strong className="text-white">
                              AI Note:
                            </strong>{' '}
                            {activity.notes}
                          </span>
                        </div>
                      )}
                    </article>

                    {/* Transit Bridge */}
                    {idx < filteredActivities.length - 1 && (
                      <div className="my-2.5 pl-6 flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
                        <ArrowDown
                          className="w-3.5 h-3.5 text-slate-600"
                          aria-hidden="true"
                        />

                        <span>
                          ~15–20 min transit buffer to next
                          scheduled stop
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Add Activity Modal */}
      {showAddModal && activeTrip && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 sm:p-8 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">
              Add Activity to Day {currentDay.dayNumber}
            </h3>

            <p className="text-xs text-slate-400 mb-4">
              TravelPilot will add this activity to the selected
              day and update the itinerary.
            </p>

            <form
              onSubmit={handleAddActivity}
              className="space-y-4 text-xs"
            >
              {/* Activity Title */}
              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Activity Title
                </label>

                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) =>
                    setNewTitle(e.target.value)
                  }
                  placeholder="Enter activity name"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              {/* Time + Duration */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1 font-medium">
                    Time
                  </label>

                  <input
                    type="time"
                    required
                    value={newTime}
                    onChange={(e) =>
                      setNewTime(e.target.value)
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 mb-1 font-medium">
                    Duration
                  </label>

                  <input
                    type="text"
                    value={newDuration}
                    onChange={(e) =>
                      setNewDuration(e.target.value)
                    }
                    placeholder="e.g. 1h 30m"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              {/* Location */}
              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Location
                </label>

                <input
                  type="text"
                  value={newLocation}
                  onChange={(e) =>
                    setNewLocation(e.target.value)
                  }
                  placeholder="Enter address or landmark"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              {/* Cost + Transport */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1 font-medium">
                    Cost ({curr})
                  </label>

                  <input
                    type="number"
                    min="0"
                    value={newCost}
                    onChange={(e) =>
                      setNewCost(Number(e.target.value))
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 mb-1 font-medium">
                    Transit Method
                  </label>

                  <input
                    type="text"
                    value={newTransport}
                    onChange={(e) =>
                      setNewTransport(e.target.value)
                    }
                    placeholder="Metro / Walk / Taxi"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              {/* Category */}
              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Category
                </label>

                <select
                  value={newCategory}
                  onChange={(e) =>
                    setNewCategory(e.target.value)
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                >
                  <option value="Sightseeing">
                    Sightseeing
                  </option>
                  <option value="Historical">
                    Historical
                  </option>
                  <option value="Museum">Museum</option>
                  <option value="Food">Food</option>
                  <option value="Photography">
                    Photography
                  </option>
                  <option value="Nature">Nature</option>
                  <option value="Walking">Walking</option>
                  <option value="Entertainment">
                    Entertainment
                  </option>
                  <option value="Shopping">Shopping</option>
                </select>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white transition cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2 rounded-xl bg-cyan-400 text-slate-950 font-bold hover:bg-cyan-300 transition cursor-pointer shadow-md shadow-cyan-500/20 disabled:opacity-50"
                >
                  {isSaving
                    ? 'Saving...'
                    : 'Save Activity'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}