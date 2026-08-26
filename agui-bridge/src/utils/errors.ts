/**
 * Custom Error Classes for AG-UI Bridge
 */

/**
 * Error from Bindu JSON-RPC responses
 */
export class BinduRPCError extends Error {
  constructor(
    public code: number,
    message: string,
  ) {
    super(message);
    this.name = 'BinduRPCError';
  }
}

/**
 * Internal bridge errors
 */
export class AGUIBridgeError extends Error {
  constructor(
    message: string,
    public aguiCode?: string,
  ) {
    super(message);
    this.name = 'AGUIBridgeError';
  }
}

/**
 * Timeout error for polling operations
 */
export class PollingTimeoutError extends Error {
  constructor(taskId: string, attempts: number) {
    super(`Polling timeout for task ${taskId} after ${attempts} attempts`);
    this.name = 'PollingTimeoutError';
  }
}
