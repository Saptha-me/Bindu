import { z } from "zod"

/**
 * Config schema for the Bindu Gateway.
 *
 * Narrower than OpenCode's config — we only need what the gateway actually
 * reads. No LSP, no formatter, no MCP here. The schema is intentionally flat
 * so that a fresh reader can trace every knob end-to-end.
 */

export const ServerConfig = z.object({
  port: z.number().int().positive().default(3774),
  hostname: z.string().default("0.0.0.0"),
})

export const GatewayAuthConfig = z.object({
  mode: z.enum(["bearer", "none"]).default("bearer"),
  tokens: z.array(z.string()).default([]),
})

// Session is now always stateless — the gateway holds per-request
// in-memory state for the lifetime of a /plan call, then drops it.
// The `mode` field is kept on the schema for forward-compat (some
// callers may still send it), but only `"stateless"` is honored;
// `"stateful"` is rejected at boot. `ttlDays` becomes informational
// — there's nothing to TTL when there's nothing persisted.
export const SessionConfig = z.object({
  mode: z.literal("stateless").default("stateless"),
  ttlDays: z.number().int().positive().default(30),
})

export const LimitsConfig = z.object({
  maxHops: z.number().int().positive().default(5),
  maxConcurrentToolCalls: z.number().int().positive().default(3),
  defaultTaskTimeoutMs: z.number().int().positive().default(60_000),
})

export const GatewayBlock = z.object({
  server: ServerConfig.default({ port: 3774, hostname: "0.0.0.0" }),
  auth: GatewayAuthConfig.default({ mode: "bearer", tokens: [] }),
  session: SessionConfig.default({ mode: "stateless", ttlDays: 30 }),
  limits: LimitsConfig.default({ maxHops: 5, maxConcurrentToolCalls: 3, defaultTaskTimeoutMs: 60_000 }),
})
export type GatewayBlock = z.infer<typeof GatewayBlock>

export const ProviderEntry = z
  .object({
    apiKey: z.string().optional(),
    baseURL: z.string().optional(),
    openaiBaseURL: z.string().optional(),
    anthropicBaseURL: z.string().optional(),
    region: z.enum(["global_en", "cn_zh"]).optional(),
    protocol: z.enum(["openai", "anthropic"]).optional(),
    fallbackModels: z.array(z.string()).optional(),
  })
  .passthrough()
export type ProviderEntry = z.infer<typeof ProviderEntry>

export const AgentEntry = z.object({
  name: z.string().optional(),
  description: z.string().optional(),
  mode: z.enum(["primary", "subagent", "all"]).default("primary"),
  model: z.string().optional(),
  prompt: z.string().optional(),
  temperature: z.number().optional(),
  topP: z.number().optional(),
  steps: z.number().int().positive().optional(),
})
export type AgentEntry = z.infer<typeof AgentEntry>

export const PermissionAction = z.enum(["allow", "deny", "ask"])
export type PermissionAction = z.infer<typeof PermissionAction>

export const PermissionRule = z.union([PermissionAction, z.record(z.string(), PermissionAction)])
export const PermissionConfig = z.record(z.string(), PermissionRule).default({})

export const Config = z.object({
  gateway: GatewayBlock,
  provider: z.record(z.string(), ProviderEntry).default({}),
  agent: z.record(z.string(), AgentEntry).default({}),
  permission: PermissionConfig,
  instructions: z.array(z.string()).default([]),
})
export type Config = z.infer<typeof Config>
