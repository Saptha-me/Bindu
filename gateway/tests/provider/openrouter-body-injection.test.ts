/**
 * Tests for the OpenRouter fetch-body injection helpers.
 *
 * The provider layer wraps ``fetch`` to add two OpenRouter-specific
 * fields to every chat-completions request body:
 *
 *   1. ``cache_control: { type: "ephemeral" }`` — enables OpenRouter's
 *      auto-breakpoint prompt caching. Safe on providers that don't
 *      support it (they strip the field).
 *   2. ``models: [primary, ...fallbacks]`` + ``route: "fallback"`` —
 *      OpenRouter's fail-over routing, driven by config.
 *
 * These helpers are exposed so tests can drive them with synthetic
 * bodies instead of spinning up a real network client.
 */

import { describe, it, expect } from "vitest"
import {
  ORCAROUTER_DEFAULT_BASE_URL,
  injectCacheControl,
  injectFallbackModels,
  parseModelId,
} from "../../src/provider"

describe("injectCacheControl — OpenRouter prompt-caching marker", () => {
  it("adds cache_control at the top level of a chat-completions body", () => {
    const body = JSON.stringify({
      model: "anthropic/claude-sonnet-4.6",
      messages: [{ role: "user", content: "hi" }],
    })
    const out = JSON.parse(injectCacheControl(body))
    expect(out.cache_control).toEqual({ type: "ephemeral" })
  })

  it("preserves all other fields untouched", () => {
    const body = JSON.stringify({
      model: "anthropic/claude-sonnet-4.6",
      messages: [{ role: "user", content: "hi" }],
      temperature: 0.5,
      tools: [{ type: "function", function: { name: "t1" } }],
    })
    const out = JSON.parse(injectCacheControl(body))
    expect(out.model).toBe("anthropic/claude-sonnet-4.6")
    expect(out.messages).toEqual([{ role: "user", content: "hi" }])
    expect(out.temperature).toBe(0.5)
    expect(out.tools).toEqual([{ type: "function", function: { name: "t1" } }])
  })

  it("respects an explicit cache_control already present upstream", () => {
    // If someone in the AI-SDK pipeline sets cache_control (e.g. a
    // test or a future provider option), we must not overwrite it.
    const body = JSON.stringify({
      model: "anthropic/claude-sonnet-4.6",
      cache_control: { type: "ephemeral", ttl: "1h" },
      messages: [],
    })
    const out = JSON.parse(injectCacheControl(body))
    expect(out.cache_control).toEqual({ type: "ephemeral", ttl: "1h" })
  })

  it("passes non-JSON bodies through untouched (defensive)", () => {
    const binary = "not-json-form-data-or-binary"
    expect(injectCacheControl(binary)).toBe(binary)
  })

  it("passes JSON primitives through untouched (not an object)", () => {
    expect(injectCacheControl("[1,2,3]")).toBe("[1,2,3]")
    expect(injectCacheControl("42")).toBe("42")
    expect(injectCacheControl("null")).toBe("null")
  })
})

describe("injectFallbackModels — OpenRouter fail-over routing", () => {
  it("replaces `model` with `models: [primary, ...fallbacks]` + route=fallback", () => {
    const body = JSON.stringify({
      model: "anthropic/claude-sonnet-4.6",
      messages: [],
    })
    const out = JSON.parse(
      injectFallbackModels(body, ["minimax/minimax-m3", "openai/gpt-4o-mini"]),
    )
    expect(out.models).toEqual([
      "anthropic/claude-sonnet-4.6",
      "minimax/minimax-m3",
      "openai/gpt-4o-mini",
    ])
    expect(out.route).toBe("fallback")
  })

  it("is a no-op when fallbackModels is empty (common case)", () => {
    const body = JSON.stringify({ model: "x", messages: [] })
    expect(injectFallbackModels(body, [])).toBe(body)
  })

  it("respects an explicit `models` array already present", () => {
    // Lets upstream callers (tests, future provider options) override
    // the gateway's default fallback chain.
    const body = JSON.stringify({
      model: "x",
      models: ["a", "b"],
      messages: [],
    })
    const out = JSON.parse(injectFallbackModels(body, ["c"]))
    expect(out.models).toEqual(["a", "b"])
  })

  it("is a no-op when body has no `model` field", () => {
    const body = JSON.stringify({ messages: [] })
    const out = injectFallbackModels(body, ["fallback/x"])
    expect(JSON.parse(out)).toEqual({ messages: [] })
  })

  it("passes non-JSON bodies through untouched (defensive)", () => {
    expect(injectFallbackModels("binary-noise", ["x/y"])).toBe("binary-noise")
  })

  it("composes cleanly with injectCacheControl (both fields coexist)", () => {
    const body = JSON.stringify({ model: "a/b", messages: [] })
    const out = JSON.parse(
      injectFallbackModels(injectCacheControl(body), ["c/d"]),
    )
    expect(out.cache_control).toEqual({ type: "ephemeral" })
    expect(out.models).toEqual(["a/b", "c/d"])
    expect(out.route).toBe("fallback")
  })

  it("preserves the original model field alongside models[] (OpenRouter ignores it but we keep for clarity)", () => {
    const body = JSON.stringify({ model: "primary/x", messages: [] })
    const out = JSON.parse(injectFallbackModels(body, ["fallback/y"]))
    expect(out.model).toBe("primary/x")
  })
})

describe("parseModelId — supported providers", () => {
  it("accepts openrouter model ids", () => {
    expect(parseModelId("openrouter/anthropic/claude-sonnet-4.6")).toEqual({
      providerId: "openrouter",
      modelId: "anthropic/claude-sonnet-4.6",
    })
  })

  it("accepts orcarouter model ids (multi-segment model id preserved)", () => {
    expect(parseModelId("orcarouter/anthropic/claude-opus-4.7")).toEqual({
      providerId: "orcarouter",
      modelId: "anthropic/claude-opus-4.7",
    })
  })

  it("accepts orcarouter's own model family", () => {
    expect(parseModelId("orcarouter/orcarouter/fusion-flash")).toEqual({
      providerId: "orcarouter",
      modelId: "orcarouter/fusion-flash",
    })
  })

  it("rejects an unsupported provider", () => {
    expect(() => parseModelId("unknown/model")).toThrow(/unsupported provider "unknown"/)
  })

  it("defaults orcarouter to the OrcaRouter API base URL", () => {
    expect(ORCAROUTER_DEFAULT_BASE_URL).toBe("https://api.orcarouter.ai/v1")
  })
})
