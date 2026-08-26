/**
 * Bindu JSON-RPC Client
 * HTTP client for communicating with Bindu A2A protocol
 */

import { BridgeConfig } from '../config';
import { BinduRPCError } from '../utils/errors';

/**
 * Bindu artifact part
 */
export interface BinduArtifactPart {
  kind: 'text' | 'file' | 'data';
  text?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Bindu task artifact
 */
export interface BinduArtifact {
  artifact_id: string;
  name?: string;
  parts: BinduArtifactPart[];
}

/**
 * Bindu history message
 */
export interface BinduHistoryMessage {
  message_id: string;
  role: 'user' | 'agent';
  parts: Array<{ kind: string; text?: string }>;
}

/**
 * Bindu task response structure
 */
export interface BinduTask {
  id: string;              // taskId
  contextId: string;       // contextId
  kind: 'task';
  status: {
    state: string;         // BinduTaskState
    timestamp: string;     // ISO 8601
  };
  artifacts?: BinduArtifact[];
  history?: BinduHistoryMessage[];
  metadata?: Record<string, unknown>;
}

/**
 * Parameters for sending a message to Bindu
 */
export interface SendMessageParams {
  message: {
    role: 'user';
    parts: Array<{ kind: 'text'; text: string }>;
    kind: 'message';
    messageId: string;
    contextId: string;
    taskId: string;
  };
  configuration?: {
    acceptedOutputModes: string[];
  };
}

/**
 * JSON-RPC response structure
 */
interface JsonRpcResponse<T> {
  jsonrpc: '2.0';
  id: string;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/**
 * Client for Bindu JSON-RPC API
 */
export class BinduClient {
  constructor(private config: BridgeConfig) {}

  /**
   * Call a Bindu JSON-RPC method
   */
  async call<T>(method: string, params: Record<string, unknown>): Promise<T> {
    const requestId = crypto.randomUUID();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.requestTimeoutMs);

    try {
      const response = await fetch(this.config.binduUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method,
          params,
          id: requestId,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new BinduRPCError(
          -32000,
          `HTTP error: ${response.status} ${response.statusText}`,
        );
      }

      const data = (await response.json()) as JsonRpcResponse<T>;

      if (data.error) {
        throw new BinduRPCError(data.error.code, data.error.message);
      }

      return data.result as T;
    } catch (error) {
      if (error instanceof BinduRPCError) {
        throw error;
      }
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new BinduRPCError(-32000, 'Request timeout');
        }
        throw new BinduRPCError(-32000, error.message);
      }
      throw new BinduRPCError(-32000, 'Unknown error');
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Send a message to create a new task
   */
  async sendMessage(params: SendMessageParams): Promise<BinduTask> {
    return this.call<BinduTask>('message/send', params as unknown as Record<string, unknown>);
  }

  /**
   * Get task status
   */
  async getTask(taskId: string): Promise<BinduTask> {
    return this.call<BinduTask>('tasks/get', { taskId });
  }

  /**
   * List tasks (optional - for future use)
   */
  async listTasks(limit?: number): Promise<BinduTask[]> {
    return this.call<BinduTask[]>('tasks/list', { limit });
  }

  /**
   * Check if Bindu is reachable
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Try to call a simple method or just check connectivity
      const response = await fetch(this.config.binduUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'agent/authenticatedExtendedCard',
          params: {},
          id: crypto.randomUUID(),
        }),
        signal: AbortSignal.timeout(5000),
      });
      
      // If we get a response (even 400), check if it's valid JSON-RPC
      if (response.ok || response.status === 400) {
        const data = await response.json() as { jsonrpc?: string };
        // A JSON-RPC response (result or error) means Bindu is reachable
        return data.jsonrpc === '2.0';
      }
      return false;
    } catch {
      return false;
    }
  }
}
