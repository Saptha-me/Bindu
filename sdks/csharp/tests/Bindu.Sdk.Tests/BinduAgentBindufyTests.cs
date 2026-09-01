using Bindu.Grpc;
using System.Text.Json;

namespace Bindu.Sdk.Tests;

public class BinduAgentBindufyTests {
    private static AgentConfig TestConfig() => new() {
        Author = "dev@example.com",
        Name = "flow-agent",
        Description = "Agent exercising the full Bindufy flow",
        GrpcCallbackPort = 0,
        Version = "3.2.1"
    };

    private static Task<object> TestHandler(IReadOnlyList<ChatMessage> messages) =>
        Task.FromResult<object>($"Echo: {messages[^1].Content}");

    [Fact]
    public async Task Bindufy_Registers_And_Returns_Registration_Result() {
        await using var core = await FakeBinduCore.StartAsync();
        using var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var result = await bindu.Bindufy(TestConfig(), TestHandler);

        Assert.Equal("agent-0001", result.AgentId);
        Assert.Equal("did:bindu:test", result.Did);
        Assert.Equal("http://localhost:3773", result.AgentUrl);

        // The fake core must have received a well-formed registration.
        var request = core.LastRegisterRequest;
        Assert.NotNull(request);
        Assert.Matches(@"^localhost:\d+$", request!.GrpcCallbackAddress);

        using var doc = JsonDocument.Parse(request.ConfigJson);
        var root = doc.RootElement;
        Assert.Equal("flow-agent", root.GetProperty("name").GetString());
        Assert.Equal("agent", root.GetProperty("kind").GetString());
    }

    [Fact]
    public async Task Bindufy_Throws_When_Core_Rejects_Registration() {
        await using var core = await FakeBinduCore.StartAsync();
        core.RegisterSucceeds = false;
        core.RegisterError = "duplicate agent name";

        using var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => bindu.Bindufy(TestConfig(), TestHandler));
        Assert.Contains("duplicate agent name", ex.Message);
    }

    [Fact]
    public async Task Dispose_Unregisters_Agent_With_The_Core() {
        await using var core = await FakeBinduCore.StartAsync();
        var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var result = await bindu.Bindufy(TestConfig(), TestHandler);

        bindu.Dispose();

        Assert.Equal("agent-0001", core.LastUnregisterRequest?.AgentId);
    }

    [Fact]
    public async Task Dispose_Async_Unregisters_Agent_With_The_Core() {
        await using var core = await FakeBinduCore.StartAsync();
        await using var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var result = await bindu.Bindufy(TestConfig(), TestHandler);
        await bindu.DisposeAsync();

        Assert.Equal("agent-0001", core.LastUnregisterRequest?.AgentId);
    }
}
