using Bindu.Grpc;
using Grpc.Core;
using static Bindu.Grpc.AgentHandler;

namespace Bindu.Sdk {

    // HandleMessagesStream is intentionally not overridden.
    // The base class returns gRPC UNIMPLEMENTED status, which is correct —
    // streaming is not implemented in the TS or Kotlin SDKs either.
    // See: docs/grpc/limitations.md

    /// <summary>
    /// gRPC service hosted by the SDK that the Bindu core calls to deliver tasks, query
    /// capabilities, and check liveness.
    /// </summary>
    internal class AgentHandler : AgentHandlerBase {
        private Func<IReadOnlyList<ChatMessage>, Task<object>> _handler;
        private readonly AgentConfig _config;

        /// <summary>
        /// Creates a handler backed by the developer's delegate and the agent configuration.
        /// </summary>
        /// <param name="handler">Delegate that processes incoming conversation history.</param>
        /// <param name="config">Agent configuration used for capabilities and health responses.</param>
        public AgentHandler(Func<IReadOnlyList<ChatMessage>, Task<object>> handler, AgentConfig config) {
            _handler = handler;
            _config = config;
        }

        /// <summary>
        /// Executes the developer's handler with the conversation history and maps the
        /// result (a <see cref="string"/> or <see cref="BinduResponse"/>) onto a
        /// <see cref="HandleResponse"/>.
        /// </summary>
        /// <param name="request">The conversation history sent by the Bindu core.</param>
        /// <param name="context">The gRPC call context.</param>
        /// <returns>A response containing the agent's content and optional state transition.</returns>
        public override async Task<HandleResponse> HandleMessages(HandleRequest request, ServerCallContext context) {
            try {
                var messages = request.Messages.ToArray();
                var resp = await _handler(messages);
                var response = new HandleResponse { IsFinal = true };
                if (resp is string text) {
                    response.Content = text;
                    response.State = "";
                }
                else if (resp is BinduResponse binduResp) {
                    response.Content = binduResp.Content;
                    response.State = binduResp.State;
                    response.Prompt = binduResp.Prompt;
                    foreach (var kv in binduResp.Metadata)
                        response.Metadata[kv.Key] = kv.Value;
                }

                return response;
            }
            catch (Exception ex) {
                // Stack traces contain CR/LF which are illegal in HTTP/2 header (trailer)
                // values — Kestrel rejects the response with HTTP 500. Flatten them first.
                var stackTrace = (ex.StackTrace ?? "no stack trace").Replace("\r", " ").Replace("\n", " ");
                var trailers = new Metadata {
                    { "exception-type", ex.GetType().Name },
                    { "stack-trace", stackTrace }
                };
                throw new RpcException(new Status(StatusCode.Internal, ex.Message), trailers);
            }
        }

        /// <summary>Returns the agent's name, description, version, and supported modes.</summary>
        public override Task<GetCapabilitiesResponse> GetCapabilities(GetCapabilitiesRequest request, ServerCallContext context) {
            return Task.FromResult(new GetCapabilitiesResponse {
                Name = _config.Name,
                Description = _config.Description,
                Version = _config.Version ?? "0.1.0",
                SupportsStreaming = false
            });
        }

        /// <summary>Reports that the agent process is alive and responsive.</summary>
        public override Task<HealthCheckResponse> HealthCheck(HealthCheckRequest request, ServerCallContext context) {
            return Task.FromResult(new HealthCheckResponse {
                Healthy = true,
                Message = $"{_config.Name} is healthy"
            });
        }
    }
}
