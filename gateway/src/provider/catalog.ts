export type MiniMaxRegion = "global_en" | "cn_zh"
export type MiniMaxProtocol = "openai" | "anthropic"

export const MINIMAX_ENDPOINTS = {
  global_en: {
    openaiBaseURL: "https://api.minimax.io/v1",
    anthropicBaseURL: "https://api.minimax.io/anthropic",
    docsRoot: "https://platform.minimax.io/docs",
  },
  cn_zh: {
    openaiBaseURL: "https://api.minimaxi.com/v1",
    anthropicBaseURL: "https://api.minimaxi.com/anthropic",
    docsRoot: "https://platform.minimaxi.com/docs",
  },
} as const satisfies Record<
  MiniMaxRegion,
  Record<`${MiniMaxProtocol}BaseURL`, string> & { docsRoot: string }
>

export const MINIMAX_MODELS = [
  {
    id: "MiniMax-M3",
    aliases: ["minimax-m3"],
    contextWindow: 1_000_000,
    pricingUsdPerMillionTokens: {
      input: 0.6,
      output: 2.4,
      cacheRead: 0.12,
      cacheWrite: null,
    },
    inputModalities: ["text", "image", "video"],
    thinking: ["adaptive", "disabled"],
  },
  {
    id: "MiniMax-M2.7",
    aliases: ["minimax-m2.7"],
    contextWindow: 204_800,
    pricingUsdPerMillionTokens: {
      input: 0.3,
      output: 1.2,
      cacheRead: 0.06,
      cacheWrite: 0.375,
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
