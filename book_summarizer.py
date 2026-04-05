#!/usr/bin/env python3
"""
Book Summarizer Pipeline
========================
A token-efficient book summarization tool using the Claude API.

Strategy:
  1. Extract text from PDF/EPUB/TXT
  2. Chunk the book into manageable sections (by chapter or fixed size)
  3. Use Haiku (cheap) for per-chunk extraction of key concepts, arguments, and examples
  4. Use Sonnet for final synthesis into a structured Obsidian-ready summary
  5. Optionally prepare a NotebookLM-ready source file

This avoids sending the entire book to an expensive model, saving 80-90% on tokens.

Usage:
  pip install anthropic pypdf ebooklib beautifulsoup4 python-dotenv
  export ANTHROPIC_API_KEY="sk-ant-..."
  python book_summarizer.py "path/to/book.pdf" --output "summary.md"

Author: Roberto's book summarization pipeline
"""

import os
import re
import sys
import json
import argparse
import textwrap
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Config:
    """Pipeline configuration with sensible defaults."""
    # Models — use Haiku for extraction (cheap), Sonnet for synthesis (smart)
    extraction_model: str = "claude-haiku-4-5-20251001"
    synthesis_model: str = "claude-sonnet-4-6"

    # Chunking
    chunk_size: int = 8000          # tokens ≈ chars / 4, so ~32k chars per chunk
    chunk_overlap: int = 500        # overlap to avoid losing context at boundaries

    # Token budgets per call
    extraction_max_tokens: int = 2000   # per-chunk extraction output
    synthesis_max_tokens: int = 4096    # final synthesis output

    # Output
    output_format: str = "obsidian"     # "obsidian" | "plain" | "notebooklm"
    include_notebooklm_source: bool = True

    # Cost tracking
    track_costs: bool = True


# ---------------------------------------------------------------------------
# Text Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(filepath)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append(f"[Page {i+1}]\n{text}")
    return "\n\n".join(pages)


def extract_text_from_epub(filepath: str) -> str:
    """Extract text from an EPUB file."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(filepath)
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if len(text.strip()) > 100:  # skip near-empty pages
            chapters.append(text)
    return "\n\n---\n\n".join(chapters)


def extract_text_from_txt(filepath: str) -> str:
    """Read plain text or markdown files."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_text(filepath: str) -> str:
    """Route to the correct extractor based on file extension."""
    ext = Path(filepath).suffix.lower()
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".epub": extract_text_from_epub,
        ".txt": extract_text_from_txt,
        ".md": extract_text_from_txt,
    }
    if ext not in extractors:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(extractors.keys())}")
    print(f"  Extracting text from {ext} file...")
    return extractors[ext](filepath)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def detect_chapters(text: str) -> list[dict]:
    """
    Try to split text by chapter headings. Falls back to fixed-size chunks.
    Returns list of {"title": str, "content": str}.
    """
    # Common chapter patterns
    chapter_patterns = [
        r"(?m)^(?:Chapter|CHAPTER)\s+\d+[.:)]\s*(.*)",
        r"(?m)^(?:Part|PART)\s+\w+[.:)]\s*(.*)",
        r"(?m)^#{1,2}\s+(.*)",  # Markdown headings
        r"(?m)^\d+\.\s+([A-Z].*)",  # "1. Title" format
    ]

    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, text))
        if len(matches) >= 3:  # need at least 3 chapters to be confident
            chapters = []
            for i, match in enumerate(matches):
                title = match.group(1).strip() if match.group(1) else f"Chapter {i+1}"
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                if len(content) > 200:  # skip tiny fragments
                    chapters.append({"title": title, "content": content})
            if chapters:
                print(f"  Detected {len(chapters)} chapters using pattern: {pattern[:40]}...")
                return chapters

    return []  # no chapters detected


def chunk_text(text: str, config: Config) -> list[dict]:
    """
    Split text into processable chunks. Tries chapter detection first,
    then falls back to fixed-size windowed chunking.
    """
    chapters = detect_chapters(text)
    if chapters:
        # If chapters are too large, sub-chunk them
        result = []
        for ch in chapters:
            char_limit = config.chunk_size * 4  # rough token-to-char ratio
            if len(ch["content"]) > char_limit:
                sub_chunks = _fixed_chunk(ch["content"], config)
                for j, sc in enumerate(sub_chunks):
                    result.append({
                        "title": f"{ch['title']} (part {j+1})",
                        "content": sc
                    })
            else:
                result.append(ch)
        return result

    # Fallback: fixed-size chunks
    print("  No chapter structure detected, using fixed-size chunks...")
    raw_chunks = _fixed_chunk(text, config)
    return [{"title": f"Section {i+1}", "content": c} for i, c in enumerate(raw_chunks)]


def _fixed_chunk(text: str, config: Config) -> list[str]:
    """Split text into overlapping fixed-size chunks by character count."""
    char_limit = config.chunk_size * 4
    overlap_chars = config.chunk_overlap * 4
    chunks = []
    start = 0
    while start < len(text):
        end = start + char_limit
        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break near the end
            break_point = text.rfind("\n\n", start + char_limit // 2, end)
            if break_point == -1:
                break_point = text.rfind(". ", start + char_limit // 2, end)
            if break_point != -1:
                end = break_point + 1
        chunks.append(text[start:end])
        start = end - overlap_chars
    return chunks


# ---------------------------------------------------------------------------
# Claude API Calls
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """\
You are a scholarly book analyst. Given a section of a book, produce a DEEP \
analysis — not a shallow index or table of contents. For this section, extract:

1. **Core Arguments & Thesis**: What is the author actually arguing? What \
claims are being made? State them precisely.

2. **Key Concepts & Frameworks**: Define each important concept the author \
introduces or uses. Explain how they relate to each other.

3. **Evidence & Examples**: What specific evidence, case studies, data, \
experiments, or stories does the author use to support their arguments? \
Summarize each meaningfully — don't just name them.

4. **Practical Takeaways**: What actionable insights or methods does the \
author recommend? Be specific about the "how", not just the "what".

5. **Connections & Tensions**: Note any connections to other ideas in the \
book, contradictions, or nuances the author acknowledges.

6. **Memorable Quotes or Phrases**: Include 1-2 particularly powerful or \
representative quotes (with approximate context).

Be thorough but concise. Write in clear prose, not bullet-point lists. \
This analysis will be synthesized with other sections into a complete \
book summary, so capture enough substance that the final summary can be \
rich and useful without re-reading the original text.
"""

SYNTHESIS_PROMPT = """\
You are a master book summarizer creating a comprehensive, actionable summary \
for a knowledge worker's personal wiki (Obsidian). You have per-section \
analyses of an entire book. Synthesize them into a single, cohesive document.

## Requirements

1. **Book Overview** (2-3 paragraphs): The book's central thesis, why it \
matters, who it's for, and how the author builds their case.

2. **Key Ideas & Frameworks**: The 5-10 most important ideas. For each: \
explain the concept deeply, give the author's best supporting evidence, \
and note practical applications. Write substantive paragraphs, not surface-level bullets.

3. **Chapter-by-Chapter Insights**: For each major section/chapter, a concise \
paragraph capturing its unique contribution to the book's argument. Skip \
this if the book doesn't have clear chapters.

4. **Practical Application Guide**: A "how to actually use this" section. \
Concrete steps, frameworks, or mental models someone can apply immediately.

5. **Critical Assessment**: Strengths, weaknesses, what the book does well, \
where it falls short, and what perspectives it might be missing.

6. **Connections**: How this book relates to other well-known works in its \
field. What should someone read next?

## Formatting (Obsidian-compatible)
- Use `#`, `##`, `###` headings
- Use `>` for key quotes as blockquotes
- Use `[[double brackets]]` for concepts that could link to other notes
- Add relevant tags at the top as `#tag`
- Include a metadata YAML frontmatter block with title, author, date_read, rating

Write with depth and substance. This summary should make someone feel they \
truly understand the book's ideas well enough to discuss them intelligently \
and apply them in practice. It should NOT read like a table of contents.
"""


def extract_from_chunk(
    client: Anthropic,
    chunk: dict,
    config: Config,
) -> dict:
    """Send a single chunk to Haiku for deep extraction."""
    message = client.messages.create(
        model=config.extraction_model,
        max_tokens=config.extraction_max_tokens,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{EXTRACTION_PROMPT}\n\n"
                    f"## Section: {chunk['title']}\n\n"
                    f"{chunk['content']}"
                ),
            }
        ],
    )
    result_text = message.content[0].text
    usage = message.usage

    return {
        "title": chunk["title"],
        "analysis": result_text,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }


def synthesize_summary(
    client: Anthropic,
    book_title: str,
    author: str,
    chunk_analyses: list[dict],
    config: Config,
) -> dict:
    """Send all chunk analyses to Sonnet for final synthesis."""
    analyses_text = "\n\n---\n\n".join(
        f"### {ca['title']}\n\n{ca['analysis']}" for ca in chunk_analyses
    )

    message = client.messages.create(
        model=config.synthesis_model,
        max_tokens=config.synthesis_max_tokens,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{SYNTHESIS_PROMPT}\n\n"
                    f"## Book: \"{book_title}\" by {author}\n\n"
                    f"## Section Analyses\n\n{analyses_text}"
                ),
            }
        ],
    )

    return {
        "summary": message.content[0].text,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }


# ---------------------------------------------------------------------------
# NotebookLM Source Preparation
# ---------------------------------------------------------------------------

def prepare_notebooklm_source(
    book_title: str,
    author: str,
    chunk_analyses: list[dict],
    output_dir: str,
) -> str:
    """
    Create a condensed source document optimized for NotebookLM upload.
    NotebookLM works best with well-structured documents under 500k chars.
    """
    sections = []
    sections.append(f"# {book_title} — Detailed Analysis\n")
    sections.append(f"**Author:** {author}\n")
    sections.append(
        "This document contains a detailed per-section analysis of the book, "
        "optimized for use as a NotebookLM source. Ask questions about specific "
        "concepts, request comparisons between chapters, or explore practical "
        "applications.\n"
    )

    for ca in chunk_analyses:
        sections.append(f"\n## {ca['title']}\n\n{ca['analysis']}")

    content = "\n".join(sections)
    filepath = os.path.join(output_dir, f"{_slugify(book_title)}_notebooklm_source.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:60]


# ---------------------------------------------------------------------------
# Cost Tracking
# ---------------------------------------------------------------------------

# Pricing per million tokens (as of March 2026)
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":        {"input": 3.00, "output": 15.00},
    "claude-opus-4-6":          {"input": 5.00, "output": 25.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given API call."""
    prices = PRICING.get(model, {"input": 3.00, "output": 15.00})
    cost = (input_tokens / 1_000_000 * prices["input"]) + \
           (output_tokens / 1_000_000 * prices["output"])
    return cost


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    filepath: str,
    book_title: str = "",
    author: str = "",
    output_path: str = "",
    config: Optional[Config] = None,
):
    """Execute the full book summarization pipeline."""
    if config is None:
        config = Config()

    client = Anthropic()

    # Derive defaults
    if not book_title:
        book_title = Path(filepath).stem.replace("_", " ").replace("-", " ").title()
    if not author:
        author = "Unknown Author"
    if not output_path:
        output_path = f"{_slugify(book_title)}_summary.md"

    output_dir = os.path.dirname(output_path) or "."

    print(f"\n{'='*60}")
    print(f"  Book Summarizer Pipeline")
    print(f"{'='*60}")
    print(f"  Book:   {book_title}")
    print(f"  Author: {author}")
    print(f"  File:   {filepath}")
    print(f"  Output: {output_path}")
    print(f"{'='*60}\n")

    # Step 1: Extract text
    print("[1/4] Extracting text...")
    raw_text = extract_text(filepath)
    char_count = len(raw_text)
    approx_tokens = char_count // 4
    print(f"  Extracted ~{approx_tokens:,} tokens ({char_count:,} chars)\n")

    # Step 2: Chunk
    print("[2/4] Chunking text...")
    chunks = chunk_text(raw_text, config)
    print(f"  Created {len(chunks)} chunks\n")

    # Step 3: Per-chunk extraction with Haiku
    print(f"[3/4] Extracting insights per chunk (using {config.extraction_model})...")
    chunk_analyses = []
    total_extract_cost = 0.0

    for i, chunk in enumerate(chunks):
        print(f"  Processing chunk {i+1}/{len(chunks)}: {chunk['title'][:50]}...", end="")
        result = extract_from_chunk(client, chunk, config)
        chunk_analyses.append(result)

        cost = calculate_cost(
            config.extraction_model,
            result["input_tokens"],
            result["output_tokens"],
        )
        total_extract_cost += cost
        print(f" ({result['input_tokens']}+{result['output_tokens']} tokens, ${cost:.4f})")

    print(f"\n  Extraction total: ${total_extract_cost:.4f}\n")

    # Step 4: Synthesize with Sonnet
    print(f"[4/4] Synthesizing final summary (using {config.synthesis_model})...")
    synthesis = synthesize_summary(client, book_title, author, chunk_analyses, config)
    synthesis_cost = calculate_cost(
        config.synthesis_model,
        synthesis["input_tokens"],
        synthesis["output_tokens"],
    )
    print(f"  Synthesis: {synthesis['input_tokens']}+{synthesis['output_tokens']} tokens, ${synthesis_cost:.4f}\n")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(synthesis["summary"])
    print(f"  Summary written to: {output_path}")

    # Prepare NotebookLM source if enabled
    nlm_path = None
    if config.include_notebooklm_source:
        nlm_path = prepare_notebooklm_source(book_title, author, chunk_analyses, output_dir)
        print(f"  NotebookLM source written to: {nlm_path}")

    # Cost summary
    total_cost = total_extract_cost + synthesis_cost
    print(f"\n{'='*60}")
    print(f"  COST SUMMARY")
    print(f"{'='*60}")
    print(f"  Extraction ({config.extraction_model}): ${total_extract_cost:.4f}")
    print(f"  Synthesis  ({config.synthesis_model}):  ${synthesis_cost:.4f}")
    print(f"  ─────────────────────────────────────")
    print(f"  TOTAL:                                  ${total_cost:.4f}")
    print(f"{'='*60}")

    naive_cost = calculate_cost("claude-sonnet-4-6", approx_tokens, 4000)
    print(f"\n  Estimated naive approach (full book → Sonnet): ${naive_cost:.4f}")
    if naive_cost > 0:
        savings = ((naive_cost - total_cost) / naive_cost) * 100
        print(f"  Savings with pipeline approach: {savings:.0f}%")

    print(f"\n  Done! Your summary is ready at: {output_path}")
    if nlm_path:
        print(f"  Upload {nlm_path} to NotebookLM for interactive Q&A.")

    return {
        "summary_path": output_path,
        "notebooklm_source_path": nlm_path,
        "total_cost": total_cost,
        "chunks_processed": len(chunks),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Summarize books using Claude API with token-efficient chunking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python book_summarizer.py book.pdf
              python book_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport"
              python book_summarizer.py book.epub --output deep_work_summary.md
              python book_summarizer.py book.pdf --extraction-model claude-haiku-4-5-20251001
        """),
    )
    parser.add_argument("filepath", help="Path to the book file (PDF, EPUB, TXT, MD)")
    parser.add_argument("--title", default="", help="Book title (auto-detected from filename if omitted)")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--output", "-o", default="", help="Output path for the summary")
    parser.add_argument(
        "--extraction-model",
        default="claude-haiku-4-5-20251001",
        help="Model for per-chunk extraction (default: haiku for cost savings)",
    )
    parser.add_argument(
        "--synthesis-model",
        default="claude-sonnet-4-6",
        help="Model for final synthesis (default: sonnet for quality)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=8000,
        help="Approximate chunk size in tokens (default: 8000)",
    )
    parser.add_argument(
        "--no-notebooklm",
        action="store_true",
        help="Skip generating the NotebookLM source file",
    )

    args = parser.parse_args()

    config = Config(
        extraction_model=args.extraction_model,
        synthesis_model=args.synthesis_model,
        chunk_size=args.chunk_size,
        include_notebooklm_source=not args.no_notebooklm,
    )

    run_pipeline(
        filepath=args.filepath,
        book_title=args.title,
        author=args.author,
        output_path=args.output,
        config=config,
    )


if __name__ == "__main__":
    main()