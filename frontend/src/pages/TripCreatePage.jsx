import React, { useMemo, useState } from 'react';
import {
  ArrowLeft,
  CalendarDays,
  MapPin,
  Wallet,
  Users,
  Sparkles,
  Utensils,
  Trees,
  Landmark,
  ShoppingBag,
  Camera,
  Music,
} from 'lucide-react';

import { useTrip } from '../hooks/useTrip';
import {
  SAMPLE_INTERESTS,
  TRAVEL_STYLES,
  TRANSPORT_PREFERENCES,
} from '../data/mockTravelData';

const getDefaultStartDate = () => {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return date.toISOString().split('T')[0];
};

const getDefaultEndDate = () => {
  const date = new Date();
  date.setDate(date.getDate() + 11);
  return date.toISOString().split('T')[0];
};

const interestIcons = {
  Food: Utensils,
  Nature: Trees,
  History: Landmark,
  Shopping: ShoppingBag,
  Photography: Camera,
  Entertainment: Music,
  Museums: Landmark,
};

export default function TripCreatePage() {
  const { createTrip, loading, setCurrentPage } = useTrip();

  const [destination, setDestination] = useState('');
  const [startDate, setStartDate] = useState(getDefaultStartDate());
  const [endDate, setEndDate] = useState(getDefaultEndDate());
  const [budget, setBudget] = useState(50000);
  const [travelers, setTravelers] = useState(2);

  const [selectedInterests, setSelectedInterests] = useState([
    'Food',
    'Nature',
  ]);

  const [travelStyle, setTravelStyle] = useState('balanced');

  const defaultTransport =
    TRANSPORT_PREFERENCES?.[0]?.label ||
    TRANSPORT_PREFERENCES?.[0] ||
    'Public Transit';

  const [transportPreference, setTransportPreference] =
    useState(defaultTransport);

  const [error, setError] = useState('');

  const tripDuration = useMemo(() => {
    if (!startDate || !endDate) return 0;

    const start = new Date(startDate);
    const end = new Date(endDate);

    const difference =
      Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;

    return difference > 0 ? difference : 0;
  }, [startDate, endDate]);

  const toggleInterest = (interest) => {
    setSelectedInterests((current) => {
      if (current.includes(interest)) {
        return current.filter((item) => item !== interest);
      }

      return [...current, interest];
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    const trimmedDestination = destination.trim();

    if (!trimmedDestination) {
      setError('Please enter a destination.');
      return;
    }

    if (!startDate || !endDate) {
      setError('Please select both start and end dates.');
      return;
    }

    if (endDate < startDate) {
      setError('End date must be after the start date.');
      return;
    }

    if (!budget || Number(budget) <= 0) {
      setError('Please enter a valid budget.');
      return;
    }

    if (!travelers || Number(travelers) <= 0) {
      setError('Please enter the number of travelers.');
      return;
    }

    if (selectedInterests.length === 0) {
      setError('Please select at least one interest.');
      return;
    }

    try {
      /*
       * Currency is intentionally NOT sent from the frontend.
       *
       * The backend determines the local currency from the destination.
       *
       * Examples:
       * Mumbai, India  -> INR
       * Tokyo, Japan   -> JPY
       * Paris, France  -> EUR
       * London, UK     -> GBP
       * New York, USA  -> USD
       */
      const tripData = {
        destination: trimmedDestination,
        start_date: startDate,
        end_date: endDate,
        budget: Number(budget),
        travelers: Number(travelers),
        interests: selectedInterests,
        travel_style: travelStyle,
        transport_preference: transportPreference,
      };

      const createdTrip = await createTrip(tripData);

      if (createdTrip) {
        setCurrentPage('dashboard');
      }
    } catch (err) {
      console.error('Trip creation failed:', err);

      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Unable to create the trip. Please try again.'
      );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <button
            type="button"
            onClick={() => setCurrentPage('landing')}
            className="mb-5 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800 hover:text-white"
          >
            <ArrowLeft size={17} />
            Back
          </button>

          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-indigo-500/15 p-3">
              <Sparkles className="text-indigo-400" size={28} />
            </div>

            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Plan a new trip
              </h1>

              <p className="mt-2 max-w-2xl text-slate-400">
                Tell TravelPilot where you want to go, when you are traveling,
                and what you enjoy. The AI planner will build and optimize
                your itinerary around your preferences.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Main form */}
            <div className="space-y-6 lg:col-span-2">
              {/* Destination */}
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="mb-5 flex items-center gap-3">
                  <MapPin className="text-indigo-400" size={21} />

                  <div>
                    <h2 className="font-semibold">Destination</h2>
                    <p className="text-sm text-slate-400">
                      Enter any city, region, or destination.
                    </p>
                  </div>
                </div>

                <input
                  type="text"
                  value={destination}
                  onChange={(event) => setDestination(event.target.value)}
                  placeholder="e.g. Tokyo, Japan"
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                />

                <p className="mt-2 text-xs text-slate-500">
                  TravelPilot will retrieve destination activity data and
                  determine the local currency automatically.
                </p>
              </section>

              {/* Dates */}
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="mb-5 flex items-center gap-3">
                  <CalendarDays className="text-indigo-400" size={21} />

                  <div>
                    <h2 className="font-semibold">Travel dates</h2>
                    <p className="text-sm text-slate-400">
                      Choose your trip duration.
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm text-slate-300">
                      Start date
                    </label>

                    <input
                      type="date"
                      value={startDate}
                      onChange={(event) => setStartDate(event.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-sm text-slate-300">
                      End date
                    </label>

                    <input
                      type="date"
                      value={endDate}
                      min={startDate}
                      onChange={(event) => setEndDate(event.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {tripDuration > 0 && (
                  <div className="mt-4 rounded-xl bg-indigo-500/10 px-4 py-3 text-sm text-indigo-300">
                    {tripDuration} day
                    {tripDuration !== 1 ? 's' : ''} trip
                  </div>
                )}
              </section>

              {/* Budget */}
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="mb-5 flex items-center gap-3">
                  <Wallet className="text-indigo-400" size={21} />

                  <div>
                    <h2 className="font-semibold">Budget</h2>
                    <p className="text-sm text-slate-400">
                      Set the total budget you want TravelPilot to plan around.
                    </p>
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-sm text-slate-300">
                    Total budget
                  </label>

                  <input
                    type="number"
                    min="1"
                    value={budget}
                    onChange={(event) => setBudget(event.target.value)}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-indigo-500"
                  />

                  <p className="mt-2 text-xs text-slate-500">
                    Currency will be detected automatically from your
                    destination.
                  </p>
                </div>
              </section>

              {/* Travelers */}
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="mb-5 flex items-center gap-3">
                  <Users className="text-indigo-400" size={21} />

                  <div>
                    <h2 className="font-semibold">Travelers</h2>
                    <p className="text-sm text-slate-400">
                      How many people are traveling?
                    </p>
                  </div>
                </div>

                <input
                  type="number"
                  min="1"
                  max="50"
                  value={travelers}
                  onChange={(event) => setTravelers(event.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-indigo-500 sm:max-w-xs"
                />
              </section>

              {/* Interests */}
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="mb-5">
                  <h2 className="font-semibold">Interests</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Select the experiences you want included in your itinerary.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                  {SAMPLE_INTERESTS.map((interest) => {
                    const label =
                      typeof interest === 'string'
                        ? interest
                        : interest.label || interest.name;

                    const Icon = interestIcons[label] || Sparkles;

                    const selected = selectedInterests.includes(label);

                    return (
                      <button
                        key={label}
                        type="button"
                        onClick={() => toggleInterest(label)}
                        className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
                          selected
                            ? 'border-indigo-500 bg-indigo-500/15 text-indigo-300'
                            : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-600'
                        }`}
                      >
                        <Icon size={18} />

                        <span className="text-sm font-medium">{label}</span>
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* Preferences */}
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="mb-5">
                  <h2 className="font-semibold">Travel preferences</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Help the planner understand how you like to travel.
                  </p>
                </div>

                <div className="space-y-5">
                  <div>
                    <label className="mb-2 block text-sm text-slate-300">
                      Travel style
                    </label>

                    <select
                      value={travelStyle}
                      onChange={(event) => setTravelStyle(event.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-indigo-500"
                    >
                      {TRAVEL_STYLES.map((style) => {
                        const value =
                          typeof style === 'string'
                            ? style
                            : style.value || style.id;

                        const label =
                          typeof style === 'string'
                            ? style
                            : style.label || style.name;

                        return (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        );
                      })}
                    </select>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm text-slate-300">
                      Preferred transportation
                    </label>

                    <select
                      value={transportPreference}
                      onChange={(event) =>
                        setTransportPreference(event.target.value)
                      }
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-indigo-500"
                    >
                      {TRANSPORT_PREFERENCES.map((transport) => {
                        const value =
                          typeof transport === 'string'
                            ? transport
                            : transport.value ||
                              transport.id ||
                              transport.label;

                        const label =
                          typeof transport === 'string'
                            ? transport
                            : transport.label || transport.name;

                        return (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                </div>
              </section>
            </div>

            {/* Summary */}
            <aside className="lg:sticky lg:top-6 lg:self-start">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
                <h2 className="text-lg font-semibold">Trip summary</h2>

                <div className="mt-5 space-y-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Destination
                    </p>

                    <p className="mt-1 text-sm text-slate-200">
                      {destination.trim() || 'Not selected'}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Dates
                    </p>

                    <p className="mt-1 text-sm text-slate-200">
                      {startDate && endDate
                        ? `${startDate} → ${endDate}`
                        : 'Not selected'}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Duration
                    </p>

                    <p className="mt-1 text-sm text-slate-200">
                      {tripDuration > 0
                        ? `${tripDuration} day${
                            tripDuration !== 1 ? 's' : ''
                          }`
                        : '—'}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Budget
                    </p>

                    <p className="mt-1 text-sm text-slate-200">
                      {Number(budget || 0).toLocaleString()}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      Local currency will be determined from the destination.
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Travelers
                    </p>

                    <p className="mt-1 text-sm text-slate-200">
                      {travelers || 0}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Interests
                    </p>

                    <div className="mt-2 flex flex-wrap gap-2">
                      {selectedInterests.length > 0 ? (
                        selectedInterests.map((interest) => (
                          <span
                            key={interest}
                            className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300"
                          >
                            {interest}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-slate-500">
                          None selected
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {error && (
                  <div className="mt-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Sparkles size={18} />

                  {loading ? 'Creating trip...' : 'Create & Plan Trip'}
                </button>

                <p className="mt-3 text-center text-xs leading-relaxed text-slate-500">
                  TravelPilot will use your destination, preferences, budget,
                  and dates to generate an optimized itinerary.
                </p>
              </div>
            </aside>
          </div>
        </form>
      </div>
    </div>
  );
}