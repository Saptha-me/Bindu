"""Tests for GrpcAgentClient — the callable that replaces manifest.run."""

from unittest.mock import MagicMock, patch


from bindu.grpc.client import GrpcAgentClient
from bindu.grpc.generated import agent_handler_pb2


class TestGrpcAgentClient:
    """Test GrpcAgentClient behavior as a manifest.run replacement."""

    def test_init(self):
        """Test client initialization stores address and timeout."""
        client = GrpcAgentClient("localhost:50052", timeout=15.0)
        assert client._address == "localhost:50052"
        assert client._timeout == 15.0
        assert client._channel is None
        assert client._stub is None

    def test_repr(self):
        """Test string representation."""
        client = GrpcAgentClient("localhost:50052", timeout=30.0)
        assert "localhost:50052" in repr(client)
        assert "30.0" in repr(client)

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_plain_string_response(self, mock_stub_class, mock_channel):
        """Test that plain text response returns str (maps to 'completed')."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="Hello from agent",
            state="",
            prompt="",
        )

        client = GrpcAgentClient("localhost:50052")
        result = client([{"role": "user", "content": "Hi"}])

        assert isinstance(result, str)
        assert result == "Hello from agent"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_input_required_response(self, mock_stub_class, mock_channel):
        """Test that input-required state returns dict with state key."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="",
            state="input-required",
            prompt="Can you clarify?",
        )

        client = GrpcAgentClient("localhost:50052")
        result = client([{"role": "user", "content": "Do something"}])

        assert isinstance(result, dict)
        assert result["state"] == "input-required"
        assert result["prompt"] == "Can you clarify?"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_auth_required_response(self, mock_stub_class, mock_channel):
        """Test that auth-required state returns dict with state key."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="",
            state="auth-required",
            prompt="Please authenticate",
        )

        client = GrpcAgentClient("localhost:50052")
        result = client([{"role": "user", "content": "Secret data"}])

        assert isinstance(result, dict)
        assert result["state"] == "auth-required"
        assert result["prompt"] == "Please authenticate"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_response_with_metadata(self, mock_stub_class, mock_channel):
        """Test that metadata from response is included in result dict."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub

        response = agent_handler_pb2.HandleResponse(
            content="Processing",
            state="input-required",
            prompt="Which format?",
        )
        response.metadata["source"] = "test"
        mock_stub.HandleMessages.return_value = response

        client = GrpcAgentClient("localhost:50052")
        result = client([{"role": "user", "content": "Convert"}])

        assert isinstance(result, dict)
        assert result["source"] == "test"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_messages_converted_to_proto(self, mock_stub_class, mock_channel):
        """Test that input messages are correctly converted to proto format."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="ok", state=""
        )

        client = GrpcAgentClient("localhost:50052")
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        client(messages)

        # Verify the proto request was constructed correctly
        call_args = mock_stub.HandleMessages.call_args
        request = call_args[0][0]
        assert len(request.messages) == 3
        assert request.messages[0].role == "system"
        assert request.messages[0].content == "You are helpful"
        assert request.messages[1].role == "user"
        assert request.messages[2].role == "assistant"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_a2a_messages_flattened_at_wire_boundary(
        self, mock_stub_class, mock_channel
    ):
        """Raw A2A messages (with parts) flatten to {role, content} proto.

        ManifestWorker now passes A2A messages through verbatim; this client
        is the one place that still needs chat format (the proto ChatMessage
        has no parts field). Text parts collapse to content, file parts get
        text-extracted, and the A2A "agent" role maps to "assistant".
        """
        import base64

        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="ok", state=""
        )

        client = GrpcAgentClient("localhost:50052")
        messages = [
            {"role": "system", "content": "You are helpful"},
            {
                "role": "user",
                "kind": "message",
                "parts": [{"kind": "text", "text": "Read this file"}],
            },
            {
                "role": "agent",
                "kind": "message",
                "parts": [{"kind": "text", "text": "Sure, send it over"}],
            },
            {
                "role": "user",
                "kind": "message",
                "parts": [
                    {
                        "kind": "file",
                        "file": {
                            "bytes": base64.b64encode(b"file body").decode(),
                            "mimeType": "text/plain",
                            "name": "notes.txt",
                        },
                    }
                ],
            },
        ]
        client(messages)

        request = mock_stub.HandleMessages.call_args[0][0]
        assert len(request.messages) == 4
        assert request.messages[0].role == "system"
        assert request.messages[0].content == "You are helpful"
        assert request.messages[1].role == "user"
        assert request.messages[1].content == "Read this file"
        assert request.messages[2].role == "assistant"
        assert request.messages[2].content == "Sure, send it over"
        assert request.messages[3].role == "user"
        assert "file body" in request.messages[3].content

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_a2a_system_message_keeps_system_role(self, mock_stub_class, mock_channel):
        """The A2A-shaped injected system prompt reaches the wire as 'system'."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="ok", state=""
        )

        client = GrpcAgentClient("localhost:50052")
        client(
            [
                {
                    "role": "system",
                    "kind": "message",
                    "parts": [{"kind": "text", "text": "Respond in JSON."}],
                },
                {
                    "role": "user",
                    "kind": "message",
                    "parts": [{"kind": "text", "text": "hi"}],
                },
            ]
        )

        request = mock_stub.HandleMessages.call_args[0][0]
        assert len(request.messages) == 2
        assert request.messages[0].role == "system"
        assert request.messages[0].content == "Respond in JSON."
        assert request.messages[1].role == "user"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_lazy_connection(self, mock_stub_class, mock_channel):
        """Test that gRPC channel is not created until first call."""
        client = GrpcAgentClient("localhost:50052")
        assert client._channel is None

        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="ok", state=""
        )

        client([{"role": "user", "content": "test"}])
        mock_channel.assert_called_once()

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_health_check_healthy(self, mock_stub_class, mock_channel):
        """Test health check returns True for healthy agent."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HealthCheck.return_value = agent_handler_pb2.HealthCheckResponse(
            healthy=True, message="OK"
        )

        client = GrpcAgentClient("localhost:50052")
        assert client.health_check() is True

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_health_check_unhealthy(self, mock_stub_class, mock_channel):
        """Test health check returns False on gRPC error."""
        import grpc as grpc_module

        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HealthCheck.side_effect = grpc_module.RpcError()

        client = GrpcAgentClient("localhost:50052")
        assert client.health_check() is False

    def test_close(self):
        """Test close cleans up channel and stub."""
        client = GrpcAgentClient("localhost:50052")
        mock_channel = MagicMock()
        client._channel = mock_channel
        client._stub = MagicMock()

        client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stub is None

    def test_close_when_not_connected(self):
        """Test close is safe when not connected."""
        client = GrpcAgentClient("localhost:50052")
        client.close()  # Should not raise

    def test_init_streaming_mode(self):
        """Test client can be initialized in streaming mode."""
        client = GrpcAgentClient("localhost:50052", timeout=15.0, use_streaming=True)
        assert client._use_streaming is True
        assert "streaming" in repr(client)

    def test_init_unary_mode_default(self):
        """Test client defaults to unary mode."""
        client = GrpcAgentClient("localhost:50052")
        assert client._use_streaming is False
        assert "unary" in repr(client)

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_streaming_response_returns_generator(self, mock_stub_class, mock_channel):
        """Test that streaming mode returns a generator (has __next__)."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub

        # Simulate a streaming response (iterable of HandleResponse)
        mock_stub.HandleMessagesStream.return_value = iter(
            [
                agent_handler_pb2.HandleResponse(
                    content="chunk 1", state="", is_final=False
                ),
                agent_handler_pb2.HandleResponse(
                    content="chunk 2", state="", is_final=False
                ),
                agent_handler_pb2.HandleResponse(
                    content="final answer", state="", is_final=True
                ),
            ]
        )

        client = GrpcAgentClient("localhost:50052", use_streaming=True)
        result = client([{"role": "user", "content": "Hello"}])

        # Result should be a generator (has __next__)
        assert hasattr(result, "__next__")

        # Drain the generator — simulates what ResultProcessor.collect_results() does
        chunks = list(result)
        assert len(chunks) == 3
        assert chunks[0] == "chunk 1"
        assert chunks[1] == "chunk 2"
        assert chunks[2] == "final answer"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_streaming_response_with_state_transition(
        self, mock_stub_class, mock_channel
    ):
        """Test streaming where final chunk has a state transition."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub

        mock_stub.HandleMessagesStream.return_value = iter(
            [
                agent_handler_pb2.HandleResponse(
                    content="thinking...", state="", is_final=False
                ),
                agent_handler_pb2.HandleResponse(
                    content="",
                    state="input-required",
                    prompt="What format?",
                    is_final=True,
                ),
            ]
        )

        client = GrpcAgentClient("localhost:50052", use_streaming=True)
        result = client([{"role": "user", "content": "Process data"}])

        chunks = list(result)
        assert len(chunks) == 2
        assert chunks[0] == "thinking..."
        assert isinstance(chunks[1], dict)
        assert chunks[1]["state"] == "input-required"
        assert chunks[1]["prompt"] == "What format?"

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_streaming_calls_correct_rpc(self, mock_stub_class, mock_channel):
        """Test streaming mode calls HandleMessagesStream, not HandleMessages."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessagesStream.return_value = iter([])

        client = GrpcAgentClient("localhost:50052", use_streaming=True)
        result = client([{"role": "user", "content": "Hi"}])
        # Drain the generator to trigger the call
        list(result)

        mock_stub.HandleMessagesStream.assert_called_once()
        mock_stub.HandleMessages.assert_not_called()

    @patch("bindu.grpc.client.grpc.insecure_channel")
    @patch("bindu.grpc.client.agent_handler_pb2_grpc.AgentHandlerStub")
    def test_unary_calls_correct_rpc(self, mock_stub_class, mock_channel):
        """Test unary mode calls HandleMessages, not HandleMessagesStream."""
        mock_stub = MagicMock()
        mock_stub_class.return_value = mock_stub
        mock_stub.HandleMessages.return_value = agent_handler_pb2.HandleResponse(
            content="ok", state=""
        )

        client = GrpcAgentClient("localhost:50052", use_streaming=False)
        client([{"role": "user", "content": "Hi"}])

        mock_stub.HandleMessages.assert_called_once()
        mock_stub.HandleMessagesStream.assert_not_called()
