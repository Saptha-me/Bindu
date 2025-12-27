// Configuration constants for Bindu UI
// Phase 1: Centralized, environment-safe configuration

export const CONFIG = {
    /* =========================
       Base URL
    ========================== */
    BASE_URL: window.location.origin,

    /* =========================
       API Endpoints
    ========================== */
    ENDPOINTS: {
        AGENT_MANIFEST: '/.well-known/agent.json',
        AGENT_SKILLS: '/agent/skills',
        AGENT_SKILL_DETAILS: '/agent/skills', // append /:id in API layer
        DID_RESOLVE: '/did/resolve',

        PAYMENT_SESSION: '/api/start-payment-session',
        PAYMENT_STATUS: '/api/payment-status', // append /:sessionId in API layer

        JSON_RPC: '/' // Main JSON-RPC endpoint
    },

    /* =========================
       Feature Flags
    ========================== */
    FEATURES: {
        ENABLE_PAYMENT: true,
        ENABLE_AUTH: true,
        ENABLE_CONTEXTS: true
    },

    /* =========================
       Timeouts & Limits (ms)
    ========================== */
    TIMEOUTS: {
        REQUEST_TIMEOUT: 30_000,      // 30s
        PAYMENT_POLLING: 300_000,     // 5 min
        TASK_POLLING: 300_000,        // 5 min
        DEBOUNCE_DELAY: 300
    },

    /* =========================
       UI Constraints
    ========================== */
    UI: {
        MAX_MESSAGE_LENGTH: 5_000,
        MAX_CONTEXTS_DISPLAY: 50,
        MESSAGE_PREVIEW_LENGTH: 50,
        THINKING_DOT_INTERVAL: 1_000
    }
};
