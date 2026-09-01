namespace Bindu.Sdk {
    /// <summary>
    /// Return this from your handler instead of a plain string when you need
    /// to signal a state transition back to the caller.
    /// </summary>
    public class BinduResponse {
        /// <summary>
        /// Creates an empty response.
        /// </summary>
        /// <remarks>
        /// Set <see cref="Content"/> (and optionally <see cref="State"/>, <see cref="Prompt"/>,
        /// and <see cref="Metadata"/>) before returning it from your handler.
        /// </remarks>
        public BinduResponse() { }

        /// <summary>The response text to return to the caller.</summary>
        public string Content { get; set; } = "";

        /// <summary>
        /// State transition signal. Use "input-required" to ask the user a
        /// follow-up question, or "auth-required" to request authentication.
        /// Leave empty for a normal completed response.
        /// </summary>
        public string State { get; set; } = "";

        /// <summary>Follow-up prompt shown to the user when State is set.</summary>
        public string Prompt { get; set; } = "";

        /// <summary>Optional key-value metadata to include in the response.</summary>
        public Dictionary<string, string> Metadata { get; set; } = [];
    }
}
