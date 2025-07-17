import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from acp_sdk.models.errors import ACPError, Error
from acp_sdk.models.platform import PlatformUIAnnotation
from acp_sdk.models.types import AgentName, ResourceUrl, RunId, SessionId
from acp_sdk.shared import ResourceLoader, ResourceStore


class Author(BaseModel):
    name: str
    email: str | None = None
    url: AnyUrl | None = None


class Contributor(BaseModel):
    name: str
    email: str | None = None
    url: AnyUrl | None = None


class LinkType(str, Enum):
    SOURCE_CODE = "source-code"
    CONTAINER_IMAGE = "container-image"
    HOMEPAGE = "homepage"
    DOCUMENTATION = "documentation"


class Link(BaseModel):
    type: LinkType
    url: AnyUrl


class DependencyType(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    MODEL = "model"


class Dependency(BaseModel):
    type: DependencyType
    name: str


class Capability(BaseModel):
    name: str
    description: str


class Annotations(BaseModel):
    beeai_ui: PlatformUIAnnotation | None = None
    model_config = ConfigDict(extra="allow")


class Metadata(BaseModel):
    annotations: Annotations | None = None
    documentation: str | None = None
    license: str | None = None
    programming_language: str | None = None
    natural_languages: list[str] | None = None
    framework: str | None = None
    capabilities: list[Capability] | None = None
    domains: list[str] | None = None
    tags: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author: Author | None = None
    contributors: list[Contributor] | None = None
    links: list[Link] | None = None
    dependencies: list[Dependency] | None = None
    recommended_models: list[str] | None = None

    model_config = ConfigDict(extra="allow")


class CitationMetadata(BaseModel):
    """
    Represents an inline citation, providing info about information source. This
    is supposed to be rendered as an inline icon, optionally marking a text
    range it belongs to.

    If CitationMetadata is included together with content in the message part,
    the citation belongs to that content and renders at the MessagePart position.
    This way may be used for non-text content, like images and files.

    Alternatively, `start_index` and `end_index` may define a text range,
    counting characters in the current Message across all MessageParts with
    content type `text/*`, where the citation will be rendered. If one of
    `start_index` and `end_index` is missing or their values are equal, the
    citation renders only as an inline icon at that position.

    If both `start_index` and `end_index` are not present and MessagePart has no
    content, the citation renders as inline icon only at the MessagePart position.

    Properties:
    - url: URL of the source document.
    - title: Title of the source document.
    - description: Accompanying text, which may be a general description of the
                   source document, or a specific snippet.
    """

    kind: Literal["citation"] = "citation"
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class TrajectoryMetadata(BaseModel):
    """
    Represents trajectory information for an agent's reasoning or tool execution
    steps. This metadata helps track the agent's decision-making process and
    provides transparency into how the agent arrived at its response.

    TrajectoryMetadata can capture either:
    1. A reasoning step with a message
    2. A tool execution with tool name, input, and output

    This information can be used for debugging, audit trails, and providing
    users with insight into the agent's thought process.

    Properties:
    - message: A reasoning step or thought in the agent's decision process.
    - tool_name: Name of the tool that was executed.
    - tool_input: Input parameters passed to the tool.
    - tool_output: Output or result returned by the tool.
    """

    kind: Literal["trajectory"] = "trajectory"
    message: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[BaseModel] = None
    tool_output: Optional[BaseModel] = None


class MessagePart(BaseModel):
    name: Optional[str] = None
    content_type: Optional[str] = "text/plain"
    content: Optional[str] = None
    content_encoding: Optional[Literal["plain", "base64"]] = "plain"
    content_url: Optional[AnyUrl] = None

    model_config = ConfigDict(extra="allow")

    metadata: Optional[CitationMetadata | TrajectoryMetadata] = Field(discriminator="kind", default=None)

    def model_post_init(self, __context: Any) -> None:
        if self.content is not None and self.content_url is not None:
            raise ValueError("Only one of content or content_url can be provided")


class Artifact(MessagePart):
    name: str


class Message(BaseModel):
    role: Literal["user"] | Literal["agent"] | str = Field("user", pattern=r"^(user|agent(\/[a-zA-Z0-9_\-]+)?)$")
    parts: list[MessagePart]
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __add__(self, other: "Message") -> "Message":
        if not isinstance(other, Message):
            raise TypeError(f"Cannot concatenate Message with {type(other).__name__}")
        if self.role != other.role:
            raise ValueError("Cannot concatenate messages with different roles")
        return Message(
            role=self.role,
            parts=self.parts + other.parts,
            created_at=min(self.created_at, other.created_at) if self.created_at and other.created_at else None,
            completed_at=max(self.completed_at, other.completed_at)
            if self.completed_at and other.completed_at
            else None,
        )

    def __str__(self) -> str:
        return "".join(
            part.content for part in self.parts if part.content is not None and part.content_type == "text/plain"
        )

    def compress(self) -> "Message":
        def can_be_joined(first: MessagePart, second: MessagePart) -> bool:
            return (
                first.name is None
                and second.name is None
                and first.content_type == "text/plain"
                and second.content_type == "text/plain"
                and first.content_encoding == "plain"
                and second.content_encoding == "plain"
                and first.content_url is None
                and second.content_url is None
            )

        def join(first: MessagePart, second: MessagePart) -> MessagePart:
            return MessagePart(
                name=None,
                content_type="text/plain",
                content=first.content + second.content,
                content_encoding="plain",
                content_url=None,
            )

        parts: list[MessagePart] = []
        for part in self.parts:
            if len(parts) > 0 and can_be_joined(parts[-1], part):
                parts[-1] = join(parts[-1], part)
            else:
                parts.append(part)
        return Message(parts=parts, created_at=self.created_at, completed_at=self.completed_at)


class RunMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    STREAM = "stream"


class RunStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in-progress"
    AWAITING = "awaiting"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        terminal_states = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
        return self in terminal_states


class MessageAwaitRequest(BaseModel):
    type: Literal["message"] = "message"
    message: Message


class MessageAwaitResume(BaseModel):
    type: Literal["message"] = "message"
    message: Message


AwaitRequest = Union[MessageAwaitRequest]
AwaitResume = Union[MessageAwaitResume]


class Run(BaseModel):
    run_id: RunId = Field(default_factory=uuid.uuid4)
    agent_name: AgentName
    session_id: SessionId | None = None
    status: RunStatus = RunStatus.CREATED
    await_request: AwaitRequest | None = None
    output: list[Message] = []
    error: Error | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    def raise_for_status(self) -> "Run":
        match self.status:
            case RunStatus.CANCELLED:
                raise asyncio.CancelledError()
            case RunStatus.FAILED:
                raise ACPError(error=self.error)
            case _:
                return self


class MessageCreatedEvent(BaseModel):
    type: Literal["message.created"] = "message.created"
    message: Message


class MessagePartEvent(BaseModel):
    type: Literal["message.part"] = "message.part"
    part: MessagePart


class ArtifactEvent(BaseModel):
    type: Literal["message.part"] = "message.part"
    part: Artifact


class MessageCompletedEvent(BaseModel):
    type: Literal["message.completed"] = "message.completed"
    message: Message


class RunAwaitingEvent(BaseModel):
    type: Literal["run.awaiting"] = "run.awaiting"
    run: Run


class GenericEvent(BaseModel):
    type: Literal["generic"] = "generic"
    generic: AnyModel


class RunCreatedEvent(BaseModel):
    type: Literal["run.created"] = "run.created"
    run: Run


class RunInProgressEvent(BaseModel):
    type: Literal["run.in-progress"] = "run.in-progress"
    run: Run


class RunFailedEvent(BaseModel):
    type: Literal["run.failed"] = "run.failed"
    run: Run


class RunCancelledEvent(BaseModel):
    type: Literal["run.cancelled"] = "run.cancelled"
    run: Run


class RunCompletedEvent(BaseModel):
    type: Literal["run.completed"] = "run.completed"
    run: Run


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    error: Error


Event = Union[
    ErrorEvent,
    RunCreatedEvent,
    RunInProgressEvent,
    MessageCreatedEvent,
    ArtifactEvent,
    MessagePartEvent,
    MessageCompletedEvent,
    RunAwaitingEvent,
    GenericEvent,
    RunCancelledEvent,
    RunFailedEvent,
    RunCompletedEvent,
]


class InputContentTypes(BaseModel):
    types: list[str]


class OutputContentTypes(BaseModel):
    types: list[str]


class AgentManifest(BaseModel):
    name: str
    description: str | None = None
    metadata: Metadata = Metadata()
    input_content_types: list[str] = Field(default_factory=lambda: ["*/*"])
    output_content_types: list[str] = Field(default_factory=lambda: ["*/*"])


class Session(BaseModel):
    id: SessionId = Field(default_factory=uuid.uuid4)
    history: list[ResourceUrl] = Field(default_factory=list)
    state: ResourceUrl | None = None

    loader: SkipJsonSchema[ResourceLoader | None] = Field(None, exclude=True)
    store: SkipJsonSchema[ResourceStore | None] = Field(None, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def load_history(self, *, loader: ResourceLoader | None = None) -> AsyncIterator[Message]:
        loader = loader or self.loader or ResourceLoader()
        for url in self.history:
            data = await loader.load(url)
            yield Message.model_validate_json(data)

    async def load_state(self, *, loader: ResourceLoader | None = None) -> bytes:
        loader = loader or self.loader or ResourceLoader()
        data = await loader.load(self.state)
        return data

    async def store_state(self, data: bytes, *, store: ResourceStore | None = None) -> ResourceUrl:
        store = store or self.store
        if not store:
            raise ValueError("Store must be specified")

        id = uuid.uuid4()
        await store.store(id, data)
        return await store.url(id)
