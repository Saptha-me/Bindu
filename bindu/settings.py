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

    # Media Types for Static Files
    media_types: dict[str, str] = {
        ".html": "text/html",
        ".js": "application/javascript",
        ".css": "text/css",
    }

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
        "langchain": ("openinference.instrumentation.langchain", "LangChainInstrumentor"),
        "llama-index": ("openinference.instrumentation.llama_index", "LlamaIndexInstrumentor"),
        "dspy": ("openinference.instrumentation.dspy", "DSPyInstrumentor"),
        "haystack": ("openinference.instrumentation.haystack", "HaystackInstrumentor"),
        "instructor": ("openinference.instrumentation.instructor", "InstructorInstrumentor"),
        "pydantic-ai": ("openinference.instrumentation.pydantic_ai", "PydanticAIInstrumentor"),
        "autogen": ("openinference.instrumentation.autogen_agentchat", "AutogenAgentChatInstrumentor"),
        "smolagents": ("openinference.instrumentation.smolagents", "SmolAgentsInstrumentor"),
        # LLM Providers
        "litellm": ("openinference.instrumentation.litellm", "LiteLLMInstrumentor"),
        "openai": ("openinference.instrumentation.openai", "OpenAIInstrumentor"),
        "anthropic": ("openinference.instrumentation.anthropic", "AnthropicInstrumentor"),
        "mistralai": ("openinference.instrumentation.mistralai", "MistralAIInstrumentor"),
        "groq": ("openinference.instrumentation.groq", "GroqInstrumentor"),
        "bedrock": ("openinference.instrumentation.bedrock", "BedrockInstrumentor"),
        "vertexai": ("openinference.instrumentation.vertexai", "VertexAIInstrumentor"),
        "google-genai": ("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
    }

    # OpenTelemetry Base Packages
    base_packages: list[str] = [
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp",
    ]


class AgentSettings(BaseSettings):
    """Agent behavior and protocol configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT__",
        extra="allow",
    )

    # Structured Response System Prompt
    # This prompt instructs LLMs to return structured JSON responses for state transitions
    # following the A2A Protocol hybrid agent pattern
    structured_response_system_prompt: str = """You are an AI agent in the Bindu framework following the A2A Protocol.

IMPORTANT: When you need additional information or authentication from the user:

1. For user input - Return ONLY this JSON format (no other text):
{
  "state": "input-required",
  "prompt": "Your specific question here"
}

2. For authentication - Return ONLY this JSON format (no other text):
{
  "state": "auth-required",
  "prompt": "Description of what authentication is needed",
  "auth_type": "api_key|oauth|credentials|token",
  "service": "service_name"
}

3. For normal completion - Return your regular response (text, markdown, code, etc.)

Examples:
- Need clarification: {"state": "input-required", "prompt": "What format would you like for the report?"}
- Need API access: {"state": "auth-required", "prompt": "OpenAI API key required for completion", "auth_type": "api_key", "service": "openai"}
- Normal response: "Here is your weather report: Sunny, 72°F with light winds..."

CRITICAL: When returning state transition JSON, return ONLY the JSON object with no additional text before or after."""

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
    agent: AgentSettings = AgentSettings()
    auth: AuthSettings = AuthSettings()


app_settings = Settings()
