using Bindu.Sdk;

namespace Bindu.Sdk.Tests;

public class RegistrationResultTests {
    [Fact]
    public void Constructor_Assigns_Values() {
        var result = new RegistrationResult("agent-123", "did:bindu:abc", "http://localhost:3773");

        Assert.Equal("agent-123", result.AgentId);
        Assert.Equal("did:bindu:abc", result.Did);
        Assert.Equal("http://localhost:3773", result.AgentUrl);
    }
}
