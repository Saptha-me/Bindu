# |--------------------------------------------------|
# |                                                  |
# |           Give Feedback / Get Help               |
# | https://github.com/Pebbling-ai/pebble/issues/new |
# |                                                  |
# |--------------------------------------------------|
#
#  Thank you!!! We ❤️ you! - The Pebbling Team

"""
Pebbling Protocol Type Definitions

This module contains all the protocol data models used for communication between
agents in the Pebbling framework. The Pebbling protocol is designed to facilitate
secure, trust-verified agent-to-agent communication with standardized message formats.

Key Components:
- Agent Identity & Trust: Models for agent identification, trust verification, and permissions
- Messaging: Standardized message formats with support for text, files, and structured data
- Tasks: Long-running operation tracking with state management and artifacts
- Negotiation: Models for agent-to-agent negotiation sessions and proposals
- Payments: Standardized payment action tracking between agents
- JSON-RPC: Request/response models following the JSON-RPC 2.0 specification

The protocol is designed to be framework-agnostic and extensible, allowing
integration with various AI backends and agent architectures.
"""

# This file is auto-generated from the Pebbling Protocol JSON Schema
# Original source: pebbling_protocol.json
# Generated: 2025-07-17

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class Role(Enum):
    """
    Defines the role of a participant in the Pebbling communication protocol.
    
    Roles determine messaging permissions and context handling.
    
    Examples:
        ```python
        # Specify that a message is from an agent
        message = Message(..., role=Role.agent, ...)
        
        # Check if a message is from a user
        if message.role == Role.user:
            # Handle user message
            pass
        ```
    """
    agent = 'agent'  # Message is from an AI agent
    user = 'user'    # Message is from a human user


class RunMode(Enum):
    """
    Execution mode for agent operations.
    
    Determines how requests are processed by the agent framework.
    
    Examples:
        ```python
        # Request synchronous processing
        config = MessageSendConfiguration(acceptedOutputModes=[RunMode.sync.value])
        
        # Check if streaming is supported
        if RunMode.stream.value in agent.capabilities.supported_operations:
            # Request streaming output
            pass
        ```
    """
    sync = 'sync'      # Synchronous operation - blocks until complete
    async_ = 'async'   # Asynchronous operation - returns immediately with task ID
    stream = 'stream'  # Streaming operation - returns results incrementally


class DebugLevel(Enum):
    """
    Debug verbosity levels for agent operations.
    
    Higher numbers indicate more verbose debugging information.
    
    Examples:
        ```python
        # Enable verbose debugging for an agent
        agent_manifest = AgentManifest(
            debug_mode=True,
            debug_level=DebugLevel.integer_2,
            # ... other fields
        )
        ```
    """
    integer_1 = 1  # Basic debugging
    integer_2 = 2  # Verbose debugging


class IdentityVerificationMethod(Enum):
    """
    Methods for verifying agent identity in the protocol.
    
    Different verification methods provide different security guarantees.
    
    Examples:
        ```python
        # Configure an agent to use DID for identity verification
        identity = AgentIdentity(
            identity_verification_method=IdentityVerificationMethod.did,
            did='did:web:agent.example.com',
            # ... other fields
        )
        ```
    """
    did = 'did'                # Decentralized Identifier (DID) verification
    agentdns = 'agentdns'      # Verification via agent DNS service
    certificate = 'certificate'  # X.509 certificate verification


class AgentCapabilities(BaseModel):
    """
    Describes the capabilities of an agent in the Pebbling framework.
    
    Agent capabilities determine what operations an agent can perform and what data it can process.
    
    Examples:
        ```python
        # Create an agent with capabilities for text processing
        agent = Agent(
            capabilities=AgentCapabilities(
                supported_operations=['text-processing'],
                input_content_types=['text/plain'],
                output_content_types=['text/plain'],
            ),
            # ... other fields
        )
        ```
    """
    supported_operations: Optional[List[str]] = Field(
        [],
        description='Operations this agent can perform',
        title='Supported Operations',
    )
    input_content_types: Optional[List[str]] = Field(
        ['text/plain'],
        description='Content types this agent can accept',
        title='Input Content Types',
    )
    output_content_types: Optional[List[str]] = Field(
        ['text/plain'],
        description='Content types this agent can produce',
        title='Output Content Types',
    )
    supports_images: Optional[bool] = Field(
        False, description='Whether agent can process images', title='Supports Images'
    )
    supports_audio: Optional[bool] = Field(
        False, description='Whether agent can process audio', title='Supports Audio'
    )
    supports_video: Optional[bool] = Field(
        False, description='Whether agent can process video', title='Supports Video'
    )
    supports_binary: Optional[bool] = Field(
        False,
        description='Whether agent can process binary data',
        title='Supports Binary',
    )
    max_message_size_bytes: Optional[int] = Field(
        None,
        description='Maximum message size in bytes',
        title='Max Message Size Bytes',
    )
    streaming_supported: Optional[bool] = Field(
        False,
        description='Whether agent supports streaming responses',
        title='Streaming Supported',
    )


class AgentMetrics(BaseModel):
    """
    Performance and usage metrics for an agent in the Pebbling framework.
    
    This model captures operational metrics for monitoring and analysis purposes.
    Usage metrics help in understanding agent performance, optimization needs,
    and resource allocation requirements.
    
    Examples:
        ```python
        # Create basic metrics for a new agent
        metrics = AgentMetrics(
            total_requests=0,
            total_tokens=0,
            avg_response_time_ms=0,
            error_rate=0.0
        )
        
        # Update metrics after processing
        metrics.total_requests += 1
        metrics.total_tokens += 512
        metrics.last_active = int(time.time())
        
        # Add custom metrics
        metrics.custom_metrics = {
            'token_efficiency': 0.87,
            'cache_hit_ratio': 0.65
        }
        ```
    """
    total_requests: Optional[int] = Field(
        0, description='Total number of requests processed', title='Total Requests'
    )
    total_tokens: Optional[int] = Field(
        None, description='Total tokens processed', title='Total Tokens'
    )
    avg_response_time_ms: Optional[int] = Field(
        None,
        description='Average response time in milliseconds',
        title='Avg Response Time Ms',
    )
    error_rate: Optional[float] = Field(
        None, description='Error rate percentage', title='Error Rate'
    )
    uptime_seconds: Optional[int] = Field(
        None, description='Total uptime in seconds', title='Uptime Seconds'
    )
    last_active: Optional[int] = Field(
        None, description='UNIX timestamp of last activity', title='Last Active'
    )
    custom_metrics: Optional[Dict[str, Any]] = Field(
        None, description='Additional custom metrics', title='Custom Metrics'
    )


class MTLSConfiguration(BaseModel):
    """
    Configuration for mutual TLS (mTLS) communication between agents.
    
    mTLS provides strong security by requiring both parties to present certificates,
    ensuring two-way authentication and encrypted communication.
    
    Examples:
        ```python
        # Basic mTLS configuration with required fields
        mtls_config = MTLSConfiguration(
            endpoint="https://agent.example.com:8443",
            public_key="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
        )
        
        # Comprehensive mTLS configuration with all security options
        secure_mtls = MTLSConfiguration(
            endpoint="https://secure-agent.example.com:8443",
            public_key="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----",
            certificate_chain=["-----BEGIN CERTIFICATE-----\n...", "-----BEGIN CERTIFICATE-----\n..."],
            certificate_expiry=1672531199,  # Dec 31, 2023
            key_rotation_policy="quarterly",
            cipher_suites=["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"],
            min_tls_version="1.3"
        )
        ```
    """
    endpoint: str = Field(
        ..., description='Secure mTLS agent endpoint.', title='Endpoint'
    )
    public_key: str = Field(
        ..., description="Agent's public key for mTLS.", title='Public Key'
    )
    certificate_chain: Optional[List[str]] = Field(
        None, description='Certificate chain for validation.', title='Certificate Chain'
    )
    certificate_expiry: Optional[int] = Field(
        None,
        description='UNIX timestamp when certificate expires.',
        title='Certificate Expiry',
    )
    key_rotation_policy: Optional[str] = Field(
        None,
        description="Policy for key rotation, e.g. 'quarterly'",
        title='Key Rotation Policy',
    )
    cipher_suites: Optional[List[str]] = Field(
        None,
        description='Allowed cipher suites for TLS connection.',
        title='Cipher Suites',
    )
    min_tls_version: Optional[str] = Field(
        '1.2', description='Minimum TLS version required.', title='Min Tls Version'
    )


class IdentityProvider(Enum):
    keycloak = 'keycloak'
    azure_ad = 'azure_ad'
    okta = 'okta'
    auth0 = 'auth0'
    custom = 'custom'


class TrustLevel(Enum):
    """
    Hierarchical trust levels for agent-to-agent interactions.
    
    Trust levels define the degree of access and operations permitted between agents,
    following a progressive security model from untrusted to emergency access.
    
    Examples:
        ```python
        # Check if an agent has sufficient trust for a sensitive operation
        def can_perform_operation(verification_result, operation_name):
            # Different operations require different trust levels
            required_levels = {
                'read_public_data': TrustLevel.minimal,
                'read_user_data': TrustLevel.medium,
                'modify_user_data': TrustLevel.high,
                'admin_operations': TrustLevel.critical
            }
            
            required_level = required_levels.get(operation_name, TrustLevel.untrusted)
            
            # Compare trust levels (relies on enum ordering)
            trust_hierarchy = list(TrustLevel)
            return (trust_hierarchy.index(verification_result.trust_level) >= 
                    trust_hierarchy.index(required_level))
        ```
    """
    untrusted = 'untrusted'
    minimal = 'minimal'
    low = 'low'
    standard = 'standard'
    medium = 'medium'
    high = 'high'
    elevated = 'elevated'
    critical = 'critical'
    super_critical = 'super-critical'
    emergency = 'emergency'


class TrustCategory(Enum):
    """
    Categories of trust for fine-grained access control and verification.
    
    Trust categories allow for domain-specific trust evaluation and permissions,
    enabling contextual security policies across different operational domains.
    
    Examples:
        ```python
        # Configure trust requirements for different operations
        trust_requirements = {
            'view_medical_records': {
                'category': TrustCategory.healthcare,
                'level': TrustLevel.high
            },
            'process_payment': {
                'category': TrustCategory.financial,
                'level': TrustLevel.elevated
            },
            'read_user_profile': {
                'category': TrustCategory.personal,
                'level': TrustLevel.standard
            }
        }
        
        # Verify if agent has category-specific trust for an operation
        def verify_categorical_trust(agent_trust, operation):
            required = trust_requirements.get(operation)
            if not required:
                return False
                
            # Check if agent has sufficient trust in the specific category
            category_trust = agent_trust.get(required['category'])
            return category_trust >= required['level']
        ```
    """
    identity = 'identity'
    authentication = 'authentication'
    authorization = 'authorization'
    data_access = 'data_access'
    financial = 'financial'
    healthcare = 'healthcare'
    personal = 'personal'
    admin = 'admin'
    system = 'system'
    communication = 'communication'
    regulatory = 'regulatory'


class TrustVerificationMethod(Enum):
    """
    Methods for verifying agent trust in the Pebbling protocol.
    
    Each method represents a different approach to establishing and verifying trust
    between agents, with varying security properties and implementation requirements.
    
    Examples:
        ```python
        # Select appropriate verification method based on security requirements
        def get_verification_method(security_level, capabilities):
            if 'zero_knowledge_proof' in capabilities and security_level == 'maximum':
                return TrustVerificationMethod.zero_knowledge
            elif 'biometric' in capabilities and security_level == 'high':
                return TrustVerificationMethod.biometric
            elif 'mtls' in capabilities:
                return TrustVerificationMethod.mtls
            elif 'did' in capabilities:
                return TrustVerificationMethod.did
            else:
                return TrustVerificationMethod.certificate
                
        # Configure trust verification based on method
        def setup_verification(method, agent_config):
            if method == TrustVerificationMethod.mtls:
                return {'requires_setup': True, 'setup_endpoint': '/setup/mtls'}
            elif method == TrustVerificationMethod.did:
                return {'requires_setup': False, 'verification_endpoint': '/verify/did'}
            # ... other methods
        ```
    """
    certificate = 'certificate'
    oauth = 'oauth'
    did = 'did'
    mtls = 'mtls'
    jwt = 'jwt'
    multi_party = 'multi_party'
    biometric = 'biometric'
    zero_knowledge = 'zero_knowledge'
    multi_factor = 'multi_factor'


class TrustVerificationResult(BaseModel):
    """
    Result of a trust verification operation between agents.
    
    This model captures the outcome of trust verification, including the
    established trust level, allowed and denied operations, and authentication
    tokens for subsequent operations.
    
    Examples:
        ```python
        # Create a successful verification result with standard trust
        import datetime
        
        verification = TrustVerificationResult(
            verified=True,
            trust_level=TrustLevel.standard,
            allowed_operations=["read", "query", "subscribe"],
            verification_timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            verification_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_expiry=(datetime.datetime.utcnow() + 
                         datetime.timedelta(hours=1)).isoformat() + "Z"
        )
        
        # Create a failed verification result
        failed_verification = TrustVerificationResult(
            verified=False,
            trust_level=TrustLevel.untrusted,
            denied_operations=["read", "write", "delete"],
            verification_timestamp=datetime.datetime.utcnow().isoformat() + "Z"
        )
        
        # Use the verification result to control access
        def check_operation_permission(result, operation):
            if not result.verified:
                return False
            if operation in result.denied_operations:
                return False
            if result.allowed_operations and operation not in result.allowed_operations:
                return False
            return True
        ```
    """
    verified: bool = Field(
        ..., description='Whether trust verification succeeded', title='Verified'
    )
    trust_level: TrustLevel = Field(..., description='The verified trust level')
    allowed_operations: Optional[List[str]] = Field(
        [],
        description='Operations allowed with the verified trust level',
        title='Allowed Operations',
    )
    denied_operations: Optional[List[str]] = Field(
        [],
        description='Operations denied due to insufficient trust level',
        title='Denied Operations',
    )
    verification_timestamp: str = Field(
        ...,
        description='ISO-8601 timestamp of the verification',
        examples=['2023-10-27T10:00:00Z'],
        title='Verification Timestamp',
    )
    verification_token: Optional[str] = Field(
        None,
        description='Token for subsequent operations',
        examples=['abc123'],
        title='Verification Token',
    )
    token_expiry: Optional[str] = Field(
        None,
        description='ISO-8601 timestamp when the verification token expires',
        examples=['2023-10-27T10:00:00Z'],
        title='Token Expiry',
    )


class TrustVerificationParams(BaseModel):
    """
    Parameters for initiating a trust verification request.
    
    This model encapsulates all necessary information for an agent to request
    trust verification with another agent, including the operations it intends
    to perform and verification credentials.
    
    Examples:
        ```python
        # Create basic verification parameters
        params = TrustVerificationParams(
            agent_id="agnt_12345",
            target_agent_id="agnt_67890",
            operations=["read", "write"]
        )
        
        # Create verification parameters with certificate
        from uuid import uuid4
        
        cert_params = TrustVerificationParams(
            agent_id=uuid4(),
            target_agent_id=uuid4(),
            operations=["read", "analyze", "summarize"],
            certificate="-----BEGIN CERTIFICATE-----\n...",
            metadata={
                "purpose": "data analysis",
                "session_id": "sess_abc123",
                "client_version": "2.3.1"
            }
        )
        
        # Use parameters to initiate verification
        async def verify_trust(params):
            result = await trust_service.verify(
                requester=params.agent_id,
                target=params.target_agent_id,
                requested_ops=params.operations,
                credentials={
                    "certificate": params.certificate,
                    **params.metadata
                }
            )
            return result
        ```
    """
    agent_id: Union[UUID, int, str] = Field(
        ..., description='ID of the agent requesting verification', title='Agent Id'
    )
    target_agent_id: Union[UUID, int, str] = Field(
        ...,
        description='ID of the target agent to interact with',
        title='Target Agent Id',
    )
    operations: Optional[List[str]] = Field(
        [], description='Operations the agent wants to perform', title='Operations'
    )
    certificate: Optional[str] = Field(
        None, description="Agent's certificate for verification", title='Certificate'
    )
    metadata: Optional[Dict[str, Any]] = Field(
        {}, description='Additional verification metadata', title='Metadata'
    )


class MessageSendConfiguration(BaseModel):
    """
    Configuration for sending messages to an agent.
    
    This model controls how messages are processed, including output modes
    (sync, async, streaming), blocking behavior, and history context length.
    
    Examples:
        ```python
        # Configure synchronous blocking request
        sync_config = MessageSendConfiguration(
            acceptedOutputModes=[RunMode.sync.value],
            blocking=True,
            historyLength=10
        )
        
        # Configure streaming non-blocking request
        stream_config = MessageSendConfiguration(
            acceptedOutputModes=[RunMode.stream.value],
            blocking=False
        )
        
        # Configure request that accepts multiple output modes
        flexible_config = MessageSendConfiguration(
            acceptedOutputModes=[RunMode.sync.value, RunMode.async_.value, RunMode.stream.value],
            blocking=True
        )
        ```
    """
    acceptedOutputModes: List[str] = Field(..., title='Acceptedoutputmodes')
    blocking: Optional[bool] = Field(None, title='Blocking')
    historyLength: Optional[int] = Field(None, title='Historylength')


class TextPart(BaseModel):
    """
    A text message part in the Pebbling communication protocol.
    
    TextPart represents plain text content in messages between users and agents.
    It's the most common message part type for standard text interactions.
    
    Examples:
        ```python
        # Create a simple text part
        text = TextPart(content="Hello! How can I assist you today?")
        
        # Create text part with metadata
        annotated_text = TextPart(
            content="Here's the information you requested.",
            metadata={
                "language": "en",
                "confidence": 0.98,
                "tone": "informational"
            }
        )
        
        # Add text part to a message
        message = Message(
            role=Role.agent,
            parts=[text],
            # ... other message fields
        )
        ```
    """
    kind: str = Field('text', const=True, title='Kind')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    content: str = Field(..., title='Content')


class DataPart(BaseModel):
    """
    A structured data message part in the Pebbling communication protocol.
    
    DataPart represents structured data in messages, allowing agents to
    exchange machine-readable information alongside human-readable content.
    Useful for conveying results, parameters, or other structured information.
    
    Examples:
        ```python
        # Create a data part with analysis results
        analysis_data = DataPart(
            content="Analysis results for your query",
            data={
                "sentiment": "positive",
                "entities": ["Apple", "technology", "innovation"],
                "confidence_score": 0.87,
                "recommended_actions": ["follow up", "investigate"] 
            }
        )
        
        # Create a data part with geolocation
        location_data = DataPart(
            content="Nearest coffee shops",
            data={
                "locations": [
                    {"name": "Coffee House", "distance": "0.3 miles", 
                     "coords": {"lat": 37.7749, "lng": -122.4194}},
                    {"name": "Brew Corner", "distance": "0.5 miles", 
                     "coords": {"lat": 37.7748, "lng": -122.4141}}
                ],
                "search_radius": "1 mile"
            },
            metadata={"source": "maps-api", "timestamp": "2023-10-27T10:00:00Z"}
        )
        ```
    """
    kind: str = Field('data', const=True, title='Kind')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    content: str = Field(..., title='Content')
    data: Dict[str, Any] = Field(..., title='Data')


class FileWithBytes(BaseModel):
    """
    File representation with raw byte content for message attachments.
    
    FileWithBytes represents a file as base64-encoded bytes with metadata
    about the file type and name. Used for file attachments in messages.
    
    Examples:
        ```python
        # Create a file attachment with base64 encoded data
        import base64
        
        # Read image file and encode as base64
        with open('image.jpg', 'rb') as f:
            image_bytes = base64.b64encode(f.read()).decode('utf-8')
            
        # Create file attachment
        image_file = FileWithBytes(
            bytes=image_bytes,
            mimeType="image/jpeg",
            name="sunset_photo.jpg"
        )
        
        # Use in a file part (assuming a FilePart class exists)
        file_part = FilePart(
            kind="file",
            file=image_file
        )
        ```
    """
    bytes: str = Field(..., title='Bytes')
    mimeType: Optional[str] = Field(None, title='Mimetype')
    name: Optional[str] = Field(None, title='Name')


class FileWithUri(BaseModel):
    """
    File representation with URI reference for message attachments.
    
    FileWithUri extends FileWithBytes by adding a URI reference to the file,
    allowing for remote access or reference to the file resource.
    
    Examples:
        ```python
        # Create a file with URI reference
        import base64
        
        # Read document file and encode as base64
        with open('document.pdf', 'rb') as f:
            doc_bytes = base64.b64encode(f.read()).decode('utf-8')
            
        # Create file with URI
        pdf_file = FileWithUri(
            bytes=doc_bytes,  # Can be empty string if only using URI
            mimeType="application/pdf",
            name="quarterly_report.pdf",
            uri="https://storage.example.com/documents/quarterly_report.pdf"
        )
        
        # Example showing a file reference with minimal bytes
        large_file = FileWithUri(
            bytes="",  # Empty since we're only using the URI
            name="large_dataset.csv",
            mimeType="text/csv",
            uri="https://data.example.com/datasets/large_dataset.csv"
        )
        ```
    """
    bytes: str = Field(..., title='Bytes')
    mimeType: Optional[str] = Field(None, title='Mimetype')
    name: Optional[str] = Field(None, title='Name')
    uri: str = Field(..., title='Uri')


class TaskState(Enum):
    """
    Possible states of a task in the Pebbling protocol.
    
    TaskState tracks the lifecycle of a task from submission to completion,
    including intermediate states that may require user interaction.
    
    Examples:
        ```python
        # Check if task requires user interaction
        def requires_user_action(task):
            interactive_states = [
                TaskState.input_required,
                TaskState.auth_required,
                TaskState.trust_verification_required
            ]
            return task.state in interactive_states
        
        # Process task based on state
        def handle_task(task):
            if task.state == TaskState.completed:
                process_results(task.result)
            elif task.state == TaskState.failed:
                handle_failure(task.error)
            elif task.state == TaskState.working:
                show_progress_indicator()
            elif requires_user_action(task):
                prompt_for_user_input(task)
        ```
    """
    submitted = 'submitted'                          # Task has been submitted but not yet started
    working = 'working'                              # Task is currently being processed
    input_required = 'input-required'                # Task requires additional input from the user
    completed = 'completed'                          # Task has been successfully completed
    canceled = 'canceled'                            # Task was canceled before completion
    failed = 'failed'                                # Task encountered an error and could not complete
    rejected = 'rejected'                            # Task was rejected by the agent
    auth_required = 'auth-required'                  # Task requires authentication to proceed
    unknown = 'unknown'                              # Task state could not be determined
    trust_verification_required = 'trust-verification-required'  # Task requires trust verification


class TaskIdParams(BaseModel):
    """
    Parameters for identifying and managing a specific task.
    
    TaskIdParams provides the necessary identification for task operations
    like retrieving status, canceling tasks, or resubscribing to updates.
    
    Examples:
        ```python
        # Create parameters for a task query
        from uuid import UUID
        
        task_params = TaskIdParams(
            id=UUID('12345678-1234-5678-1234-567812345678'),
            metadata={
                "client_version": "2.1.0",
                "request_source": "mobile_app"
            }
        )
        
        # Use parameters in a task status request
        get_task_request = GetTaskRequest(
            id=UUID('87654321-8765-4321-8765-432187654321'),
            method='tasks/get',
            params=task_params
        )
        
        # Use parameters in a task cancellation
        cancel_params = TaskIdParams(id=UUID('12345678-1234-5678-1234-567812345678'))
        cancel_request = CancelTaskRequest(
            id=UUID('98765432-9876-5432-9876-543298765432'),
            method='tasks/cancel',
            params=cancel_params
        )
        ```
    """
    id: UUID = Field(..., title='Id')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')


class NegotiationStatus(Enum):
    proposed = 'proposed'
    accepted = 'accepted'
    rejected = 'rejected'
    countered = 'countered'


class NegotiationSessionStatus(Enum):
    initiated = 'initiated'
    ongoing = 'ongoing'
    completed = 'completed'
    rejected = 'rejected'


class NegotiationProposal(BaseModel):
    proposal_id: UUID = Field(
        ..., description='Unique ID of this specific proposal', title='Proposal Id'
    )
    from_agent: UUID = Field(
        ..., description='Agent ID initiating the proposal', title='From Agent'
    )
    to_agent: UUID = Field(
        ..., description='Agent ID receiving the proposal', title='To Agent'
    )
    terms: Dict[str, Any] = Field(
        ..., description='Negotiation terms (structured)', title='Terms'
    )
    timestamp: str = Field(
        ...,
        description='ISO-8601 timestamp when the proposal was made',
        examples=['2023-10-27T10:00:00Z'],
        title='Timestamp',
    )
    status: Optional[NegotiationStatus] = Field(
        'proposed', description='Status of this specific proposal'
    )


class NegotiationSession(BaseModel):
    session_id: UUID = Field(
        ...,
        description='Unique identifier for the negotiation session',
        title='Session Id',
    )
    status: Optional[NegotiationSessionStatus] = Field(
        'initiated', description='Current status of the negotiation'
    )
    participants: List[UUID] = Field(
        ..., description='List of participating agent IDs', title='Participants'
    )
    proposals: Optional[List[NegotiationProposal]] = Field(
        [], description='Array of negotiation proposals exchanged', title='Proposals'
    )


class PaymentActionType(Enum):
    submit = 'submit'
    cancel = 'cancel'
    refund = 'refund'
    verify = 'verify'
    unknown = 'unknown'


class PaymentStatus(Enum):
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'
    refunded = 'refunded'
    cancelled = 'cancelled'
    disputed = 'disputed'


class PaymentMethod(Enum):
    credit_card = 'credit_card'
    debit_card = 'debit_card'
    ach = 'ach'
    wire_transfer = 'wire_transfer'
    crypto = 'crypto'
    sepa = 'sepa'
    paypal = 'paypal'
    other = 'other'


class BillingPeriod(Enum):
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'
    quarterly = 'quarterly'
    yearly = 'yearly'
    one_time = 'one-time'


class PaymentAction(BaseModel):
    action_type: Optional[PaymentActionType] = Field(
        'submit', description='Type of payment action'
    )
    amount: float = Field(
        ..., description='The amount of the payment', examples=[10.0], title='Amount'
    )
    currency: str = Field(
        ...,
        description='ISO currency code clearly identified (e.g., USD)',
        title='Currency',
    )
    billing_period: Optional[BillingPeriod] = Field(
        'one-time',
        description='Billing frequency clearly defined if subscription-based',
    )
    transaction_id: Optional[str] = Field(
        None, description='Unique transaction identifier', title='Transaction Id'
    )
    payment_method: Optional[PaymentMethod] = Field(
        None, description='Method of payment'
    )
    payment_status: Optional[PaymentStatus] = Field(
        None, description='Current status of the payment'
    )
    created_timestamp: Optional[str] = Field(
        None,
        description='ISO-8601 timestamp when payment was created',
        examples=['2023-10-27T10:00:00Z'],
        title='Created Timestamp',
    )
    processed_timestamp: Optional[str] = Field(
        None,
        description='ISO-8601 timestamp when payment was processed',
        examples=['2023-10-27T10:00:00Z'],
        title='Processed Timestamp',
    )
    payer_id: Optional[Union[UUID, str]] = Field(
        None, description='ID of the paying entity', title='Payer Id'
    )
    payee_id: Optional[Union[UUID, str]] = Field(
        None, description='ID of the receiving entity', title='Payee Id'
    )
    reference: Optional[str] = Field(
        None, description='Payment reference or memo', title='Reference'
    )
    regulatory_info: Optional[Dict[str, Any]] = Field(
        None,
        description='Regulatory information for compliance',
        title='Regulatory Info',
    )


class JSONRPCError(BaseModel):
    code: int = Field(..., title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field(..., title='Message')


class GetTaskRequest(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    method: str = Field('tasks/get', const=True, title='Method')
    params: TaskIdParams


class CancelTaskRequest(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    method: str = Field('tasks/cancel', const=True, title='Method')
    params: TaskIdParams


class TaskResubscriptionRequest(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    method: str = Field('tasks/resubscribe', const=True, title='Method')
    params: TaskIdParams


class JSONParseError(BaseModel):
    code: int = Field(-32700, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Invalid JSON', const=True, title='Message')


class InvalidRequestError(BaseModel):
    code: int = Field(-32600, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Validation error', const=True, title='Message')


class MethodNotFoundError(BaseModel):
    code: int = Field(-32601, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Method not found', const=True, title='Message')


class InvalidParamsError(BaseModel):
    code: int = Field(-32602, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Invalid parameters', const=True, title='Message')


class InternalError(BaseModel):
    code: int = Field(-32603, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Internal error', const=True, title='Message')


class TaskNotFoundError(BaseModel):
    code: int = Field(-32007, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Task not found', const=True, title='Message')


class TaskNotCancelableError(BaseModel):
    code: int = Field(-32008, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Task not cancelable', const=True, title='Message')


class PushNotificationNotSupportedError(BaseModel):
    code: int = Field(-32009, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Push notification not supported', const=True, title='Message')


class UnsupportedOperationError(BaseModel):
    code: int = Field(-32010, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Unsupported operation', const=True, title='Message')


class ContentTypeNotSupportedError(BaseModel):
    code: int = Field(-32011, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Content type not supported', const=True, title='Message')


class InvalidAgentResponseError(BaseModel):
    code: int = Field(-32006, const=True, title='Code')
    data: Any = Field(None, title='Data')
    message: str = Field('Invalid agent response', const=True, title='Message')


class AgentIdentity(BaseModel):
    did: Optional[str] = Field(
        None,
        description='Agent DID for decentralized identity (URI format).',
        title='Did',
    )
    did_document: Optional[Dict[str, Any]] = Field(
        None,
        description='Complete DID document containing verification methods, services, etc.',
        title='Did Document',
    )
    did_resolution_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description='Metadata from DID resolution process.',
        title='Did Resolution Metadata',
    )
    agentdns_url: Optional[str] = Field(
        None,
        description='Agent DNS-based identity URL (agentdns.ai).',
        title='Agentdns Url',
    )
    endpoint: str = Field(
        ..., description='Secure mTLS agent endpoint.', title='Endpoint'
    )
    mtls_config: MTLSConfiguration = Field(
        ..., description='mTLS configuration for agent.'
    )
    identity_verification_method: Optional[IdentityVerificationMethod] = Field(
        'certificate',
        description='Primary method for identity verification.',
        title='Identity Verification Method',
    )


class KeycloakRole(BaseModel):
    role_id: UUID = Field(
        ..., description='Role ID from Keycloak IAM.', title='Role Id'
    )
    role_name: str = Field(
        ..., description='Human-readable role name.', title='Role Name'
    )
    permissions: Optional[List[str]] = Field(
        [], description='Specific permissions tied to this role.', title='Permissions'
    )
    trust_level: Optional[TrustLevel] = Field(
        'medium', description='Default trust level for this role'
    )
    realm_name: str = Field(
        ..., description='The Keycloak realm this role belongs to.', title='Realm Name'
    )
    external_mappings: Optional[Dict[str, str]] = Field(
        None,
        description='Mappings to equivalent roles in other identity systems',
        title='External Mappings',
    )
    operation_permissions: Optional[Dict[str, TrustLevel]] = Field(
        None,
        description="Operation-specific trust requirements, e.g., {'update_customer': 'high'}",
        title='Operation Permissions',
    )


class TrustVerificationRequest(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    method: str = Field('trust/verify', const=True, title='Method')
    params: TrustVerificationParams


class TrustVerificationResponse(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    result: TrustVerificationResult


class FilePart(BaseModel):
    kind: str = Field('file', const=True, title='Kind')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    content: str = Field(..., title='Content')
    file: Union[FileWithBytes, FileWithUri] = Field(..., title='File')


class JSONRPCErrorResponse(BaseModel):
    error: Union[
        JSONRPCError,
        JSONParseError,
        InvalidRequestError,
        MethodNotFoundError,
        InvalidParamsError,
        InternalError,
        TaskNotFoundError,
        TaskNotCancelableError,
        PushNotificationNotSupportedError,
        UnsupportedOperationError,
        ContentTypeNotSupportedError,
        InvalidAgentResponseError,
    ] = Field(..., title='Error')
    id: Optional[Union[str, int]] = Field(None, title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')


class AgentTrust(BaseModel):
    identity_provider: IdentityProvider = Field(
        ..., description='Identity provider used for authentication'
    )
    inherited_roles: Optional[List[KeycloakRole]] = Field(
        [],
        description="Roles inherited from the agent's creator",
        title='Inherited Roles',
    )
    certificate: Optional[str] = Field(
        None,
        description="Agent's security certificate for verification",
        title='Certificate',
    )
    certificate_fingerprint: Optional[str] = Field(
        None,
        description="Fingerprint of the agent's certificate",
        title='Certificate Fingerprint',
    )
    creator_id: Union[UUID, int, str] = Field(
        ..., description='ID of the user who created this agent', title='Creator Id'
    )
    creation_timestamp: str = Field(
        ...,
        description='ISO-8601 timestamp of agent creation',
        examples=['2023-10-27T10:00:00Z'],
        title='Creation Timestamp',
    )
    trust_verification_required: Optional[bool] = Field(
        True,
        description='Whether trust verification is required',
        title='Trust Verification Required',
    )
    allowed_operations: Optional[Dict[str, TrustLevel]] = Field(
        {},
        description='Operations this agent is allowed to perform with required trust levels',
        title='Allowed Operations',
    )


class Part(BaseModel):
    __root__: Union[TextPart, FilePart, DataPart] = Field(
        ..., description='Union type for all possible message parts', title='Part'
    )


class Artifact(BaseModel):
    artifact_id: UUID = Field(
        ..., description='Unique identifier for the artifact', title='Artifact Id'
    )
    name: Optional[str] = Field(None, title='Name')
    description: Optional[str] = Field(None, title='Description')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    parts: List[Part] = Field(..., title='Parts')


class TaskArtifactUpdateEvent(BaseModel):
    append: Optional[bool] = Field(None, title='Append')
    artifact: Artifact
    contextId: UUID = Field(..., title='Contextid')
    kind: str = Field('artifact-update', const=True, title='Kind')
    lastChunk: Optional[bool] = Field(None, title='Lastchunk')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    taskId: UUID = Field(..., title='Taskid')


class AgentManifest(BaseModel):
    agnt_id: Union[UUID, int, str] = Field(
        ...,
        description='The unique identifier of the agent',
        examples=['123e4567-e89b-12d3-a456-426614174000'],
        title='Agnt Id',
    )
    name: str = Field(
        ...,
        description='The name of the agent',
        examples=['Japanese Restaurant Reviewer Agent'],
        title='Name',
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of the agent's purpose and capabilities",
        title='Description',
    )
    user_id: Union[UUID, int, str] = Field(..., description='user', title='User Id')
    identity: AgentIdentity = Field(..., description='Agent identity information.')
    trust_config: Optional[AgentTrust] = Field(
        None, description='Trust configuration and inherited permissions'
    )
    capabilities: Optional[AgentCapabilities] = Field(
        None, description="Agent's capabilities and supported operations"
    )
    metrics: Optional[AgentMetrics] = Field(
        None, description='Agent usage and performance metrics'
    )
    num_history_sessions: Optional[int] = Field(None, title='Num History Sessions')
    storage: Optional[Dict[str, Any]] = Field(None, title='Storage')
    context: Optional[Dict[str, Any]] = Field(None, title='Context')
    extra_data: Optional[Dict[str, Any]] = Field(None, title='Extra Data')
    stream: Optional[bool] = Field(None, title='Stream')
    debug_mode: Optional[bool] = Field(False, title='Debug Mode')
    debug_level: Optional[DebugLevel] = Field(1, title='Debug Level')
    monitoring: Optional[bool] = Field(False, title='Monitoring')
    telemetry: Optional[bool] = Field(True, title='Telemetry')
    version: str = Field(..., examples=['1.0.0'], title='Version')


class Message(BaseModel):
    contextId: UUID = Field(..., title='Contextid')
    kind: str = Field('message', const=True, title='Kind')
    messageId: UUID = Field(..., title='Messageid')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    parts: List[Part] = Field(..., title='Parts')
    role: Role
    extra_data: Optional[Dict[str, Any]] = Field(None, title='Extra Data')


class MessageSendParams(BaseModel):
    configuration: Optional[MessageSendConfiguration] = None
    message: Message
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')


class TaskStatus(BaseModel):
    message: Optional[Message] = None
    state: TaskState
    timestamp: Optional[str] = Field(
        None,
        description='ISO-8601 timestamp of the task status update',
        examples=['2023-10-27T10:00:00Z'],
        title='Timestamp',
    )


class TaskStatusUpdateEvent(BaseModel):
    contextId: UUID = Field(..., title='Contextid')
    final: bool = Field(..., title='Final')
    kind: str = Field('status-update', const=True, title='Kind')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    status: TaskStatus
    taskId: UUID = Field(..., title='Taskid')


class SendMessageRequest(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    method: str = Field('message/send', const=True, title='Method')
    params: MessageSendParams


class SendStreamingMessageRequest(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    method: str = Field('message/stream', const=True, title='Method')
    params: MessageSendParams


class Task(BaseModel):
    artifacts: Optional[List[Artifact]] = Field(None, title='Artifacts')
    contextId: UUID = Field(..., title='Contextid')
    history: Optional[List[Message]] = Field(None, title='History')
    id: str = Field(..., title='Id')
    kind: str = Field('task', const=True, title='Kind')
    metadata: Optional[Dict[str, Any]] = Field(None, title='Metadata')
    status: TaskStatus


class SendMessageSuccessResponse(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    result: Union[Task, Message] = Field(..., title='Result')


class SendStreamingMessageSuccessResponse(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    result: Union[Task, Message, TaskStatusUpdateEvent, TaskArtifactUpdateEvent] = (
        Field(..., title='Result')
    )


class GetTaskSuccessResponse(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    result: Task


class CancelTaskSuccessResponse(BaseModel):
    id: UUID = Field(..., title='Id')
    jsonrpc: str = Field('2.0', const=True, title='Jsonrpc')
    result: Task


class JSONRPCResponse(BaseModel):
    __root__: Union[
        JSONRPCErrorResponse,
        SendMessageSuccessResponse,
        SendStreamingMessageSuccessResponse,
        GetTaskSuccessResponse,
        CancelTaskSuccessResponse,
        TrustVerificationResponse,
    ] = Field(
        ...,
        description='Union type for all JSON-RPC responses',
        title='JSONRPCResponse',
    )


class PebblingProtocol(BaseModel):
    Role: Optional[Role] = None
    RunMode: Optional[RunMode] = None
    AgentManifest: Optional[AgentManifest] = None
    AgentIdentity: Optional[AgentIdentity] = None
    AgentCapabilities: Optional[AgentCapabilities] = None
    AgentMetrics: Optional[AgentMetrics] = None
    AgentTrust: Optional[AgentTrust] = None
    MTLSConfiguration: Optional[MTLSConfiguration] = None
    IdentityProvider: Optional[IdentityProvider] = None
    KeycloakRole: Optional[KeycloakRole] = None
    TrustLevel: Optional[TrustLevel] = None
    TrustCategory: Optional[TrustCategory] = None
    TrustVerificationMethod: Optional[TrustVerificationMethod] = None
    TrustVerificationRequest: Optional[TrustVerificationRequest] = None
    TrustVerificationResponse: Optional[TrustVerificationResponse] = None
    TrustVerificationResult: Optional[TrustVerificationResult] = None
    TrustVerificationParams: Optional[TrustVerificationParams] = None
    Message: Optional[Message] = None
    MessageSendConfiguration: Optional[MessageSendConfiguration] = None
    MessageSendParams: Optional[MessageSendParams] = None
    Part: Optional[Part] = None
    TextPart: Optional[TextPart] = None
    FilePart: Optional[FilePart] = None
    DataPart: Optional[DataPart] = None
    FileWithBytes: Optional[FileWithBytes] = None
    FileWithUri: Optional[FileWithUri] = None
    Task: Optional[Task] = None
    TaskState: Optional[TaskState] = None
    TaskStatus: Optional[TaskStatus] = None
    Artifact: Optional[Artifact] = None
    TaskIdParams: Optional[TaskIdParams] = None
    TaskStatusUpdateEvent: Optional[TaskStatusUpdateEvent] = None
    TaskArtifactUpdateEvent: Optional[TaskArtifactUpdateEvent] = None
    NegotiationStatus: Optional[NegotiationStatus] = None
    NegotiationSessionStatus: Optional[NegotiationSessionStatus] = None
    NegotiationProposal: Optional[NegotiationProposal] = None
    NegotiationSession: Optional[NegotiationSession] = None
    PaymentActionType: Optional[PaymentActionType] = None
    PaymentStatus: Optional[PaymentStatus] = None
    PaymentMethod: Optional[PaymentMethod] = None
    BillingPeriod: Optional[BillingPeriod] = None
    PaymentAction: Optional[PaymentAction] = None
    JSONRPCError: Optional[JSONRPCError] = None
    JSONRPCErrorResponse: Optional[JSONRPCErrorResponse] = None
    JSONRPCResponse: Optional[JSONRPCResponse] = None
    SendMessageRequest: Optional[SendMessageRequest] = None
    SendStreamingMessageRequest: Optional[SendStreamingMessageRequest] = None
    GetTaskRequest: Optional[GetTaskRequest] = None
    CancelTaskRequest: Optional[CancelTaskRequest] = None
    TaskResubscriptionRequest: Optional[TaskResubscriptionRequest] = None
    SendMessageSuccessResponse: Optional[SendMessageSuccessResponse] = None
    SendStreamingMessageSuccessResponse: Optional[
        SendStreamingMessageSuccessResponse
    ] = None
    GetTaskSuccessResponse: Optional[GetTaskSuccessResponse] = None
    CancelTaskSuccessResponse: Optional[CancelTaskSuccessResponse] = None
    JSONParseError: Optional[JSONParseError] = None
    InvalidRequestError: Optional[InvalidRequestError] = None
    MethodNotFoundError: Optional[MethodNotFoundError] = None
    InvalidParamsError: Optional[InvalidParamsError] = None
    InternalError: Optional[InternalError] = None
    TaskNotFoundError: Optional[TaskNotFoundError] = None
    TaskNotCancelableError: Optional[TaskNotCancelableError] = None
    PushNotificationNotSupportedError: Optional[PushNotificationNotSupportedError] = (
        None
    )
    UnsupportedOperationError: Optional[UnsupportedOperationError] = None
    ContentTypeNotSupportedError: Optional[ContentTypeNotSupportedError] = None
    InvalidAgentResponseError: Optional[InvalidAgentResponseError] = None
