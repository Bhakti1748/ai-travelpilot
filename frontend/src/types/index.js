/**
 * @typedef {Object} Activity
 * @property {string} id
 * @property {string} time
 * @property {string} title
 * @property {string} duration
 * @property {string} location
 * @property {number} cost
 * @property {string} transportation
 * @property {'Confirmed' | 'In Progress' | 'Delayed' | 'Rerouted' | 'Pending'} status
 * @property {string} [notes]
 * @property {string} [category]
 */

/**
 * @typedef {Object} DayPlan
 * @property {number} dayNumber
 * @property {string} date
 * @property {string} title
 * @property {Activity[]} activities
 */

/**
 * @typedef {Object} BudgetBreakdown
 * @property {number} accommodation
 * @property {number} transportation
 * @property {number} activities
 * @property {number} food
 * @property {number} miscellaneous
 */

/**
 * @typedef {Object} DisruptionEvent
 * @property {string} id
 * @property {string} type - 'cancellation' | 'delay' | 'hotel' | 'budget' | 'custom'
 * @property {string} title
 * @property {string} severity - 'critical' | 'warning' | 'info'
 * @property {string} description
 * @property {string} aiResolution
 * @property {string} timestamp
 * @property {boolean} resolved
 */

/**
 * @typedef {Object} Trip
 * @property {string} id
 * @property {string} destination
 * @property {string} startDate
 * @property {string} endDate
 * @property {number} budget
 * @property {number} spending
 * @property {number} travelers
 * @property {string[]} interests
 * @property {string} travelStyle
 * @property {string} transportPreference
 * @property {BudgetBreakdown} budgetBreakdown
 * @property {DayPlan[]} itinerary
 * @property {DisruptionEvent[]} activeAlerts
 * @property {string[]} aiInsights
 */

export {};
