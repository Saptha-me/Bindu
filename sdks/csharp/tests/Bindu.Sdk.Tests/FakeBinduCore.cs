using Bindu.Grpc;
using Grpc.Core;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using System.Net;
using static Bindu.Grpc.BinduService;

namespace Bindu.Sdk.Tests;

/// <summary>
/// An in-process stand-in for the Bindu Python core. Hosts the <c>BinduService</c>
/// gRPC contract on a dynamically assigned port so tests never touch the real core.
/// </summary>
public sealed class FakeBinduCore : IAsyncDisposable {
    private readonly WebApplication _app;

    /// <summary>Captures the most recent registration request the SDK sent.</summary>
    public RegisterAgentRequest? LastRegisterRequest { get; private set; }

    /// <summary>Captures the most recent unregister request the SDK sent.</summary>
    public UnregisterAgentRequest? LastUnregisterRequest { get; private set; }

    /// <summary>Captures the most recent heartbeat request the SDK sent.</summary>
    public HeartbeatRequest? LastHeartbeatRequest { get; set; }

    /// <summary>Total number of heartbeat requests received.</summary>
    public int HeartbeatCount { get; private set; }

    /// <summary>
    /// When <c>true</c>, the fake core rejects heartbeats with an <c>RpcException</c>
    /// so the SDK's heartbeat error handling is exercised.
    /// </summary>
    public bool RejectHeartbeats { get; set; }

    /// <summary>Whether RegisterAgent should succeed. Set to <c>false</c> to test failure paths.</summary>
    public bool RegisterSucceeds { get; set; } = true;

    /// <summary>Error text returned when <see cref="RegisterSucceeds"/> is <c>false</c>.</summary>
    public string RegisterError { get; set; } = "registration rejected by test";

    /// <summary>Agent ID the fake core assigns on successful registration.</summary>
    public string AgentId { get; set; } = "agent-0001";

    /// <summary>DID the fake core assigns on successful registration.</summary>
    public string Did { get; set; } = "did:bindu:test";

    /// <summary>A2A URL the fake core assigns on successful registration.</summary>
    public string AgentUrl { get; set; } = "http://localhost:3773";

    /// <summary>The port the fake core is listening on.</summary>
    public int Port { get; }

    /// <summary>Base address (including trailing slash) of the fake core.</summary>
    public string Address => $"http://localhost:{Port}/";

    private FakeBinduCore(WebApplication app, int port) {
        _app = app;
        Port = port;
    }

    /// <summary>
    /// Starts the fake core on a dynamically assigned free port.
    /// </summary>
    public static async Task<FakeBinduCore> StartAsync() {
        var core = new FakeBinduCorePlaceholder();
        var builder = WebApplication.CreateBuilder();

        builder.WebHost.ConfigureKestrel(options => {
            options.Listen(IPAddress.Any, 0, listenOptions => {
                listenOptions.Protocols = HttpProtocols.Http2;
            });
        });

        builder.Services.AddSingleton(core);
        builder.Services.AddGrpc();

        var app = builder.Build();
        app.MapGrpcService<FakeBinduCoreService>();

        await app.StartAsync();

        var addressFeature = app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>();
        var address = addressFeature?.Addresses.FirstOrDefault() ?? throw new InvalidOperationException("No server address");
        var port = new Uri(address).Port;

        var instance = new FakeBinduCore(app, port);
        core.Instance = instance;
        return instance;
    }

    public async ValueTask DisposeAsync() {
        await _app.StopAsync();
        await _app.DisposeAsync();
    }

    /// <summary>Wiring helper so the gRPC service can reach the owning core instance.</summary>
    private sealed class FakeBinduCorePlaceholder {
        public FakeBinduCore? Instance { get; set; }
    }

    private sealed class FakeBinduCoreService : BinduServiceBase {
        private readonly FakeBinduCorePlaceholder _core;

        public FakeBinduCoreService(FakeBinduCorePlaceholder core) {
            _core = core;
        }

        public override Task<RegisterAgentResponse> RegisterAgent(RegisterAgentRequest request, ServerCallContext context) {
            var core = _core.Instance!;
            core.LastRegisterRequest = request;
            return Task.FromResult(new RegisterAgentResponse {
                Success = core.RegisterSucceeds,
                Error = core.RegisterSucceeds ? "" : core.RegisterError,
                AgentId = core.AgentId,
                Did = core.Did,
                AgentUrl = core.AgentUrl
            });
        }

        public override Task<HeartbeatResponse> Heartbeat(HeartbeatRequest request, ServerCallContext context) {
            var core = _core.Instance!;
            core.LastHeartbeatRequest = request;
            core.HeartbeatCount++;
            if (core.RejectHeartbeats) {
                throw new RpcException(new Status(StatusCode.Unavailable, "core not accepting heartbeats"));
            }
            return Task.FromResult(new HeartbeatResponse {
                Acknowledged = true,
                ServerTimestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            });
        }

        public override Task<UnregisterAgentResponse> UnregisterAgent(UnregisterAgentRequest request, ServerCallContext context) {
            var core = _core.Instance!;
            core.LastUnregisterRequest = request;
            return Task.FromResult(new UnregisterAgentResponse { Success = true });
        }
    }
}

/// <summary>
/// A <see cref="CoreLauncher"/> stub that never spawns a real core process.
/// Used to run <see cref="BinduAgent.Bindufy"/> against <see cref="FakeBinduCore"/>.
/// </summary>
internal sealed class NoOpCoreLauncher : CoreLauncher {
    public override Task LaunchBinduServer() => Task.CompletedTask;
}
