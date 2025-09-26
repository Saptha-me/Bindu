"""
a2a and ap2 Protocol Type Definitions.

This module contains all the protocol data models used for communication between
agents and the framework.
"""

from __future__ import annotations as _annotations

from typing import Annotated, Any, Literal, List, TypeVar, Union, Dict, Generic
from uuid import UUID

import pydantic
from pydantic import Discriminator, Field, TypeAdapter
from pydantic.alias_generators import to_camel
from typing_extensions import Required, NotRequired, TypeAlias, TypedDict


# -----------------------------------------------------------------------------
# Base Types and Enums
# -----------------------------------------------------------------------------

# TypeVars for generic types
ResultT = TypeVar("ResultT")
ErrorT = TypeVar("ErrorT")

Role: TypeAlias = Literal["agent", "user"]

TaskState: TypeAlias = Literal[
    "submitted",  # The task has been submitted and is awaiting execution.
    "working",  # The agent is actively working on the task.
    "input-required",  # The task is paused and waiting for input from the user.
    "completed",  # The task has been successfully completed.
    "canceled",  # The task has been canceled by the user.
    "failed",  # The task failed due to an error during execution.
    "rejected",  # The task was rejected by the agent and was not started.
    "auth-required",  # The task requires authentication to proceed.
    "unknown",  # The task is in an unknown or indeterminate state. <NotPartOfA2A>
    "trust-verification-required",  # The task requires trust verification to proceed. <NotPartOfA2A>
    "pending",  # The task is pending execution. <NotPartOfA2A>
    "suspended",  # The task is suspended and is not currently running. <NotPartOfA2A>
    "resumed",  # The task is resumed and is currently running. <NotPartOfA2A>
    "negotiation-bid-submitted",  # The task is submitted for negotiation. <NotPartOfA2A>
    "negotiation-bid-lost",  # The task bid was lost in negotiation. <NotPartOfA2A>
    "negotiation-bid-won",  # The task bid was won in negotiation. <NotPartOfA2A>
]

NegotiationStatus: TypeAlias = Literal[
    "proposed",  # The negotiation is proposed. <NotPartOfA2A>
    "accepted",  # The negotiation is accepted. <NotPartOfA2A>
    "rejected",  # The negotiation is rejected. <NotPartOfA2A>
    "countered",  # The negotiation is countered. <NotPartOfA2A>
]

NegotiationSessionStatus: TypeAlias = Literal[
    "initiated",  # The negotiation session is initiated. <NotPartOfA2A>
    "ongoing",  # The negotiation session is ongoing. <NotPartOfA2A>
    "completed",  # The negotiation session is completed. <NotPartOfA2A>
    "rejected",  # The negotiation session is rejected. <NotPartOfA2A>
]

TrustLevel: TypeAlias = Literal[
    "admin",  # Admin operations, minimal risk <NotPartOfA2A>
    "analyst",  # Standard operations <NotPartOfA2A>
    "auditor",  # Sensitive operations <NotPartOfA2A>
    "editor",  # Edit operations, moderate risk <NotPartOfA2A>
    "guest",  # Limited access, read-only operations <NotPartOfA2A>
    "manager",  # Management operations, elevated permissions <NotPartOfA2A>
    "operator",  # System operations, moderate risk <NotPartOfA2A>
    "super_admin",  # Highest level access, all operations permitted <NotPartOfA2A>
    "support",  # Support operations, troubleshooting access <NotPartOfA2A>
    "viewer",  # View-only access, minimal permissions <NotPartOfA2A>
]

IdentityProvider: TypeAlias = Literal[
    "keycloak",  # Keycloak identity provider <NotPartOfA2A>
    "azure_ad",  # Azure AD identity provider <NotPartOfA2A>
    "okta",  # Okta identity provider <NotPartOfA2A>
    "auth0",  # Auth0 identity provider <NotPartOfA2A>
    "custom",  # Custom identity provider <NotPartOfA2A>
]

CONTACT_ADDRESS_DATA_KEY = "contact_picker.ContactAddress"
PAYMENT_METHOD_DATA_DATA_KEY = "payment_request.PaymentMethodData"
CART_MANDATE_DATA_KEY = "ap2.mandates.CartMandate"
INTENT_MANDATE_DATA_KEY = "ap2.mandates.IntentMandate"
PAYMENT_MANDATE_DATA_KEY = "ap2.mandates.PaymentMandate"

# -----------------------------------------------------------------------------
# Content & Message Parts
# -----------------------------------------------------------------------------

@pydantic.with_config({"alias_generator": to_camel})
class TextPart(TypedDict):
    """Represents a text segment within parts."""

    kind: Required[Literal["text"]]
    """The kind of the part."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata about the text part."""

    text: Required[str]
    """The text of the part."""

    embeddings: NotRequired[list[float]]
    """The embeddings of Text. <NotPartOfA2A>"""

@pydantic.with_config({"alias_generator": to_camel})
class FileWithBytes(TypedDict):
    """File representation with binary content."""

    bytes: Required[str]
    """The bytes of the file."""

    mimeType: NotRequired[str]
    """The MIME type of the file."""

    name: NotRequired[str]
    """The name of the file."""

    embeddings: NotRequired[list[float]]
    """The embeddings of File. <NotPartOfA2A>"""


@pydantic.with_config({"alias_generator": to_camel})
class FileWithUri(FileWithBytes):
    """File representation with URI reference."""

    uri: Required[str]
    """The URI of the file."""


@pydantic.with_config({"alias_generator": to_camel})
class FilePart(TextPart):
    """Represents a file segment within a message or artifact.
    
    The file content can be provided either directly as bytes or as a URI.
    """

    kind: Required[Literal["file"]]
    """The kind of the part."""

    file: Required[FileWithBytes | FileWithUri]
    """The file of the part."""

    embeddings: NotRequired[list[float]]
    """The embeddings of File. <NotPartOfA2A>"""


class DataPart(TextPart):
    """Represents a structured data segment (e.g., JSON) within a message or artifact."""

    kind: Required[Literal["data"]]
    """The kind of the part."""

    data: Required[dict[str, Any]]
    """The data of the part."""

    embeddings: NotRequired[list[float]]
    """The embeddings of Data. <NotPartOfA2A>"""


Part = Annotated[Union[TextPart, FilePart, DataPart], Field(discriminator="kind")]

# -----------------------------------------------------------------------------
# Artifacts
# -----------------------------------------------------------------------------

@pydantic.with_config({"alias_generator": to_camel})
class Artifact(TypedDict):
    """Represents the final output generated by an agent after completing a task.

    Artifacts are immutable data structures that contain the results of agent execution.
    They can contain multiple parts (text, files, structured data) and are uniquely
    identified for tracking and retrieval.

    A single task may produce multiple artifacts when the output naturally
    separates into distinct deliverables (e.g., frontend + backend code).
    """

    artifact_id: Required[UUID]
    """Unique identifier for the artifact."""

    name: NotRequired[str]
    """Human Readable name of the artifact."""

    description: NotRequired[str]
    """A description of the artifact."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata about the artifact."""

    parts: NotRequired[list[Part]]
    """The parts that make up the artifact."""

    append: NotRequired[bool]
    """Whether to append this artifact to an existing one."""

    last_chunk: NotRequired[bool]
    """Whether this is the last chunk of the artifact."""

    extensions: NotRequired[list[str]]
    """Array of extensions."""



@pydantic.with_config({"alias_generator": to_camel})
class Message(TypedDict):
    """Communication content exchanged between agents, users, and systems.

    Messages represent all non-result communication in the Pebbling protocol.
    Unlike Artifacts (which contain task outputs), Messages carry operational
    content like instructions, status updates, context, and metadata.

    Message Types:
    - User Instructions: Task requests with context and files
    - Agent Communication: Status updates, thoughts, coordination
    - System Messages: Errors, warnings, protocol information
    - Context Sharing: Background information, references, metadata

    Multi-part Structure:
    Messages can contain multiple parts to organize different content types:
    - Text parts for instructions or descriptions
    - File parts for context documents or references
    - Data parts for structured metadata or parameters

    Flow Pattern:
    Client → Message (request) → Agent → Message (status) → Artifact (result)
    """

    message_id: Required[UUID]
    """Identifier created by the message creator."""
    
    context_id: Required[UUID]
    """The context the message is associated with."""
    
    task_id: Required[UUID]
    """Identifier of task the message is related to."""
    
    reference_task_ids: NotRequired[list[UUID]]
    """List of identifiers of tasks that this message is related to."""
    
    kind: Required[Literal["message"]]
    """The type of the message."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata associated with the message."""

    parts: Required[list[Part]]
    """The parts of the message."""

    role: Required[Literal['user', 'agent', 'system']]
    """The role of the message."""

    extensions: NotRequired[list[str]]
    """Array of extensions."""


# -----------------------------------------------------------------------------
# Security Schemes
# -----------------------------------------------------------------------------


@pydantic.with_config({"alias_generator": to_camel})
class HTTPAuthSecurityScheme(TypedDict):
    """HTTP security scheme."""

    type: Required[Literal["http"]]
    """The type of the security scheme."""
    
    scheme: Required[str]
    """The scheme of the security scheme."""
    
    bearer_format: NotRequired[str]
    """The bearer format of the security scheme."""
    
    description: NotRequired[str]
    """The description of the security scheme."""


@pydantic.with_config({"alias_generator": to_camel})
class APIKeySecurityScheme(TypedDict):
    """API Key security scheme."""

    type: Required[Literal["apiKey"]]
    """The type of the security scheme."""
    
    name: Required[str]
    """The name of the security scheme."""
    
    in_: Required[Literal["query", "header", "cookie"]]
    """The location of the security scheme."""
    
    description: NotRequired[str]
    """The description of the security scheme."""


@pydantic.with_config({"alias_generator": to_camel})
class OAuth2SecurityScheme(TypedDict):
    """OAuth2 security scheme."""

    type: Required[Literal["oauth2"]]
    """The type of the security scheme."""
    
    flows: Required[dict[str, Any]]
    """The flows of the security scheme."""
    
    description: NotRequired[str]
    """The description of the security scheme."""


@pydantic.with_config({"alias_generator": to_camel})
class OpenIdConnectSecurityScheme(TypedDict):
    """OpenID Connect security scheme."""

    type: Required[Literal["openIdConnect"]]
    """The type of the security scheme."""
    
    open_id_connect_url: Required[str]
    """The OpenID Connect URL of the security scheme."""
    
    description: NotRequired[str]
    """The description of the security scheme."""


@pydantic.with_config({"alias_generator": to_camel})
class MutualTLSSecurityScheme(TypedDict):
    """Mutual TLS security scheme."""

    type: Required[Literal["mutualTLS"]]
    """The type of the security scheme."""
    
    description: NotRequired[str]
    """The description of the security scheme."""


SecurityScheme = Annotated[
    Union[
        HTTPAuthSecurityScheme,
        APIKeySecurityScheme,
        OAuth2SecurityScheme,
        OpenIdConnectSecurityScheme,
        MutualTLSSecurityScheme,
    ],
    Discriminator("type"),
]


# -----------------------------------------------------------------------------
# Push Notification Configuration
# -----------------------------------------------------------------------------


@pydantic.with_config({"alias_generator": to_camel})
class PushNotificationConfig(TypedDict):
    """Configuration for push notifications.

    When the server needs to notify the client of an update outside of a connected session.
    """

    id: Required[UUID]
    """The ID of the push notification configuration."""
    
    url: Required[str]
    """The URL of the push notification configuration."""
    
    token: NotRequired[str]
    """The token of the push notification configuration."""
    
    authentication: NotRequired[SecurityScheme]
    """The authentication of the push notification configuration."""


@pydantic.with_config({"alias_generator": to_camel})
class PushNotificationAuthenticationInfo(TypedDict):
    """Authentication information for push notifications."""

    schemes: list[str]
    """A list of supported authentication schemes (e.g., 'Basic', 'Bearer')."""
    
    credentials: NotRequired[str]
    """Optional credentials required by the push notification endpoint."""


@pydantic.with_config({"alias_generator": to_camel})
class TaskPushNotificationConfig(TypedDict):
    """Configuration for task push notifications."""

    id: Required[UUID]
    """The ID of the task push notification configuration."""
    
    push_notification_config: Required[PushNotificationConfig]
    """The push notification configuration of the task push notification configuration."""


# -----------------------------------------------------------------------------
# Task
# -----------------------------------------------------------------------------

@pydantic.with_config({"alias_generator": to_camel})
class TaskStatus(TypedDict):
    """Status information for a task."""

    message: NotRequired[Message]
    state: Required[TaskState]
    timestamp: Required[str] = Field(
        examples=["2025-10-10T10:00:00Z"], description="ISO datetime value of when the status was updated."
    )


@pydantic.with_config({"alias_generator": to_camel})
class Task(TypedDict):
    """Stateful execution unit that coordinates client-agent interaction to achieve a goal.

    Tasks serve as the primary coordination mechanism in the Pebbling protocol,
    managing the complete lifecycle from request to completion. They maintain
    conversation history, track execution state, and collect generated artifacts.

    Core Responsibilities:
    - Message Exchange: Facilitate communication between clients and agents
    - State Management: Track task progress and execution status
    - Artifact Collection: Gather and organize agent-generated outputs
    - History Tracking: Maintain complete conversation and decision trail

    Task Lifecycle:
    1. Creation: Client initiates task with initial message/requirements
    2. Processing: Agent processes messages and updates status
    3. Communication: Bidirectional message exchange as needed
    4. Artifact Generation: Agent produces deliverable outputs
    5. Completion: Final status update and artifact delivery

    Key Properties:
    - Client-Initiated: Always created by clients, never by agents
    - Agent-Controlled: Status and progress determined by executing agent
    - Stateful: Maintains complete execution context and history
    - Traceable: Unique ID enables task tracking and reference

    Task Relationships:
    - Contains: Multiple messages (conversation history)
    - Produces: Multiple artifacts (execution results)
    - References: Other tasks via reference_task_ids for coordination
    - Belongs to: Specific context for session management
    """

    id: Required[UUID]
    """The ID of the task."""
    
    context_id: Required[UUID]
    """The ID of the context the task is associated with."""
    
    kind: Required[Literal["task"]]
    """The type of the task."""
    
    status: Required[TaskStatus]
    """The status of the task."""

    artifacts: NotRequired[list[Artifact]]
    """The artifacts of the task."""
    
    history: NotRequired[list[Message]]
    """The history of the task."""
    
    metadata: NotRequired[dict[str, Any]]
    """The metadata of the task."""


@pydantic.with_config({"alias_generator": to_camel})
class TaskStatusUpdateEvent(TypedDict):
    """Event sent by the agent to notify the client of a change in a task's status.

    This is typically used in streaming or subscription models.
    """

    task_id: Required[UUID]
    """The ID of the task."""
    
    context_id: Required[UUID]
    """The ID of the context the task is associated with."""
    
    final: Required[bool]
    """Indicates if this is the final status update."""
    
    kind: Required[Literal["status-update"]]
    """The type of the event."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""
    
    status: Required[TaskStatus]
    """The status of the task."""
    


@pydantic.with_config({"alias_generator": to_camel})
class TaskArtifactUpdateEvent(TypedDict):
    """Event sent by the agent to notify the client that an artifact has been generated or updated.
    
    This is typically used in streaming models.
    """

    task_id: Required[UUID]
    """The ID of the task."""
    
    append: NotRequired[bool]
    """Indicates if this is an append operation."""
    
    artifact: Required[Artifact]
    """The artifact that has been generated or updated."""
    
    context_id: Required[UUID]
    """The ID of the context the task is associated with."""
    
    kind: Required[Literal["artifact-update"]]
    """The type of the event."""
    
    last_chunk: NotRequired[bool]
    """Indicates if this is the last chunk of the artifact."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""
    

@pydantic.with_config({"alias_generator": to_camel})
class TaskSendParams(TypedDict):
    """Internal parameters for task execution within the framework. <NotPartOfA2A>."""

    task_id: Required[UUID]
    """The ID of the task."""
    
    context_id: Required[UUID]
    """The ID of the context the task is associated with."""
    
    message: NotRequired[Message]
    """The message to send."""
    
    history_length: NotRequired[int]
    """The length of the history."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class TaskIdParams(TypedDict):
    """Defines parameters containing a task ID, used for simple task operations."""

    task_id: Required[UUID]
    """The ID of the task."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class TaskQueryParams(TaskIdParams):
    """Defines parameters for querying a task, with an option to limit history length."""

    history_length: NotRequired[int]
    """The length of the history."""


@pydantic.with_config({"alias_generator": to_camel})
class ListTasksParams(TypedDict):
    """Defines parameters for listing tasks. <NotPartOfA2A>."""

    history_length: NotRequired[int]
    """The length of the history."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class TaskFeedbackParams(TypedDict):
    """Defines parameters for providing feedback on a task. <NotPartOfA2A>."""

    task_id: Required[UUID]
    """The ID of the task."""
    
    feedback: Required[str]
    """The feedback to provide."""
    
    rating: NotRequired[int]  # Optional rating 1(lowest)-5(highest)
    """The rating to provide."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class MessageSendConfiguration(TypedDict):
    """Configuration for message sending."""

    accepted_output_modes: Required[list[str]]
    """The accepted output modes."""
    
    blocking: NotRequired[bool]
    """The blocking mode."""
    
    history_length: NotRequired[int]
    """The history length."""
    
    push_notification_config: NotRequired[PushNotificationConfig]
    """The push notification configuration."""


@pydantic.with_config({"alias_generator": to_camel})
class MessageSendParams(TypedDict):
    """Parameters for sending messages."""

    configuration: Required[MessageSendConfiguration]
    """The configuration for message sending."""
    
    message: Required[Message]
    """The message to send."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class ListTaskPushNotificationConfigParams(TypedDict):
    """Parameters for getting list of pushNotificationConfigurations associated with a Task."""

    id: Required[UUID]
    """The ID of the task."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class DeleteTaskPushNotificationConfigParams(TypedDict):
    """Parameters for removing pushNotificationConfiguration associated with a Task."""

    id: Required[UUID]
    """The ID of the task."""
    
    push_notification_config_id: Required[UUID]
    """The ID of the push notification configuration."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


# -----------------------------------------------------------------------------
# Context <NotPartOfA2A>
# -----------------------------------------------------------------------------


@pydantic.with_config({"alias_generator": to_camel})
class Context(TypedDict):
    """Conversation session that groups related tasks and maintains interaction history.

    Contexts serve as conversation containers in the Pebbling protocol, managing
    the complete interaction lifecycle between clients and agents. They maintain
    conversation continuity, preserve context across multiple tasks, and provide
    session-level organization.

    Core Responsibilities:
    - Session Management: Group related tasks under a unified conversation
    - History Preservation: Maintain complete message history across tasks
    - Context Continuity: Preserve conversation state and references
    - Metadata Tracking: Store session-level information and preferences

    Context Lifecycle:
    1. Creation: Client initiates conversation or system creates implicit context
    2. Task Association: Multiple tasks can belong to the same context
    3. History Building: Messages and artifacts accumulate over time
    4. State Management: Track conversation status and metadata
    5. Completion: Context can be closed or archived when conversation ends

    Key Properties:
    - Multi-Task: Contains multiple related tasks over time
    - Stateful: Maintains conversation history and context
    - Client-Controlled: Clients can explicitly manage context lifecycle
    - Traceable: Unique ID enables context tracking and reference

    Context Relationships:
    - Contains: Multiple tasks (one-to-many relationship)
    - Maintains: Complete conversation history across all tasks
    - Preserves: Session-level metadata and preferences
    - References: Can link to other contexts for complex workflows
    """

    context_id: Required[UUID]
    """The ID of the context."""
    
    kind: Required[Literal["context"]]
    """The type of the context."""

    tasks: NotRequired[list[UUID]]
    """List of task IDs belonging to this context."""

    name: NotRequired[str]
    """Human-readable context name."""
    
    description: NotRequired[str]
    """Context purpose or summary."""
    
    role: Required[str]
    """Role of the context."""
    
    created_at: Required[str] = Field(
        examples=["2023-10-27T10:00:00Z"], description="ISO datetime when context was created"
    )
    updated_at: Required[str] = Field(
        examples=["2023-10-27T10:00:00Z"], description="ISO datetime when context was last updated"
    )

    status: NotRequired[Literal["active", "paused", "completed", "archived"]]
    """Context status."""
    
    tags: NotRequired[list[str]]
    """Organizational tags."""
    
    metadata: NotRequired[dict[str, Any]]
    """Custom context metadata."""

    parent_context_id: NotRequired[UUID]
    """For nested or related contexts."""
    
    reference_context_ids: NotRequired[list[UUID]]
    """Related contexts."""
    
    extensions: NotRequired[dict[str, Any]]
    """Additional extensions."""


# -----------------------------------------------------------------------------
# Context Operations <NotPartOfA2A>
# -----------------------------------------------------------------------------


@pydantic.with_config({"alias_generator": to_camel})
class ContextIdParams(TypedDict):
    """Parameters for context identification."""

    context_id: Required[UUID]
    """The ID of the context."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


@pydantic.with_config({"alias_generator": to_camel})
class ContextQueryParams(ContextIdParams):
    """Query parameters for a context."""

    history_length: NotRequired[int]
    """The length of the history."""


@pydantic.with_config({"alias_generator": to_camel})
class ListContextsParams(TypedDict):
    """Parameters for listing contexts."""

    history_length: NotRequired[int]
    """The length of the list."""
    
    metadata: NotRequired[dict[str, Any]]
    """Additional metadata."""


# -----------------------------------------------------------------------------
# Agent-to-Agent Negotiation Models <NotPartOfA2A>
# -----------------------------------------------------------------------------


@pydantic.with_config({"alias_generator": to_camel})
class NegotiationProposal(TypedDict):
    """Structured negotiation proposal exchanged between agents."""

    proposal_id: Required[UUID]
    """The ID of the proposal."""
    
    from_agent: Required[UUID]
    """The ID of the agent making the proposal."""
    
    to_agent: Required[UUID]
    """The ID of the agent receiving the proposal."""
    
    terms: Required[Dict[str, Any]]
    """The terms of the proposal."""
    
    timestamp: Required[str]
    """The timestamp of the proposal."""
    
    status: Required[NegotiationStatus]
    """The status of the proposal."""


@pydantic.with_config({"alias_generator": to_camel})
class NegotiationContext(TypedDict):
    """Context details for agent-to-agent negotiations."""

    context_id: Required[UUID]
    """The ID of the context."""
    
    status: Required[NegotiationStatus]
    """The status of the context."""
    
    participants: Required[List[str]]
    """The participants in the context."""
    
    proposals: Required[List[NegotiationProposal]]
    """The proposals in the context."""


# -----------------------------------------------------------------------------
# Payment Models - Mainly Agent Payments Protocol AP2
# -----------------------------------------------------------------------------

@pydantic.with_config({"alias_generator": to_camel})
class ContactAddress(TypedDict):
    """The ContactAddress interface represents a physical address."""

    city: NotRequired[str]
    """The city."""
    
    country: NotRequired[str]
    """The country."""
    
    dependent_locality: NotRequired[str]
    """The dependent locality."""
    
    organization: NotRequired[str]
    """The organization."""
    
    phone_number: NotRequired[str]
    """The phone number."""
    
    postal_code: NotRequired[str]
    """The postal code."""
    
    recipient: NotRequired[str]
    """The recipient."""
    
    region: NotRequired[str]
    """The region."""
    
    sorting_code: NotRequired[str]
    """The sorting code."""
    
    address_line: NotRequired[list[str]]
    """The address line."""

@pydantic.with_config({"alias_generator": to_camel})
class PaymentCurrencyAmount(TypedDict):
    """A PaymentCurrencyAmount is used to supply monetary amounts."""

    currency: Required[str]
    """The three-letter ISO 4217 currency code."""
    
    value: Required[float]
    """The monetary value."""


@pydantic.with_config({"alias_generator": to_camel})
class PaymentItem(TypedDict):
    """An item for purchase and the value asked for it."""
    
    label: Required[str]
    """A human-readable description of the item."""
    
    amount: Required[PaymentCurrencyAmount]
    """The monetary amount of the item."""
    
    pending: NotRequired[bool]
    """If true, indicates the amount is not final."""
    
    refund_period: NotRequired[int]
    """The refund duration for this item, in days."""


@pydantic.with_config({"alias_generator": to_camel})
class PaymentShippingOption(TypedDict):
    """Describes a shipping option."""
    
    id: Required[str]
    """A unique identifier for the shipping option."""
    
    label: Required[str]
    """A human-readable description of the shipping option."""
    
    amount: Required[PaymentCurrencyAmount]
    """The cost of this shipping option."""
    
    selected: NotRequired[bool]
    """If true, indicates this as the default option."""


@pydantic.with_config({"alias_generator": to_camel})
class PaymentOptions(TypedDict):
    """Information about the eligible payment options for the payment request."""
    
    request_payer_name: NotRequired[bool]
    """Indicates if the payer's name should be collected."""
    
    request_payer_email: NotRequired[bool]
    """Indicates if the payer's email should be collected."""
    
    request_payer_phone: NotRequired[bool]
    """Indicates if the payer's phone number should be collected."""
    
    request_shipping: NotRequired[bool]
    """Indicates if the payer's shipping address should be collected."""
    
    shipping_type: NotRequired[str]
    """Can be `shipping`, `delivery`, or `pickup`."""
    

@pydantic.with_config({"alias_generator": to_camel})
class PaymentMethodData(TypedDict):
    """Indicates a payment method and associated data specific to the method."""
    
    supported_methods: Required[str]
    """A string identifying the payment method."""
    
    data: NotRequired[Dict[str, Any]]
    """Payment method specific details."""


@pydantic.with_config({"alias_generator": to_camel})
class PaymentDetailsModifier(TypedDict):
    """Provides details that modify the payment details based on a payment method."""
    
    supported_methods: Required[str]
    """The payment method ID that this modifier applies to."""
    
    total: NotRequired[PaymentItem]
    """A PaymentItem value that overrides the original item total."""
    
    additional_display_items: NotRequired[list[PaymentItem]]
    """Additional PaymentItems applicable for this payment method."""
    
    data: NotRequired[Any]
    """Payment method specific data for the modifier."""
    

@pydantic.with_config({"alias_generator": to_camel})
class PaymentDetailsInit(TypedDict):
    """Contains the details of the payment being requested."""
    
    id: Required[str]
    """A unique identifier for the payment request."""
    
    display_items: Required[list[PaymentItem]]
    """A list of payment items to be displayed to the user."""
    
    shipping_options: NotRequired[list[PaymentShippingOption]]
    """A list of available shipping options."""
    
    modifiers: NotRequired[list[PaymentDetailsModifier]]
    """A list of price modifiers for particular payment methods."""
    
    total: Required[PaymentItem]
    """The total payment amount."""
    
    description: NotRequired[str]
    """A description of the payment request."""
    
    
@pydantic.with_config({"alias_generator": to_camel})
class PaymentRequest(TypedDict):
    """A request for payment."""

    method_data: list[PaymentMethodData]
    """A list of supported payment methods."""
    
    details: PaymentDetailsInit
    """The financial details of the transaction."""
    
    options: NotRequired[PaymentOptions]
    """Information about the eligible payment options for the payment request."""
    
    shipping_address: NotRequired[ContactAddress]
    """The user's provided shipping address."""


@pydantic.with_config({"alias_generator": to_camel})
class PaymentResponse(TypedDict):
    """Indicates a user has chosen a payment method & approved a payment request."""
    
    request_id: Required[str]
    """The unique ID from the original PaymentRequest."""
    
    method_name: Required[str]
    """The payment method chosen by the user."""
    
    details: NotRequired[Dict[str, Any]]
    """A dictionary generated by a payment method that a merchant can use to process a transaction. The contents will depend upon the payment method."""
    
    shipping_address: NotRequired[ContactAddress]
    """The user's provided shipping address."""
    
    shipping_option: NotRequired[PaymentShippingOption]
    """The selected shipping option."""
    
    payer_name: NotRequired[str]
    """The name of the payer."""
    
    payer_email: NotRequired[str]
    """The email of the payer."""
    
    payer_phone: NotRequired[str]
    """The phone number of the payer."""


@pydantic.with_config({"alias_generator": to_camel})
class IntentMandate(TypedDict):
    """Represents the user's purchase intent.

    These are the initial fields utilized in the human-present flow. For
    human-not-present flows, additional fields will be added to this mandate.
    """

    user_cart_confirmation_required: Required[bool]
    """
    If false, the agent can make purchases on the user's behalf once all
    purchase conditions have been satisfied. This must be true if the
    intent mandate is not signed by the user.
    """
    
    natural_language_description: Required[str]
    """
    The natural language description of the user's intent. This is
    generated by the shopping agent, and confirmed by the user. The
    goal is to have informed consent by the user."""
    
    merchants: NotRequired[list[str]]
    """
    Merchants allowed to fulfill the intent. If not set, the shopping
    agent is able to work with any suitable merchant."""

    skus: NotRequired[list[str]]
    """
    A list of specific product SKUs. If not set, any SKU is allowed."""
    
    requires_refundability: NotRequired[bool]
    """
    If true, items must be refundable."""
    
    intent_expiry: Required[str]
    """
    When the intent mandate expires, in ISO 8601 format."""


@pydantic.with_config({"alias_generator": to_camel})
class CartContents(TypedDict):
    """The detailed contents of a cart.

    This object is signed by the merchant to create a CartMandate.
    """

    id: Required[str]
    """A unique identifier for this cart."""
    
    user_cart_confirmation_required: Required[bool]
    """
    If true, the merchant requires the user to confirm the cart before
    the purchase can be completed."""
    
    payment_request: Required[PaymentRequest]
    """
    The W3C PaymentRequest object to initiate payment. This contains the
    items being purchased, prices, and the set of payment methods
    accepted by the merchant for this cart."""
    
    cart_expiry: Required[str]
    """
    When this cart expires, in ISO 8601 format."""
    
    merchant_name: Required[str]
    """
    The name of the merchant."""


@pydantic.with_config({"alias_generator": to_camel})
class CartMandate(TypedDict):
    """A cart whose contents have been digitally signed by the merchant.

    This serves as a guarantee of the items and price for a limited time.
    """

    contents: Required[CartContents]
    """The contents of the cart."""
    
    merchant_authorization: NotRequired[str]
    """ A base64url-encoded JSON Web Token (JWT) that digitally
        signs the cart contents, guaranteeing its authenticity and integrity:
        1. Header includes the signing algorithm and key ID.
        2. Payload includes:
          - iss, sub, aud: Identifiers for the merchant (issuer)
            and the intended recipient (audience), like a payment processor.
          - iat: iat, exp: Timestamps for the token's creation and its
            short-lived expiration (e.g., 5-15 minutes) to enhance security.
          - jti: Unique identifier for the JWT to prevent replay attacks.
          - cart_hash: A secure hash of the CartMandate, ensuring
             integrity. The hash is computed over the canonical JSON
             representation of the CartContents object.
        3. Signature: A digital signature created with the merchant's private
          key. It allows anyone with the public key to verify the token's
          authenticity and confirm that the payload has not been tampered with.
        The entire JWT is base64url encoded to ensure safe transmission.
        """

@pydantic.with_config({"alias_generator": to_camel})
class PaymentMandateContents(TypedDict):
    """The data contents of a PaymentMandate."""

    payment_mandate_id: Required[str]
    """A unique identifier for this payment mandate."""
    
    payment_details_id: Required[str]
    """A unique identifier for the payment request."""

    payment_details_total: Required[PaymentItem]
    """The total payment amount."""
    
    payment_response: Required[PaymentResponse]
    """The payment response containing details of the payment method chosen by the user."""
    
    merchant_agent: Required[str]
    """Identifier for the merchant."""
    
    timestamp: Required[str]
    """The date and time the mandate was created, in ISO 8601 format."""


@pydantic.with_config({"alias_generator": to_camel})
class PaymentMandate(TypedDict):
    """Contains the user's instructions & authorization for payment.

    While the Cart and Intent mandates are required by the merchant to fulfill the
    order, separately the protocol provides additional visibility into the agentic
    transaction to the payments ecosystem. For this purpose, the PaymentMandate
    (bound to Cart/Intent mandate but containing separate information) may be
    shared with the network/issuer along with the standard transaction
    authorization messages. The goal of the PaymentMandate is to help the
    network/issuer build trust into the agentic transaction.
    """

    payment_mandate_contents: Required[PaymentMandateContents]
    """The data contents of the payment mandate."""
    
    user_authorization: NotRequired[str]
    """This is a base64_url-encoded verifiable presentation of a verifiable
        credential signing over the cart_mandate and payment_mandate_hashes.
        For example an sd-jwt-vc would contain:

        - An issuer-signed jwt authorizing a 'cnf' claim
        - A key-binding jwt with the claims
            "aud": ...
            "nonce": ...
            "sd_hash": hash of the issuer-signed jwt
            "transaction_data": an array containing the secure hashes of 
              CartMandate and PaymentMandateContents.

        """


# -----------------------------------------------------------------------------
# Credit System for Hibiscus Centralized Management <NotPartOfA2A>
# -----------------------------------------------------------------------------

@pydantic.with_config({"alias_generator": to_camel})
class AgentExecutionCost(TypedDict):
    """Defines the credit cost for executing an agent."""

    agent_id: Required[str]
    """The unique identifier of the agent."""
    
    agent_name: Required[str]
    """The name of the agent."""
    
    credits_per_request: Required[int]
    """The number of credits required to execute the agent."""
    
    creator_did: Required[str]
    """The DID of the creator of the agent."""
    
    minimum_trust_level: Required[TrustLevel]
    """The minimum trust level required to execute the agent."""


@pydantic.with_config({"alias_generator": to_camel})
class ExecutionRequest(TypedDict):
    """Represents a request to execute an agent with credit verification."""

    request_id: Required[UUID]
    """The unique identifier of the request."""
    
    executor_did: Required[str]
    """The DID of the executor."""
    
    agent_id: Required[str]
    """The unique identifier of the agent."""
    
    input_data: Required[str]
    """The input data for the agent execution."""
    
    estimated_credits: Required[int]
    """The estimated number of credits required for the execution."""
    
    trust_level: Required[TrustLevel]
    """The trust level of the executor."""


@pydantic.with_config({"alias_generator": to_camel})
class ExecutionResponse(TypedDict):
    """Represents the response from an agent execution with credit deduction."""

    request_id: Required[UUID]
    """The unique identifier of the request."""
    
    execution_id: Required[UUID]
    """The unique identifier of the execution."""
    
    success: Required[bool]
    """Indicates whether the execution was successful."""
    
    credits_charged: Required[int]
    """The number of credits charged for the execution."""
    
    transaction_id: NotRequired[UUID]
    """The unique identifier of the transaction."""
    
    output_data: NotRequired[str]
    """The output data from the agent execution."""
    
    error_message: NotRequired[str]
    """The error message if the execution failed."""
    
    execution_time: Required[str]
    """The time the execution was completed."""


# -----------------------------------------------------------------------------
# JSON-RPC Definition and Error Types
# -----------------------------------------------------------------------------

CodeT = TypeVar("CodeT", bound=int)
MessageT = TypeVar("MessageT", bound=str)

Method = TypeVar("Method")
Params = TypeVar("Params")


class JSONRPCMessage(TypedDict):
    """A JSON RPC message."""

    jsonrpc: Required[Literal["2.0"]]
    id: Required[UUID]


class JSONRPCRequest(JSONRPCMessage, Generic[Method, Params]):
    """A JSON RPC request."""

    method: Required[Method]
    params: Required[Params]


class JSONRPCError(TypedDict, Generic[CodeT, MessageT]):
    """A JSON RPC error."""

    code: Required[CodeT]
    message: Required[MessageT]
    data: NotRequired[Any]


class JSONRPCResponse(JSONRPCMessage, Generic[ResultT, ErrorT]):
    """A JSON RPC response."""

    result: NotRequired[ResultT]
    error: NotRequired[ErrorT]


JSONParseError = JSONRPCError[
    Literal[-32700],
    Literal[
        "Failed to parse JSON payload. Please ensure the request body contains valid JSON syntax. See: https://www.jsonrpc.org/specification#error_object"
    ],
]
InvalidRequestError = JSONRPCError[
    Literal[-32600],
    Literal[
        "Request payload validation failed. The request structure does not conform to JSON-RPC 2.0 specification. See: https://www.jsonrpc.org/specification#request_object"
    ],
]
MethodNotFoundError = JSONRPCError[
    Literal[-32601],
    Literal[
        "The requested method is not available on this server. Please check the method name and try again. See API docs: /docs"
    ],
]
InvalidParamsError = JSONRPCError[
    Literal[-32602],
    Literal[
        "Invalid or missing parameters for the requested method. Please verify parameter types and required fields. See API docs: /docs"
    ],
]
InternalError = JSONRPCError[
    Literal[-32603],
    Literal[
        "An internal server error occurred while processing the request. Please try again or contact support if the issue persists. See: /health"
    ],
]
TaskNotFoundError = JSONRPCError[
    Literal[-32001],
    Literal[
        "The specified task ID was not found. The task may have been completed, canceled, or expired. Check task status: GET /tasks/{id}"
    ],
]
TaskNotCancelableError = JSONRPCError[
    Literal[-32002],
    Literal[
        "This task cannot be canceled in its current state. Tasks can only be canceled while pending or running. See task lifecycle: /docs/tasks"
    ],
]
ContextNotFoundError = JSONRPCError[
    Literal[-32003],
    Literal[
        "The specified context ID was not found. The context may have been deleted or expired. Check context status: GET /contexts/{id}"
    ],
]
ContextNotCancelableError = JSONRPCError[
    Literal[-32004],
    Literal[
        "This context cannot be canceled in its current state. Contexts can only be canceled while pending or running. See context lifecycle: /docs/contexts"
    ],
]
PushNotificationNotSupportedError = JSONRPCError[
    Literal[-32005],
    Literal[
        "Push notifications are not supported by this server configuration. Please use polling to check task status. See: GET /tasks/{id}"
    ],
]
UnsupportedOperationError = JSONRPCError[
    Literal[-32006],
    Literal[
        "The requested operation is not supported by this agent or server configuration. See supported operations: /docs/capabilities"
    ],
]
ContentTypeNotSupportedError = JSONRPCError[
    Literal[-32007],
    Literal[
        "The content type in the request is not supported. Please use application/json or check supported content types. See: /docs/content-types"
    ],
]
InvalidAgentResponseError = JSONRPCError[
    Literal[-32008],
    Literal[
        "The agent returned an invalid or malformed response. This may indicate an agent configuration issue. See troubleshooting: /docs/troubleshooting"
    ],
]


# -----------------------------------------------------------------------------
# JSON-RPC Request & Response Types
# -----------------------------------------------------------------------------

SendMessageRequest = JSONRPCRequest[Literal["message/send"], MessageSendParams]
SendMessageResponse = JSONRPCResponse[Union[Task, Message], JSONRPCError[Any, Any]]

StreamMessageRequest = JSONRPCRequest[Literal["message/stream"], MessageSendParams]
StreamMessageResponse = JSONRPCResponse[Union[Task, Message], JSONRPCError[Any, Any]]

GetTaskRequest = JSONRPCRequest[Literal["tasks/get"], TaskQueryParams]
GetTaskResponse = JSONRPCResponse[Task, TaskNotFoundError]

CancelTaskRequest = JSONRPCRequest[Literal["tasks/cancel"], TaskIdParams]
CancelTaskResponse = JSONRPCResponse[Task, Union[TaskNotCancelableError, TaskNotFoundError]]

ListTasksRequest = JSONRPCRequest[Literal["tasks/list"], ListTasksParams]
ListTasksResponse = JSONRPCResponse[List[Task], Union[TaskNotFoundError, TaskNotCancelableError]]

TaskFeedbackRequest = JSONRPCRequest[Literal["tasks/feedback"], TaskFeedbackParams]
TaskFeedbackResponse = JSONRPCResponse[Dict[str, str], TaskNotFoundError]

ListContextsRequest = JSONRPCRequest[Literal["contexts/list"], ListContextsParams]
ListContextsResponse = JSONRPCResponse[List[Context], Union[ContextNotFoundError, ContextNotCancelableError]]

ClearContextsRequest = JSONRPCRequest[Literal["contexts/clear"], ContextIdParams]
ClearContextsResponse = JSONRPCResponse[Context, JSONRPCError[ContextNotFoundError, ContextNotCancelableError]]

SetTaskPushNotificationRequest = JSONRPCRequest[Literal["tasks/pushNotification/set"], TaskPushNotificationConfig]
SetTaskPushNotificationResponse = JSONRPCResponse[TaskPushNotificationConfig, PushNotificationNotSupportedError]

GetTaskPushNotificationRequest = JSONRPCRequest[Literal["tasks/pushNotification/get"], TaskIdParams]
GetTaskPushNotificationResponse = JSONRPCResponse[TaskPushNotificationConfig, PushNotificationNotSupportedError]

ResubscribeTaskRequest = JSONRPCRequest[Literal["tasks/resubscribe"], TaskIdParams]
ResubscribeTaskResponse = JSONRPCResponse[Task, Union[TaskNotCancelableError, TaskNotFoundError]]

ListTaskPushNotificationConfigRequest = JSONRPCRequest[
    Literal["tasks/pushNotificationConfig/list"], ListTaskPushNotificationConfigParams
]
ListTaskPushNotificationConfigResponse = JSONRPCResponse[TaskPushNotificationConfig, PushNotificationNotSupportedError]

DeleteTaskPushNotificationConfigRequest = JSONRPCRequest[
    Literal["tasks/pushNotificationConfig/delete"], DeleteTaskPushNotificationConfigParams
]
DeleteTaskPushNotificationConfigResponse = JSONRPCResponse[
    TaskPushNotificationConfig, PushNotificationNotSupportedError
]

A2ARequest = Annotated[
    Union[
        SendMessageRequest,
        StreamMessageRequest,
        GetTaskRequest,
        CancelTaskRequest,
        ListTasksRequest,
        TaskFeedbackRequest,
        ListContextsRequest,
        ClearContextsRequest,
        SetTaskPushNotificationRequest,
        GetTaskPushNotificationRequest,
        ResubscribeTaskRequest,
        ListTaskPushNotificationConfigRequest,
        DeleteTaskPushNotificationConfigRequest,
    ],
    Discriminator("method"),
]

A2AResponse: TypeAlias = Union[
    SendMessageResponse,
    StreamMessageResponse,
    GetTaskResponse,
    CancelTaskResponse,
    ListTasksResponse,
    TaskFeedbackResponse,
    ListContextsResponse,
    ClearContextsResponse,
    SetTaskPushNotificationResponse,
    GetTaskPushNotificationResponse,
    ResubscribeTaskResponse,
    ListTaskPushNotificationConfigResponse,
    DeleteTaskPushNotificationConfigResponse,
]

a2a_request_ta: TypeAdapter[A2ARequest] = TypeAdapter(A2ARequest)
a2a_response_ta: TypeAdapter[A2AResponse] = TypeAdapter(A2AResponse)
send_message_request_ta: TypeAdapter[SendMessageRequest] = TypeAdapter(SendMessageRequest)
send_message_response_ta: TypeAdapter[SendMessageResponse] = TypeAdapter(SendMessageResponse)
stream_message_request_ta: TypeAdapter[StreamMessageRequest] = TypeAdapter(StreamMessageRequest)
stream_message_response_ta: TypeAdapter[StreamMessageResponse] = TypeAdapter(StreamMessageResponse)


# -----------------------------------------------------------------------------
# Trust
# -----------------------------------------------------------------------------

@pydantic.with_config({"alias_generator": to_camel})
class KeycloakRole(TypedDict):
    """Keycloak role model."""

    role_id: Required[UUID]
    """The ID of the role."""
    
    role_name: Required[str]
    """The name of the role."""
    
    permissions: Required[List[str]]
    """The permissions of the role."""
    
    trust_level: Required[TrustLevel]
    """The trust level of the role."""
    
    realm_name: Required[str]
    """The realm name of the role."""
    
    external_mappings: NotRequired[Dict[str, str]] = {}
    """The external mappings of the role."""
    
    operation_permissions: NotRequired[Dict[str, TrustLevel]] = {}
    """The operation permissions of the role."""


@pydantic.with_config({"alias_generator": to_camel})
class AgentTrust(TypedDict):
    """Trust configuration for an agent."""

    identity_provider: Required[IdentityProvider]
    """The identity provider of the agent."""
    
    inherited_roles: Required[List[KeycloakRole]]
    """The roles inherited by the agent."""
    
    certificate: NotRequired[str]
    """The certificate of the agent."""
    
    certificate_fingerprint: NotRequired[str]
    """The fingerprint of the certificate of the agent."""
    
    creator_id: Union[UUID, int, str]
    """The creator ID of the agent."""
    
    creation_timestamp: int
    """The creation timestamp of the agent."""
    trust_verification_required: bool
    allowed_operations: Dict[str, TrustLevel]


# -----------------------------------------------------------------------------
# Agent
# -----------------------------------------------------------------------------


@pydantic.with_config({"alias_generator": to_camel})
class AgentIdentity(TypedDict):
    """Agent identity configuration with DID and other identifiers."""

    did: Required[str]
    """The agent's Decentralized Identifier (DID)."""

    did_document: Required[Dict[str, Any]]
    """The agent's DID document containing public keys and other identifiers."""

    agentdns_url: NotRequired[str]
    """The agent's AgentDNS URL for decentralized identity resolution."""

    endpoint: NotRequired[str]
    """The agent's endpoint URL for communication."""

    public_key: Required[str]
    """The agent's public key for authentication."""

    csr: Required[str]
    """The agent's Certificate Signing Request (CSR) for authentication."""


@pydantic.with_config({'alias_generator': to_camel})
class AgentInterface(TypedDict):
    """An interface that the agent supports."""

    transport: str
    """The transport protocol (e.g., 'jsonrpc', 'websocket')."""

    url: str
    """The URL endpoint for this transport."""

    description: NotRequired[str]
    """Description of this interface."""


@pydantic.with_config({'alias_generator': to_camel})
class AgentExtension(TypedDict):
    """A declaration of an extension supported by an Agent."""

    uri: str
    """The URI of the extension."""

    description: NotRequired[str]
    """A description of how this agent uses this extension."""

    required: NotRequired[bool]
    """Whether the client must follow specific requirements of the extension."""

    params: NotRequired[dict[str, Any]]
    """Optional configuration for the extension."""


@pydantic.with_config({'alias_generator': to_camel})
class Skill(TypedDict):
    """Skills are a unit of capability that an agent can perform."""

    id: str
    """A unique identifier for the skill."""

    name: str
    """Human readable name of the skill."""

    description: str
    """A human-readable description of the skill.

    It will be used by the client or a human as a hint to understand the skill.
    """

    tags: list[str]
    """Set of tag-words describing classes of capabilities for this specific skill.

    Examples: "cooking", "customer support", "billing".
    """

    examples: NotRequired[list[str]]
    """The set of example scenarios that the skill can perform.

    Will be used by the client as a hint to understand how the skill can be used. (e.g. "I need a recipe for bread")
    """

    input_modes: list[str]
    """Supported mime types for input data."""

    output_modes: list[str]
    """Supported mime types for output data."""


@pydantic.with_config({"alias_generator": to_camel})
class AgentCapabilities(TypedDict):
    """Defines optional capabilities supported by an agent."""

    extensions: NotRequired[list[AgentExtension]]
    """List of extensions supported by the agent."""
    
    push_notifications: NotRequired[bool]
    """Whether the agent supports push notifications."""
    
    state_transition_history: NotRequired[bool]
    """Whether the agent supports state transition history."""
    
    streaming: NotRequired[bool]
    """Whether the agent supports streaming."""


@pydantic.with_config({"alias_generator": to_camel})
class AgentCard(TypedDict):
    """The card that describes an agent - following Pebbling pattern."""

    id: Required[UUID]
    """Unique identifier for the agent."""
    
    name: Required[str]
    """Human readable name of the agent."""
    
    description: Required[str]
    """A human-readable description of the agent.

    It will be used by the client or a human as a hint to understand the agent.
    """
    
    url: Required[str]
    """URL of the agent."""
    
    version: Required[str]
    """Version of the agent."""
    
    protocol_version: Required[str]
    """Version of the protocol used by the agent."""
    
    documentation_url: NotRequired[str]
    """URL of the documentation of the agent."""

    icon_url: NotRequired[str]
    """A URL to an icon for the agent."""

    identity: Required[AgentIdentity]
    """Identity of the agent."""
    
    agent_trust: Required[AgentTrust]
    """Trust of the agent."""

    capabilities: Required[AgentCapabilities]
    """Capabilities of the agent."""
    
    skills: Required[List[Skill]]
    """Skills of the agent."""

    kind: Required[Literal["agent", "team", "workflow"]]
    """Kind of the agent."""

    execution_cost: NotRequired[AgentExecutionCost]
    """Execution cost of the agent."""

    num_history_sessions: Required[int]
    """Number of history sessions of the agent."""

    preferred_transport: NotRequired[str]
    """The transport of the preferred endpoint. If empty, defaults to JSONRPC."""
    
    extra_data: Required[Dict[str, Any]]
    """Extra data about the agent."""

    debug_mode: Required[bool]
    """Debug mode of the agent."""
    
    debug_level: Required[Literal[1, 2]]
    """Debug level of the agent."""

    monitoring: Required[bool]
    """Monitoring of the agent."""
    
    telemetry: Required[bool]
    """Telemetry of the agent."""

    additional_interfaces: NotRequired[list[AgentInterface]]
    """Announcement of additional supported transports."""

    security: NotRequired[list[dict[str, list[str]]]]
    """Security requirements for contacting the agent."""

    security_schemes: NotRequired[dict[str, SecurityScheme]]
    """Security scheme definitions."""

    default_input_modes: list[str]
    """Supported mime types for input data."""

    default_output_modes: list[str]
    """Supported mime types for output data."""

agent_card_ta = pydantic.TypeAdapter(AgentCard)

# Rebuild TypeAdapters to resolve forward references
a2a_request_ta.rebuild()
a2a_response_ta.rebuild()
send_message_request_ta.rebuild()
send_message_response_ta.rebuild()
stream_message_request_ta.rebuild()
stream_message_response_ta.rebuild()