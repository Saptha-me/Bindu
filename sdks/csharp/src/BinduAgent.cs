using Bindu.Grpc;

namespace Bindu.Sdk {
    /// <summary>
    /// Entry point for the Bindu .NET SDK.
    /// </summary>
    /// <remarks>
    /// Call <see cref="Bindufy(AgentConfig, Func{IReadOnlyList{ChatMessage}, Task{object}})"/>
    /// to launch the Bindu core and register an agent that can handle incoming tasks.
    /// Dispose the instance (or let the process exit) to unregister the agent and shut
    /// everything down cleanly.
    /// </remarks>
    /// <example>
    /// <code>
    /// var bindu = new BinduAgent();
    /// var config = new AgentConfig { Author = "dev@example.com", Name = "my-agent", Description = "..." };
    /// var result = await bindu.Bindufy(config, HandleMessages);
    /// Console.WriteLine(result.AgentId);
    /// </code>
    /// </example>
    public class BinduAgent : IDisposable, IAsyncDisposable {
        private CoreLauncher? _launcher;
        private RegistrationResult? _registrationResult;
        private HeartbeatService? _heartbeatService;
        private GrpcServer? _grpcServer;
        private GrpcClient? _grpcClient;
        private readonly CoreLauncher? _injectedLauncher;
        private readonly string? _coreAddress;

        /// <summary>
        /// Creates a new Bindu SDK instance.
        /// </summary>
        /// <remarks>
        /// Call <see cref="Bindufy(AgentConfig, Func{IReadOnlyList{ChatMessage}, Task{object}})"/>
        /// to launch the Bindu core and register an agent.
        /// </remarks>
        public BinduAgent() { }

        /// <summary>
        /// Creates a Bindu SDK instance with an injected launcher and core address.
        /// Used by the test suite to run against an in-process fake core.
        /// </summary>
        internal BinduAgent(CoreLauncher launcher, string coreAddress) {
            _injectedLauncher = launcher;
            _coreAddress = coreAddress;
        }


        /// <summary>
        /// Launches the Bindu core, starts the agent's gRPC callback server, and registers
        /// the agent with the core.
        /// </summary>
        /// <remarks>
        /// This method blocks until registration is complete. Afterwards it starts a
        /// heartbeat service (every 30 seconds) so the core knows the agent is alive, and
        /// hooks up process-exit and Ctrl+C handlers that unregister the agent and shut
        /// down cleanly.
        /// </remarks>
        /// <param name="config">Configuration describing the agent to register.</param>
        /// <param name="handler">
        /// Delegate invoked by the core whenever a task arrives. It receives the full
        /// conversation history and must return either a <see cref="string"/> or a
        /// <see cref="BinduResponse"/>.
        /// </param>
        /// <returns>A <see cref="RegistrationResult"/> with the agent's assigned ID, DID, and URL.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when the Bindu core cannot be found or started, or when the core rejects
        /// the agent registration.
        /// </exception>
        /// <exception cref="TimeoutException">Thrown when the core does not start within the allotted time.</exception>
        public async Task<RegistrationResult> Bindufy(AgentConfig config, Func<IReadOnlyList<ChatMessage>, Task<object>> handler) {

            //TODO: Verify the config files if needed before starting up all the server

            var launcher = _injectedLauncher ?? new CoreLauncher();
            var grpcServer = new GrpcServer(config.GrpcCallbackPort);
            var grpcClient = new GrpcClient(_coreAddress ?? "http://localhost:3774/");

            await launcher.LaunchBinduServer();
            await grpcServer.StartServerAsync(handler, config);
            await CoreLauncher.WaitForPortAsync(grpcServer.GetPort);
            var binduClient = grpcClient.InitializeBinduClient(grpcServer);
            var response = await grpcClient.RegisterAgent(config);
            var regResult = new RegistrationResult(response?.AgentId ?? "", response?.Did ?? "", response?.AgentUrl ?? "");
            _registrationResult = regResult;

            var heartBeat = new HeartbeatService(regResult, binduClient);

            AppDomain.CurrentDomain.ProcessExit += OnApplicationShutdown;
            Console.CancelKeyPress += Console_CancelKeyPress;

            //Assign all class Fields for shutdown handling
            _launcher = launcher;
            _heartbeatService = heartBeat;
            _grpcServer = grpcServer;
            _grpcClient = grpcClient;

            return regResult;
        }

        private void Console_CancelKeyPress(object? sender, ConsoleCancelEventArgs e) {
            e.Cancel = true;
            Console.WriteLine("\n[bindu-sdk] Shutting down...");
            CleanUp();
            Environment.Exit(0);
        }

        private void OnApplicationShutdown(object? sender, EventArgs e) {
            Console.WriteLine("\n[bindu-sdk] Shutting down...");
            CleanUp();
        }

        private void CleanUp() {
            _grpcClient?.UnRegisterAgent(_registrationResult!);
            _launcher?.CleanUp();
            _grpcServer?.StopServerAsync();
            _heartbeatService?.CleanUp();
        }

        /// <summary>
        /// Unregisters the agent from the core, stops the callback server and heartbeat
        /// service, and terminates the Bindu core process.
        /// </summary>
        public void Dispose() {
            CleanUp();
        }

        /// <inheritdoc cref="Dispose"/>
        public ValueTask DisposeAsync() {
            CleanUp();
            return new ValueTask();
        }

    }

    /// <summary>
    /// Configuration describing an agent to register with the Bindu core.
    /// </summary>
    public class AgentConfig {
        /// <summary>
        /// Creates an empty agent configuration.
        /// </summary>
        /// <remarks>
        /// The <see cref="Author"/>, <see cref="Name"/>, and <see cref="Description"/>
        /// properties are required and must be set before passing this to
        /// <see cref="BinduAgent.Bindufy(AgentConfig, Func{IReadOnlyList{ChatMessage}, Task{object}})" />.
        /// </remarks>
        public AgentConfig() { }

        /// <summary>Email address of the agent's author.</summary>
        public required string Author { get; set; }
        /// <summary>Name of the agent. Returned by the agent's capabilities response.</summary>
        public required string Name { get; set; }
        /// <summary>Human-readable description of what the agent does.</summary>
        public required string Description { get; set; }
        /// <summary>
        /// Port the SDK's gRPC callback server listens on. Use <c>0</c> to let the SDK
        /// pick a free port automatically.
        /// </summary>
        public int GrpcCallbackPort { get; set; } = 0;
        /// <summary>Base URL of the Bindu deployment server.</summary>
        public string DeploymentUrl { get; set; } = "http://localhost:3773";
        /// <summary>Whether the agent's deployment should be exposed publicly.</summary>
        public bool ExposeDeployment { get; set; } = false;
        /// <summary>
        /// Skills associated with this agent. Reserved for future use — skills are not yet
        /// transmitted to the core during registration.
        /// </summary>
        public string[] Skills { get; set; } = [];

        /// <summary>Optional version string for this agent. Defaults to "0.1.0".</summary>
        public string? Version { get; set; }

    }


    /// <summary>
    /// Describes a successfully registered agent: its assigned ID, DID, and endpoint URL.
    /// </summary>
    /// <param name="agentId">The unique identifier (UUID) assigned to the agent by the Bindu core.</param>
    /// <param name="did">The W3C Decentralized Identifier (DID) assigned to the agent.</param>
    /// <param name="agentUrl">The A2A HTTP endpoint URL where the agent can be reached.</param>
    public class RegistrationResult(string agentId, string did, string agentUrl) {
        /// <summary>Gets the unique identifier (UUID) assigned to the agent by the Bindu core.</summary>
        public string AgentId { get; } = agentId;

        /// <summary>Gets the W3C Decentralized Identifier (DID) assigned to the agent.</summary>
        public string Did { get; } = did;

        /// <summary>Gets the A2A HTTP endpoint URL where the agent can be reached (e.g. <c>http://localhost:3773</c>).</summary>
        public string AgentUrl { get; } = agentUrl;
    }
}
