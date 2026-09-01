using Bindu.Sdk;

namespace Bindu.Sdk.Tests;

public class BinduResponseTests {
    [Fact]
    public void Defaults_Are_Empty() {
        var response = new BinduResponse();

        Assert.Equal("", response.Content);
        Assert.Equal("", response.State);
        Assert.Equal("", response.Prompt);
        Assert.NotNull(response.Metadata);
        Assert.Empty(response.Metadata);
    }

    [Fact]
    public void Properties_Are_Settable() {
        var response = new BinduResponse {
            Content = "Hello!",
            State = "input-required",
            Prompt = "Which topic?",
            Metadata = { ["source"] = "test" }
        };

        Assert.Equal("Hello!", response.Content);
        Assert.Equal("input-required", response.State);
        Assert.Equal("Which topic?", response.Prompt);
        Assert.Equal("test", response.Metadata["source"]);
    }
}
