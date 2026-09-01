using Bindu.Grpc;
using Grpc.Core;
using static Bindu.Grpc.BinduService;

namespace Bindu.Sdk {
    /// <summary>
    /// Sends periodic heartbeats to the Bindu core so it knows the registered agent
    /// process is still alive.
    /// </summary>
    internal class HeartbeatService {

        private Timer? _timer;
        private BinduServiceClient? _binduClient;

        /// <summary>
        /// Starts sending heartbeats to the core every 30 seconds.
        /// </summary>
        /// <param name="regInfo">The agent's registration result (used for the agent ID).</param>
        /// <param name="client">gRPC client connected to the Bindu core.</param>
        public HeartbeatService(RegistrationResult regInfo, BinduServiceClient client)
            : this(regInfo, client, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30)) { }

        /// <summary>
        /// Starts sending heartbeats with a custom schedule. Used by the test suite to
        /// run a heartbeat without waiting 30 seconds.
        /// </summary>
        internal HeartbeatService(RegistrationResult regInfo, BinduServiceClient client, TimeSpan dueTime, TimeSpan period) {
            _timer = new Timer(HeartBeat, regInfo, dueTime, period);
            _binduClient = client;
        }

        /// <summary>
        /// Sends a single heartbeat for the registered agent and logs the core's response.
        /// </summary>
        /// <param name="state">The <see cref="RegistrationResult"/> passed to the timer.</param>
        private async void HeartBeat(object? state) {
            try {
                if (state == null) {
                    throw new RpcException(new Status(StatusCode.Internal, ""));
                }
                RegistrationResult info = (RegistrationResult)state;

                var heartbeatRequest = new HeartbeatRequest {
                    AgentId = info.AgentId,
                    Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
                };

                var response = await SendHeartBeat(heartbeatRequest);
                Console.WriteLine($"[bindu-sdk:heartbeat]: Acknowledged: {response.Acknowledged}, TimeStamp: {response.ServerTimestamp}");
            }
            catch (RpcException ex) {
                Console.WriteLine($"[bindu-sdk:err] Heartbeat failed: {ex.Status.Detail}");
                Console.WriteLine($"[bindu-sdk:err] Heartbeat failed: {ex.Message}");
            }
            catch (Exception ex) {
                Console.WriteLine($"[bindu-sdk:err] Heartbeat unexpected error: {ex.Message}");
                Console.WriteLine($"[bindu-sdk:err] Heartbeat unexpected error: {ex.StackTrace}");
            }
        }

        /// <summary>Sends a heartbeat request over gRPC and returns the core's response.</summary>
        private async Task<HeartbeatResponse> SendHeartBeat(HeartbeatRequest heartbeatRequest) {

            var response = await _binduClient!.HeartbeatAsync(heartbeatRequest, new CallOptions());
            return response;
        }

        /// <summary>Stops the heartbeat timer.</summary>
        public void CleanUp() {
            _timer?.Dispose();
            _timer = null;
        }

    }


}
