export type MiniMaxRegion = "global_en" | "cn_zh"
export type MiniMaxProtocol = "openai" | "anthropic"

export const MINIMAX_ENDPOINTS = {
  global_en: {
    openaiBaseURL: "https://api.minimax.io/v1",
    anthropicBaseURL: "https://api.minimax.io/anthropic",
  },
  cn_zh: {
    openaiBaseURL: "https://api.minimaxi.com/v1",
    anthropicBaseURL: "https://api.minimaxi.com/anthropic",
  },
} as const satisfies Record<MiniMaxRegion, Record<`${MiniMaxProtocol}BaseURL`, string>>

export const MINIMAX_MODELS = [
  {
    id: "MiniMax-M3",
    aliases: ["minimax-m3"],
    contextWindow: 1_000_000,
    pricingUsdPerMillionTokens: {
      standard: [
        { inputTokensLte: 512_000, input: 0.3, output: 1.2, cacheRead: 0.06, cacheWrite: null },
        { inputTokensGt: 512_000, input: 0.6, output: 2.4, cacheRead: 0.12, cacheWrite: null },
      ],
      priority: [
        { inputTokensLte: 512_000, input: 0.45, output: 1.8, cacheRead: 0.09, cacheWrite: null },
        { inputTokensGt: 512_000, input: 0.9, output: 3.6, cacheRead: 0.18, cacheWrite: null },
      ],
    },
    inputModalities: ["text", "image", "video"],
    thinking: ["adaptive", "disabled"],
  },
  {
    id: "MiniMax-M2.7",
    aliases: ["minimax-m2.7"],
    contextWindow: 204_800,
    pricingUsdPerMillionTokens: {
      standard: [{ input: 0.3, output: 1.2, cacheRead: 0.06, cacheWrite: 0.375 }],
    },
    inputModalities: ["text"],
    thinking: ["always_on"],
  },
] as const

export const DEFAULT_MINIMAX_MODEL = "MiniMax-M3"

export function normalizeMiniMaxModelId(modelId: string): string {
  const model = MINIMAX_MODELS.find(
    (candidate) => candidate.id === modelId || candidate.aliases.some((alias) => alias === modelId),
  )
  if (!model) {
    throw new Error(
      `provider: unsupported MiniMax model "${modelId}" (supported: ${MINIMAX_MODELS.map((item) => item.id).join(", ")})`,
    )
  }
  return model.id
}
