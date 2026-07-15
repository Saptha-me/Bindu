import { existsSync, readFileSync } from "fs"
import { resolve } from "path"
import { homedir } from "os"
import { Config } from "./schema"
import type { z } from "zod"

/**
 * Config loading strategy (simpler than OpenCode's hierarchical stack):
 * 1. Start with all defaults.
 * 2. Merge in config file if found (checked in order): $GATEWAY_CONFIG env, ./gateway.config.json, ./gateway.config.jsonc, ~/.config/bindu-gateway/config.json.
 * 3. Resolve any `"$VAR"` string values to process.env[VAR].
 * 4. Apply explicit env-var overrides for a known small set.
 * 5. Validate against the Zod schema.
 */

const CONFIG_FILENAMES = [
  "gateway.config.json",
  "gateway.config.jsonc",
]

function findConfigFile(cwd: string): string | null {
  if (process.env.GATEWAY_CONFIG && existsSync(process.env.GATEWAY_CONFIG)) {
    return process.env.GATEWAY_CONFIG
  }
  for (const name of CONFIG_FILENAMES) {
    const p = resolve(cwd, name)
    if (existsSync(p)) return p
  }
  const xdg = resolve(process.env.XDG_CONFIG_HOME ?? resolve(homedir(), ".config"), "bindu-gateway", "config.json")
  if (existsSync(xdg)) return xdg
  return null
}

function stripJsoncComments(raw: string): string {
  // Minimal: strip // line comments and /* */ block comments. Preserves strings.
  let out = ""
  let i = 0
  let inStr: false | '"' | "'" = false
  while (i < raw.length) {
    const c = raw[i]
    const n = raw[i + 1]
    if (inStr) {
      out += c
      if (c === "\\" && i + 1 < raw.length) {
        out += raw[i + 1]
        i += 2
        continue
      }
      if (c === inStr) inStr = false
      i++
      continue
    }
    if (c === '"' || c === "'") {
      inStr = c
      out += c
      i++
      continue
    }
    if (c === "/" && n === "/") {
      while (i < raw.length && raw[i] !== "\n") i++
      continue
    }
    if (c === "/" && n === "*") {
      i += 2
      while (i < raw.length && !(raw[i] === "*" && raw[i + 1] === "/")) i++
      i += 2
      continue
    }
    out += c
    i++
  }
  return out
}

function resolveEnv(value: unknown): unknown {
  if (typeof value === "string") {
    const m = value.match(/^\$([A-Z_][A-Z0-9_]*)$/)
    if (m) return process.env[m[1]] ?? value
    return value
  }
  if (Array.isArray(value)) return value.map(resolveEnv)
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value)) out[k] = resolveEnv(v)
    return out
  }
  return value
}

/**
 * Apply env-var overrides for the small subset we expose as ergonomic
 * environment knobs. Anything richer should go in the config file.
 */
function envOverrides(base: Record<string, any>): Record<string, any> {
  const out = JSON.parse(JSON.stringify(base))
  out.gateway = out.gateway ?? {}

  if (process.env.GATEWAY_PORT) {
    out.gateway.server = out.gateway.server ?? {}
    out.gateway.server.port = Number(process.env.GATEWAY_PORT)
  }
  if (process.env.GATEWAY_HOSTNAME) {
    out.gateway.server = out.gateway.server ?? {}
    out.gateway.server.hostname = process.env.GATEWAY_HOSTNAME
  }
  if (process.env.GATEWAY_API_KEY) {
    out.gateway.auth = out.gateway.auth ?? {}
    out.gateway.auth.tokens = [process.env.GATEWAY_API_KEY]
  }
  // SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY env hooks removed — the
  // gateway no longer has a persistent store. Setting them in your
  // .env.local is harmless (they're ignored), but they no longer wire
  // anything. Stateless gateway, see config/schema.ts §SessionConfig.

  // OpenRouter is the single supported LLM provider — see
  // src/provider/index.ts for the rationale. The env hook wires
  // OpenRouter's OpenAI-compatible API (baseURL filled in by the
  // provider layer if not explicitly set in a config file).
  if (process.env.OPENROUTER_API_KEY) {
    out.provider = out.provider ?? {}
    out.provider.openrouter = {
      ...out.provider.openrouter,
      apiKey: process.env.OPENROUTER_API_KEY,
    }
  }

  if (
    process.env.MINIMAX_API_KEY ||
    process.env.MINIMAX_REGION ||
    process.env.MINIMAX_PROTOCOL ||
    process.env.MINIMAX_OPENAI_BASE_URL ||
    process.env.MINIMAX_ANTHROPIC_BASE_URL
  ) {
    out.provider = out.provider ?? {}
    out.provider.minimax = {
      ...out.provider.minimax,
      ...(process.env.MINIMAX_API_KEY ? { apiKey: process.env.MINIMAX_API_KEY } : {}),
      ...(process.env.MINIMAX_REGION ? { region: process.env.MINIMAX_REGION } : {}),
      ...(process.env.MINIMAX_PROTOCOL ? { protocol: process.env.MINIMAX_PROTOCOL } : {}),
      ...(process.env.MINIMAX_OPENAI_BASE_URL
        ? { openaiBaseURL: process.env.MINIMAX_OPENAI_BASE_URL }
        : {}),
      ...(process.env.MINIMAX_ANTHROPIC_BASE_URL
        ? { anthropicBaseURL: process.env.MINIMAX_ANTHROPIC_BASE_URL }
        : {}),
    }
  }

  // Optional: comma-separated fallback model IDs. When primary fails
  // (rate limit, upstream error), OpenRouter tries each in order.
  // Example: OPENROUTER_FALLBACK_MODELS="minimax/minimax-m3,openai/gpt-4o-mini"
  if (process.env.OPENROUTER_FALLBACK_MODELS) {
    const fallbacks = process.env.OPENROUTER_FALLBACK_MODELS.split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    if (fallbacks.length > 0) {
      out.provider = out.provider ?? {}
      out.provider.openrouter = {
        ...out.provider.openrouter,
        fallbackModels: fallbacks,
      }
    }
  }

  return out
}

export interface LoadOptions {
  cwd?: string
}

export function loadConfig(opts: LoadOptions = {}): z.infer<typeof Config> {
  const cwd = opts.cwd ?? process.cwd()
  const filePath = findConfigFile(cwd)

  let raw: Record<string, any> = {}
  if (filePath) {
    const text = readFileSync(filePath, "utf8")
    const parsed = filePath.endsWith(".jsonc") ? stripJsoncComments(text) : text
    try {
      raw = JSON.parse(parsed)
    } catch (e) {
      throw new Error(`config: failed to parse ${filePath}: ${(e as Error).message}`)
    }
  }

  raw = resolveEnv(raw) as Record<string, any>
  raw = envOverrides(raw)

  const result = Config.safeParse(raw)
  if (!result.success) {
    const issues = result.error.issues
      .map((i) => `  - ${i.path.join(".")}: ${i.message}`)
      .join("\n")
    throw new Error(`config: validation failed (source: ${filePath ?? "defaults+env"}):\n${issues}`)
  }
  return result.data
}
