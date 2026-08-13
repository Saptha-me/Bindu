using Xunit;

// Several tests probe for a free port and then immediately bind it (GrpcServer port
// selection, WaitForPortAsync timeout). Running test classes in parallel could let
// another test steal the probed port in between, so keep execution serial.
[assembly: CollectionBehavior(DisableTestParallelization = true)]
