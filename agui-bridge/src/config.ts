/**
 * Bridge Configuration
 * Environment-based configuration with defaults
 */

export interface BridgeConfig {
  binduUrl: string;
  port: number;
  pollIntervalMs: number;
  requestTimeoutMs: number;
  maxPollAttempts: number;
}

function getEnvOrDefault(key: string, defaultValue: string): string {
  return process.env[key] ?? defaultValue;
}

function getEnvNumberOrDefault(key: string, defaultValue: number): number {
  const value = process.env[key];
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}

export const config: BridgeConfig = {
  binduUrl: getEnvOrDefault('BINDU_URL', 'http://localhost:3773'),
  port: getEnvNumberOrDefault('PORT', 8080),
  pollIntervalMs: getEnvNumberOrDefault('POLL_INTERVAL_MS', 500),
  requestTimeoutMs: getEnvNumberOrDefault('REQUEST_TIMEOUT_MS', 30000),
  maxPollAttempts: getEnvNumberOrDefault('MAX_POLL_ATTEMPTS', 120),
};

export default config;
