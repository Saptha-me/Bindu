using System.Diagnostics;
using System.Net.Sockets;


namespace Bindu.Sdk {
    /// <summary>
    /// Locates a Bindu installation (bindu, uv, or python3) and launches the core with
    /// its gRPC server enabled on port 3774.
    /// </summary>
    internal class CoreLauncher {

        private int _grpcPort = 3774;
        private Process? _process;

        /// <summary>
        /// Starts the Bindu core process and waits until its gRPC port is accepting
        /// connections.
        /// </summary>
        /// <exception cref="InvalidOperationException">
        /// Thrown when neither bindu, uv, nor python3 can be found, or when the process
        /// fails to start.
        /// </exception>
        /// <exception cref="TimeoutException">
        /// Thrown when the core does not open its gRPC port within the wait window.
        /// </exception>
        public virtual async Task LaunchBinduServer() {
            var binduPath = FindBinduExecutable();
            var command = "";
            var argsList = Array.Empty<string>();

            if (binduPath != null) {
                command = binduPath;
                argsList = [ "serve", "--grpc", "--grpc-port", _grpcPort.ToString() ];
            }
            else if (IsUvInstalled()) {
                command = "uv";
                argsList = ["run", "bindu", "serve", "--grpc", "--grpc-port", _grpcPort.ToString()];
            }
            else if(IsPython3Installed()) {
                command = "python3";
                argsList = ["-m", "bindu.cli", "serve", "--grpc", "--grpc-port", _grpcPort.ToString()];
            }
            else {
                throw new InvalidOperationException("Cannot find bindu, uv, or python3. Ensure at least one is installed.");
            }

            var processInfo = new ProcessStartInfo {
                FileName = command,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            for (int i = 0; i < argsList.Length; i++) {
                processInfo.ArgumentList.Add(argsList[i]);
            }

            Console.WriteLine($"[bindu-sdk] Starting Bindu core: {command} {string.Join(" ", argsList)}");
            var binduProcess = Process.Start(processInfo) ?? throw new InvalidOperationException("Failed to start Bindu core process.");
            _process = binduProcess;

            binduProcess.Exited += BinduProcess_Exited;

            binduProcess.EnableRaisingEvents = true;

            binduProcess.OutputDataReceived += (sender, e) => {
                if (e.Data != null) Console.WriteLine($"[bindu-core] {e.Data}");
            };
            binduProcess.ErrorDataReceived += (s, e) => {
                if (e.Data != null) Console.WriteLine($"[bindu-core:err] {e.Data}");
            };
            binduProcess.BeginOutputReadLine();
            binduProcess.BeginErrorReadLine();


            await WaitForPortAsync(_grpcPort);
            Console.WriteLine("[bindu-sdk] Core is ready and accepting registrations.");
        }

        private void BinduProcess_Exited(object? sender, EventArgs e) {
            Console.WriteLine($"[bindu-sdk] Bindu core exited unexpectedly with code {_process!.ExitCode}");
            CleanUp();
        }

        /// <summary>Kills and disposes the Bindu core process if one was started.</summary>
        public void CleanUp() {
            _process?.Kill(entireProcessTree: true);
            _process?.Dispose();
            _process = null;
        }

        /// <summary>
        /// Polls <paramref name="host"/>:<paramref name="port"/> until a TCP connection
        /// succeeds or the timeout elapses.
        /// </summary>
        /// <param name="port">TCP port to probe.</param>
        /// <param name="host">Host to probe (defaults to localhost).</param>
        /// <param name="timeoutMs">Maximum time to wait, in milliseconds.</param>
        /// <exception cref="TimeoutException">Thrown when the port never opens within the timeout.</exception>
        public static async Task WaitForPortAsync(int port, string host = "localhost", int timeoutMs = 30000) {
            using var cts = new CancellationTokenSource(timeoutMs);

            while (!cts.IsCancellationRequested) {
                try {
                    using var client = new TcpClient();

                    await client.ConnectAsync(host, port, cts.Token);

                    return;
                }
                catch (SocketException) {

                }
                catch (OperationCanceledException) {
                    break;
                }

                await Task.Delay(500, cts.Token);
            }
            throw new TimeoutException($"[bindu-sdk] Bindu core did not start within {timeoutMs / 1000}s on port {port}");
        }

        /// <summary>
        /// Resolves the full path of an executable on the PATH using <c>where.exe</c>
        /// (Windows) or <c>which</c> (Unix).
        /// </summary>
        /// <param name="executableName">Name of the executable to look up.</param>
        /// <returns>The first matching path, or <c>null</c> if the executable is not found.</returns>
        private static string? FindExecutable(string executableName) {
            var fileName = OperatingSystem.IsWindows() ? "where.exe" : "which";
            try {
                using var process = Process.Start(new ProcessStartInfo {
                    FileName = fileName,
                    Arguments = executableName,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                if (process == null) {
                    return null;
                }
                var path = process.StandardOutput.ReadToEnd();
                process.WaitForExit();

                if (process.ExitCode != 0) {
                    return null;
                }
                else if (string.IsNullOrWhiteSpace(path)) {
                    return null;
                }
                else {
                    return path.Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault();
                }
            }
            catch {
                return null;
            }
        }
        private static bool IsPython3Installed() => FindExecutable("python3") is not null;
        private static string? FindBinduExecutable() => FindExecutable("bindu");
        private static bool IsUvInstalled() => FindExecutable("uv") is not null;
    }
}
