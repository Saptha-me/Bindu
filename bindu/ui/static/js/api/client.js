// api/client.js
import { CONFIG } from '../config.js';

export class ApiError extends Error {
  constructor(message, status = null, payload = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

class ApiClient {
  constructor(baseURL = CONFIG.BASE_URL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseURL}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      CONFIG.TIMEOUTS.REQUEST_TIMEOUT
    );

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let payload = null;

        try {
          payload = await response.json();
        } catch {
          /* ignore non-JSON body */
        }

        throw new ApiError(
          payload?.message || response.statusText,
          response.status,
          payload
        );
      }

      // Safely parse JSON
      try {
        return await response.json();
      } catch {
        return null;
      }

    } catch (error) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new ApiError('Request timeout');
      }

      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError(error.message || 'Network error');
    }
  }

  async jsonRpcRequest(method, params = {}, id = crypto.randomUUID()) {
    const response = await this.request(CONFIG.ENDPOINTS.JSON_RPC, {
      method: 'POST',
      body: JSON.stringify({
        jsonrpc: '2.0',
        method,
        params,
        id
      })
    });

    if (response?.error) {
      throw new ApiError(
        response.error.message || 'JSON-RPC error',
        null,
        response.error
      );
    }

    return response?.result ?? null;
  }

  addAuthHeaders(options = {}, authToken) {
    if (!authToken) return options;

    const token = authToken.trim();
    if (!/^[\x00-\x7F]*$/.test(token)) {
      throw new ApiError('Invalid auth token format');
    }

    return {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`
      }
    };
  }

  addPaymentHeaders(options = {}, paymentToken) {
    if (!paymentToken) return options;

    const token = paymentToken.trim();
    if (!/^[\x00-\x7F]*$/.test(token)) {
      throw new ApiError('Invalid payment token format');
    }

    return {
      ...options,
      headers: {
        ...options.headers,
        'X-PAYMENT': token
      }
    };
  }
}

export const apiClient = new ApiClient();
