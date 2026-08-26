/**
 * AG-UI Event Builder
 * Factory for creating properly formatted AG-UI events
 */

import {
  BaseEvent,
  BinduTaskState,
  EventType,
  RunErrorEvent,
  RunFinishedEvent,
  RunStartedEvent,
  StateDeltaEvent,
  TextMessageContentEvent,
  TextMessageEndEvent,
  TextMessageStartEvent,
} from './types';

export class AGUIEventBuilder {
  constructor(
    private threadId: string,
    private runId: string,
  ) {}

  private base(type: EventType): BaseEvent {
    return {
      type,
      timestamp: Date.now(),
      thread_id: this.threadId,
      run_id: this.runId,
    };
  }

  runStarted(): RunStartedEvent {
    return this.base(EventType.RUN_STARTED) as RunStartedEvent;
  }

  runFinished(): RunFinishedEvent {
    return this.base(EventType.RUN_FINISHED) as RunFinishedEvent;
  }

  runError(error: string, code?: number): RunErrorEvent {
    return {
      ...this.base(EventType.RUN_ERROR),
      error: { message: error, code },
    } as RunErrorEvent;
  }

  stateDelta(binduState: BinduTaskState): StateDeltaEvent {
    return {
      ...this.base(EventType.STATE_DELTA),
      delta: { bindu_state: binduState },
    } as StateDeltaEvent;
  }

  textMessageStart(messageId: string, role: string = 'assistant'): TextMessageStartEvent {
    return {
      ...this.base(EventType.TEXT_MESSAGE_START),
      message_id: messageId,
      role,
    } as TextMessageStartEvent;
  }

  textMessageContent(messageId: string, content: string): TextMessageContentEvent {
    return {
      ...this.base(EventType.TEXT_MESSAGE_CONTENT),
      message_id: messageId,
      content,
    } as TextMessageContentEvent;
  }

  textMessageEnd(messageId: string): TextMessageEndEvent {
    return {
      ...this.base(EventType.TEXT_MESSAGE_END),
      message_id: messageId,
    } as TextMessageEndEvent;
  }
}
