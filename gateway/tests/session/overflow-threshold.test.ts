/**
 * Tests for the model-aware overflow threshold resolver.
 *
 * This guards the regression described in
 * ``bugs/known-issues.md#context-window-hardcoded``: the overflow
 * threshold used to be a single constant (200k, Claude Opus) regardless
 * of which model the planner was actually calling. Operators swapping
 * to GPT-4o-mini (128k) hit ``context_length_exceeded`` from the
 * provider before compaction fired; operators swapping to Gemini Flash
 * (1M) paid for summarization runs that weren't needed.
 *
 * ``thresholdForModel`` now resolves the window from a lookup table
 * keyed on the gateway's model identifier (``provider/modelId``), with
 * a conservative fallback for unknown models and a per-call override
 * for operators running exotic models.
 */

import { describe, it, expect } from "vitest"
import { thresholdForModel, DEFAULT_THRESHOLD, isOverflow } from "../../src/session/overflow"

describe("thresholdForModel — model-aware context window resolution", () => {
  it("returns 200k for known Anthropic 4.x models", () => {
    expect(thresholdForModel("anthropic/claude-opus-4-7").contextWindow).toBe(200_000)
    expect(thresholdForModel("anthropic/claude-sonnet-4-6").contextWindow).toBe(200_000)
    expect(thresholdForModel("anthropic/claude-haiku-4-5").contextWindow).toBe(200_000)
  })

  it("returns 128k for GPT-4o family (the actual bug: these used to get 200k)", () => {
    expect(thresholdForModel("openai/gpt-4o").contextWindow).toBe(128_000)
    expect(thresholdForModel("openai/gpt-4o-mini").contextWindow).toBe(128_000)
  })

  it("returns ~1M for GPT-4.1 family", () => {
    expect(thresholdForModel("openai/gpt-4.1").contextWindow).toBe(1_047_576)
    expect(thresholdForModel("openai/gpt-4.1-mini").contextWindow).toBe(1_047_576)
  })

  it("returns 200k for o3 reasoning models", () => {
    expect(thresholdForModel("openai/o3").contextWindow).toBe(200_000)
    expect(thresholdForModel("openai/o3-mini").contextWindow).toBe(200_000)
  })

  it("uses the registered MiniMax context windows", () => {
    expect(thresholdForModel("minimax/MiniMax-M3").contextWindow).toBe(1_000_000)
    expect(thresholdForModel("minimax/MiniMax-M2.7").contextWindow).toBe(204_800)
  })

  it("falls back to the conservative default for unknown models", () => {
    // A fresh-off-the-press model we haven't added to the table yet.
    // The default is deliberately SMALLER than every common window so
    // compaction fires early rather than letting the caller hit a
    // provider-side overflow.
    const t = thresholdForModel("some-new-provider/never-seen-this-model")
    expect(t.contextWindow).toBe(DEFAULT_THRESHOLD.contextWindow)
    expect(t.contextWindow).toBe(128_000) // explicit — don't let the default drift silently
  })

  it("respects caller override (operator escape hatch)", () => {
    // Operator running an exotic 2M-context model declares it via config.
    const t = thresholdForModel("exotic/big-brain", { contextWindow: 2_000_000 })
    expect(t.contextWindow).toBe(2_000_000)
  })

  it("override on reserveForOutput + triggerFraction carries through", () => {
    const t = thresholdForModel("anthropic/claude-sonnet-4-6", {
      reserveForOutput: 32_000,
      triggerFraction: 0.6,
    })
    // Model lookup still wins for contextWindow (not in override)
    expect(t.contextWindow).toBe(200_000)
    expect(t.reserveForOutput).toBe(32_000)
    expect(t.triggerFraction).toBe(0.6)
  })

  it("override on contextWindow wins over table lookup", () => {
    // Operator explicitly caps Sonnet 4.6 to 100k (unusual but valid).
    const t = thresholdForModel("anthropic/claude-sonnet-4-6", { contextWindow: 100_000 })
    expect(t.contextWindow).toBe(100_000)
  })
})

describe("isOverflow — fires at the right token count per model", () => {
  // Previously everything compared against 200k regardless of model.
  // These tests assert the new per-model behavior.

  it("GPT-4o-mini @ 100k tokens → overflow (was SAFE with the old hardcoded 200k)", () => {
    const threshold = thresholdForModel("openai/gpt-4o-mini")
    // (128k - 16k reserve) * 0.8 = 89.6k. 100k > 89.6k.
    expect(isOverflow(100_000, threshold)).toBe(true)
  })

  it("GPT-4o-mini @ 50k tokens → no overflow", () => {
    expect(isOverflow(50_000, thresholdForModel("openai/gpt-4o-mini"))).toBe(false)
  })

  it("Sonnet 4.6 @ 100k tokens → no overflow (within 200k - 16k - 20%)", () => {
    // (200k - 16k) * 0.8 = 147.2k. 100k is fine.
    expect(isOverflow(100_000, thresholdForModel("anthropic/claude-sonnet-4-6"))).toBe(false)
  })

  it("Sonnet 4.6 @ 160k tokens → overflow (crosses 147.2k trigger)", () => {
    expect(isOverflow(160_000, thresholdForModel("anthropic/claude-sonnet-4-6"))).toBe(true)
  })

  it("GPT-4.1 @ 500k tokens → no overflow (1M window absorbs it)", () => {
    // (1_047_576 - 16k) * 0.8 = ~825k. 500k is fine.
    expect(isOverflow(500_000, thresholdForModel("openai/gpt-4.1"))).toBe(false)
  })

  it("unknown model falls back to 128k threshold, not the old 200k", () => {
    // A regression guard: the bug was that every model got 200k. Now
    // an unknown model gets 128k (conservative), which triggers
    // compaction earlier — strictly safer.
    const t = thresholdForModel("experimental/untested-model")
    // (128k - 16k) * 0.8 = 89.6k. 100k overflows.
    expect(isOverflow(100_000, t)).toBe(true)
    // With the old 200k default this same 100k WOULD NOT have
    // overflowed — proving the fix changes behavior as intended.
  })
})
