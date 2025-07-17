# |--------------------------------------------------|
# |                                                  |
# |           Give Feedback / Get Help               |
# | https://github.com/Pebbling-ai/pebble/issues/new |
# |                                                  |
# |--------------------------------------------------|
#
#  Thank you!!! We ❤️ you! - Raahul && Claude

"""
Pebbling Protocol Type Definitions

This module contains all the protocol data models used for communication between
agents and the Pebbling framework.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import Field, RootModel

from pebbling.protocol._base import PebblingProtocolBaseModel

#-----------------------------------------------------------------------------
# Base Types and Enums
#-----------------------------------------------------------------------------

class Role(str, Enum):
    """Message sender's role"""
    agent = 'agent'
    user = 'user'

class RunMode(str, Enum):
    sync = "sync"
    async_ = "async"
    stream = "stream"

class TaskState(str, Enum):
    """Represents the possible states of a Task."""
    submitted = 'submitted'
    working = 'working'
    input_required = 'input-required'
    completed = 'completed'
    canceled = 'canceled'
    failed = 'failed'
    rejected = 'rejected'
    auth_required = 'auth-required'
    unknown = 'unknown'
    trust_verification_required = 'trust-verification-required'


class TrustLevel(str, Enum):
    """Trust levels for operations and permissions"""
    untrusted = "untrusted"  # No trust established, restricted operations only
    minimal = "minimal"      # Very low trust, highly restricted operations
    low = "low"              # Basic operations, minimal risk
    standard = "standard"    # Standard operations for authenticated users
    medium = "medium"        # Standard operations with some sensitive capabilities
    high = "high"            # Sensitive operations requiring strong verification
    elevated = "elevated"    # Operations requiring multi-factor or multi-party verification
    critical = "critical"    # Highly sensitive operations like financial transactions
    super_critical = "super-critical" # Operations with regulatory or extreme risk implications
    emergency = "emergency"  # Special case operations requiring override in critical situations


class TrustCategory(str, Enum):
    """Categories of operations requiring trust verification"""
    identity = "identity"                # Identity verification operations
    authentication = "authentication"    # Authentication-related operations
    authorization = "authorization"      # Authorization and permissions management
    data_access = "data_access"          # Access to sensitive data
    financial = "financial"              # Financial transactions and account management
    healthcare = "healthcare"            # Healthcare and medical data operations
    personal = "personal"                # Access to personal identifiable information
    admin = "admin"                      # Administrative functions
    system = "system"                    # Core system operations
    communication = "communication"      # Communication between agents/systems
    regulatory = "regulatory"            # Operations subject to regulatory requirements


class TrustVerificationMethod(str, Enum):
    """Methods used to verify trust between agents"""
    certificate = "certificate"         # Using X.509 certificates
    oauth = "oauth"                     # OAuth 2.0 based verification
    did = "did"                         # Decentralized Identity verification
    mtls = "mtls"                       # Mutual TLS verification
    jwt = "jwt"                         # JWT token based verification
    multi_party = "multi_party"         # Multiple parties must approve
    biometric = "biometric"             # Biometric verification required
    zero_knowledge = "zero_knowledge"   # Zero-knowledge proof verification
    multi_factor = "multi_factor"       # Multiple verification factors


class IdentityProvider(str, Enum):
    """Supported identity providers"""
    keycloak = "keycloak"
    azure_ad = "azure_ad"
    okta = "okta"
    auth0 = "auth0"
    custom = "custom"


#-----------------------------------------------------------------------------
# Content & Message Parts
#-----------------------------------------------------------------------------

class TextPart(PebblingProtocolBaseModel):
    """Represents a text segment within parts."""
    kind: Literal['text'] = 'text'
    metadata: dict[str, Any] | None = None
    content: str


class FileWithBytes(PebblingProtocolBaseModel):
    """File representation with binary content"""
    bytes: str
    mimeType: str | None = None
    name: str | None = None


class FileWithUri(FileWithBytes):
    """File representation with URI reference"""
    uri: str


class FilePart(TextPart):
    """Represents a file part in a message"""
    kind: Literal['file'] = 'file'
    file: FileWithBytes | FileWithUri


class DataPart(TextPart):
    """Represents a structured data part in a message"""
    kind: Literal['data'] = 'data'
    data: dict[str, Any]


class Part(RootModel[TextPart | FilePart | DataPart]):
    """Union type for all possible message parts"""
    root: TextPart | FilePart | DataPart


class Artifact(PebblingProtocolBaseModel):
    """Represents an artifact generated for a task."""
    artifact_id: UUID = Field(..., description="Unique identifier for the artifact")
    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    parts: list[Part]


class Message(PebblingProtocolBaseModel):
    """Message exchanged between agents or users"""
    contextId: UUID
    kind: Literal['message'] = 'message'
    messageId: UUID
    metadata: dict[str, Any] | None = None
    parts: list[Part]
    role: Role
    extra_data: dict[str, Any] | None = None


class TaskStatus(PebblingProtocolBaseModel):
    """Status information for a task"""
    message: Message | None = None
    state: TaskState
    timestamp: str | None = Field(
        default=None, examples=['2023-10-27T10:00:00Z']
    )


class Task(PebblingProtocolBaseModel):
    """Top-level task representation"""
    artifacts: list[Artifact] | None = None
    contextId: UUID
    history: list[Message] | None = None
    id: str
    kind: Literal['task'] = 'task'
    metadata: dict[str, Any] | None = None
    status: TaskStatus

class TrustVerificationResult(PebblingProtocolBaseModel):
    """Result of trust verification"""
    verified: bool = Field(..., description="Whether trust verification succeeded")
    trust_level: TrustLevel = Field(..., description="The verified trust level")
    allowed_operations: List[str] = Field(
        default_factory=list, 
        description="Operations allowed with the verified trust level"
    )
    denied_operations: List[str] = Field(
        default_factory=list,
        description="Operations denied due to insufficient trust level" 
    )
    verification_timestamp: str = Field(..., 
        description="When verification occurred", examples=['2023-10-27T10:00:00Z'])
    verification_token: Optional[str] = Field(None, 
        description="Token for subsequent operations", examples=['abc123'])
    token_expiry: Optional[str] = Field(None, 
        description="When the verification token expires", examples=['2023-10-27T10:00:00Z'])


#-----------------------------------------------------------------------------
# Agent-to-Agent Negotiation Models
#-----------------------------------------------------------------------------

class NegotiationStatus(str, Enum):
    """Represents the possible negotiation statuses."""
    proposed = 'proposed'
    accepted = 'accepted'
    rejected = 'rejected'
    countered = 'countered'


class NegotiationSessionStatus(str, Enum):
    """Represents the possible statuses of a negotiation session."""
    initiated = 'initiated'
    ongoing = 'ongoing'
    completed = 'completed'
    rejected = 'rejected'


class NegotiationProposal(PebblingProtocolBaseModel):
    """Structured negotiation proposal exchanged between agents"""
    proposal_id: UUID = Field(..., description="Unique ID of this specific proposal")
    from_agent: UUID = Field(..., description="Agent ID initiating the proposal")
    to_agent: UUID = Field(..., description="Agent ID receiving the proposal")
    terms: Dict[str, Any] = Field(..., description="Negotiation terms (structured)")
    timestamp: str = Field(..., 
        description="UNIX timestamp when the proposal was made", 
        examples=['2023-10-27T10:00:00Z'])
    status: NegotiationStatus = Field(
        NegotiationStatus.proposed, 
        description="Status of this specific proposal"
    )


class NegotiationSession(PebblingProtocolBaseModel):
    """Session details for agent-to-agent negotiations"""
    session_id: UUID = Field(..., description="Unique identifier for the negotiation session")
    status: NegotiationSessionStatus = Field(
        NegotiationSessionStatus.initiated,
        description="Current status of the negotiation"
    )
    participants: List[UUID] = Field(..., description="List of participating agent IDs")
    proposals: List[NegotiationProposal] = Field(
        default_factory=list,
        description="Array of negotiation proposals exchanged"
    )


#-----------------------------------------------------------------------------
# Payment Models
#-----------------------------------------------------------------------------

class PaymentActionType(str, Enum):
    """Types of payment actions that can be performed"""
    submit = 'submit'
    cancel = 'cancel'
    refund = 'refund'
    verify = 'verify'
    unknown = 'unknown'


class PaymentStatus(str, Enum):
    """Status of a payment in its lifecycle"""
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'
    refunded = 'refunded'
    cancelled = 'cancelled'
    disputed = 'disputed'


class PaymentMethod(str, Enum):
    """Common payment methods"""
    credit_card = 'credit_card'
    debit_card = 'debit_card'
    ach = 'ach'
    wire_transfer = 'wire_transfer'
    crypto = 'crypto'
    sepa = 'sepa'
    paypal = 'paypal'
    other = 'other'


class BillingPeriod(str, Enum):
    """Billing frequency options for recurring payments"""
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'
    quarterly = 'quarterly'
    yearly = 'yearly'
    one_time = 'one-time'


class PaymentAction(PebblingProtocolBaseModel):
    """Represents the possible payment actions."""
    action_type: PaymentActionType = Field(PaymentActionType.submit, description="Type of payment action")
    amount: float = Field(..., description="The amount of the payment", examples=[10.0])
    currency: str = Field(..., description="ISO currency code clearly identified (e.g., USD)")
    billing_period: BillingPeriod = Field(
        BillingPeriod.one_time, 
        description="Billing frequency clearly defined if subscription-based"
    )
    
    # Additional fields for comprehensive payment handling
    transaction_id: Optional[str] = Field(None, description="Unique transaction identifier")
    payment_method: Optional[PaymentMethod] = Field(None, description="Method of payment")
    payment_status: Optional[PaymentStatus] = Field(None, description="Current status of the payment")
    
    # Time tracking
    created_timestamp: Optional[str] = Field(
        None, description="UNIX timestamp when payment was created", examples=['2023-10-27T10:00:00Z'])
    processed_timestamp: Optional[str] = Field(
        None, description="UNIX timestamp when payment was processed", examples=['2023-10-27T10:00:00Z'])
    
    # Entity information
    payer_id: Optional[Union[UUID, str]] = Field(
        None, description="ID of the paying entity")
    payee_id: Optional[Union[UUID, str]] = Field(
        None, description="ID of the receiving entity")
    
    # Banking specific
    reference: Optional[str] = Field(
        None, description="Payment reference or memo")
    regulatory_info: Optional[Dict[str, Any]] = Field(
        None, description="Regulatory information for compliance")


#-----------------------------------------------------------------------------
# JSON-RPC Error Types
#-----------------------------------------------------------------------------

class JSONRPCError(PebblingProtocolBaseModel):
    """Base JSON-RPC error representation"""
    code: int
    data: Any | None = None
    message: str


class JSONParseError(JSONRPCError):
    """JSON-RPC parse error"""
    code: Literal[-32700] = -32700
    message: Literal['Invalid JSON'] = 'Invalid JSON'


class InvalidRequestError(JSONRPCError):
    """JSON-RPC invalid request error"""
    code: Literal[-32600] = -32600
    message: Literal['Validation error'] = 'Validation error'


class MethodNotFoundError(JSONRPCError):
    """JSON-RPC method not found error"""
    code: Literal[-32601] = -32601
    message: Literal['Method not found'] = 'Method not found'


class InvalidParamsError(JSONRPCError):
    """JSON-RPC invalid parameters error"""
    code: Literal[-32602] = -32602
    message: Literal['Invalid parameters'] = 'Invalid parameters'


class InternalError(JSONRPCError):
    """JSON-RPC internal error"""
    code: Literal[-32603] = -32603
    message: Literal['Internal error'] = 'Internal error'


class InvalidAgentResponseError(JSONRPCError):
    """Error for invalid agent responses"""
    code: Literal[-32006] = -32006
    message: Literal['Invalid agent response'] = 'Invalid agent response'


class TaskNotFoundError(JSONRPCError):
    """Error for task not found"""
    code: Literal[-32007] = -32007
    message: Literal['Task not found'] = 'Task not found'


class TaskNotCancelableError(JSONRPCError):
    """Error for task not cancelable"""
    code: Literal[-32008] = -32008
    message: Literal['Task not cancelable'] = 'Task not cancelable'


class PushNotificationNotSupportedError(JSONRPCError):
    """Error for push notification not supported"""
    code: Literal[-32009] = -32009
    message: Literal['Push notification not supported'] = 'Push notification not supported'


class UnsupportedOperationError(JSONRPCError):
    """Error for unsupported operations"""
    code: Literal[-32010] = -32010
    message: Literal['Unsupported operation'] = 'Unsupported operation'


class ContentTypeNotSupportedError(JSONRPCError):
    """Error for unsupported content types"""
    code: Literal[-32011] = -32011
    message: Literal['Content type not supported'] = 'Content type not supported'


#-----------------------------------------------------------------------------
# JSON-RPC Request & Response Types
#-----------------------------------------------------------------------------

class JSONRPCErrorResponse(PebblingProtocolBaseModel):
    """JSON-RPC error response"""
    error: (
        JSONRPCError
        | JSONParseError
        | InvalidRequestError
        | MethodNotFoundError
        | InvalidParamsError
        | InternalError
        | TaskNotFoundError
        | TaskNotCancelableError
        | PushNotificationNotSupportedError
        | UnsupportedOperationError
        | ContentTypeNotSupportedError
        | InvalidAgentResponseError
    )
    id: str | int | None = None
    jsonrpc: Literal['2.0'] = '2.0'


class TaskStatusUpdateEvent(PebblingProtocolBaseModel):
    """Event for task status updates"""
    contextId: UUID
    final: bool
    kind: Literal['status-update'] = 'status-update'
    metadata: dict[str, Any] | None = None
    status: TaskStatus
    taskId: UUID


class TaskArtifactUpdateEvent(PebblingProtocolBaseModel):
    """Event for task artifact updates"""
    append: bool | None = None
    artifact: Artifact
    contextId: UUID
    kind: Literal['artifact-update'] = 'artifact-update'
    lastChunk: bool | None = None
    metadata: dict[str, Any] | None = None
    taskId: UUID


class TaskIdParams(PebblingProtocolBaseModel):
    """Parameters for task identification"""
    id: UUID
    metadata: dict[str, Any] | None = None


class MessageSendConfiguration(PebblingProtocolBaseModel):
    """Configuration for message sending"""
    acceptedOutputModes: list[str]
    blocking: bool | None = None
    historyLength: int | None = None


class MessageSendParams(PebblingProtocolBaseModel):
    """Parameters for sending messages"""
    configuration: MessageSendConfiguration | None = None
    message: Message
    metadata: dict[str, Any] | None = None


# Response types
class SendMessageSuccessResponse(PebblingProtocolBaseModel):
    """Success response for sending a message"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task | Message


class SendStreamingMessageSuccessResponse(PebblingProtocolBaseModel):
    """Success response for sending a streaming message"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task | Message | TaskStatusUpdateEvent | TaskArtifactUpdateEvent


class GetTaskSuccessResponse(PebblingProtocolBaseModel):
    """Success response for getting a task"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task


class CancelTaskSuccessResponse(PebblingProtocolBaseModel):
    """Success response for canceling a task"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task

class TrustVerificationResponse(PebblingProtocolBaseModel):
    """Success response for trust verification"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: TrustVerificationResult


# Request types
class SendMessageRequest(PebblingProtocolBaseModel):
    """Request to send a message"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    method: Literal['message/send'] = 'message/send'
    params: MessageSendParams


class SendStreamingMessageRequest(SendMessageRequest):
    """Request to send a streaming message"""
    method: Literal['message/stream'] = 'message/stream'


class GetTaskRequest(PebblingProtocolBaseModel):
    """Request to get a task"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    method: Literal['tasks/get'] = 'tasks/get'
    params: TaskIdParams


class CancelTaskRequest(GetTaskRequest):
    """Request to cancel a task"""
    method: Literal['tasks/cancel'] = 'tasks/cancel'


class TaskResubscriptionRequest(GetTaskRequest):
    """Request to resubscribe to task events"""
    method: Literal['tasks/resubscribe'] = 'tasks/resubscribe'


class TrustVerificationParams(PebblingProtocolBaseModel):
    """Parameters for trust verification requests"""
    agent_id: Union[UUID, int, str] = Field(..., description="ID of the agent requesting verification")
    target_agent_id: Union[UUID, int, str] = Field(..., description="ID of the target agent to interact with")
    operations: List[str] = Field(default_factory=list, description="Operations the agent wants to perform")
    certificate: Optional[str] = Field(None, description="Agent's certificate for verification")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional verification metadata")


class TrustVerificationRequest(PebblingProtocolBaseModel):
    """Request to verify trust between agents"""
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    method: Literal['trust/verify'] = 'trust/verify'
    params: TrustVerificationParams


# Union types for requests and responses
class JSONRPCResponse(
    RootModel[
        JSONRPCErrorResponse
        | SendMessageSuccessResponse
        | SendStreamingMessageSuccessResponse
        | GetTaskSuccessResponse
        | CancelTaskSuccessResponse
        | TrustVerificationResponse
    ]
):
    """Union type for all JSON-RPC responses"""
    root: (
        JSONRPCErrorResponse
        | SendMessageSuccessResponse
        | SendStreamingMessageSuccessResponse
        | GetTaskSuccessResponse
        | CancelTaskSuccessResponse
        | TrustVerificationResponse
    )


class SendMessageResponse(
    RootModel[JSONRPCErrorResponse | SendMessageSuccessResponse]
):
    """Union type for send message responses"""
    root: JSONRPCErrorResponse | SendMessageSuccessResponse


class SendStreamingMessageResponse(
    RootModel[JSONRPCErrorResponse | SendStreamingMessageSuccessResponse]
):
    """Union type for streaming message responses"""
    root: JSONRPCErrorResponse | SendStreamingMessageSuccessResponse


class PebblingRequest(
    RootModel[
        SendMessageRequest
        | SendStreamingMessageRequest
        | GetTaskRequest
        | CancelTaskRequest
        | TaskResubscriptionRequest
        | TrustVerificationRequest
    ]
):
    """Union type for all Pebbling requests"""
    root: (
        SendMessageRequest
        | SendStreamingMessageRequest
        | GetTaskRequest
        | CancelTaskRequest
        | TaskResubscriptionRequest
        | TrustVerificationRequest
    )
    """A2A supported request types"""

#-----------------------------------------------------------------------------
# Lets handle Trust
#-----------------------------------------------------------------------------

class KeycloakRole(PebblingProtocolBaseModel):
    """Keycloak role model"""
    role_id: UUID = Field(..., description="Role ID from Keycloak IAM.")
    role_name: str = Field(..., description="Human-readable role name.")
    permissions: List[str] = Field(default_factory=list, description="Specific permissions tied to this role.")
    trust_level: TrustLevel = Field(TrustLevel.MEDIUM, description="Default trust level for this role")
    realm_name: str = Field(..., description="The Keycloak realm this role belongs to.")
    
    # For integrations with other identity providers
    external_mappings: Optional[Dict[str, str]] = Field(
        None, 
        description="Mappings to equivalent roles in other identity systems"
    )
    
    # For detailed permission control
    operation_permissions: Optional[Dict[str, TrustLevel]] = Field(
        None,
        description="Operation-specific trust requirements, e.g., {'update_customer': 'high'}"
    )

class AgentTrust(PebblingProtocolBaseModel):
    """Trust configuration for an agent"""
    identity_provider: IdentityProvider = Field(..., description="Identity provider used for authentication")
    inherited_roles: List[KeycloakRole] = Field(
        default_factory=list, 
        description="Roles inherited from the agent's creator"
    )
    certificate: Optional[str] = Field(None, description="Agent's security certificate for verification")
    certificate_fingerprint: Optional[str] = Field(None, description="Fingerprint of the agent's certificate")
    creator_id: Union[UUID, int, str] = Field(..., description="ID of the user who created this agent")
    creation_timestamp: str = Field(
        ..., 
        description="UNIX timestamp of agent creation",
        examples=['2023-10-27T10:00:00Z']
    )
    trust_verification_required: bool = Field(True, description="Whether trust verification is required")
    allowed_operations: Dict[str, TrustLevel] = Field(
        default_factory=dict,
        description="Operations this agent is allowed to perform with required trust levels"
    )
    
#-----------------------------------------------------------------------------
# Security 
#-----------------------------------------------------------------------------

class MTLSConfiguration(PebblingProtocolBaseModel):
    """Secure mTLS configuration for agent communication"""
    endpoint: str = Field(..., description="Secure mTLS agent endpoint.")
    public_key: str = Field(..., description="Agent's public key for mTLS.")
    certificate_chain: Optional[List[str]] = Field(None, description="Certificate chain for validation.")
    certificate_expiry: Optional[int] = Field(None, description="UNIX timestamp when certificate expires.")
    key_rotation_policy: Optional[str] = Field(None, description="Policy for key rotation, e.g. 'quarterly'")
    cipher_suites: Optional[List[str]] = Field(None, description="Allowed cipher suites for TLS connection.")
    min_tls_version: Optional[str] = Field("1.2", description="Minimum TLS version required.")

class AgentIdentity(PebblingProtocolBaseModel):
    # DID identification
    did: Optional[str] = Field(None, description="Agent DID for decentralized identity (URI format).")
    did_document: Optional[Dict[str, Any]] = Field(None, description="Complete DID document containing verification methods, services, etc.")
    did_resolution_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata from DID resolution process.")
    
    # Alternative identification
    agentdns_url: Optional[str] = Field(None, description="Agent DNS-based identity URL (agentdns.ai).")
    
    # MTLS configuration
    endpoint: str = Field(..., description="Secure mTLS agent endpoint.")
    mtls_config: MTLSConfiguration = Field(..., description="mTLS configuration for agent.")
    
    # Verification method preference
    identity_verification_method: Literal["did", "agentdns", "certificate"] = Field(
        "certificate", description="Primary method for identity verification."
    )

#-----------------------------------------------------------------------------
# Security 
#-----------------------------------------------------------------------------

class AgentCapabilities(PebblingProtocolBaseModel):
    """Agent capabilities including supported media types and operations"""
    supported_operations: List[str] = Field(default_factory=list, description="Operations this agent can perform")
    input_content_types: List[str] = Field(default_factory=lambda: ["text/plain"], description="Content types this agent can accept")
    output_content_types: List[str] = Field(default_factory=lambda: ["text/plain"], description="Content types this agent can produce")
    supports_images: bool = Field(False, description="Whether agent can process images")
    supports_audio: bool = Field(False, description="Whether agent can process audio")
    supports_video: bool = Field(False, description="Whether agent can process video")
    supports_binary: bool = Field(False, description="Whether agent can process binary data")
    max_message_size_bytes: Optional[int] = Field(None, description="Maximum message size in bytes")
    streaming_supported: bool = Field(False, description="Whether agent supports streaming responses")


class AgentMetrics(PebblingProtocolBaseModel):
    """Agent usage and performance metrics"""
    total_requests: int = Field(0, description="Total number of requests processed")
    total_tokens: Optional[int] = Field(None, description="Total tokens processed")
    avg_response_time_ms: Optional[int] = Field(None, description="Average response time in milliseconds")
    error_rate: Optional[float] = Field(None, description="Error rate percentage")
    uptime_seconds: Optional[int] = Field(None, description="Total uptime in seconds")
    last_active: Optional[int] = Field(None, description="UNIX timestamp of last activity")
    custom_metrics: Optional[Dict[str, Any]] = Field(None, description="Additional custom metrics")


class AgentManifest(PebblingProtocolBaseModel):
    """Complete agent manifest with identity and capabilities"""
    agnt_id: Union[UUID, int, str] = Field(
        ..., 
        description="The unique identifier of the agent", 
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    name: str = Field(
        ..., 
        description="The name of the agent", 
        examples=["Japanese Restaurant Reviewer Agent"]
    )
    description: Optional[str] = Field(None, description="Detailed description of the agent's purpose and capabilities")
    user_id: Union[UUID, int, str] = Field(..., description="user")
    
    # Identity
    identity: AgentIdentity = Field(..., description="Agent identity information.")

    # Trust
    trust_config: Optional[AgentTrust] = Field(
        None, 
        description="Trust configuration and inherited permissions"
    )
    
    # Capabilities
    capabilities: AgentCapabilities = Field(
        default_factory=AgentCapabilities,
        description="Agent's capabilities and supported operations"
    )
    
    # Metrics
    metrics: Optional[AgentMetrics] = Field(
        None, 
        description="Agent usage and performance metrics"
    )
    
    # Configuration
    num_history_sessions: Optional[int] = None
    storage: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = None
    
    # Debug settings
    debug_mode: bool = False
    debug_level: Literal[1, 2] = 1
    
    # Monitoring
    monitoring: bool = False
    telemetry: bool = True
    
    version: str = Field(..., examples=['1.0.0'])
