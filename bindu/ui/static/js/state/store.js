// Centralized application state (Phase 1)

const initialState = {
  agentInfo: null,
  authToken: null,
  paymentToken: null,

  currentTaskId: null,
  currentTaskState: null,
  taskHistory: [],

  contextId: null,
  contexts: [],

  uiState: {
    activeTab: 'chat',
    modals: {
      auth: false,
      payment: false,
      feedback: false,
      skill: null
    },
    loading: false,
    error: null
  }
};

let state = structuredClone(initialState);
const listeners = new Set();

function getState() {
  return structuredClone(state);
}

function setState(partial) {
  state = {
    ...state,
    ...partial,
    uiState: {
      ...state.uiState,
      ...(partial.uiState || {})
    }
  };
  listeners.forEach(fn => fn(getState()));
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function resetState() {
  state = structuredClone(initialState);
  listeners.forEach(fn => fn(getState()));
}

export const store = {
  getState,
  setState,
  subscribe,
  resetState
};
