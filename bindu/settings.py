"""Settings configuration for the bindu agent system.

This module defines the configuration settings for the application using pydantic models.
"""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    environment: str = Field(default="development", env="ENVIRONMENT")
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
    bindu_context: str = "https://bindu.ai/ns/v1"
    verification_key_type: str = "Ed25519VerificationKey2020"
    key_fragment: str = "key-1"
    service_fragment: str = "agent-service"
    service_type: str = "binduAgentService"

    # DID Method Prefixes
    method_bindu: str = "bindu"
    method_key: str = "key"
    multibase_prefix: str = "z"  # Base58btc prefix for ed25519

    # DID Extension
    extension_uri: str = "https://github.com/Saptha-me/saptha_me"
    extension_description: str = "DID-based identity management for bindu agents"
    resolver_endpoint: str = "/did/resolve"
    info_endpoint: str = "/agent/info"

    # DID Key Directory
    pki_dir: str = ".pebbling"

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
    default_host: str = Field(default="localhost", env="HOST")
    default_port: int = Field(default=3773, env="PORT")

    # Timeouts (seconds)
    request_timeout: int = 30
    connection_timeout: int = 10

    @computed_field
    @property
    def default_url(self) -> str:
        """Compute default URL from host and port."""
        return f"http://{self.default_host}:{self.default_port}"


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
    facilitator_url: str = ""
    default_network: str = "base"
    pay_to_env: str = "X402_PAY_TO"
    max_timeout_seconds: int = 600

    # Extension URI
    extension_uri: str = "https://github.com/google-a2a/a2a-x402/v0.1"

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
        "tasks/get": "get_task",
        "tasks/cancel": "cancel_task",
        "tasks/list": "list_tasks",
        "contexts/list": "list_contexts",
        "contexts/clear": "clear_context",
        "tasks/feedback": "task_feedback",
    }

    # Task State Configuration (A2A Protocol)
    # Non-terminal states: Task is mutable, can receive new messages
    non_terminal_states: frozenset[str] = frozenset(
        {
            "submitted",  # Task submitted, awaiting execution
            "working",  # Agent actively processing
            "input-required",  # Waiting for user input
            "auth-required",  # Waiting for authentication
            "payment-required",  # Waiting for payment (Bindu extension)
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

    Supports multiple authentication providers:
    - auth0: Auth0 (default)
    - cognito: AWS Cognito (future)
    - azure: Azure AD (future)
    - custom: Custom JWT provider (future)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUTH__",
        extra="allow",
    )

    # Enable/disable authentication
    enabled: bool = False

    # Authentication provider
    provider: str = "auth0"  # Options: auth0, cognito, azure, custom

    # Auth0 Configuration
    domain: str = ""
    audience: str = ""
    algorithms: list[str] = ["RS256"]
    issuer: str = ""

    # JWKS Configuration
    jwks_uri: str = ""
    jwks_cache_ttl: int = 3600  # Cache JWKS for 1 hour

    # Token Validation
    leeway: int = 10  # Clock skew tolerance in seconds

    # AWS Cognito Configuration (future use)
    region: str = ""  # e.g., "us-east-1"
    user_pool_id: str = ""  # e.g., "us-east-1_XXXXXXXXX"
    app_client_id: str = ""  # Cognito app client ID

    # Azure AD Configuration (future use)
    tenant_id: str = ""  # Azure AD tenant ID
    client_id: str = ""  # Azure AD application ID

    # Public Endpoints (no authentication required)
    public_endpoints: list[str] = [
        "/.well-known/agent.json",
        "/did/resolve",
        "/agent/info",
        "/agent.html",
        "/chat.html",
        "/storage.html",
        "/js/*",
        "/css/*",
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
    deployment: DeploymentSettings = DeploymentSettings()
    logging: LoggingSettings = LoggingSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    x402: X402Settings = X402Settings()
    agent: AgentSettings = AgentSettings()
    auth: AuthSettings = AuthSettings()


app_settings = Settings()
