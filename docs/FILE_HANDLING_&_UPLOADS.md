# File Handling & Uploads

When a client uploads a file, your handler receives the real bytes. Bindu stores the uploaded A2A file part verbatim in task history and passes it through to your handler untouched — base64 payload, MIME type, and filename intact. Your agent decides what to do with them: parse a PDF, feed an image to a vision model, or hand the bytes to a downstream tool.

This matters because flattening files to text destroys information. A framework cannot know whether your agent wants extracted text, raw bytes for a vision model, or the original file for re-upload — so it doesn't guess.

## Upload Request Format

Files travel as A2A `FilePart` entries inside `message/send`. The file payload is nested under `file` — not at the top level of the part:

```json
{
  "jsonrpc": "2.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "message/send",
  "params": {
    "message": {
      "messageId": "550e8400-e29b-41d4-a716-446655440001",
      "contextId": "550e8400-e29b-41d4-a716-446655440002",
      "taskId": "550e8400-e29b-41d4-a716-446655440003",
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Please summarize this document."
        },
        {
          "kind": "file",
          "text": "report.pdf",
          "file": {
            "bytes": "JVBERi0xLjQK...<base64>...",
            "mimeType": "application/pdf",
            "name": "report.pdf"
          }
        }
      ]
    }
  }
}
```

The `text` field on the file part is currently required by request validation; use the filename.

## Reading Files in a Python Handler

Your handler receives the full A2A message history. Find file parts and decode:

```python
import base64


def handler(messages):
    last = messages[-1]
    for part in last.get("parts", []):
        if part.get("kind") == "file":
            file_obj = part["file"]
            raw = base64.b64decode(file_obj.get("bytes", ""))
            name = file_obj.get("name", "upload")
            mime = file_obj.get("mimeType", "")
            # raw is the exact uploaded content — parse, embed, or forward it.
    ...
```

Byte integrity is guaranteed end to end: what the client base64-encoded is exactly what `b64decode` returns in your handler.

## gRPC (SDK) Agents Get Extracted Text

The gRPC wire format (`ChatMessage`) only carries `{role, content}` strings, so file parts are flattened at that boundary — and only there:

- `application/pdf`, `text/plain`, and `.docx` payloads are decoded and their text is injected into `content` as a `--- Document Uploaded ---` block.
- Other MIME types (images included) arrive as an `[Unsupported file type: ...]` placeholder — binary cannot cross the current proto.
- A `FileWithUri` part without inline bytes arrives as `[File reference not fetched: <uri>]`; the core does not download URIs.

If your agent needs raw file bytes, write it as a Python handler for now; carrying parts over the proto is a planned protocol change (see [gRPC limitations](./grpc/limitations.md)).

## Security Considerations

- Treat uploaded bytes as untrusted input: cap sizes, validate MIME types against what your agent actually supports, and sandbox parsers.
- Keep parser dependencies (pypdf, python-docx, image libraries) updated for security patches.
- Reject unsupported formats early with a clear validation error rather than deep in your pipeline.

## Related Documentation

- [Streaming](./STREAMING.md)
- [Storage](./STORAGE.md)
- [Authentication](./AUTHENTICATION.md)
