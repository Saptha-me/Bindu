"""Settings configuration for the bindu agent system.

This module defines the configuration settings for the application using pydantic models.
"""

import re

from pydantic import Field, computed_field, BaseModel, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices
from typing import Literal


class ExtraNetwork(BaseModel):
    """Operator-supplied mapping for a non-default EVM network.

    The x402 v2 SDK only knows about Base mainnet (``eip155:8453``) and
    Base Sepolia (``eip155:84532``) out of the box. Reaching any other
    EVM chain — SKALE, Polygon, Avalanche, Ethereum mainnet, etc. — needs
    two things:

    1. A facilitator that supports that chain (set ``facilitator_url`` on
       :class:`X402Settings` to a facilitator advertising the chain in its
       ``/supported`` response).
    2. A way for the SDK's price parser to convert a human-readable amount
       (``"$0.01"``) into the right ERC-20 contract on that chain.

    This config carries #2 — the asset metadata the resource server
    registers with x402 v2's ``ExactEvmServerScheme.add_money_parser`` so
    pricing in the agent's ``execution_cost`` lands on the right asset.
    The friendly key (the dict key in :attr:`X402Settings.extra_networks`)
    is what operators write in their agent config; the ``caip2`` field is
    what gets stamped on PaymentRequirements.

    Example — adding SKALE Europa Hub:

    .. code-block:: python

        extra_networks={
            "skale-europa": ExtraNetwork(
                caip2="eip155:1187947933",
                asset="0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
                asset_name="Bridged USDC (SKALE Bridge)",
                asset_decimals=6,
                asset_eip712_version="2",
            )
        }
    """

    caip2: str = Field(
        ...,
        description="CAIP-2 network identifier (e.g. 'eip155:1187947933').",
    )
    asset: str = Field(
        ...,
        description="ERC-20 contract address that the facilitator settles in.",
    )
    asset_symbol: str = Field(default="USDC", description="Token symbol.")
    asset_name: str = Field(
        default="USD Coin",
        description="Token name. Goes into EIP-712 domain — must match the on-chain token's `name()`.",
    )
    asset_decimals: int = Field(
        default=6,
        ge=0,
        le=36,
        description="Token decimals — used to scale Money to atomic units.",
    )
    asset_eip712_version: str = Field(
        default="2",
        description="EIP-712 domain version — must match the on-chain token's domain separator.",
    )

    @field_validator("caip2")
    @classmethod
    def _validate_caip2(cls, value: str) -> str:
        if not re.fullmatch(r"eip155:\d+", value):
            raise ValueError("caip2 must match 'eip155:<chain_id>' (digits only)")
        return value

    @field_validator("asset")
    @classmethod
    def _validate_asset(cls, value: str) -> str:
        if not re.fullmatch(r"0x[a-fA-F0-9]{40}", value):
            raise ValueError("asset must be a 0x-prefixed 40-hex-character address")
        return value


class ProjectSettings(BaseSettings):
    """
    Project-level configuration settings.

    Contains general application settings like environment, debug mode,
    and project metadata.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROJECT__",
        extra="allow",
    )

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "PROJECT__ENVIRONMENT"),
    )
    name: str = "bindu Agent"
    version: str = "0.1.0"

    @computed_field
    @property
    def debug(self) -> bool:
        """Compute debug mode based on environment."""
        return self.environment != "production"

    @computed_field
    @property
    def testing(self) -> bool:
        """Compute testing mode based on environment."""
        return self.environment == "testing"


class DIDSettings(BaseSettings):
    """DID (Decentralized Identity) configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DID__",
        extra="allow",
    )

    # DID Configuration
    config_filename: str = "did.json"
    method: str = "key"
    agent_extension_metadata: str = "did.message.signature"

    # DID File Names
    private_key_filename: str = "private.pem"
    public_key_filename: str = "public.pem"

    # DID Document Constants
    w3c_context: str = "https://www.w3.org/ns/did/v1"
    bindu_context: str = "https://getbindu.com/ns/v1"
    verification_key_type: str = "Ed25519VerificationKey2020"
    key_fragment: str = "key-1"
    service_fragment: str = "agent-service"
    service_type: str = "binduAgentService"

    # DID Method Prefixes
    method_bindu: str = "bindu"
    method_key: str = "key"
    multibase_prefix: str = "z"  # Base58btc prefix for ed25519

    # DID Extension
    extension_uri: str = "https://github.com/getbindu/bindu"
    extension_description: str = "DID-based identity management for bindu agents"
    resolver_endpoint: str = "/did/resolve"
    info_endpoint: str = "/agent/info"

    # DID Key Directory
    pki_dir: str = ".bindu"

    # DID Validation
    prefix: str = "did:"
    min_parts: int = 3
    bindu_parts: int = 4

    # Text Encoding
    text_encoding: str = "utf-8"
    base58_encoding: str = "ascii"


class NetworkSettings(BaseSettings):
    """Network and connectivity configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NETWORK__",
        extra="allow",
    )

    # Default Host and URL
    default_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("HOST", "NETWORK__DEFAULT_HOST"),
    )
    default_port: int = Field(
        default=3773,
        validation_alias=AliasChoices("PORT", "NETWORK__DEFAULT_PORT"),
    )

    # Timeouts (seconds)
    request_timeout: int = 30
    connection_timeout: int = 10

    @computed_field
    @property
    def default_url(self) -> str:
        """Compute default URL from host and port."""
        return f"http://{self.default_host}:{self.default_port}"


class TunnelSettings(BaseSettings):
    """FRP tunnel configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TUNNEL__",
        extra="allow",
    )

    # Tunnel timeout (seconds)
    timeout_seconds: int = 30

    # Error message for tunnel failures
    error_message: str = (
        "Could not create tunnel. Please check the logs below for more information:"
    )

    # Default FRP server configuration
    default_server_address: str = "142.132.241.44:7000"
    default_tunnel_domain: str = "tunnel.getbindu.com"

    # FRP client version
    frpc_version: str = "0.61.0"


class DeploymentSettings(BaseSettings):
    """Deployment and server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DEPLOYMENT__",
        extra="allow",
    )

    # Server Types
    server_type_agent: str = "agent"
    server_type_mcp: str = "mcp"

    # Endpoint Types
    endpoint_type_json_rpc: str = "json-rpc"
    endpoint_type_http: str = "http"
    endpoint_type_sse: str = "sse"

    # Docker Configuration
    docker_port: int = 8080
    docker_healthcheck_path: str = "/healthz"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOGGING__",
        extra="allow",
    )

    # Log Directory and File
    log_dir: str = "logs"
    log_filename: str = "bindu_server.log"

    # Log Rotation and Retention
    log_rotation: str = "10 MB"
    log_retention: str = "1 week"

    # Log Format
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}:{function}:{line} | {message}"

    # Log Levels
    default_level: str = "INFO"

    # Rich Theme Colors
    theme_info: str = "bold cyan"
    theme_warning: str = "bold yellow"
    theme_error: str = "bold red"
    theme_critical: str = "bold white on red"
    theme_debug: str = "dim blue"
    theme_did: str = "bold green"
    theme_security: str = "bold magenta"
    theme_agent: str = "bold blue"

    # Rich Console Settings
    traceback_width: int = 120
    show_locals: bool = True


class ObservabilitySettings(BaseSettings):
    """Observability and instrumentation configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OBSERVABILITY__",
        extra="allow",
    )

    # OpenInference Instrumentor Mapping
    # Maps framework names to their instrumentor module paths and class names
    # Format: framework_name: (module_path, class_name)
    instrumentor_map: dict[str, tuple[str, str]] = {
        # Agent Frameworks
        "agno": ("openinference.instrumentation.agno", "AgnoInstrumentor"),
        "crewai": ("openinference.instrumentation.crewai", "CrewAIInstrumentor"),
        "langchain": (
            "openinference.instrumentation.langchain",
            "LangChainInstrumentor",
        ),
        "llama-index": (
            "openinference.instrumentation.llama_index",
            "LlamaIndexInstrumentor",
        ),
        "dspy": ("openinference.instrumentation.dspy", "DSPyInstrumentor"),
        "haystack": ("openinference.instrumentation.haystack", "HaystackInstrumentor"),
        "instructor": (
            "openinference.instrumentation.instructor",
            "InstructorInstrumentor",
        ),
        "pydantic-ai": (
            "openinference.instrumentation.pydantic_ai",
            "PydanticAIInstrumentor",
        ),
        "autogen": (
            "openinference.instrumentation.autogen_agentchat",
            "AutogenAgentChatInstrumentor",
        ),
        "smolagents": (
            "openinference.instrumentation.smolagents",
            "SmolAgentsInstrumentor",
        ),
        # LLM Providers
        "litellm": ("openinference.instrumentation.litellm", "LiteLLMInstrumentor"),
        "openai": ("openinference.instrumentation.openai", "OpenAIInstrumentor"),
        "anthropic": (
            "openinference.instrumentation.anthropic",
            "AnthropicInstrumentor",
        ),
        "mistralai": (
            "openinference.instrumentation.mistralai",
            "MistralAIInstrumentor",
        ),
        "groq": ("openinference.instrumentation.groq", "GroqInstrumentor"),
        "bedrock": ("openinference.instrumentation.bedrock", "BedrockInstrumentor"),
        "vertexai": ("openinference.instrumentation.vertexai", "VertexAIInstrumentor"),
        "google-genai": (
            "openinference.instrumentation.google_genai",
            "GoogleGenAIInstrumentor",
        ),
    }

    # OpenTelemetry Base Packages
    base_packages: list[str] = [
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp",
    ]


class X402Settings(BaseSettings):
    """x402 payments configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="X402__",
        extra="allow",
    )

    provider: str = "coinbase"
    facilitator_url: str = "https://x402.org/facilitator"
    default_network: str = "base-sepolia"
    pay_to_env: str = "X402_PAY_TO"
    max_timeout_seconds: int = 600

    # TRACE Trust API Integration
    trace_api_key: str | None = None
    trace_min_score: float = 0.35
    trace_api_url: str = "https://trace-api-sigma.vercel.app"

    # Extension URI
    extension_uri: str = "https://github.com/google-a2a/a2a-x402/v0.1"

    # Protected methods that require payment
    # Similar to auth's public_endpoints, this defines which JSON-RPC methods need payment
    protected_methods: list[str] = [
        "message/send",  # Creating new tasks requires payment
        # "message/stream",  # Uncomment if streaming should require payment
    ]

    # Metadata keys
    meta_status_key: str = "x402.payment.status"
    meta_required_key: str = "x402.payment.required"
    meta_payload_key: str = "x402.payment.payload"
    meta_receipts_key: str = "x402.payment.receipts"
    meta_error_key: str = "x402.payment.error"

    # Status values
    status_required: str = "payment-required"
    status_submitted: str = "payment-submitted"
    status_verified: str = "payment-verified"
    status_completed: str = "payment-completed"
    status_failed: str = "payment-failed"

    # RPC URLs by network — REMOVED in the x402 v2 migration. The v0.2.1
    # middleware connected to RPC providers directly for the on-chain
    # `balanceOf` check; in v2 that responsibility moves to the facilitator
    # (HTTPFacilitatorClient → /verify), so the resource server never makes
    # an RPC call. Configuring RPC URLs here is now a no-op. If you need to
    # change which facilitator answers /verify, set
    # `app_settings.x402.facilitator_url` instead.

    # Operator-extensible mapping for EVM networks the x402 SDK doesn't ship
    # with built-in metadata. See :class:`ExtraNetwork` for the per-entry
    # contract. The default ships one example — SKALE Europa Hub via
    # facilitator.x402.fi — so that "SKALE just works" out of the box
    # *iff* the operator also sets ``facilitator_url`` to a SKALE-aware
    # facilitator. The Coinbase default (``x402.org/facilitator``) does
    # NOT support SKALE today.
    extra_networks: dict[str, ExtraNetwork] = {
        "skale-europa": ExtraNetwork(
            caip2="eip155:1187947933",
            asset="0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
            asset_symbol="USDC",
            asset_name="Bridged USDC (SKALE Bridge)",
            asset_decimals=6,
            asset_eip712_version="2",
        ),
    }


class AgentSettings(BaseSettings):
    """Agent behavior and protocol configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT__",
        extra="allow",
    )

    # A2A Protocol Method Handlers
    # Maps JSON-RPC method names to task_manager handler method names
    method_handlers: dict[str, str] = {
        "message/send": "send_message",
        "message/stream": "stream_message",
        "tasks/get": "get_task",
        "tasks/cancel": "cancel_task",
        "tasks/list": "list_tasks",
        "contexts/list": "list_contexts",
        "contexts/clear": "clear_context",
        "tasks/feedback": "task_feedback",
        # Push-notification config methods (A2A protocol extension)
        "tasks/pushNotificationConfig/set": "set_task_push_notification",
        "tasks/pushNotificationConfig/get": "get_task_push_notification",
        "tasks/pushNotificationConfig/list": "list_task_push_notifications",
        "tasks/pushNotificationConfig/delete": "delete_task_push_notification",
    }

    # Task State Configuration (A2A Protocol)
    # Non-terminal states: Task is mutable, can receive new messages
    non_terminal_states: frozenset[str] = frozenset(
        {
            "submitted",  # Task submitted, awaiting execution
            "working",  # Agent actively processing
            "input-required",  # Waiting for user input
            "auth-required",  # Waiting for authentication
        }
    )

    # Terminal states: Task is immutable, no further changes allowed
    terminal_states: frozenset[str] = frozenset(
        {
            "completed",  # Successfully completed with artifacts
            "failed",  # Failed due to error
            "canceled",  # Canceled by user
            "rejected",  # Rejected by agent
        }
    )

    # message/stream polling behavior
    stream_poll_interval_seconds: float = 0.1
    stream_missing_task_retries: int = 2
    stream_missing_task_retry_delay_seconds: float = 0.05

    # Structured Response System Prompt
    # This prompt instructs LLMs to return structured JSON responses for state transitions
    # following the A2A Protocol hybrid agent pattern
    structured_response_system_prompt: str = """
    You are an AI agent in the Bindu framework following the A2A Protocol.

Goal
- If the user's request is underspecified, ask exactly one high-impact clarifying question
  using the required state JSON.
- If the request is sufficiently specified, return the normal completion
  (text/markdown/code/etc.).

Strict Output Rule for Clarification
- When clarification is needed, return ONLY this JSON (no extra text, no code fences):
{
  "state": "input-required",
  "prompt": "Your specific question here"
}
Underspecification Heuristics (ask if any of these matter and are missing)
- Platform / channel
- Audience
- Purpose / goal
- Tone / voice
- Format
- Length constraint
- Style constraints
- Language / locale
- Visual context
- Domain context
- Compliance constraints

Decision Rubric
1) Can you deliver a high-quality, low-regret result without knowing any of the missing items above?
   - YES → Provide completion immediately (do NOT ask).
   - NO → Ask exactly ONE clarifying question that most increases quality.
2) If multiple items are missing, prefer a **single multiple-choice question**
   capturing the most impactful dimension (e.g., platform) and include an "Other" option.
3) Never chain questions. Ask one, then wait for the user’s answer.
4) If the user explicitly says “any/you pick/default,” proceed without further questions and choose sensible defaults.
5) If the user has previously specified a stable preference in this conversation
   (e.g., "Instagram captions"), apply it silently.

Question Crafting Guidelines
- Be specific, short, and action-oriented.
- Prefer multiple choice with 3–5 options + “Other”.
- Mention the default you’ll use if they don’t care (e.g., “If no preference, I’ll format for Instagram”).

{{ ... }}
Allowed Outputs
- Clarification needed → ONLY the state JSON above.
- Otherwise → Normal completion (no JSON).

Few-Shot Examples

(1) User: "provide sunset quote"
→ Missing: platform/length/tone.
Return:
{
  "state": "input-required",
  "prompt": "Do you want this as an Instagram caption, a Pinterest pin text, or a "
            "general quote? (Options: Instagram, Pinterest, General, Other)"
}

(2) User: "write a caption for my beach photo"
→ Missing: platform. Caption implies short & casual; platform most impactful.
Return:
{
  "state": "input-required",
  "prompt": "Which platform should I format the caption for? (Options: Instagram, TikTok, Pinterest, LinkedIn, Other)"
}

Defaults (use only if user says 'any/you pick/default' or prior context establishes them)
- Platform: Instagram
- Tone: concise, warm, professional (or playful for captions)
- Length: short
- Language: same as user’s request
- Hashtags: none unless platform is Instagram/Pinterest and user implies discoverability; then add 2–3 relevant tags.

CRITICAL
- When returning the state JSON, return ONLY the JSON object with no additional text before or after.

   """

    # Enable/disable structured response system
    enable_structured_responses: bool = True


class AuthSettings(BaseSettings):
    """Authentication and authorization configuration settings.

    Uses Ory Hydra as the authentication provider.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUTH__",
        extra="allow",
    )

    # Enable/disable authentication
    enabled: bool = False

    # Authentication provider
    provider: str = "hydra"

    # Token Validation
    algorithms: list[str] = ["RS256"]
    leeway: int = 10  # Clock skew tolerance in seconds

    # Public Endpoints (no authentication required)
    public_endpoints: list[str] = [
        "/.well-known/agent.json",
        "/.well-known/*",
        "/did/resolve",
        "/agent/info",
        "/agent/negotiation",
        "/agent/skills",
        "/agent/skills/*",
        "/health",
        "/healthz",  # strict readiness probe for k8s
        "/metrics",
        "/payment-capture",  # x402 payment capture page (browser-based)
        "/api/start-payment-session",  # x402 payment session creation
        "/api/payment-status/*",  # x402 payment status check
    ]

    # Permission-based access control
    require_permissions: bool = False
    permissions: dict[str, list[str]] = {
        "message/send": ["agent:write"],
        "tasks/get": ["agent:read"],
        "tasks/cancel": ["agent:write"],
        "tasks/list": ["agent:read"],
        "contexts/list": ["agent:read"],
        "tasks/feedback": ["agent:write"],
    }

    # Admission control. When None (default), any DID that passes Hydra
    # introspection + signature verification is admitted — preserves the
    # pre-allowlist behavior. When set, only listed DIDs are admitted;
    # every other authenticated caller is rejected with HTTP 403 by the
    # auth middleware. Closes `did-admission-control-missing`.
    allowed_dids: list[str] | None = None


# ============================================================================
# Ory Configuration Models
# ============================================================================


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration for external services."""

    name: str = Field(..., description="Provider name (notion, google, github, etc.)")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    auth_url: HttpUrl = Field(..., description="Authorization URL")
    token_url: HttpUrl = Field(..., description="Token URL")
    userinfo_url: HttpUrl | None = Field(None, description="User info URL")
    scope: str = Field(..., description="Default scope")
    redirect_uri: HttpUrl = Field(..., description="Redirect URI")


# ============================================================================
# Hydra Settings
# ============================================================================


class HydraSettings(BaseSettings):
    """Ory Hydra OAuth2 authentication configuration settings.

    Hydra provides OAuth2/OIDC authentication for securing Bindu APIs
    and enabling agent-to-agent authentication.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HYDRA__",
        extra="allow",
    )

    # Enable/disable Hydra authentication
    enabled: bool = False

    # Hydra API endpoints
    admin_url: str = "https://hydra-admin.getbindu.com"
    public_url: str = "https://hydra.getbindu.com"

    # Connection settings
    timeout: int = 10  # Request timeout in seconds
    verify_ssl: bool = True  # Verify SSL certificates
    max_retries: int = 3  # Maximum retry attempts

    # Token cache settings
    cache_ttl: int = 300  # Token introspection cache TTL (5 minutes)
    max_cache_size: int = 1000  # Maximum cache entries

    # Scopes that bypass the introspection cache. Tokens carrying any of
    # these are re-introspected against Hydra on every request so that
    # revocations take effect immediately. Matches the in-process default
    # in ``bindu.server.middleware.auth.hydra.DEFAULT_SENSITIVE_SCOPES``;
    # override per-deployment to widen or shrink the set.
    sensitive_scopes: list[str] = [
        "admin",
        "agent:execute",
        "payment:capture",
        "key:rotate",
    ]

    # Auto-registration settings
    auto_register_agents: bool = True  # Auto-register agents as OAuth clients
    agent_client_prefix: str = "agent-"  # Prefix for agent client IDs

    # Default OAuth2 scopes for agents
    default_agent_scopes: list[str] = [
        "openid",
        "offline",
        "agent:read",
        "agent:write",
    ]

    # Default grant types for agents
    default_grant_types: list[str] = [
        "client_credentials",  # M2M authentication
        "authorization_code",  # User authentication
        "refresh_token",  # Token refresh
    ]

    # Public endpoints (no authentication required)
    public_endpoints: list[str] = [
        "/.well-known/agent.json",
        "/.well-known/*",
        "/did/resolve",
        "/agent/info",
        "/agent/negotiation",
        "/agent/skills",
        "/agent/skills/*",
        "/health",
        "/healthz",  # strict readiness probe for k8s
        "/metrics",
        "/payment-capture",
        "/favicon.ico",
        "/oauth/*",  # OAuth callback endpoints
    ]


class MTLSSettings(BaseSettings):
    """Mutual TLS (mTLS) configuration for end-to-end encrypted agent communication.

    Bindu agents fetch short-lived X.509 certificates from a Smallstep step-ca
    server, using a Hydra OIDC token as the provisioner credential. Certificates
    live on disk alongside the DID keypair (``DIDSettings.pki_dir``), are backed
    up to Vault when ``VaultSettings.enabled`` is true, and are renewed in-process
    before expiry.

    See ``docs/MTLS_DEPLOYMENT_GUIDE.md`` for the CA architecture.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MTLS__",
        extra="allow",
    )

    # Enable/disable mTLS. Off by default so existing deployments are unaffected
    # until the step-ca service is up and an agent is explicitly opted in.
    enabled: bool = False

    # step-ca service endpoints. The root URL serves the public PEM bundle and
    # does not require authentication; the API URL is mTLS-protected on the
    # CA side once the agent is enrolled.
    ca_url: str = "https://ca.getbindu.com"
    ca_root_url: str = "https://ca.getbindu.com/roots.pem"
    ca_provisioner: str = "hydra"  # OIDC provisioner name configured in step-ca

    # Connection settings
    timeout: int = 10
    verify_ssl: bool = True
    max_retries: int = 3

    # Certificate lifecycle. Short TTL + passive renewal is the revocation
    # strategy (see deployment guide); there is no CRL.
    cert_ttl_hours: int = 24
    renew_before_hours: int = 8  # re-fetch when fewer than this many hours remain
    renew_check_interval_seconds: int = 3600  # how often the renewal task wakes up

    # Key type for agent certs. step-ca templates expect EC P-256.
    key_type: str = "EC"
    key_curve: str = "P-256"

    # On-disk filenames. These live next to the DID key files inside
    # ``DIDSettings.pki_dir`` so a single backup captures both identities.
    cert_filename: str = "tls_cert.pem"
    key_filename: str = "tls_key.pem"
    ca_bundle_filename: str = "ca_bundle.pem"
    csr_filename: str = "tls.csr"  # written for debugging; not load-bearing

    # Server-side TLS behavior. When ``require_client_cert`` is true, the HTTP
    # and gRPC servers reject any connection that doesn't present a verified
    # peer cert (full mTLS).
    require_client_cert: bool = True

    # Client-side TLS behavior. Verify peer server certs against the bundled CA.
    verify_server_cert: bool = True

    # Rollout mode controls how inbound auth is validated:
    #   "hybrid" - mTLS + Hydra both required; cert CN must match Hydra client_id
    #              (default during the migration window)
    #   "mtls"   - mTLS only; skip Hydra introspection entirely on inbound
    #   "off"    - same effect as enabled=False; mTLS is wired but not enforced
    mode: str = "hybrid"

    # Vault paths for cert backup. Only used when ``VaultSettings.enabled`` is
    # true; ``{agent_id}`` is substituted at runtime.
    vault_path_template: str = "secret/bindu/agents/{agent_id}/mtls"

    # OIDC audience that step-ca's OIDC provisioner expects in the token's
    # ``aud`` claim. step-ca rejects sign requests whose token doesn't carry
    # this audience, so Hydra registration and the token request both need
    # to include it. Matches the ``clientID`` field in step-ca's
    # ``ca-config.json`` on the infra side.
    oidc_audience: str = "step-ca"


class StorageSettings(BaseSettings):
    """Storage backend configuration settings.

    Supports multiple storage backends:
    - memory: In-memory storage (default, non-persistent)
    - postgres: PostgreSQL storage (persistent)

    PostgreSQL settings must be provided via environment variables or config.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    # Storage backend selection
    backend: Literal["memory", "postgres"] = Field(
        default="memory",
        validation_alias=AliasChoices("backend", "STORAGE_TYPE"),
    )

    # PostgreSQL Configuration - must be provided via env vars or config
    postgres_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("postgres_url", "DATABASE_URL"),
    )
    postgres_pool_min: int = 2
    postgres_pool_max: int = 10
    postgres_timeout: int = 60
    postgres_command_timeout: int = 30

    # DID-based schema isolation
    postgres_did: str | None = Field(
        default=None,
        validation_alias=AliasChoices("postgres_did", "POSTGRES_DID", "DID"),
    )

    # Connection retry settings
    postgres_max_retries: int = 3
    postgres_retry_delay: float = 1.0

    # Migration settings
    run_migrations_on_startup: bool = False  # Safer default for production


class SchedulerSettings(BaseSettings):
    """Scheduler backend configuration settings.

    Supports multiple scheduler backends:
    - memory: In-memory scheduler (default, single-process)
    - redis: Redis scheduler (distributed, multi-process)

    Redis settings must be provided via environment variables or config.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    # Scheduler backend selection
    backend: Literal["memory", "redis"] = Field(
        default="memory",
        validation_alias=AliasChoices("backend", "SCHEDULER_TYPE"),
    )

    # Redis Configuration - must be provided via env vars or config
    redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("redis_url", "REDIS_URL"),
    )
    redis_host: str | None = None
    redis_port: int | None = None
    redis_password: str | None = None
    redis_db: int | None = None
    queue_name: str = "bindu:tasks"  # Can keep default queue name
    max_connections: int = 10  # Connection pool setting
    retry_on_timeout: bool = True  # Retry behavior setting
    poll_timeout: int = Field(
        default=1,
        validation_alias=AliasChoices("poll_timeout", "REDIS_POLL_TIMEOUT"),
        description="Timeout in seconds for Redis blpop operations. Higher values reduce API calls but increase task start latency.",
    )


class RetrySettings(BaseSettings):
    """Retry mechanism configuration settings using Tenacity.

    Configures retry behavior for different operation types:
    - Worker operations (task execution)
    - Storage operations (database, redis)
    - Scheduler operations (task scheduling)
    - API calls (external services)
    """

    # Worker task execution retries
    worker_max_attempts: int = 3
    worker_min_wait: float = 1.0  # seconds
    worker_max_wait: float = 10.0  # seconds

    # Storage operation retries (database, redis)
    storage_max_attempts: int = 5
    storage_min_wait: float = 0.5  # seconds
    storage_max_wait: float = 5.0  # seconds

    # Scheduler operation retries
    scheduler_max_attempts: int = 3
    scheduler_min_wait: float = 1.0  # seconds
    scheduler_max_wait: float = 8.0  # seconds

    # External API call retries
    api_max_attempts: int = 4
    api_min_wait: float = 1.0  # seconds
    api_max_wait: float = 15.0  # seconds


class NegotiationSettings(BaseSettings):
    """Negotiation and capability assessment configuration settings.

    Controls how agents assess their ability to handle tasks during
    the negotiation phase of agent-to-agent communication.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NEGOTIATION__",
        extra="allow",
    )

    # Scoring weights for capability assessment
    # All weights are normalized to sum to 1.0 during calculation
    skill_match_weight: float = 0.55
    io_compatibility_weight: float = 0.20
    performance_weight: float = 0.15
    load_weight: float = 0.05
    cost_weight: float = 0.05

    # Default latency estimate when no performance data available
    default_latency_ms: int = 5000

    # Keyword extraction limits
    max_keyword_length: int = 100
    max_task_text_length: int = 10000

    # Minimum score threshold for acceptance
    min_score_threshold: float = 0.0

    # Embedding-based semantic matching
    use_embeddings: bool = True
    embedding_provider: str = "openrouter"  # Options: openrouter, sentence-transformers
    embedding_model: str = "text-embedding-3-small"  # OpenRouter model
    embedding_api_key: str = ""  # OpenRouter API key (set via config or env)
    embedding_weight: float = 0.7  # Weight for embedding score in hybrid matching
    keyword_weight: float = 0.3  # Weight for keyword score in hybrid matching
    embedding_batch_size: int = 32
    embedding_cache_size: int = 1000  # Max task embeddings to cache


class VaultSettings(BaseSettings):
    """HashiCorp Vault configuration for DID keys and Hydra credentials storage.

    When enabled, Vault provides persistent storage for:
    - DID private/public keys (ensures same DID across pod restarts)
    - Hydra OAuth2 client credentials (prevents duplicate client registrations)

    This is critical for Kubernetes deployments where pods are ephemeral.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VAULT__",
        extra="allow",
    )

    # Vault connection
    url: str = Field(
        default="http://localhost:8200",
        validation_alias=AliasChoices("VAULT__URL", "VAULT_ADDR"),
        description="Vault server URL (e.g., https://vault.example.com:8200)",
    )
    token: str = Field(
        default="",
        validation_alias=AliasChoices("VAULT__TOKEN", "VAULT_TOKEN"),
        description="Vault authentication token for API access",
    )

    # Enable/disable Vault
    enabled: bool = Field(
        default=False,
        description="Enable Vault integration for persistent credential storage",
    )


class OAuthSettings(BaseSettings):
    """OAuth provider configuration for user credential management (v0)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OAUTH__",
        extra="allow",
    )

    # Base URL for OAuth callbacks
    callback_base_url: str = Field(
        default="http://localhost:3773",
        description="Base URL for OAuth callbacks (e.g., https://your-domain.com)",
    )

    # Notion OAuth
    notion_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("OAUTH__NOTION_CLIENT_ID", "NOTION_CLIENT_ID"),
    )
    notion_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OAUTH__NOTION_CLIENT_SECRET", "NOTION_CLIENT_SECRET"
        ),
    )

    # Google OAuth (for Gmail)
    google_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("OAUTH__GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    )
    google_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OAUTH__GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"
        ),
    )

    # GitHub OAuth
    github_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("OAUTH__GITHUB_CLIENT_ID", "GITHUB_CLIENT_ID"),
    )
    github_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OAUTH__GITHUB_CLIENT_SECRET", "GITHUB_CLIENT_SECRET"
        ),
    )


class SentrySettings(BaseSettings):
    """Sentry error tracking and performance monitoring configuration.

    Sentry provides real-time error tracking, performance monitoring,
    and release health tracking for production deployments.
    """

    # Enable/disable Sentry
    enabled: bool = False

    # Sentry DSN (Data Source Name)
    # Get this from your Sentry project settings
    dsn: str = ""

    # Environment name (e.g., production, staging, development)
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("SENTRY__ENVIRONMENT", "ENVIRONMENT"),
    )

    # Release version (for tracking deployments)
    # Defaults to project version if not specified
    release: str = ""

    # Sample rate for error events (0.0 to 1.0)
    # 1.0 = capture all errors
    traces_sample_rate: float = 1.0

    # Sample rate for performance monitoring (0.0 to 1.0)
    # 0.1 = capture 10% of transactions for performance monitoring
    profiles_sample_rate: float = 0.1

    # Enable performance monitoring
    enable_tracing: bool = True

    # Enable profiling
    enable_profiling: bool = False

    # Send default PII (Personally Identifiable Information)
    # Set to False in production for privacy compliance
    send_default_pii: bool = False

    # Maximum breadcrumbs to capture
    max_breadcrumbs: int = 100

    # Attach stack trace to messages
    attach_stacktrace: bool = True

    integrations: list[str] = [
        "starlette",  # Covers all HTTP endpoints in bindu/server/endpoints/
        "sqlalchemy",  # PostgreSQL storage integration
        "redis",  # Redis scheduler integration
        "asyncio",  # Async task integration
    ]

    # Tags to add to all events
    # Useful for filtering and grouping in Sentry UI
    default_tags: dict[str, str] = {}

    # Before send hook - filter events before sending to Sentry
    # Can be used to scrub sensitive data or filter out noise
    filter_transactions: list[str] = [
        "/healthz",
        "/health",
        "/metrics",
        "/favicon.ico",
    ]

    # Ignore specific errors by exception type
    ignore_errors: list[str] = [
        "KeyboardInterrupt",
        "SystemExit",
    ]

    # Server name (defaults to hostname)
    server_name: str = ""

    # Debug mode (logs Sentry SDK debug info)
    debug: bool = False


class GrpcSettings(BaseSettings):
    """gRPC adapter configuration for language-agnostic agent support.

    When enabled, the Bindu core starts a gRPC server alongside the HTTP server.
    External SDKs (TypeScript, Kotlin, Rust) connect to this gRPC server to
    register their agents and receive handler calls.

    The gRPC server implements BinduService (registration) and acts as a client
    to the SDK's AgentHandler service (task execution).

    Architecture:
        SDK (any language) --gRPC--> Bindu Core (:3774)
            RegisterAgent(config, skills, callback_address)

        Bindu Core --gRPC--> SDK (callback_address)
            HandleMessages(messages) when a task arrives
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GRPC__",
        extra="allow",
    )

    # Enable/disable gRPC adapter server
    enabled: bool = Field(
        default=False,
        description="Enable gRPC server for language-agnostic SDK support",
    )

    # gRPC server bind address
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the gRPC server to",
    )

    # gRPC server port (separate from HTTP port 3773)
    port: int = Field(
        default=3774,
        description="Port for the gRPC server (default: 3774)",
    )

    # Thread pool size for gRPC server
    max_workers: int = Field(
        default=10,
        description="Maximum number of gRPC server worker threads",
    )

    # Maximum message size (4MB default)
    max_message_length: int = Field(
        default=4 * 1024 * 1024,
        description="Maximum gRPC message size in bytes (default: 4MB)",
    )

    # Timeout for HandleMessages calls to SDK (seconds)
    handler_timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for calling SDK's HandleMessages",
    )

    # Health check interval for registered agents (seconds)
    health_check_interval: int = Field(
        default=30,
        description="Interval in seconds for health checking registered agents",
    )


class Settings(BaseSettings):
    """Main settings class that aggregates all configuration components."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="allow",
    )

    project: ProjectSettings = ProjectSettings()
    did: DIDSettings = DIDSettings()
    network: NetworkSettings = NetworkSettings()
    tunnel: TunnelSettings = TunnelSettings()
    deployment: DeploymentSettings = DeploymentSettings()
    logging: LoggingSettings = LoggingSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    x402: X402Settings = X402Settings()
    agent: AgentSettings = AgentSettings()
    auth: AuthSettings = AuthSettings()
    hydra: HydraSettings = HydraSettings()
    mtls: MTLSSettings = MTLSSettings()
    vault: VaultSettings = VaultSettings()
    oauth: OAuthSettings = OAuthSettings()
    storage: StorageSettings = StorageSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    retry: RetrySettings = RetrySettings()
    negotiation: NegotiationSettings = NegotiationSettings()
    sentry: SentrySettings = SentrySettings()
    grpc: GrpcSettings = GrpcSettings()


app_settings = Settings()
