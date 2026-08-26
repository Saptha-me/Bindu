/**
 * AG-UI Event Type Definitions
 */

// Bindu Task States
export type BinduTaskState =
  | 'submitted'      // Task created, queued for execution
  | 'working'        // Task is being processed
  | 'input-required' // Agent needs user input
  | 'auth-required'  // Authentication needed
  | 'completed'      // Task finished successfully
  | 'canceled'       // Task was canceled
  | 'failed';        // Task execution failed

// Terminal states (stop polling when reached)
export const TERMINAL_STATES: BinduTaskState[] = ['completed', 'canceled', 'failed'];

// AG-UI Event Types
export enum EventType {
  RUN_STARTED = 'RUN_STARTED',
  RUN_FINISHED = 'RUN_FINISHED',
  RUN_ERROR = 'RUN_ERROR',
  STATE_DELTA = 'STATE_DELTA',
  TEXT_MESSAGE_START = 'TEXT_MESSAGE_START',
  TEXT_MESSAGE_CONTENT = 'TEXT_MESSAGE_CONTENT',
  TEXT_MESSAGE_END = 'TEXT_MESSAGE_END',
  // Future: TOOL_CALL_* events
}

// Base event interface
export interface BaseEvent {
  type: EventType;
  timestamp: number;
  thread_id: string;
  run_id: string;
}

// Specific event types
export interface RunStartedEvent extends BaseEvent {
  type: EventType.RUN_STARTED;
}

export interface RunFinishedEvent extends BaseEvent {
  type: EventType.RUN_FINISHED;
}

export interface RunErrorEvent extends BaseEvent {
  type: EventType.RUN_ERROR;
  error: {
    message: string;
    code?: number;
  };
}

export interface StateDeltaEvent extends BaseEvent {
  type: EventType.STATE_DELTA;
  delta: {
    bindu_state: BinduTaskState;
  };
}

export interface TextMessageStartEvent extends BaseEvent {
  type: EventType.TEXT_MESSAGE_START;
  message_id: string;
  role: string;
}

export interface TextMessageContentEvent extends BaseEvent {
  type: EventType.TEXT_MESSAGE_CONTENT;
  message_id: string;
  content: string;
}

export interface TextMessageEndEvent extends BaseEvent {
  type: EventType.TEXT_MESSAGE_END;
  message_id: string;
}

// Union type for all events
export type AGUIEvent =
  | RunStartedEvent
  | RunFinishedEvent
  | RunErrorEvent
  | StateDeltaEvent
  | TextMessageStartEvent
  | TextMessageContentEvent
  | TextMessageEndEvent;
