/**
 * SSE Response Utilities
 * Formatting and streaming SSE events
 */

import { AGUIEvent, BaseEvent } from './types';

/**
 * Format an event as an SSE message
 */
export function formatSSEEvent(event: BaseEvent | AGUIEvent): string {
  const eventType = event.type;
  const data = JSON.stringify(event);
  return `event: ${eventType}\ndata: ${data}\n\n`;
}

/**
 * SSE Stream interface for emitting events
 */
export interface SSEStream {
  emit: (event: BaseEvent | AGUIEvent) => Promise<void>;
  close: () => Promise<void>;
}

/**
 * Create an SSE stream wrapper with emit and close methods
 */
export function createSSEStream(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  encoder: TextEncoder,
): SSEStream {
  return {
    async emit(event: BaseEvent | AGUIEvent): Promise<void> {
      const formatted = formatSSEEvent(event);
      await writer.write(encoder.encode(formatted));
    },
    async close(): Promise<void> {
      await writer.close();
    },
  };
}

/**
 * Create SSE response headers
 */
export function getSSEHeaders(): Record<string, string> {
  return {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  };
}
