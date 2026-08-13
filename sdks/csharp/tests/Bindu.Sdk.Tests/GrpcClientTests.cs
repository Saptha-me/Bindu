using System.Text.Json;

namespace Bindu.Sdk.Tests;

public class GrpcClientTests {
    private static AgentConfig TestConfig() => new() {
        Author = "dev@example.com",
        Name = "json-agent",
        Description = "Agent that tests JSON",
        DeploymentUrl = "http://localhost:9000",
        ExposeDeployment = true
    };

    private static async Task<(GrpcServer server, GrpcClient client)> CreateClientAsync(FakeBinduCore core) {
        // A real callback server so the registration carries a real callback address.
        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>("ok"), TestConfig());
        var client = new GrpcClient(core.Address);
        client.InitializeBinduClient(server);
        return (server, client);
    }

    [Fact]
    public async Task RegisterAgent_Sends_Correct_Json_And_Callback_Address() {
        await using var core = await FakeBinduCore.StartAsync();
        var (server, client) = await CreateClientAsync(core);
        try {
            var response = await client.RegisterAgent(TestConfig());

            Assert.NotNull(response);
            Assert.True(response!.Success);
            Assert.Equal("agent-0001", response.AgentId);

            var request = core.LastRegisterRequest;
            Assert.NotNull(request);
            Assert.Equal($"localhost:{server.GetPort}", request!.GrpcCallbackAddress);

            using var doc = JsonDocument.Parse(request.ConfigJson);
            var root = doc.RootElement;

            Assert.Equal("dev@example.com", root.GetProperty("author").GetString());
            Assert.Equal("json-agent", root.GetProperty("name").GetString());
            Assert.Equal("Agent that tests JSON", root.GetProperty("description").GetString());
            Assert.Equal("http://localhost:9000", root.GetProperty("deployment").GetProperty("url").GetString());
            Assert.True(root.GetProperty("deployment").GetProperty("expose").GetBoolean());
            Assert.Equal("agent", root.GetProperty("kind").GetString());
        }
        finally {
            server.StopServerAsync();
        }
    }

    [Fact]
    public async Task RegisterAgent_Throws_When_Core_Rejects() {
        await using var core = await FakeBinduCore.StartAsync();
        core.RegisterSucceeds = false;
        core.RegisterError = "config validation failed";

        var (server, client) = await CreateClientAsync(core);
        try {
            var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => client.RegisterAgent(TestConfig()));
            Assert.Contains("config validation failed", ex.Message);
        }
        finally {
            server.StopServerAsync();
        }
    }

    [Fact]
    public async Task RegisterAgent_Returns_Null_Before_Initialize() {
        var client = new GrpcClient("http://localhost:1/");
        var response = await client.RegisterAgent(TestConfig());
        Assert.Null(response);
    }

    [Fact]
    public async Task UnRegisterAgent_Sends_AgentId_To_Core() {
        await using var core = await FakeBinduCore.StartAsync();
        var (server, client) = await CreateClientAsync(core);
        try {
            var regResult = new RegistrationResult("agent-0001", "did:bindu:test", "http://localhost:3773");

            var response = client.UnRegisterAgent(regResult);

            Assert.NotNull(response);
            Assert.True(response!.Success);
            Assert.Equal("agent-0001", core.LastUnregisterRequest?.AgentId);
        }
        finally {
            server.StopServerAsync();
        }
    }
}
