"""
PDF Research Agent Example for Bindu

This example agent accepts either a PDF file path or raw text and
returns a structured summary. It demonstrates how to wrap a simple
document-processing workflow using `bindufy()` so the agent becomes
a live service.

Prerequisites
-------------
    uv add bindu agno pypdf python-dotenv

Usage
-----
    export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
    python pdf_research_agent.py

The agent will be live at http://localhost:3775
Send it an A2A message whose parts carry either an inline PDF file part:
    {"kind": "file", "text": "paper.pdf",
     "file": {"bytes": "<base64>", "mimeType": "application/pdf", "name": "paper.pdf"}}
or a text part with a PDF path or raw document text.
"""
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv
import base64
import io
import os

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Helper — extract text from a PDF path or pass raw text straight through
# ---------------------------------------------------------------------------

def _read_content(source: str) -> str:
    """Return plain text from a PDF file path, or the source string itself."""
    if source.strip().endswith(".pdf") and os.path.isfile(source.strip()):
        try:
            from pypdf import PdfReader  # optional dependency
            reader = PdfReader(source.strip())
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
            if len(text.strip()) < 100:
                return f"PDF file '{source.strip()}' appears to be empty or contains very little text."
            return text
        except ImportError:
            return (
                f"[pypdf not installed — cannot read '{source.strip()}'. "
                "Run: uv add pypdf]"
            )
        except Exception as e:
            return f"Error reading PDF '{source.strip()}': {str(e)}"
    return source  # treat as raw document text


def _read_pdf_bytes(data: bytes) -> str:
    """Return plain text extracted from an in-memory PDF (inline file part)."""
    try:
        from pypdf import PdfReader  # optional dependency
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages)
        if len(text.strip()) < 100:
            return "Attached PDF appears to be empty or contains very little text."
        return text
    except ImportError:
        return "[pypdf not installed — cannot read the attached PDF. Run: uv add pypdf]"
    except Exception as e:
        return f"Error reading attached PDF: {str(e)}"


# ---------------------------------------------------------------------------
# 2. Agent definition
# ---------------------------------------------------------------------------

agent = Agent(
    instructions=(
        "You are a research assistant that reads documents and produces clear, "
        "concise summaries. When given document text:\n"
        "  1. Identify the main topic or thesis.\n"
        "  2. List the key findings or arguments (3-5 bullet points).\n"
        "  3. Note any important conclusions or recommendations.\n"
        "Be factual and brief. If the text is too short or unclear, say so."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
    markdown=True,  # Enable markdown formatting for better output
)


# ---------------------------------------------------------------------------
# 3. Bindu configuration
# ---------------------------------------------------------------------------

config = {
    "author": "your.email@example.com",
    "name": "pdf_research_agent",
    "description": "Summarises PDF files and document text using OpenRouter.",
    "version": "1.0.0",
    "capabilities": {
        "file_processing": ["pdf"],
        "text_analysis": ["summarization", "research"],
        "streaming": False
    },
     "skills": ["skills/pdf-research-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
}


# ---------------------------------------------------------------------------
# 4. Handler — the bridge between Bindu messages and the agent
# ---------------------------------------------------------------------------

def handler(messages: list[dict[str, str]]):
    """
    Receive a conversation history from Bindu, extract the latest user
    message, read its content (PDF or raw text), and return a summary.

    Args:
        messages: Raw A2A message list; the latest user message's parts carry
                  an inline PDF file part, a PDF path, or raw document text.

    Returns:
        Agent response with the document summary.
    """
    try:
        # Grab the most recent user message
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return "No user message found. Please send a PDF path or document text."

        parts = user_messages[-1].get("parts", [])
        user_input = " ".join(
            p.get("text", "") for p in parts if p.get("kind") == "text"
        ).strip()
        pdf_bytes = next(
            (
                (p.get("file") or {}).get("bytes")
                for p in parts
                if p.get("kind") == "file"
                and (p.get("file") or {}).get("mimeType") == "application/pdf"
                and (p.get("file") or {}).get("bytes")
            ),
            None,
        )

        if pdf_bytes:
            document_text = _read_pdf_bytes(base64.b64decode(pdf_bytes))
        elif user_input:
            document_text = _read_content(user_input)
        else:
            return "Empty message received. Please attach a PDF or provide a path/document text."

        # Check if document processing failed
        if document_text.startswith("[") or document_text.startswith("Error"):
            return document_text

        # Limit document size to prevent token overflow
        if len(document_text) > 50000:
            document_text = document_text[:50000] + "\n\n[Document truncated for processing...]"

        # Build a prompt that includes the full document text
        prompt = f"Summarize the following document and highlight the key insights:\n\n{document_text}"
        enriched_messages = [{"role": "user", "content": prompt}]

        result = agent.run(input=enriched_messages)
        return result

    except Exception as e:
        return f"Error processing request: {str(e)}"


# ---------------------------------------------------------------------------
# 5. Bindu-fy the agent — one call turns it into a live microservice
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🚀 PDF Research Agent running at http://localhost:3773")
    print("📄 Send PDF paths or paste document text to get summaries")
    print("🔧 Example: {\"role\": \"user\", \"content\": \"/path/to/paper.pdf\"}")
    bindufy(config, handler)
