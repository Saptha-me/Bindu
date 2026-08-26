"""
Research Paper Agent — Scrapes arXiv and discusses research papers.

Runs on port 3778. Uses arXiv's public Atom API (no key required).
"""

import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from bindu.penguin.bindufy import bindufy

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# arXiv Atom namespace
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


# ── Query keyword extraction ───────────────────────────────────

_STRIP_PHRASES = re.compile(
    r"(?i)\b(find|search|show|get|fetch|look up|look for|recent|latest|papers?|"
    r"research|articles?|studies|study|on|about|related to|regarding|in the field of|"
    r"journal|publication|me|please|can you|could you|i want|i need|give)\b"
)


def _extract_query(user_message: str) -> str:
    """Extract the core topic from a user message."""
    cleaned = _STRIP_PHRASES.sub("", user_message)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,!?")
    return cleaned if cleaned else user_message.strip()


# ── arXiv Fetching ─────────────────────────────────────────────

def _fetch_arxiv_papers(query: str, max_results: int = 5) -> list[dict]:
    """Fetch papers from the arXiv API and return a list of paper dicts."""
    encoded_query = urllib.parse.quote(query)
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query=all:{encoded_query}"
        f"&start=0&max_results={max_results}"
        f"&sortBy=relevance&sortOrder=descending"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BinduResearchAgent/1.0 (research assistant)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read().decode("utf-8")
    except Exception as e:
        return [{"error": str(e)}]

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        return [{"error": f"XML parse error: {e}"}]

    papers = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        title_el = entry.find(f"{{{ATOM_NS}}}title")
        summary_el = entry.find(f"{{{ATOM_NS}}}summary")
        published_el = entry.find(f"{{{ATOM_NS}}}published")
        id_el = entry.find(f"{{{ATOM_NS}}}id")

        authors = [
            a.find(f"{{{ATOM_NS}}}name").text
            for a in entry.findall(f"{{{ATOM_NS}}}author")
            if a.find(f"{{{ATOM_NS}}}name") is not None
        ]

        title = (title_el.text or "").replace("\n", " ").strip() if title_el is not None else "Unknown"
        abstract = (summary_el.text or "").strip() if summary_el is not None else ""
        published = (published_el.text or "")[:10] if published_el is not None else "Unknown"
        arxiv_url = (id_el.text or "").strip() if id_el is not None else ""

        # Categories (tags)
        categories = [
            c.get("term", "")
            for c in entry.findall(f"{{{ATOM_NS}}}category")
        ]

        papers.append({
            "title": title,
            "authors": authors,
            "published": published,
            "abstract": abstract,
            "url": arxiv_url,
            "categories": categories,
        })

    return papers


# ── Discussion Generation ──────────────────────────────────────

def _shorten_abstract(abstract: str, max_sentences: int = 3) -> str:
    """Return the first N sentences of an abstract."""
    sentences = re.split(r"(?<=[.!?])\s+", abstract.strip())
    return " ".join(sentences[:max_sentences])


def _format_authors(authors: list[str]) -> str:
    """Format author list nicely."""
    if not authors:
        return "Unknown authors"
    if len(authors) == 1:
        return authors[0]
    if len(authors) <= 3:
        return ", ".join(authors)
    return f"{authors[0]}, {authors[1]}, et al."


def _generate_discussion(query: str, papers: list[dict]) -> str:
    """Build the rich discussion report."""

    report = f"## 📚 Research Paper Agent — Discussion Report\n\n"
    report += f"**Query:** *{query}*\n\n"

    if not papers:
        report += "❌ No papers found. Try a different search term.\n"
        return report

    if papers and "error" in papers[0]:
        report += f"⚠️ **Error fetching papers:** {papers[0]['error']}\n"
        report += "Please check your internet connection.\n"
        return report

    report += f"Found **{len(papers)} paper(s)**. Here's a detailed discussion:\n\n"
    report += "---\n\n"

    # ── Individual paper summaries ─────────────────────────────
    all_categories: list[str] = []

    for i, p in enumerate(papers, 1):
        year = p["published"][:4] if len(p.get("published", "")) >= 4 else "?"
        authors_str = _format_authors(p["authors"])
        short_abstract = _shorten_abstract(p["abstract"])
        cats = ", ".join(p.get("categories", [])[:3]) or "General"
        all_categories.extend(p.get("categories", []))

        report += f"### {i}. {p['title']}\n"
        report += f"**Authors:** {authors_str}  \n"
        report += f"**Published:** {p['published']}  &nbsp;|&nbsp; **Field:** {cats}\n\n"

        if short_abstract:
            report += f"> {short_abstract}\n\n"

        if p.get("url"):
            report += f"🔗 [Read on arXiv]({p['url']})\n\n"

        report += "---\n\n"

    # ── Thematic synthesis ─────────────────────────────────────
    report += "### 🔍 Thematic Discussion\n\n"

    # Collect recurring categories
    cat_counts: dict[str, int] = {}
    for cat in all_categories:
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    top_cats = sorted(cat_counts, key=lambda c: cat_counts[c], reverse=True)[:5]

    if top_cats:
        report += "**Dominant research areas:**\n"
        for cat in top_cats:
            report += f"  - `{cat}` ({cat_counts[cat]} paper{'s' if cat_counts[cat] > 1 else ''})\n"
        report += "\n"

    # Year range
    years = [
        int(p["published"][:4])
        for p in papers
        if len(p.get("published", "")) >= 4 and p["published"][:4].isdigit()
    ]
    if years:
        report += f"**Publication range:** {min(years)}–{max(years)}\n\n"

    # Abstract keywords
    combined_abstracts = " ".join(p.get("abstract", "") for p in papers).lower()
    highlight_keywords = []
    for kw in ["deep learning", "neural network", "large language model", "transformer",
                "reinforcement learning", "generative", "diffusion", "attention", "bert",
                "gpt", "vision", "graph", "quantum", "optimization", "benchmark", "dataset"]:
        if kw in combined_abstracts:
            highlight_keywords.append(kw)

    if highlight_keywords:
        report += "**Recurring technical themes:**  \n"
        report += "  " + "  ·  ".join(f"`{k}`" for k in highlight_keywords[:8]) + "\n\n"

    # ── Reading recommendations ────────────────────────────────
    report += "### 📖 Suggested Reading Order\n\n"
    for i, p in enumerate(papers, 1):
        year = p['published'][:4] if len(p.get('published', '')) >= 4 else '?'
        report += f"{i}. **{p['title'][:80]}{'…' if len(p['title']) > 80 else ''}** ({year})\n"
    report += "\n"

    # ── What to look for ──────────────────────────────────────
    report += "### 💡 Key Questions These Papers Address\n\n"
    questions = [
        f"What novel approaches are being proposed for **{query}**?",
        "How do the methodologies compare across papers?",
        "What datasets or benchmarks are commonly used?",
        "What are the reported limitations and future work directions?",
        "Which paper has the most practical real-world applications?",
    ]
    for q in questions:
        report += f"- {q}\n"

    report += f"\n*Research report generated by Research Paper Agent v1.0 · Source: arXiv*\n"
    return report


# ── Handler ────────────────────────────────────────────────────

def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Process research paper requests."""
    user_message = messages[-1].get("content", "") if messages else ""
    lower = user_message.lower()

    # Check if user wants a specific number of results
    num_match = re.search(r"\b(\d+)\s*papers?\b", lower)
    max_results = min(int(num_match.group(1)), 10) if num_match else 5

    query = _extract_query(user_message)
    if not query or len(query) < 2:
        query = "machine learning"  # sensible default

    papers = _fetch_arxiv_papers(query, max_results=max_results)
    discussion = _generate_discussion(query, papers)

    return [{"role": "assistant", "content": discussion}]


# ── Agent Config ───────────────────────────────────────────────

config = {
    "author": "naresh@example.com",
    "name": "research_paper_agent",
    "description": "Searches for and discusses academic research papers from arXiv on any topic.",
    "deployment": {"url": "http://localhost:3778", "expose": True},
    "skills": [str(PROJECT_ROOT / "skills" / "research-papers")],
}

if __name__ == "__main__":
    bindufy(config, handler)
