import { describe, expect, it } from "vitest"
import {
  DEFAULT_MINIMAX_MODEL,
  MINIMAX_ENDPOINTS,
  MINIMAX_MODELS,
  normalizeMiniMaxModelId,
} from "../../src/provider/catalog"
import { parseModelId } from "../../src/provider"

describe("MiniMax provider catalog", () => {
  it("covers both regions and both protocol base URLs", () => {
    expect(MINIMAX_ENDPOINTS.global_en.openaiBaseURL).toMatch(/\/v1$/)
    expect(MINIMAX_ENDPOINTS.global_en.anthropicBaseURL).toMatch(/\/anthropic$/)
    expect(MINIMAX_ENDPOINTS.global_en.docsRoot).toBe("https://platform.minimax.io/docs")
    expect(MINIMAX_ENDPOINTS.cn_zh.openaiBaseURL).toMatch(/\/v1$/)
    expect(MINIMAX_ENDPOINTS.cn_zh.anthropicBaseURL).toMatch(/\/anthropic$/)
    expect(MINIMAX_ENDPOINTS.cn_zh.docsRoot).toBe("https://platform.minimaxi.com/docs")
  })

  it("registers the default and secondary target models with metadata", () => {
    expect(DEFAULT_MINIMAX_MODEL).toBe("MiniMax-M3")
    expect(MINIMAX_MODELS.map((model) => model.id)).toEqual(["MiniMax-M3", "MiniMax-M2.7"])
    expect(MINIMAX_MODELS[0].contextWindow).toBe(1_000_000)
    expect(MINIMAX_MODELS[1].contextWindow).toBe(204_800)
    expect(MINIMAX_MODELS[0].inputModalities).toEqual(["text", "image", "video"])
    expect(MINIMAX_MODELS[1].thinking).toEqual(["always_on"])
    expect(MINIMAX_MODELS[0].pricingUsdPerMillionTokens).toEqual({
      input: 0.6,
      output: 2.4,
      cacheRead: 0.12,
      cacheWrite: null,
    })
    expect(MINIMAX_MODELS[1].pricingUsdPerMillionTokens).toEqual({
      input: 0.3,
      output: 1.2,
      cacheRead: 0.06,
      cacheWrite: 0.375,
    })
  })

  it("normalizes the registered aliases without accepting unknown models", () => {
    expect(normalizeMiniMaxModelId("MiniMax-M3")).toBe("MiniMax-M3")
    expect(normalizeMiniMaxModelId("minimax-m2.7")).toBe("MiniMax-M2.7")
    expect(() => normalizeMiniMaxModelId("unknown-model")).toThrow(/unsupported MiniMax model/)
  })

  it("parses both target model IDs through the provider registry", () => {
    expect(parseModelId("minimax/MiniMax-M3")).toEqual({
      providerId: "minimax",
      modelId: "MiniMax-M3",
    })
    expect(parseModelId("minimax/MiniMax-M2.7")).toEqual({
      providerId: "minimax",
      modelId: "MiniMax-M2.7",
    })
  })
})
