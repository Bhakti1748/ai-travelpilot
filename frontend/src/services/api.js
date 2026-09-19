/**
 * TravelPilot API Service Layer
 * Real REST API client connected to FastAPI + SQLite backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const BACKEND_FALLBACK = 'http://localhost:8000/api';

/**
 * Standard HTTP fetch wrapper with timeout and fallback
 * to direct backend URL.
 */
async function request(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const cleanEndpoint = endpoint.startsWith('/')
    ? endpoint
    : `/${endpoint}`;

  const url = `${API_BASE}${cleanEndpoint}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errDetail = `HTTP ${res.status} ${res.statusText}`;

      try {
        const errorData = await res.json();
        errDetail =
          errorData.detail ||
          errorData.error ||
          errDetail;
      } catch (_) {}

      throw new Error(errDetail);
    }

    return await res.json();
  } catch (err) {
    // If relative API path failed, try direct backend URL.
    if (
      API_BASE.startsWith('/') &&
      !endpoint.startsWith('http')
    ) {
      try {
        const fallbackUrl =
          `${BACKEND_FALLBACK}${cleanEndpoint}`;

        const fallbackRes = await fetch(fallbackUrl, {
          ...options,
          headers,
        });

        if (!fallbackRes.ok) {
          let errDetail = `HTTP ${fallbackRes.status}`;

          try {
            const errorData = await fallbackRes.json();

            errDetail =
              errorData.detail ||
              errorData.error ||
              errDetail;
          } catch (_) {}

          throw new Error(errDetail);
        }

        return await fallbackRes.json();
      } catch (fallbackErr) {
        throw new Error(
          `API Request failed: ${err.message}`
        );
      }
    }

    throw err;
  }
}

export const api = {
  /**
   * Health check to test backend connectivity.
   */
  async checkHealth() {
    try {
      return await request('/health', {
        method: 'GET',
      });
    } catch (err) {
      return {
        status: 'offline',
        message: 'Backend unavailable',
        error: err.message,
      };
    }
  },

  /**
   * List all registered trips.
   */
  async listTrips() {
    return await request('/trips', {
      method: 'GET',
    });
  },

  /**
   * Fetch trip by ID.
   */
  async getTrip(tripId) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    return await request(
      `/trips/${encodeURIComponent(tripId)}`,
      {
        method: 'GET',
      }
    );
  },

  /**
   * Fetch the active/latest trip.
   *
   * There is intentionally NO hardcoded demo trip.
   */
  async getActiveTrip(preferredId = null) {
    try {
      if (preferredId) {
        try {
          return await this.getTrip(preferredId);
        } catch (_) {
          // Continue to latest trip fallback.
        }
      }

      const trips = await this.listTrips();

      if (Array.isArray(trips) && trips.length > 0) {
        return trips[0];
      }

      throw new Error(
        'No trips found. Create a trip to get started.'
      );
    } catch (err) {
      console.warn(
        'Could not fetch active trip from backend:',
        err.message
      );

      throw err;
    }
  },

  /**
   * Create a new trip.
   *
   * POST /api/trips
   */
  async createTrip(tripPayload) {
    if (!tripPayload?.destination?.trim()) {
      throw new Error('Destination is required.');
    }

    const payload = {
      destination: tripPayload.destination.trim(),

      start_date:
        tripPayload.startDate ||
        tripPayload.start_date,

      end_date:
        tripPayload.endDate ||
        tripPayload.end_date,

      budget:
        Number(tripPayload.budget) || 100000,

      currency:
        tripPayload.currency || 'INR',

      travelers:
        Number(tripPayload.travelers) || 1,

      interests:
        Array.isArray(tripPayload.interests)
          ? tripPayload.interests
          : [],

      travel_style:
        tripPayload.travelStyle ||
        tripPayload.travel_style ||
        'Balanced',

      transport_preference:
        tripPayload.transportPreference ||
        tripPayload.transport_preference ||
        'Public Transit',

      auto_generate_itinerary: false,
    };

    return await request('/trips', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Generate adaptive itinerary for a trip.
   *
   * POST /api/trips/{trip_id}/itinerary/generate
   */
  async generateItinerary(tripId) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    return await request(
      `/trips/${encodeURIComponent(tripId)}/itinerary/generate`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Fetch day-by-day itinerary.
   *
   * GET /api/trips/{trip_id}/itinerary
   */
  async getItinerary(tripId) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    return await request(
      `/trips/${encodeURIComponent(tripId)}/itinerary`,
      {
        method: 'GET',
      }
    );
  },

  /**
   * Replace or bulk update itinerary items.
   *
   * PUT /api/trips/{trip_id}/itinerary
   */
  async updateItinerary(tripId, items) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    return await request(
      `/trips/${encodeURIComponent(tripId)}/itinerary`,
      {
        method: 'PUT',
        body: JSON.stringify({
          items: Array.isArray(items) ? items : [],
        }),
      }
    );
  },

  /**
   * Fetch financial status and budget breakdown.
   *
   * GET /api/trips/{trip_id}/budget
   */
  async getBudget(tripId) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    return await request(
      `/trips/${encodeURIComponent(tripId)}/budget`,
      {
        method: 'GET',
      }
    );
  },

  /**
   * Simulate a travel disruption event.
   *
   * Simulation mode is read-only.
   *
   * POST /api/trips/{trip_id}/disruptions/simulate
   */
  async simulateDisruption(tripId, payload = {}) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    const body = {
      disruption_type:
        payload.disruption_type ||
        payload.type ||
        'activity_cancelled',

      title:
        payload.title || null,

      description:
        payload.description || null,

      activity_id:
        payload.activity_id || null,

      time:
        payload.time || null,

      delay_minutes:
        Number(payload.delay_minutes) || 0,

      cost_delta:
        Number(payload.cost_delta) || 0,

      new_budget:
        payload.new_budget !== undefined &&
        payload.new_budget !== null
          ? Number(payload.new_budget)
          : null,

      new_interests:
        payload.new_interests || null,
    };

    try {
      return await request(
        `/trips/${encodeURIComponent(
          tripId
        )}/disruptions/simulate`,
        {
          method: 'POST',
          body: JSON.stringify(body),
        }
      );
    } catch (_) {
      return await request('/disruptions/simulate', {
        method: 'POST',
        body: JSON.stringify({
          ...body,
          trip_id: tripId,
        }),
      });
    }
  },

  /**
   * Apply replanned itinerary.
   *
   * This commits the proposed changes to SQLite.
   */
  async applyReplan(tripId, payload = {}) {
    if (!tripId) {
      throw new Error('Trip ID is required.');
    }

    const body = {
      disruption_type:
        payload.disruption_type ||
        payload.type ||
        'activity_cancelled',

      title:
        payload.title || null,

      description:
        payload.description || null,

      activity_id:
        payload.activity_id || null,

      time:
        payload.time || null,

      delay_minutes:
        Number(payload.delay_minutes) || 0,

      cost_delta:
        Number(payload.cost_delta) || 0,

      new_budget:
        payload.new_budget !== undefined &&
        payload.new_budget !== null
          ? Number(payload.new_budget)
          : null,

      new_interests:
        payload.new_interests || null,
    };

    try {
      return await request(
        `/trips/${encodeURIComponent(
          tripId
        )}/replan`,
        {
          method: 'POST',
          body: JSON.stringify(body),
        }
      );
    } catch (_) {
      return await request('/replan', {
        method: 'POST',
        body: JSON.stringify({
          ...body,
          trip_id: tripId,
        }),
      });
    }
  },

  /**
   * Send conversational message to TravelPilot AI Assistant.
   *
   * POST /api/assistant/chat
   */
  async sendAssistantMessage(message, tripId = null) {
    if (!message?.trim()) {
      throw new Error('Message is required.');
    }

    if (!tripId) {
      throw new Error(
        'Create or select a trip before using the AI Assistant.'
      );
    }

    const body = {
      message: message.trim(),
      trip_id: tripId,
    };

    return await request('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};