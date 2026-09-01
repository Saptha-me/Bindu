using Bindu.Grpc;
using Grpc.Core;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using System.Net;
using System.Net.Sockets;


namespace Bindu.Sdk {

    /// <summary>
    /// ASP.NET Core gRPC server that hosts the agent's <see cref="AgentHandler"/> so the
    /// Bindu core can deliver tasks to the SDK.
    /// </summary>
    internal class GrpcServer {
        private int _port = 0; //default value
        private int _usedPort = 0;
        private WebApplication? _app;

        /// <summary>Gets the actual port the callback server is listening on (0 until started).</summary>
        public int GetPort => _usedPort;

        /// <summary>
        /// Creates a server configuration for the given port.
        /// </summary>
        /// <param name="port">
        /// Port to listen on, or <c>0</c> to let the OS pick a free port. If the requested
        /// port is already in use, a free port is chosen automatically.
        /// </param>
        public GrpcServer(int port) {
            if (port != 0 && IsPortInUse(port)) {
                Console.WriteLine($"[bindu-sdk] Port {port} is in use, picking a free port automatically.");
                _port = 0;
                return;
            }
            _port = port;
        }

        /// <summary>
        /// Starts the gRPC callback server (HTTP/2) with the given handler and agent config.
        /// </summary>
        /// <param name="handler">Delegate that processes incoming conversation history.</param>
        /// <param name="config">Agent configuration used by the handler service.</param>
        public async Task StartServerAsync(Func<IReadOnlyList<ChatMessage>, Task<object>> handler, AgentConfig config) {

            var builder = WebApplication.CreateBuilder();

            builder.Services.AddSingleton(handler);
            builder.Services.AddSingleton(config);

            builder.WebHost.ConfigureKestrel(options => {
                options.Listen(IPAddress.Any, _port, listenOptions => {
                    listenOptions.Protocols = HttpProtocols.Http2;
                });
            });

            builder.Services.AddGrpc();

            var app = builder.Build();

            app.MapGrpcService<AgentHandler>();

            await app.StartAsync();
            _app = app;

            var addressFeature = _app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>();
            var address = addressFeature?.Addresses.FirstOrDefault();
            _usedPort = new Uri(address!).Port;
        }

        /// <summary>Stops and disposes the underlying web application.</summary>
        public async void StopServerAsync() {
            if (_app is not null) {
                await _app.StopAsync();
                await _app.DisposeAsync();
                _app = null;
            }
        }

        /// <summary>Checks whether a TCP connection can be established to the given port.</summary>
        /// <param name="port">Port to probe.</param>
        /// <returns><c>true</c> if something is already listening on the port.</returns>
        private static bool IsPortInUse(int port) {
            try {
                using var client = new TcpClient();
                client.Connect("localhost", port);

                return true; // connected = something is already there
            }
            catch (SocketException) {
                return false; // connection refused = port is free
            }
        }
    }
}
