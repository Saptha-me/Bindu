/**
 * Global State Management
 * Centralized state for the Bindu Agent UI
 */

export const state = {
    agentInfo: null,
    currentTaskId: null,
    currentTaskState: null,
    contextId: null,
    replyToTaskId: null,
    taskHistory: [],
    contexts: [],
    currentPollingTaskId: null
};

export const BASE_URL = window.location.origin;

/**
 * Generate a unique ID for JSON-RPC requests
 */
export function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
