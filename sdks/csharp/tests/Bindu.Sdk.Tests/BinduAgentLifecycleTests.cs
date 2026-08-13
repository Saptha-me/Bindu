using Bindu.Sdk;

namespace Bindu.Sdk.Tests;

public class BinduAgentLifecycleTests {
    [Fact]
    public void Dispose_Before_Bindufy_Does_Not_Throw() {
        using var bindu = new BinduAgent();
        bindu.Dispose();
    }

    [Fact]
    public void Dispose_Can_Be_Called_Twice() {
        var bindu = new BinduAgent();
        bindu.Dispose();
        bindu.Dispose();
    }

    [Fact]
    public async Task DisposeAsync_Before_Bindufy_Does_Not_Throw() {
        await using var bindu = new BinduAgent();
        await bindu.DisposeAsync();
    }
}
