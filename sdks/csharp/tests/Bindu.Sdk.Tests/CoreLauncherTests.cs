using System.Net;
using System.Net.Sockets;

namespace Bindu.Sdk.Tests;

public class CoreLauncherTests {
    [Fact]
    public async Task WaitForPortAsync_Completes_When_Port_Is_Open() {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        try {
            var port = ((IPEndPoint)listener.LocalEndpoint).Port;
            // Should return promptly because something is already listening.
            await CoreLauncher.WaitForPortAsync(port, timeoutMs: 5000);
        }
        finally {
            listener.Stop();
        }
    }

    [Fact]
    public async Task WaitForPortAsync_Throws_Timeout_When_Port_Never_Opens() {
        // Grab a free port by binding and releasing it.
        var probe = new TcpListener(IPAddress.Loopback, 0);
        probe.Start();
        var freePort = ((IPEndPoint)probe.LocalEndpoint).Port;
        probe.Stop();

        var ex = await Assert.ThrowsAsync<TimeoutException>(() =>
            CoreLauncher.WaitForPortAsync(freePort, timeoutMs: 1500));

        Assert.Contains(freePort.ToString(), ex.Message);
    }
}
