/**
 * AG-UI Run Handler
 * Main handler for /agui/run endpoint
 */

import { Context } from 'hono';
import { BridgeConfig } from '../config';
import { BinduClient, BinduTask } from '../clients/bindu';
import { AGUIEventBuilder } from '../events/builder';
import { createSSEStream, getSSEHeaders, SSEStream } from '../events/sse';
import { BinduTaskState, TERMINAL_STATES } from '../events/types';
import { sleep } from '../utils/sleep';

/**
 * AG-UI Run Request structure
 */
export interface AGUIRunRequest {
  thread_id: string;        // Maps to Bindu contextId
  run_id?: string;          // Optional, auto-generated if not provided
  messages: AGUIMessage[];  // User messages to send
  config?: {
    polling_interval_ms?: number;
    timeout_ms?: number;
  };
}

export interface AGUIMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

/**
 * Emit artifacts from completed task as text message events
 */
async function emitArtifactsAsMessages(
  sse: SSEStream,
  events: AGUIEventBuilder,
  task: BinduTask,
): Promise<void> {
  if (!task.artifacts?.length) return;

  for (const artifact of task.artifacts) {
    // Extract text from artifact parts
    for (const part of artifact.parts) {
      if (part.kind === 'text' && part.text) {
        const msgId = crypto.randomUUID();
        await sse.emit(events.textMessageStart(msgId, 'assistant'));
        await sse.emit(events.textMessageContent(msgId, part.text));
        await sse.emit(events.textMessageEnd(msgId));
      }
    }
  }
}

/**
 * Create the run handler with injected dependencies
 */
export function createRunHandler(binduClient: BinduClient, config: BridgeConfig) {
  return async function handleAGUIRun(c: Context): Promise<Response> {
    // Parse request body
    let body: AGUIRunRequest;
    try {
      body = await c.req.json<AGUIRunRequest>();
    } catch {
      return c.json({ error: 'Invalid JSON body' }, 400);
    }

    // Validate required fields
    if (!body.thread_id) {
      return c.json({ error: 'thread_id is required' }, 400);
    }
    if (!body.messages || body.messages.length === 0) {
      return c.json({ error: 'messages array is required and cannot be empty' }, 400);
    }

    // Generate IDs
    const threadId = body.thread_id;
    const taskId = body.run_id || crypto.randomUUID();
    const messageId = crypto.randomUUID();

    // Get polling config (use request overrides or defaults)
    const pollIntervalMs = body.config?.polling_interval_ms ?? config.pollIntervalMs;
    const maxPollAttempts = body.config?.timeout_ms
      ? Math.ceil(body.config.timeout_ms / pollIntervalMs)
      : config.maxPollAttempts;

    // Create SSE stream
    const { readable, writable } = new TransformStream<Uint8Array>();
    const writer = writable.getWriter();
    const encoder = new TextEncoder();
    const sse = createSSEStream(writer, encoder);
    const events = new AGUIEventBuilder(threadId, taskId);

    // Start background processing
    (async () => {
      try {
        // Filter only user messages for sending to Bindu
        const userMessages = body.messages.filter(m => m.role === 'user');
        if (userMessages.length === 0) {
          await sse.emit(events.runError('No user messages to send'));
          return;
        }

        // Call Bindu message/send
        await binduClient.sendMessage({
          message: {
            role: 'user',
            parts: userMessages.map(m => ({ kind: 'text' as const, text: m.content })),
            kind: 'message',
            messageId,
            contextId: threadId,
            taskId,
          },
          configuration: { acceptedOutputModes: ['text', 'text/plain', 'application/json'] },
        });

        // Emit RUN_STARTED
        await sse.emit(events.runStarted());

        // Poll for task completion
        let lastState: BinduTaskState = 'submitted';
        let pollCount = 0;

        while (pollCount < maxPollAttempts) {
          await sleep(pollIntervalMs);

          let currentTask: BinduTask;
          try {
            currentTask = await binduClient.getTask(taskId);
          } catch (error) {
            // If we can't get the task, emit error and break
            const message = error instanceof Error ? error.message : 'Failed to get task status';
            await sse.emit(events.runError(message));
            break;
          }

          const currentState = currentTask.status.state as BinduTaskState;

          // Emit state change if different
          if (currentState !== lastState) {
            await sse.emit(events.stateDelta(currentState));
            lastState = currentState;
          }

          // Check for terminal state
          if (TERMINAL_STATES.includes(currentState)) {
            if (currentState === 'completed') {
              // Emit message events for artifacts
              await emitArtifactsAsMessages(sse, events, currentTask);
              await sse.emit(events.runFinished());
            } else if (currentState === 'failed') {
              await sse.emit(events.runError('Task failed'));
            } else if (currentState === 'canceled') {
              await sse.emit(events.runError('Task canceled', -32000));
            }
            break;
          }

          pollCount++;
        }

        // Timeout error if we hit max attempts
        if (pollCount >= maxPollAttempts && !TERMINAL_STATES.includes(lastState)) {
          await sse.emit(events.runError('Polling timeout'));
        }

      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        try {
          await sse.emit(events.runError(message));
        } catch {
          // Writer might already be closed
        }
      } finally {
        try {
          await sse.close();
        } catch {
          // Writer might already be closed
        }
      }
    })();

    // Return SSE response immediately
    return new Response(readable, {
      headers: getSSEHeaders(),
    });
  };
}
