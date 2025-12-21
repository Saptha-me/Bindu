// utils/storage.js
// localStorage & sessionStorage wrapper with serialization

const KEYS = {
  AUTH_TOKEN: 'bindu:auth_token'
};

function isStorageAvailable(storage) {
  try {
    const test = '__test__';
    storage.setItem(test, test);
    storage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

const local = isStorageAvailable(window.localStorage)
  ? window.localStorage
  : null;

const session = isStorageAvailable(window.sessionStorage)
  ? window.sessionStorage
  : null;

function serialize(value) {
  return JSON.stringify(value);
}

function deserialize(value, fallback = null) {
  try {
    return value === null ? fallback : JSON.parse(value);
  } catch {
    return fallback;
  }
}

export const storage = {
  set(key, value, scope = 'local') {
    const target = scope === 'session' ? session : local;
    if (!target) return false;
    target.setItem(key, serialize(value));
    return true;
  },

  get(key, fallback = null, scope = 'local') {
    const target = scope === 'session' ? session : local;
    if (!target) return fallback;
    return deserialize(target.getItem(key), fallback);
  },

  remove(key, scope = 'local') {
    const target = scope === 'session' ? session : local;
    if (!target) return false;
    target.removeItem(key);
    return true;
  },

  clear(keys = [], scope = 'local') {
    const target = scope === 'session' ? session : local;
    if (!target) return;
    keys.forEach(k => target.removeItem(k));
  },

  // Domain-specific helpers (still go through wrapper)
  getAuthToken() {
    return storage.get(KEYS.AUTH_TOKEN);
  },

  setAuthToken(token) {
    storage.set(KEYS.AUTH_TOKEN, token);
  },

  clearAuthToken() {
    storage.remove(KEYS.AUTH_TOKEN);
  }
};

export { KEYS as STORAGE_KEYS };
