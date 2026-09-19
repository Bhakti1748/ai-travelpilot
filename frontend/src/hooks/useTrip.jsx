import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';

import { api } from '../services/api';

const TripContext = createContext(null);

const INITIAL_CHAT_MESSAGE = {
  id: 'welcome',
  sender: 'ai',
  text:
    'Hello! I’m your TravelPilot Co-pilot. Create a trip and I’ll help you plan, monitor, and adapt your itinerary.',
  timestamp: 'Now',
  suggestions: [
    'Check my budget',
    'Show my itinerary',
    'What should I do next?',
  ],
};

export function TripProvider({ children }) {
  // =========================================================
  // CORE STATE
  // =========================================================

  const [activeTrip, setActiveTrip] = useState(null);

  const [currentPage, setCurrentPage] = useState('landing');

  const [chatMessages, setChatMessages] = useState([
    INITIAL_CHAT_MESSAGE,
  ]);

  const [isAiTyping, setIsAiTyping] = useState(false);

  const [isLoading, setIsLoading] = useState(true);

  const [backendError, setBackendError] = useState(null);

  const [toastMessage, setToastMessage] = useState(null);

  // =========================================================
  // DISRUPTION / REPLAN STATE
  // =========================================================

  const [proposedReplan, setProposedReplan] = useState(null);

  const [isSimulating, setIsSimulating] = useState(false);

  const [isReplanning, setIsReplanning] = useState(false);

  // =========================================================
  // AI PLANNING STATE
  // =========================================================

  const [isPlanning, setIsPlanning] = useState(false);

  const [planningStep, setPlanningStep] = useState(0);

  const [planningError, setPlanningError] = useState(null);

  // Prevent initial backend loading from running repeatedly.
  const initialLoadDone = useRef(false);

  // =========================================================
  // TOAST
  // =========================================================

  const showToast = useCallback(
    (title, message, type = 'info') => {
      const toast = {
        title,
        message,
        type,
        id: Date.now(),
      };

      setToastMessage(toast);

      window.setTimeout(() => {
        setToastMessage((previous) => {
          if (previous?.id === toast.id) {
            return null;
          }

          return previous;
        });
      }, 4500);
    },
    []
  );

  // =========================================================
  // ITINERARY TRANSFORMER
  // =========================================================

  const transformItinerary = useCallback(
    (itinData, tripData) => {
      if (!itinData || !tripData) {
        return [];
      }

      return (itinData.days || []).map((day) => ({
        dayNumber: day.day_number,

        date: day.date,

        title:
          day.title ||
          `Day ${day.day_number}: ${tripData.destination}`,

        totalCost: Number(day.total_cost || 0),

        activities: (day.activities || []).map((act) => ({
          id: act.id,

          time: act.time,

          title: act.title,

          duration: act.duration,

          location: act.location,

          cost: Number(act.cost || 0),

          currency:
            act.currency ||
            tripData.currency ||
            'INR',

          transportation:
            act.transportation ||
            tripData.transport_preference ||
            'Public Transit',

          status:
            act.status ||
            'Confirmed',

          category:
            act.category ||
            'Sightseeing',

          notes:
            act.notes || '',
        })),
      }));
    },
    []
  );

  // =========================================================
  // FALLBACK BUDGET
  // =========================================================

  const createFallbackBudgetBreakdown = useCallback(
    (budget) => {
      const totalBudget = Number(budget || 0);

      return {
        accommodation: Math.round(totalBudget * 0.35),
        transportation: Math.round(totalBudget * 0.20),
        activities: Math.round(totalBudget * 0.20),
        food: Math.round(totalBudget * 0.20),
        miscellaneous: Math.round(totalBudget * 0.05),
      };
    },
    []
  );

  // =========================================================
  // AI INSIGHTS
  // =========================================================

  const buildAiInsights = useCallback((tripData) => {
    if (!tripData) {
      return [];
    }

    const currency =
      tripData.currency || 'INR';

    const spending =
      Number(tripData.spending || 0);

    const budget =
      Number(tripData.budget || 0);

    return [
      `Optimized pacing for ${
        tripData.travelers || 1
      } traveler(s) based on "${
        tripData.travel_style || 'Balanced'
      }" preference.`,

      `Grounded in activity data and geographic transit times for ${tripData.destination}.`,

      `Current spending is ${currency} ${spending.toLocaleString()} of ${currency} ${budget.toLocaleString()} total ceiling.`,

      'Autonomous disruption simulator is active with multi-constraint validation.',
    ];
  }, []);

  // =========================================================
  // BUILD ALERTS
  // =========================================================

  const buildAlerts = useCallback(
    (tripData, currentProposedReplan = null) => {
      const alerts = [];

      if (currentProposedReplan) {
        const disruptionType =
          String(
            currentProposedReplan.disruption_type ||
              'Travel disruption'
          ).replace(/_/g, ' ');

        const description =
          currentProposedReplan.reason_for_disruption ||
          currentProposedReplan.description ||
          'A travel disruption was detected.';

        const alternative =
          currentProposedReplan
            .recommended_alternative;

        const alternativeName =
          alternative?.title ||
          alternative?.name;

        alerts.push({
          id: `alert-sim-${Date.now()}`,

          type: 'warning',

          title: `Simulation: ${disruptionType}`,

          severity:
            currentProposedReplan.severity ||
            'warning',

          description,

          aiResolution:
            alternativeName
              ? `Recommended substitution: ${alternativeName}`
              : 'AI replanning ready to apply.',

          timestamp: 'Just now',

          resolved: false,
        });
      }

      if (tripData?.id) {
        alerts.push({
          id: `alert-monitor-${tripData.id}`,

          type: 'info',

          title:
            'Real-time Disruption Monitor Armed',

          severity: 'info',

          description:
            `TravelPilot is monitoring the itinerary for ${tripData.destination}.`,

          aiResolution:
            'Dynamic constraint rerouting buffer configured.',

          timestamp: 'Live',

          resolved: false,
        });
      }

      return alerts;
    },
    []
  );

  // =========================================================
  // REFRESH TRIP DATA
  // =========================================================

  const refreshTripData = useCallback(
    async (tripId) => {
      const targetId =
        tripId || activeTrip?.id;

      if (!targetId) {
        setActiveTrip(null);
        setIsLoading(false);
        return null;
      }

      setIsLoading(true);

      try {
        const [
          tripRes,
          itinRes,
          budgetRes,
        ] = await Promise.allSettled([
          api.getTrip(targetId),
          api.getItinerary(targetId),
          api.getBudget(targetId),
        ]);

        // Trip itself is required.
        if (tripRes.status === 'rejected') {
          throw new Error(
            tripRes.reason?.message ||
              'Failed to fetch trip from API.'
          );
        }

        const tripData =
          tripRes.value;

        if (!tripData?.id) {
          throw new Error(
            'Backend returned an invalid trip.'
          );
        }

        const itinData =
          itinRes.status === 'fulfilled'
            ? itinRes.value
            : null;

        const budgetData =
          budgetRes.status === 'fulfilled'
            ? budgetRes.value
            : null;

        const days =
          transformItinerary(
            itinData,
            tripData
          );

        const budgetBreakdown =
          budgetData?.breakdown ||
          createFallbackBudgetBreakdown(
            tripData.budget
          );

        const currency =
          tripData.currency || 'INR';

        // IMPORTANT:
        // Preserve proposedReplan while refreshing.
        setActiveTrip({
          id: tripData.id,

          destination:
            tripData.destination,

          startDate:
            tripData.start_date,

          endDate:
            tripData.end_date,

          budget:
            Number(tripData.budget || 0),

          spending:
            Number(tripData.spending || 0),

          currency,

          travelers:
            Number(
              tripData.travelers || 1
            ),

          interests:
            tripData.interests || [],

          travelStyle:
            tripData.travel_style ||
            'Balanced',

          transportPreference:
            tripData.transport_preference ||
            'Public Transit',

          budgetBreakdown,

          budgetStatus:
            budgetData?.status ||
            'healthy',

          // Do not use proposedReplan here.
          // Temporary simulation alerts are handled
          // separately by the UI.

          activeAlerts: [],

          aiInsights:
            buildAiInsights(tripData),

          itinerary: days,
        });

        setBackendError(null);

        return tripData;
      } catch (err) {
        console.error(
          'Failed to refresh trip:',
          err
        );

        setBackendError(
          `Backend error: ${
            err.message ||
            'Unable to load trip data.'
          }`
        );

        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [
      activeTrip?.id,
      transformItinerary,
      createFallbackBudgetBreakdown,
      buildAiInsights,
    ]
  );

  // =========================================================
  // INITIAL LOAD
  // =========================================================
  //
  // IMPORTANT FIX:
  //
  // The old code used:
  //
  // useEffect(..., [refreshTripData])
  //
  // but refreshTripData depended on activeTrip and
  // proposedReplan. That could cause repeated reloads.
  //
  // This effect intentionally runs only once.
  // =========================================================

  useEffect(() => {
    if (initialLoadDone.current) {
      return;
    }

    initialLoadDone.current = true;

    let cancelled = false;

    const loadInitialTrip = async () => {
      setIsLoading(true);

      try {
        const trip =
          await api.getActiveTrip();

        if (cancelled) {
          return;
        }

        if (trip?.id) {
          await refreshTripData(
            trip.id
          );
        } else {
          setActiveTrip(null);
          setBackendError(null);
          setIsLoading(false);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }

        console.warn(
          'No active trip available:',
          err.message
        );

        setActiveTrip(null);

        setBackendError(
          `Unable to load trips from backend: ${
            err.message
          }`
        );

        setIsLoading(false);
      }
    };

    loadInitialTrip();

    return () => {
      cancelled = true;
    };

    // Intentionally run only once on application startup.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // =========================================================
  // CREATE TRIP
  // =========================================================

  const createTrip = async (formData) => {
    setIsPlanning(true);
    setPlanningStep(0);
    setPlanningError(null);
    setBackendError(null);

    const stepDelay = (ms) =>
      new Promise((resolve) =>
        window.setTimeout(
          resolve,
          ms
        )
      );

    try {
      // Step 0
      setPlanningStep(0);
      await stepDelay(300);

      // Step 1
      setPlanningStep(1);

      const createdTrip =
        await api.createTrip(
          formData
        );

      if (!createdTrip?.id) {
        throw new Error(
          'Backend did not return a valid trip ID.'
        );
      }

      // Step 2
      setPlanningStep(2);
      await stepDelay(350);

      // Step 3
      setPlanningStep(3);

      await api.generateItinerary(
        createdTrip.id
      );

      // Step 4
      setPlanningStep(4);
      await stepDelay(350);

      // Step 5
      setPlanningStep(5);

      const refreshedTrip =
        await refreshTripData(
          createdTrip.id
        );

      if (!refreshedTrip) {
        throw new Error(
          'Trip was created but could not be loaded again.'
        );
      }

      // Step 6
      setPlanningStep(6);
      await stepDelay(400);

      setIsPlanning(false);

      setCurrentPage(
        'dashboard'
      );

      showToast(
        'Trip Generated!',
        `AI Co-pilot generated an itinerary for ${createdTrip.destination}.`,
        'success'
      );

      return createdTrip;
    } catch (err) {
      console.error(
        'Failed to generate trip:',
        err
      );

      setPlanningError(
        err.message ||
          'Failed to communicate with backend.'
      );

      setIsPlanning(false);

      throw err;
    }
  };

  // =========================================================
  // SIMULATE DISRUPTION
  // =========================================================

  const simulateDisruption =
    async (params) => {
      if (isSimulating) {
        return null;
      }

      setIsSimulating(true);

      try {
        const tripId =
          activeTrip?.id;

        if (!tripId) {
          throw new Error(
            'Please create a trip before simulating a disruption.'
          );
        }

        if (
          !params ||
          !params.disruption_type
        ) {
          throw new Error(
            'Invalid disruption request.'
          );
        }

        console.log(
          '[TravelPilot] Simulating disruption:',
          {
            tripId,
            params,
          }
        );

        const simResult =
          await api.simulateDisruption(
            tripId,
            params
          );

        console.log(
          '[TravelPilot] Simulation response:',
          simResult
        );

        if (!simResult) {
          throw new Error(
            'The backend returned an empty disruption response.'
          );
        }

        /*
         * Combine backend result with submitted
         * parameters so the UI always has the
         * information needed to display the event.
         */
        const proposed = {
          ...(simResult || {}),
          ...params,
        };

        setProposedReplan(
          proposed
        );

        const alternative =
          simResult
            ?.recommended_alternative;

        const alternativeName =
          alternative?.title ||
          alternative?.name ||
          'an alternative activity';

        showToast(
          'Disruption Simulated',
          `TravelPilot generated a replan with ${alternativeName}.`,
          'warning'
        );

        return simResult;
      } catch (err) {
        console.error(
          '[TravelPilot] Simulation failed:',
          err
        );

        showToast(
          'Simulation Error',
          err.message ||
            'Unable to simulate disruption.',
          'warning'
        );

        /*
         * IMPORTANT:
         * Do NOT rethrow here.
         *
         * An async button handler should not create
         * an unhandled rejected promise.
         */
        return null;
      } finally {
        setIsSimulating(false);
      }
    };

  // =========================================================
  // APPLY REPLAN
  // =========================================================

  const applyReplan =
    async (params = null) => {
      if (isReplanning) {
        return null;
      }

      setIsReplanning(true);

      try {
        const tripId =
          activeTrip?.id;

        if (!tripId) {
          throw new Error(
            'Please create a trip before applying a replan.'
          );
        }

        if (
          !params &&
          !proposedReplan
        ) {
          throw new Error(
            'There is no proposed replan to apply.'
          );
        }

        const affectedItem =
          proposedReplan
            ?.affected_items?.[0];

        const payload =
          params || {
            disruption_type:
              proposedReplan?.disruption_type ||
              'activity_cancelled',

            title:
              affectedItem?.title ||
              affectedItem?.activity_name ||
              proposedReplan?.title ||
              null,

            description:
              proposedReplan?.description ||
              proposedReplan?.reason_for_disruption ||
              null,

            activity_id:
              affectedItem?.activity_id ||
              affectedItem?.id ||
              null,

            delay_minutes:
              Number(
                proposedReplan?.delay_minutes || 0
              ),

            cost_delta:
              Number(
                proposedReplan?.cost_delta || 0
              ),

            new_budget:
              proposedReplan?.new_budget ??
              null,

            new_interests:
              proposedReplan?.new_interests ??
              null,
          };

        console.log(
          '[TravelPilot] Applying replan:',
          {
            tripId,
            payload,
          }
        );

        const result =
          await api.applyReplan(
            tripId,
            payload
          );

        console.log(
          '[TravelPilot] Replan response:',
          result
        );

        // Clear temporary proposal.
        setProposedReplan(null);

        // Reload database state.
        await refreshTripData(
          tripId
        );

        showToast(
          'Replan Applied!',
          result?.summary_of_changes ||
            'Your itinerary has been updated.',
          'success'
        );

        return result;
      } catch (err) {
        console.error(
          '[TravelPilot] Apply replan failed:',
          err
        );

        showToast(
          'Replan Failed',
          err.message ||
            'Unable to apply the proposed changes.',
          'warning'
        );

        return null;
      } finally {
        setIsReplanning(false);
      }
    };

  // =========================================================
  // RESOLVE ALERT
  // =========================================================

  const resolveAlert = (
    alertId
  ) => {
    setActiveTrip(
      (previous) => {
        if (!previous) {
          return previous;
        }

        return {
          ...previous,

          activeAlerts:
            (
              previous.activeAlerts ||
              []
            ).map((alert) =>
              alert.id === alertId
                ? {
                    ...alert,
                    resolved: true,
                  }
                : alert
            ),
        };
      }
    );

    showToast(
      'Alert Acknowledged',
      'Disruption marked as resolved.',
      'info'
    );
  };

  // =========================================================
  // AI ASSISTANT
  // =========================================================

  const sendMessage =
    async (userText) => {
      if (
        !userText ||
        !userText.trim()
      ) {
        return;
      }

      if (!activeTrip?.id) {
        showToast(
          'No Trip Selected',
          'Create or select a trip before using the AI Assistant.',
          'warning'
        );

        return;
      }

      const userMsg = {
        id: `user-${Date.now()}`,

        sender: 'user',

        text: userText,

        timestamp:
          new Date().toLocaleTimeString(
            [],
            {
              hour: '2-digit',
              minute: '2-digit',
            }
          ),
      };

      setChatMessages(
        (previous) => [
          ...previous,
          userMsg,
        ]
      );

      setIsAiTyping(true);

      try {
        const tripId =
          activeTrip.id;

        const response =
          await api.sendAssistantMessage(
            userText,
            tripId
          );

        const aiResponse =
          response?.ai_response || {};

        let suggestions = [];

        if (
          aiResponse.suggestions
        ) {
          try {
            suggestions =
              typeof aiResponse.suggestions ===
              'string'
                ? JSON.parse(
                    aiResponse.suggestions
                  )
                : aiResponse.suggestions;
          } catch {
            suggestions = [];
          }
        }

        const aiMsg = {
          id:
            aiResponse.id ||
            `ai-${Date.now()}`,

          sender: 'ai',

          text:
            aiResponse.message ||
            response?.message ||
            'I have analyzed your request.',

          timestamp:
            aiResponse.timestamp ||
            new Date().toLocaleTimeString(
              [],
              {
                hour: '2-digit',
                minute: '2-digit',
              }
            ),

          suggestions:
            Array.isArray(
              suggestions
            )
              ? suggestions
              : [],

          intent:
            response?.intent,

          actionType:
            response?.action_type,
        };

        setChatMessages(
          (previous) => [
            ...previous,
            aiMsg,
          ]
        );

        if (
          response?.intent ===
            'confirm_apply' ||
          response?.action_type ===
            'replan_applied'
        ) {
          await refreshTripData(
            tripId
          );

          showToast(
            'Itinerary Updated',
            'AI Assistant applied changes to your itinerary.',
            'success'
          );
        }
      } catch (err) {
        console.error(
          'Chat error:',
          err
        );

        const fallbackMsg = {
          id: `ai-err-${Date.now()}`,

          sender: 'ai',

          text:
            `I encountered an issue contacting the planning agent: ${
              err.message ||
              'Unknown error'
            }. Please check that the TravelPilot backend is running on http://127.0.0.1:8000.`,

          timestamp:
            new Date().toLocaleTimeString(
              [],
              {
                hour: '2-digit',
                minute: '2-digit',
              }
            ),

          suggestions: [
            'Retry question',
            'Check budget status',
            'Show my itinerary',
          ],
        };

        setChatMessages(
          (previous) => [
            ...previous,
            fallbackMsg,
          ]
        );
      } finally {
        setIsAiTyping(false);
      }
    };

  // =========================================================
  // CLEAR TRIP SELECTION
  // =========================================================

  const clearCurrentTripSelection =
    useCallback(() => {
      setProposedReplan(null);

      setActiveTrip(null);

      setChatMessages([
        INITIAL_CHAT_MESSAGE,
      ]);

      setBackendError(null);

      setCurrentPage(
        'landing'
      );

      showToast(
        'Trip Selection Cleared',
        'Create a new trip to continue.',
        'info'
      );
    }, [showToast]);

  // Compatibility alias.
  const resetToDemoTrip =
    clearCurrentTripSelection;

  // =========================================================
  // CONTEXT VALUE
  // =========================================================

  const contextValue = {
    // Trip
    activeTrip,

    // Navigation
    currentPage,
    setCurrentPage,

    // Trip creation
    createTrip,

    // Backend
    refreshTripData,

    // Disruptions
    simulateDisruption,
    applyReplan,
    proposedReplan,
    setProposedReplan,
    isSimulating,
    isReplanning,
    resolveAlert,

    // Assistant
    chatMessages,
    isAiTyping,
    sendMessage,

    // Selection
    clearCurrentTripSelection,
    resetToDemoTrip,

    // Backend state
    isLoading,
    backendError,

    // Toast
    toastMessage,
    setToastMessage,

    // Planning
    isPlanning,
    planningStep,
    planningError,
    setIsPlanning,
  };

  return (
    <TripContext.Provider value={contextValue}>
      {children}
    </TripContext.Provider>
  );
}

export function useTrip() {
  const context =
    useContext(TripContext);

  if (!context) {
    throw new Error(
      'useTrip must be used within a TripProvider'
    );
  }

  return context;
}