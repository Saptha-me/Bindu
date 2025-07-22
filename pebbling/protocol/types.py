# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Pebbling Protocol Type Definitions.

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
    """Message sender's role."""
    
    agent = 'agent'
    user = 'user'


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


class ErrorCode(str, Enum):
    """Error code enum for API responses."""
    
    server_error = "server_error"
    invalid_input = "invalid_input"
    not_found = "not_found"


class RunMode(str, Enum):
    """Run mode options for agent execution."""
    
    sync = "sync"           # Synchronous execution, wait for complete response
    async_mode = "async"    # Asynchronous execution, don't wait for response
    stream = "stream"       # Streaming execution, receive partial results


#-----------------------------------------------------------------------------
# Content & Message Parts
#-----------------------------------------------------------------------------

class TextPart(PebblingProtocolBaseModel):
    """Represents a text segment within parts."""
    
    kind: Literal['text'] = 'text'
    metadata: dict[str, Any] | None = None
    content: str


class FileWithBytes(PebblingProtocolBaseModel):
    """File representation with binary content."""
    
    bytes: str
    mimeType: str | None = None
    name: str | None = None


class FileWithUri(FileWithBytes):
    """File representation with URI reference."""
    
    uri: str


class FilePart(TextPart):
    """Represents a file part in a message."""
    
    kind: Literal['file'] = 'file'
    file: FileWithBytes | FileWithUri


class DataPart(TextPart):
    """Represents a structured data part in a message."""
    
    kind: Literal['data'] = 'data'
    data: dict[str, Any]


class Part(RootModel[TextPart | FilePart | DataPart]):
    """Union type for all possible message parts."""
    
    root: TextPart | FilePart | DataPart


class Artifact(PebblingProtocolBaseModel):
    """Represents an artifact generated for a task."""
    
    artifact_id: UUID = Field(..., description="Unique identifier for the artifact")
    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    parts: list[Part]


class Message(PebblingProtocolBaseModel):
    """Message exchanged between agents or users."""
    
    contextId: UUID
    kind: Literal['message'] = 'message'
    messageId: UUID
    metadata: dict[str, Any] | None = None
    parts: list[Part]
    role: Role
    extra_data: dict[str, Any] | None = None


class TaskStatus(PebblingProtocolBaseModel):
    """Status information for a task."""
    
    message: Message | None = None
    state: TaskState
    timestamp: str | None = Field(
        default=None, examples=['2023-10-27T10:00:00Z']
    )


class Task(PebblingProtocolBaseModel):
    """Top-level task representation."""
    
    artifacts: list[Artifact] | None = None
    contextId: UUID
    history: list[Message] | None = None
    id: str
    kind: Literal['task'] = 'task'
    metadata: dict[str, Any] | None = None
    status: TaskStatus


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
    """Structured negotiation proposal exchanged between agents."""
    
    proposal_id: UUID = Field(..., description="Unique ID of this specific proposal")
    from_agent: UUID = Field(..., description="Agent ID initiating the proposal")
    to_agent: UUID = Field(..., description="Agent ID receiving the proposal")
    terms: Dict[str, Any] = Field(..., description="Negotiation terms (structured)")
    timestamp: int = Field(..., description="UNIX timestamp when the proposal was made")
    status: NegotiationStatus = Field(
        NegotiationStatus.proposed, 
        description="Status of this specific proposal"
    )


class NegotiationSession(PebblingProtocolBaseModel):
    """Session details for agent-to-agent negotiations."""
    
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

class PaymentAction(PebblingProtocolBaseModel):
    """Represents the possible payment actions."""
    
    action_type: Literal['submit', 'cancel', 'unknown'] = 'submit'
    amount: float = Field(..., description="The amount of the payment", examples=[10.0])
    currency: str = Field(..., description="ISO currency code clearly identified (e.g., USD)")
    billing_period: Literal["daily", "weekly", "monthly", "yearly", "one-time"] = Field(
        "one-time", 
        description="Billing frequency clearly defined if subscription-based"
    )


#-----------------------------------------------------------------------------
# JSON-RPC Error Types
#-----------------------------------------------------------------------------

class JSONRPCError(PebblingProtocolBaseModel):
    """Base JSON-RPC error representation."""
    
    code: int
    data: Any | None = None
    message: str


class JSONParseError(JSONRPCError):
    """JSON-RPC parse error."""
    
    code: Literal[-32700] = -32700
    message: Literal['Invalid JSON'] = 'Invalid JSON'


class InvalidRequestError(JSONRPCError):
    """JSON-RPC invalid request error."""
    
    code: Literal[-32600] = -32600
    message: Literal['Validation error'] = 'Validation error'


class MethodNotFoundError(JSONRPCError):
    """JSON-RPC method not found error."""
    
    code: Literal[-32601] = -32601
    message: Literal['Method not found'] = 'Method not found'


class InvalidParamsError(JSONRPCError):
    """JSON-RPC invalid parameters error."""
    
    code: Literal[-32602] = -32602
    message: Literal['Invalid parameters'] = 'Invalid parameters'


class InternalError(JSONRPCError):
    """JSON-RPC internal error."""
    
    code: Literal[-32603] = -32603
    message: Literal['Internal error'] = 'Internal error'


class InvalidAgentResponseError(JSONRPCError):
    """Error for invalid agent responses."""
    
    code: Literal[-32006] = -32006
    message: Literal['Invalid agent response'] = 'Invalid agent response'


class TaskNotFoundError(JSONRPCError):
    """Error for task not found."""
    
    code: Literal[-32007] = -32007
    message: Literal['Task not found'] = 'Task not found'


class TaskNotCancelableError(JSONRPCError):
    """Error for task not cancelable."""
    
    code: Literal[-32008] = -32008
    message: Literal['Task not cancelable'] = 'Task not cancelable'


class PushNotificationNotSupportedError(JSONRPCError):
    """Error for push notification not supported."""
    
    code: Literal[-32009] = -32009
    message: Literal['Push notification not supported'] = 'Push notification not supported'


class UnsupportedOperationError(JSONRPCError):
    """Error for unsupported operations."""
    
    code: Literal[-32010] = -32010
    message: Literal['Unsupported operation'] = 'Unsupported operation'


class ContentTypeNotSupportedError(JSONRPCError):
    """Error for unsupported content types."""
    
    code: Literal[-32011] = -32011
    message: Literal['Content type not supported'] = 'Content type not supported'


#-----------------------------------------------------------------------------
# JSON-RPC Request & Response Types
#-----------------------------------------------------------------------------

class JSONRPCErrorResponse(PebblingProtocolBaseModel):
    """JSON-RPC error response."""
    
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
    """Event for task status updates."""
    
    contextId: UUID
    final: bool
    kind: Literal['status-update'] = 'status-update'
    metadata: dict[str, Any] | None = None
    status: TaskStatus
    taskId: UUID


class TaskArtifactUpdateEvent(PebblingProtocolBaseModel):
    """Event for task artifact updates."""
    
    append: bool | None = None
    artifact: Artifact
    contextId: UUID
    kind: Literal['artifact-update'] = 'artifact-update'
    lastChunk: bool | None = None
    metadata: dict[str, Any] | None = None
    taskId: UUID


class TaskIdParams(PebblingProtocolBaseModel):
    """Parameters for task identification."""
    
    id: UUID
    metadata: dict[str, Any] | None = None


class MessageSendConfiguration(PebblingProtocolBaseModel):
    """Configuration for message sending."""
    
    acceptedOutputModes: list[str]
    blocking: bool | None = None
    historyLength: int | None = None


class MessageSendParams(PebblingProtocolBaseModel):
    """Parameters for sending messages."""
    
    configuration: MessageSendConfiguration | None = None
    message: Message
    metadata: dict[str, Any] | None = None


# Response types
class SendMessageSuccessResponse(PebblingProtocolBaseModel):
    """Success response for sending a message."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task | Message


class SendStreamingMessageSuccessResponse(PebblingProtocolBaseModel):
    """Success response for sending a streaming message."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task | Message | TaskStatusUpdateEvent | TaskArtifactUpdateEvent


class GetTaskSuccessResponse(PebblingProtocolBaseModel):
    """Success response for getting a task."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task


class CancelTaskSuccessResponse(PebblingProtocolBaseModel):
    """Success response for canceling a task."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task

class TrustVerificationResponse(PebblingProtocolBaseModel):
    """Success response for trust verification."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    result: Task


# Request types
class SendMessageRequest(PebblingProtocolBaseModel):
    """Request to send a message."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    method: Literal['message/send'] = 'message/send'
    params: MessageSendParams


class SendStreamingMessageRequest(SendMessageRequest):
    """Request to send a streaming message."""
    
    method: Literal['message/stream'] = 'message/stream'


class GetTaskRequest(PebblingProtocolBaseModel):
    """Request to get a task."""
    
    id: UUID
    jsonrpc: Literal['2.0'] = '2.0'
    method: Literal['tasks/get'] = 'tasks/get'
    params: TaskIdParams


class CancelTaskRequest(GetTaskRequest):
    """Request to cancel a task."""
    
    method: Literal['tasks/cancel'] = 'tasks/cancel'


class TaskResubscriptionRequest(GetTaskRequest):
    """Request to resubscribe to task events."""
    
    method: Literal['tasks/resubscribe'] = 'tasks/resubscribe'

class TrustVerificationRequest(GetTaskRequest):
    """Request to verify trust."""
    
    method: Literal['trust/verify'] = 'trust/verify'


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
    """Union type for all JSON-RPC responses."""
    
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
    """Union type for send message responses."""
    
    root: JSONRPCErrorResponse | SendMessageSuccessResponse


class SendStreamingMessageResponse(
    RootModel[JSONRPCErrorResponse | SendStreamingMessageSuccessResponse]
):
    """Union type for streaming message responses."""
    
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
    """Union type for all Pebbling requests."""
    
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
# Lets handle Security
#-----------------------------------------------------------------------------

class AgentSecurity(PebblingProtocolBaseModel):
    """Security configuration for agents in the Pebbling framework."""
    
    # DID-based security settings
    challenge_expiration_seconds: int = Field(
        300, 
        description="Seconds until a challenge expires for DID-based verification"
    )
    require_challenge_response: bool = Field(
        True, 
        description="Whether to require challenge-response verification for agent communication"
    )
    signature_algorithm: str = Field(
        "Ed25519", 
        description="Algorithm used for digital signatures"
    )
    key_storage_path: Optional[str] = Field(
        None, 
        description="Path where security keys are stored"
    )
    
    # Server security settings
    endpoint_type: str = Field(
        "json-rpc", 
        description="Type of endpoint (json-rpc, mlts, or http)"
    )
    verify_requests: bool = Field(
        True, 
        description="Whether to verify incoming requests"
    )
    
    # Certificate settings
    certificate_type: Optional[str] = Field(
        None, 
        description="Type of certificate (self-signed, letsencrypt, sheldon)"
    )
    certificate_path: Optional[str] = Field(
        None, 
        description="Path to certificate file"
    )
    
    # Policies
    max_retries: int = Field(
        3, 
        description="Maximum number of retries for failed security operations"
    )
    allow_anonymous: bool = Field(
        False, 
        description="Whether to allow anonymous access"
    )

#-----------------------------------------------------------------------------
# Lets handle Trust
#-----------------------------------------------------------------------------

class TrustLevel(str, Enum):
    """Trust levels for operations and permissions."""
    
    ADMIN = "admin"           # Admin operations, minimal risk
    ANALYST = "analyst"     # Standard operations
    AUDITOR = "auditor"         # Sensitive operations
    EDITOR = "editor"         # Edit operations, moderate risk
    GUEST = "guest"           # Limited access, read-only operations
    MANAGER = "manager"       # Management operations, elevated permissions
    OPERATOR = "operator"     # System operations, moderate risk
    SUPER_ADMIN = "super_admin" # Highest level access, all operations permitted
    SUPPORT = "support"       # Support operations, troubleshooting access
    VIEWER = "viewer"         # View-only access, minimal permissions

class IdentityProvider(str, Enum):
    """Supported identity providers."""
    
    KEYCLOAK = "keycloak"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    AUTH0 = "auth0"
    CUSTOM = "custom"

class KeycloakRole(PebblingProtocolBaseModel):
    """Keycloak role model."""
    role_id: UUID = Field(..., description="Role ID from Keycloak IAM.")
    role_name: str = Field(..., description="Human-readable role name.")
    permissions: List[str] = Field(default_factory=list, description="Specific permissions tied to this role.")
    trust_level: TrustLevel = Field(TrustLevel.GUEST, description="Default trust level for this role")
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
    """Trust configuration for an agent."""
    identity_provider: IdentityProvider = Field(..., description="Identity provider used for authentication")
    inherited_roles: List[KeycloakRole] = Field(
        default_factory=list, 
        description="Roles inherited from the agent's creator"
    )
    certificate: Optional[str] = Field(None, description="Agent's security certificate for verification")
    certificate_fingerprint: Optional[str] = Field(None, description="Fingerprint of the agent's certificate")
    creator_id: Union[UUID, int, str] = Field(..., description="ID of the user who created this agent")
    creation_timestamp: int = Field(..., description="UNIX timestamp of agent creation")
    trust_verification_required: bool = Field(True, description="Whether trust verification is required")
    allowed_operations: Dict[str, TrustLevel] = Field(
        default_factory=dict,
        description="Operations this agent is allowed to perform with required trust levels"
    )

#-----------------------------------------------------------------------------
# Agent 
#-----------------------------------------------------------------------------

class AgentIdentity(PebblingProtocolBaseModel):
    """Agent identity configuration with DID and other identifiers."""
    did: Optional[str] = Field(None, description="Agent DID string.")
    did_document: Optional[Dict[str, Any]] = Field(None, description="Agent DID document for decentralized identity.")
    agentdns_url: Optional[str] = Field(None, description="Agent DNS-based identity URL (agentdns.ai).")
    endpoint: Optional[str] = Field(None, description="Secure mTLS agent endpoint.")
    public_key: Optional[str] = Field(None, description="Agent's public key for mTLS.")

class AgentSkill(PebblingProtocolBaseModel):
    """Represents a distinct capability or function that an agent can perform."""
    description: str
    examples: list[str] | None = Field(
        default=None, examples=[['I need a recipe for bread']]
    )
    id: str
    input_modes: list[str] | None = None
    name: str
    output_modes: list[str] | None = None
    tags: list[str] = Field(
        ..., examples=[['cooking', 'customer support', 'billing']]
    )

class AgentExtension(PebblingProtocolBaseModel):
    """A declaration of a protocol extension supported by an Agent."""
    description: str | None = None
    params: dict[str, Any] | None = None
    required: bool | None = None
    uri: str

class AgentCapabilities(PebblingProtocolBaseModel):
    """Defines optional capabilities supported by an agent."""
    extensions: list[AgentExtension] | None = None
    push_notifications: bool | None = None
    state_transition_history: bool | None = None
    streaming: bool | None = None


class AgentManifest(PebblingProtocolBaseModel):
    """Complete agent manifest with identity and capabilities."""
    id: Union[UUID, int, str] = Field(
        ..., 
        description="The unique identifier of the agent", 
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    name: str = Field(
        ..., 
        description="The name of the agent", 
        examples=["Japanese Restaurant Reviewer Agent"]
    )
    description: str | None = Field(None, description="Description of the agent")
    user_id: Union[UUID, int, str] = Field(..., description="user")

    # Trust
    trust_config: Optional[AgentTrust] = Field(
        None, 
        description="Trust configuration and inherited permissions"
    )

    capabilities: Optional[AgentCapabilities] = Field(
        None, 
        description="Optional capabilities supported by the agent"
    )
    skills: Optional[list[AgentSkill]] = Field(
        None, 
        description="Optional skills supported by the agent"
    )

    instance: Optional[Any] = Field(
        None, 
        description="The agent/team/workflow instance"
    )
    
    # DID-related fields
    did: Optional[str] = Field(
        None,
        description="Decentralized Identifier of the agent"
    )
    did_document: Optional[Dict[str, Any]] = Field(
        None,
        description="Full DID document"
    )
    
    # Configuration
    num_history_sessions: Optional[int] = None
    storage: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
    
    # Debug settings
    debug_mode: bool = False
    debug_level: Literal[1, 2] = 1 # 1 = Basic, 2 = Detailed
    
    # Monitoring
    monitoring: bool = False
    telemetry: bool = True

    # Security
    security: Optional[AgentSecurity] = Field(
        None, 
        description="Security configuration for the agent"
    )

    # Trust
    trust: Optional[AgentTrust] = Field(
        None, 
        description="Trust configuration for the agent"
    )

    # Identity
    identity: Optional[AgentIdentity] = Field(
        None, 
        description="Identity configuration for the agent"
    )
    
    # Versioning
    version: str = Field(..., examples=['1.0.0'])