import { Effect, Stream } from "effect"
import { streamText, type LanguageModel, type ModelMessage, type Tool as AITool, type StopCondition } from "ai"

/**
 * Injected as a system reminder on the FINAL agentic step when `maxSteps`
 * is about to be hit. Mirrors opencode's `session/prompt/max-steps.txt`:
 * instead of letting the AI SDK silently cut off mid-tool-call when the
 * loop's step cap trips, we let the loop run normally up to `maxSteps - 1`
 * and force the final step to be tool-free with a summarize-and-stop
 * instruction. The result is a graceful final assistant turn ("hit the
 * step budget; here's what got done, here's what didn't") instead of a
 * truncated `finishReason: "length"` from the model's POV.
 */
const MAX_STEPS_SOFT_TERMINATION = [
  "CRITICAL — MAXIMUM PLANNER STEPS REACHED",
  "",
  "The agentic loop's step budget for this request is exhausted. Tools are",
  "disabled for this step. Respond with text only.",
  "",
  "STRICT REQUIREMENTS:",
  "1. Do NOT call any tools.",
  "2. Provide a final response that:",
  "   - States that the maximum number of planner steps was reached.",
  "   - Summarizes which recipients were invoked so far and what they returned.",
  "   - Lists any parts of the user's request that could not be completed.",
  "   - Recommends a next action the user can take (rephrase, re-submit, etc.).",
  "",
  "This constraint overrides any prior instruction to call a tool or continue planning.",
].join("\n")

/**
 * Thin wrapper around AI SDK's `streamText` that returns an Effect Stream
 * of the LLM events.
 *
 * Design note: OpenCode's `session/llm.ts` is 453 lines because it handles
 * multi-provider retries, structured output, Anthropic cache-control
 * injection, GPT reasoning, Gemini safety, usage normalization, etc. The
 * gateway defers those concerns — Phase 1 supports Anthropic + OpenAI with
 * their defaults. Phase 2 can add provider-specific knobs.
 */

export type StreamEvent =
  | { type: "start" }
  | { type: "text-delta"; id: string; delta: string }
  | { type: "text-end"; id: string }
  | {
      type: "tool-call"
      toolCallId: string
      toolName: string
      input: unknown
    }
  | {
      type: "tool-result"
      toolCallId: string
      toolName: string
      output: unknown
    }
  | {
      type: "tool-error"
      toolCallId: string
      toolName: string
      error: unknown
    }
  | {
      type: "finish"
      finishReason: "stop" | "length" | "tool-calls" | "content-filter" | "error" | "other" | "unknown"
      usage: {
        inputTokens?: number
        outputTokens?: number
        totalTokens?: number
        cachedInputTokens?: number
      }
    }
  | { type: "error"; error: Error }

export interface StreamInput {
  /** The LanguageModel handle (obtain via ProviderService.model). */
  model: LanguageModel
  systemPrompt: string
  messages: ModelMessage[]
  tools: Record<string, AITool>
  temperature?: number
  topP?: number
  maxSteps?: number
  abortSignal?: AbortSignal
}

/**
 * Returns an Effect Stream of LLM events. Caller must have already resolved
 * the LanguageModel (via ProviderService.model). Keeps this module free of
 * service dependencies so callers can compose it without adding R.
 */
export function stream(input: StreamInput): Stream.Stream<StreamEvent, Error> {
  return streamTextToEffect(input.model, input)
}

function streamTextToEffect(model: LanguageModel, input: StreamInput): Stream.Stream<StreamEvent, Error> {
  const maxSteps = input.maxSteps
  // Soft termination only makes sense when maxSteps >= 2 — a 1-step budget
  // means the FIRST step is already the final step, and we can't both make
  // the agent useful and forbid it from calling tools.
  const softTerminate = typeof maxSteps === "number" && maxSteps >= 2
  const result = streamText({
    model,
    system: input.systemPrompt,
    messages: input.messages,
    tools: input.tools,
    temperature: input.temperature,
    topP: input.topP,
    stopWhen: maxSteps ? (stepCountIs(maxSteps) as StopCondition<any>) : undefined,
    abortSignal: input.abortSignal,
    prepareStep: softTerminate
      ? ({ stepNumber }) => {
          // On the final permitted step, disable every tool and append a
          // summarize-and-stop reminder to the system prompt so the model
          // produces a clean text finish instead of trying to fire a
          // tool that we'd silently cut off when stopWhen kicks in.
          if (stepNumber !== maxSteps! - 1) return undefined
          return {
            activeTools: [],
            system: `${input.systemPrompt}\n\n${MAX_STEPS_SOFT_TERMINATION}`,
          }
        }
      : undefined,
  })

  // Pull from AI SDK's AsyncIterable<fullStream event>, map each event to
  // our narrower StreamEvent union (or null), then drop nulls. Prepend a
  // synthetic `start` frame so downstream has a known first signal.
  const raw: Stream.Stream<unknown, Error> = Stream.fromAsyncIterable(result.fullStream, (cause): Error =>
    cause instanceof Error ? cause : new Error(String(cause)),
  )

  const mapped = raw.pipe(
    Stream.map((evt: any): StreamEvent | null => mapEvent(evt)),
    Stream.filter((e): e is StreamEvent => e !== null),
  )

  const start: Stream.Stream<StreamEvent, Error> = Stream.fromArray<StreamEvent>([{ type: "start" }])
  return Stream.concat(start, mapped)
}

function mapEvent(evt: any): StreamEvent | null {
  switch (evt.type) {
    case "text-delta":
      return { type: "text-delta", id: evt.id, delta: evt.text }
    case "text-end":
      return { type: "text-end", id: evt.id }
    case "tool-call":
      return {
        type: "tool-call",
        toolCallId: evt.toolCallId,
        toolName: evt.toolName,
        input: evt.input,
      }
    case "tool-result":
      return {
        type: "tool-result",
        toolCallId: evt.toolCallId,
        toolName: evt.toolName,
        output: evt.output,
      }
    case "tool-error":
      return {
        type: "tool-error",
        toolCallId: evt.toolCallId,
        toolName: evt.toolName,
        error: evt.error,
      }
    case "finish":
      return {
        type: "finish",
        finishReason: evt.finishReason ?? "unknown",
        usage: {
          inputTokens: evt.totalUsage?.inputTokens,
          outputTokens: evt.totalUsage?.outputTokens,
          totalTokens: evt.totalUsage?.totalTokens,
          cachedInputTokens: evt.totalUsage?.cachedInputTokens,
        },
      }
    case "error":
      return { type: "error", error: evt.error instanceof Error ? evt.error : new Error(String(evt.error)) }
    default:
      return null
  }
}

/** AI SDK v5 `stepCountIs` helper shim — it's exported from "ai" but only on some versions. */
function stepCountIs(n: number) {
  return ({ steps }: { steps: { text?: string }[] }) => steps.length >= n
}
