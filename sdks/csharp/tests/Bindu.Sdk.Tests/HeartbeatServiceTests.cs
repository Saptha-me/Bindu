using Bindu.Grpc;
using Grpc.Net.Client;
using static Bindu.Grpc.BinduService;

namespace Bindu.Sdk.Tests;

public class HeartbeatServiceTests {
    [Fact]
    public async Task Heartbeat_Is_Sent_To_Core_With_AgentId() {
        await using var core = await FakeBinduCore.StartAsync();
        var channel = GrpcChannel.ForAddress(core.Address);
        var client = new BinduServiceClient(channel);

        var regInfo = new RegistrationResult("agent-0001", "did:bindu:test", "http://localhost:3773");
        // Fire the first heartbeat almost immediately so the test doesn't wait 30s.
        var heartbeat = new HeartbeatService(regInfo, client, dueTime: TimeSpan.FromMilliseconds(200), period: TimeSpan.FromSeconds(30));
        try {
            await WaitForHeartbeatAsync(core, TimeSpan.FromSeconds(5));

            Assert.NotNull(core.LastHeartbeatRequest);
            Assert.Equal("agent-0001", core.LastHeartbeatRequest!.AgentId);
            Assert.True(core.LastHeartbeatRequest.Timestamp > 0);
        }
        finally {
            heartbeat.CleanUp();
            channel.Dispose();
        }
    }

    [Fact]
    public async Task CleanUp_Stops_Heartbeats() {
        await using var core = await FakeBinduCore.StartAsync();
        var channel = GrpcChannel.ForAddress(core.Address);
        var client = new BinduServiceClient(channel);

        var regInfo = new RegistrationResult("agent-0002", "did:bindu:test", "http://localhost:3773");
        var heartbeat = new HeartbeatService(regInfo, client, dueTime: TimeSpan.FromMilliseconds(100), period: TimeSpan.FromMilliseconds(100));
        try {
            // Let at least one heartbeat through, then stop the timer.
            await WaitForHeartbeatAsync(core, TimeSpan.FromSeconds(5));
            heartbeat.CleanUp();

            // Absorb any in-flight callback, then verify no further heartbeats arrive.
            await Task.Delay(300);
            var countAfterFirstDrain = core.HeartbeatCount;
            await Task.Delay(400);

            Assert.Equal(countAfterFirstDrain, core.HeartbeatCount);
        }
        finally {
            heartbeat.CleanUp();
            channel.Dispose();
        }
    }

    [Fact]
    public async Task Rejected_Heartbeat_Is_Handled_Without_Throwing() {
        await using var core = await FakeBinduCore.StartAsync();
        core.RejectHeartbeats = true;
        var channel = GrpcChannel.ForAddress(core.Address);
        var client = new BinduServiceClient(channel);

        var regInfo = new RegistrationResult("agent-0003", "did:bindu:test", "http://localhost:3773");
        var heartbeat = new HeartbeatService(regInfo, client, dueTime: TimeSpan.FromMilliseconds(200), period: TimeSpan.FromSeconds(30));
        try {
            // A rejected heartbeat must be caught and logged by the SDK, never surfaced.
            await WaitForAttemptedHeartbeatAsync(core, TimeSpan.FromSeconds(5));
            Assert.True(core.HeartbeatCount > 0);
        }
        finally {
            heartbeat.CleanUp();
            channel.Dispose();
        }
    }

    private static async Task WaitForHeartbeatAsync(FakeBinduCore core, TimeSpan timeout) {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline) {
            if (core.LastHeartbeatRequest is not null) {
                return;
            }
            await Task.Delay(50);
        }
    }

    private static async Task WaitForAttemptedHeartbeatAsync(FakeBinduCore core, TimeSpan timeout) {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline) {
            if (core.HeartbeatCount > 0) {
                return;
            }
            await Task.Delay(50);
        }
    }
}
