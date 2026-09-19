export const SAMPLE_INTERESTS = [
  'History',
  'Food',
  'Museums',
  'Photography',
  'Nature',
  'Shopping',
  'Adventure',
];

export const TRAVEL_STYLES = [
  {
    id: 'balanced',
    label: 'Balanced',
    desc: 'Mix of sights, local food, and leisure',
  },
  {
    id: 'relaxed',
    label: 'Relaxed & Slow',
    desc: 'Fewer stops, more time to soak in the atmosphere',
  },
  {
    id: 'fast',
    label: 'Fast-Paced Explorer',
    desc: 'Maximum highlights packed into each day',
  },
  {
    id: 'luxury',
    label: 'Boutique & Luxury',
    desc: 'High-end dining, private transit, premium stays',
  },
  {
    id: 'backpacker',
    label: 'Backpacker & Value',
    desc: 'Smart budget choices and authentic local experiences',
  },
];

export const TRANSPORT_PREFERENCES = [
  {
    id: 'public',
    label: 'Public Transit (Metro & Train)',
  },
  {
    id: 'walking',
    label: 'Walking & Foot Exploration',
  },
  {
    id: 'rideshare',
    label: 'Rideshare & Taxis',
  },
  {
    id: 'rental',
    label: 'Rental Car / Self-Drive',
  },
];

/*
 * No hard-coded demo trip is kept here.
 *
 * Trips are now created dynamically from the Trip Creation page
 * and stored/managed by the backend.
 *
 * INITIAL_TRIP is intentionally kept as null for backward
 * compatibility with any component that may still import it.
 */
export const INITIAL_TRIP = null;

/*
 * Generic disruption presets.
 *
 * These presets intentionally do not mention a specific city,
 * venue, hotel, transport provider, currency, or activity.
 * The backend uses the actual active trip destination and
 * itinerary when processing the disruption.
 */
export const DISRUPTION_PRESETS = [
  {
    id: 'sim-cancel',
    title: 'Activity Cancelled',
    type: 'cancellation',
    icon: 'CalendarX',
    severity: 'critical',
    label: 'Activity Cancellation',
    description:
      'A planned activity becomes unavailable because of a sudden closure or cancellation.',
    defaultImpact:
      'A planned time slot becomes available and the itinerary may need an alternative activity.',
    defaultAiAction:
      'TravelPilot searches for a suitable alternative based on location, interests, timing, availability, and budget.',
  },

  {
    id: 'sim-delay',
    title: 'Transportation Delayed',
    type: 'delay',
    icon: 'ClockAlert',
    severity: 'warning',
    label: 'Transport Delay',
    description:
      'A planned transportation service is delayed and may affect upcoming activities.',
    defaultImpact:
      'Arrival time changes and one or more following activities may need to be rescheduled.',
    defaultAiAction:
      'TravelPilot recalculates travel time, checks schedule conflicts, and adjusts affected itinerary items.',
  },

  {
    id: 'sim-hotel',
    title: 'Hotel Unavailable',
    type: 'hotel',
    icon: 'Building2',
    severity: 'critical',
    label: 'Accommodation Unavailable',
    description:
      'The planned accommodation becomes unavailable and requires a replacement.',
    defaultImpact:
      'The accommodation booking needs to be replaced while preserving the trip budget and location preferences where possible.',
    defaultAiAction:
      'TravelPilot identifies alternative accommodation options and updates the affected part of the trip plan.',
  },

  {
    id: 'sim-budget',
    title: 'Budget Reduced',
    type: 'budget',
    icon: 'TrendingDown',
    severity: 'warning',
    label: 'Budget Reduction',
    description:
      'The traveler reduces the amount available for the remaining trip.',
    defaultImpact:
      'Remaining spending capacity becomes smaller and some planned expenses may no longer fit.',
    defaultAiAction:
      'TravelPilot recalculates the budget and replaces or adjusts expensive activities and transport options where necessary.',
  },

  {
    id: 'sim-custom',
    title: 'Custom Disruption',
    type: 'custom',
    icon: 'Sparkles',
    severity: 'info',
    label: 'Custom Travel Disruption',
    description:
      'A traveler-defined disruption affects the current itinerary.',
    defaultImpact:
      'The affected itinerary items may need to be rescheduled, replaced, or removed.',
    defaultAiAction:
      'TravelPilot analyzes the disruption and creates an updated plan while preserving the traveler’s preferences and constraints.',
  },
];

/*
 * Generic initial AI chat message.
 *
 * The assistant becomes trip-aware after a trip is created.
 */
export const INITIAL_CHAT_MESSAGES = [
  {
    id: 'msg-1',
    sender: 'ai',
    text:
      'Hello! I am your TravelPilot AI co-pilot. Create a trip and I will help you plan, monitor, and adapt your itinerary.',
    timestamp: 'Now',
    suggestions: [
      'Check my budget',
      'Show my itinerary',
      'What should I do next?',
      'Help me adjust my trip',
    ],
  },
];