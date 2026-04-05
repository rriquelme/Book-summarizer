#!/usr/bin/env python3
"""
Local Book Summarizer using Ollama
====================================
A zero-API-cost alternative to the Claude-based pipeline that runs
extraction locally via Ollama, with optional Claude API for final synthesis.

Strategy:
  1. Extract text from PDF/EPUB/TXT (same as main pipeline)
  2. Chunk the book into sections
  3. Use a local LLM via Ollama for per-chunk extraction (FREE)
  4. Optionally use Claude API for final synthesis (cheap, one call)
     OR use Ollama for synthesis too (100% free)

This is ideal for Roberto's 64GB RAM machine running Ollama with
models like Qwen 2.5 32B, GLM-4, or Llama 3.

Prerequisites:
  pip install ollama pypdf ebooklib beautifulsoup4 python-dotenv
  # Ollama must be running: ollama serve
  # Pull a model: ollama pull qwen2.5:32b

Usage:
  # Fully local (zero cost)
  python ollama_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport"

  # Local extraction + Claude synthesis (best quality, ~$0.05 per book)
  python ollama_summarizer.py book.pdf --title "Deep Work" --claude-synthesis

  # Use a specific Ollama model
  python ollama_summarizer.py book.pdf --model "llama3:70b"

  # Faster with smaller model (less quality)
  python ollama_summarizer.py book.pdf --model "qwen2.5:14b"
"""

import os
import re
import sys
import json
import time
import argparse
import textwrap
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Reuse text extraction and chunking from the main pipeline
# ---------------------------------------------------------------------------
try:
    from book_summarizer import (
        extract_text,
        chunk_text,
        Config as BaseConfig,
        _slugify,
        EXTRACTION_PROMPT,
        SYNTHESIS_PROMPT,
        prepare_notebooklm_source,
    )
except ImportError:
    print("ERROR: book_summarizer.py must be in the same directory.")
    print("This script reuses its text extraction and chunking logic.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class OllamaConfig:
    """Configuration for the Ollama-based pipeline."""
    # Ollama settings
    ollama_model: str = "qwen2.5:32b"       # Good balance of quality and speed on 64GB
    ollama_host: str = "http://localhost:11434"
    ollama_timeout: float = 300.0            # 5 min timeout per chunk (large models are slow)

    # Context and generation
    num_ctx: int = 16384            # Context window for Ollama model
    extraction_max_tokens: int = 2000
    synthesis_max_tokens: int = 4096

    # Chunking (inherited from base config)
    chunk_size: int = 6000          # Slightly smaller chunks for local models
    chunk_overlap: int = 400

    # Synthesis strategy
    use_claude_synthesis: bool = False   # Use Claude API for final synthesis?
    claude_model: str = "claude-sonnet-4-6"

    # Output
    include_notebooklm_source: bool = True

    # Performance
    num_parallel: int = 1           # Ollama handles one request at a time by default


# ---------------------------------------------------------------------------
# Ollama Client
# ---------------------------------------------------------------------------

class OllamaClient:
    """Simple Ollama client using the ollama Python package."""

    def __init__(self, config: OllamaConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self.config.ollama_host)
            except ImportError:
                print("\nERROR: ollama package not installed.")
                print("Install with: pip install ollama")
                print("Also make sure Ollama is running: ollama serve")
                sys.exit(1)
        return self._client

    def check_model(self) -> bool:
        """Verify the model is available locally."""
        client = self._get_client()
        try:
            models = client.list()
            model_names = []
            for m in models.get("models", []):
                name = m.get("name", "") if isinstance(m, dict) else getattr(m, "name", "")
                model_names.append(name)

            # Check if our model is available (handle tag variations)
            target = self.config.ollama_model
            found = any(
                target in name or name.startswith(target.split(":")[0])
                for name in model_names
            )

            if not found:
                print(f"\n  WARNING: Model '{target}' not found locally.")
                print(f"  Available models: {', '.join(model_names[:10])}")
                print(f"  Pull it with: ollama pull {target}")
                return False

            print(f"  Model '{target}' is available.")
            return True

        except Exception as e:
            print(f"\n  ERROR: Cannot connect to Ollama at {self.config.ollama_host}")
            print(f"  Make sure Ollama is running: ollama serve")
            print(f"  Error: {e}")
            return False

    def generate(self, prompt: str, system: str = "") -> dict:
        """
        Generate a response from the local Ollama model.

        Returns dict with 'text', 'eval_count' (output tokens),
        'prompt_eval_count' (input tokens), 'duration_ms'.
        """
        client = self._get_client()
        start = time.time()

        try:
            response = client.chat(
                model=self.config.ollama_model,
                messages=[
                    {"role": "system", "content": system} if system else None,
                    {"role": "user", "content": prompt},
                ],
                options={
                    "num_ctx": self.config.num_ctx,
                    "num_predict": self.config.extraction_max_tokens,
                    "temperature": 0.3,  # Lower temp for factual extraction
                },
            )

            # Filter None messages in case system was empty
            elapsed = (time.time() - start) * 1000

            # Handle both dict and object response formats
            if isinstance(response, dict):
                text = response.get("message", {}).get("content", "")
                eval_count = response.get("eval_count", 0)
                prompt_eval = response.get("prompt_eval_count", 0)
            else:
                text = response.message.content if response.message else ""
                eval_count = getattr(response, "eval_count", 0)
                prompt_eval = getattr(response, "prompt_eval_count", 0)

            return {
                "text": text,
                "eval_count": eval_count,
                "prompt_eval_count": prompt_eval,
                "duration_ms": elapsed,
            }

        except Exception as e:
            print(f"\n  ERROR during generation: {e}")
            return {
                "text": f"[Extraction failed: {e}]",
                "eval_count": 0,
                "prompt_eval_count": 0,
                "duration_ms": 0,
            }

    def generate_clean(self, prompt: str, system: str = "") -> dict:
        """
        Generate with cleaned message list (no None entries).
        """
        client = self._get_client()
        start = time.time()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat(
                model=self.config.ollama_model,
                messages=messages,
                options={
                    "num_ctx": self.config.num_ctx,
                    "num_predict": self.config.synthesis_max_tokens,
                    "temperature": 0.3,
                },
            )

            elapsed = (time.time() - start) * 1000

            if isinstance(response, dict):
                text = response.get("message", {}).get("content", "")
                eval_count = response.get("eval_count", 0)
                prompt_eval = response.get("prompt_eval_count", 0)
            else:
                text = response.message.content if response.message else ""
                eval_count = getattr(response, "eval_count", 0)
                prompt_eval = getattr(response, "prompt_eval_count", 0)

            return {
                "text": text,
                "eval_count": eval_count,
                "prompt_eval_count": prompt_eval,
                "duration_ms": elapsed,
            }
        except Exception as e:
            print(f"\n  ERROR during generation: {e}")
            return {"text": "", "eval_count": 0, "prompt_eval_count": 0, "duration_ms": 0}


# ---------------------------------------------------------------------------
# Extraction (Ollama)
# ---------------------------------------------------------------------------

def extract_from_chunk_ollama(
    client: OllamaClient,
    chunk: dict,
) -> dict:
    """Send a single chunk to the local Ollama model for extraction."""
    prompt = (
        f"## Section: {chunk['title']}\n\n"
        f"{chunk['content']}"
    )

    result = client.generate_clean(prompt=prompt, system=EXTRACTION_PROMPT)

    return {
        "title": chunk["title"],
        "analysis": result["text"],
        "input_tokens": result["prompt_eval_count"],
        "output_tokens": result["eval_count"],
        "duration_ms": result["duration_ms"],
    }


# ---------------------------------------------------------------------------
# Synthesis (Ollama or Claude)
# ---------------------------------------------------------------------------

def synthesize_with_ollama(
    client: OllamaClient,
    book_title: str,
    author: str,
    chunk_analyses: list[dict],
    config: OllamaConfig,
) -> dict:
    """Synthesize all chunk analyses using the local Ollama model."""
    analyses_text = "\n\n---\n\n".join(
        f"### {ca['title']}\n\n{ca['analysis']}" for ca in chunk_analyses
    )

    prompt = (
        f"## Book: \"{book_title}\" by {author}\n\n"
        f"## Section Analyses\n\n{analyses_text}"
    )

    # For synthesis, allow more output tokens
    result = client.generate_clean(prompt=prompt, system=SYNTHESIS_PROMPT)

    return {
        "summary": result["text"],
        "input_tokens": result["prompt_eval_count"],
        "output_tokens": result["eval_count"],
        "duration_ms": result["duration_ms"],
    }


def synthesize_with_claude(
    book_title: str,
    author: str,
    chunk_analyses: list[dict],
    config: OllamaConfig,
) -> dict:
    """Use Claude API for high-quality final synthesis."""
    from anthropic import Anthropic
    from book_summarizer import calculate_cost

    client = Anthropic()
    analyses_text = "\n\n---\n\n".join(
        f"### {ca['title']}\n\n{ca['analysis']}" for ca in chunk_analyses
    )

    message = client.messages.create(
        model=config.claude_model,
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

    cost = calculate_cost(
        config.claude_model,
        message.usage.input_tokens,
        message.usage.output_tokens,
    )

    return {
        "summary": message.content[0].text,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "cost": cost,
    }


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_ollama_pipeline(
    filepath: str,
    book_title: str = "",
    author: str = "",
    output_path: str = "",
    config: Optional[OllamaConfig] = None,
):
    """Execute the Ollama-based book summarization pipeline."""
    if config is None:
        config = OllamaConfig()

    # Derive defaults
    if not book_title:
        book_title = Path(filepath).stem.replace("_", " ").replace("-", " ").title()
    if not author:
        author = "Unknown Author"
    if not output_path:
        output_path = f"{_slugify(book_title)}_summary.md"

    output_dir = os.path.dirname(output_path) or "."

    print(f"\n{'='*60}")
    print(f"  Ollama Book Summarizer")
    print(f"{'='*60}")
    print(f"  Book:     {book_title}")
    print(f"  Author:   {author}")
    print(f"  Model:    {config.ollama_model}")
    print(f"  Strategy: {'Ollama extract + Claude synthesis' if config.use_claude_synthesis else 'Fully local (Ollama)'}")
    print(f"  Cost:     {'~$0.05' if config.use_claude_synthesis else 'FREE'}")
    print(f"{'='*60}\n")

    # Initialize Ollama client
    ollama_client = OllamaClient(config)
    if not ollama_client.check_model():
        print("\n  Aborting. Please pull the model first.")
        sys.exit(1)

    # Step 1: Extract text
    print("\n[1/4] Extracting text...")
    raw_text = extract_text(filepath)
    char_count = len(raw_text)
    approx_tokens = char_count // 4
    print(f"  Extracted ~{approx_tokens:,} tokens ({char_count:,} chars)")

    # Step 2: Chunk
    print("\n[2/4] Chunking text...")
    base_config = BaseConfig(chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
    chunks = chunk_text(raw_text, base_config)
    print(f"  Created {len(chunks)} chunks")

    # Step 3: Per-chunk extraction with Ollama
    print(f"\n[3/4] Extracting insights per chunk (using {config.ollama_model})...")
    chunk_analyses = []
    total_duration = 0.0

    for i, chunk in enumerate(chunks):
        print(f"\n  Chunk {i+1}/{len(chunks)}: {chunk['title'][:50]}...")
        result = extract_from_chunk_ollama(ollama_client, chunk)
        chunk_analyses.append(result)

        duration_s = result["duration_ms"] / 1000
        total_duration += duration_s
        tokens_per_sec = (
            result["output_tokens"] / duration_s if duration_s > 0 else 0
        )
        print(f"    {result['input_tokens']} in → {result['output_tokens']} out")
        print(f"    {duration_s:.1f}s ({tokens_per_sec:.1f} tok/s)")

    avg_time = total_duration / len(chunks) if chunks else 0
    print(f"\n  Extraction complete: {total_duration:.0f}s total, {avg_time:.1f}s avg per chunk")

    # Step 4: Synthesis
    if config.use_claude_synthesis:
        print(f"\n[4/4] Synthesizing with Claude ({config.claude_model})...")
        synthesis = synthesize_with_claude(
            book_title, author, chunk_analyses, config
        )
        synthesis_cost = synthesis.get("cost", 0)
        print(f"  Synthesis: {synthesis['input_tokens']}+{synthesis['output_tokens']} tokens")
        print(f"  Claude API cost: ${synthesis_cost:.4f}")
    else:
        print(f"\n[4/4] Synthesizing with Ollama ({config.ollama_model})...")
        synthesis = synthesize_with_ollama(
            ollama_client, book_title, author, chunk_analyses, config
        )
        duration_s = synthesis.get("duration_ms", 0) / 1000
        print(f"  Synthesis: {synthesis['input_tokens']}+{synthesis['output_tokens']} tokens")
        print(f"  Duration: {duration_s:.1f}s")
        synthesis_cost = 0.0

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(synthesis["summary"])
    print(f"\n  Summary written to: {output_path}")

    # NotebookLM source
    nlm_path = None
    if config.include_notebooklm_source:
        nlm_path = prepare_notebooklm_source(
            book_title, author, chunk_analyses, output_dir
        )
        print(f"  NotebookLM source written to: {nlm_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Chunks processed:  {len(chunks)}")
    print(f"  Total time:        {total_duration + (synthesis.get('duration_ms', 0)/1000):.0f}s")
    print(f"  API cost:          ${synthesis_cost:.4f}")
    print(f"  Model used:        {config.ollama_model}")

    if config.use_claude_synthesis:
        print(f"  Synthesis model:   {config.claude_model}")
    print(f"{'='*60}")

    return {
        "summary_path": output_path,
        "notebooklm_source_path": nlm_path,
        "total_cost": synthesis_cost,
        "chunks_processed": len(chunks),
        "total_duration_s": total_duration,
    }


# ---------------------------------------------------------------------------
# Model Recommendations
# ---------------------------------------------------------------------------

RECOMMENDED_MODELS = """
Recommended Ollama models for book summarization (64GB RAM):

  Model                RAM     Quality   Speed     Notes
  ─────────────────────────────────────────────────────────────
  qwen2.5:32b         ~20GB   ★★★★★    ★★★       Best quality/speed balance
  qwen2.5:14b         ~10GB   ★★★★     ★★★★      Good quality, faster
  llama3:70b-q4       ~40GB   ★★★★★    ★★        Highest quality, slow
  llama3:8b           ~5GB    ★★★      ★★★★★     Fast but less depth
  deepseek-r1:32b     ~20GB   ★★★★★    ★★★       Strong reasoning
  gemma2:27b          ~17GB   ★★★★     ★★★       Google's model, solid
  mistral:7b          ~5GB    ★★★      ★★★★★     Fast, less depth

  For best results: qwen2.5:32b for extraction, claude-sonnet-4-6 for synthesis
  For zero cost:     qwen2.5:32b for both extraction and synthesis
  For speed:         qwen2.5:14b or llama3:8b

  Pull a model: ollama pull qwen2.5:32b
"""

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Summarize books locally using Ollama (zero API cost).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Fully local, zero cost
              python ollama_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport"

              # Local extraction + Claude synthesis (best quality, ~$0.05)
              python ollama_summarizer.py book.pdf --title "Deep Work" --claude-synthesis

              # Use a specific model
              python ollama_summarizer.py book.pdf --model qwen2.5:14b

              # Show recommended models
              python ollama_summarizer.py --list-models

            Prerequisites:
              pip install ollama pypdf ebooklib beautifulsoup4 python-dotenv
              ollama serve              # start Ollama server
              ollama pull qwen2.5:32b   # download a model
        """),
    )

    parser.add_argument("filepath", nargs="?", help="Path to book file")
    parser.add_argument("--title", default="", help="Book title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--output", "-o", default="", help="Output file path")
    parser.add_argument(
        "--model", default="qwen2.5:32b",
        help="Ollama model to use (default: qwen2.5:32b)",
    )
    parser.add_argument(
        "--claude-synthesis", action="store_true",
        help="Use Claude API for final synthesis (better quality, small cost)",
    )
    parser.add_argument(
        "--claude-model", default="claude-sonnet-4-6",
        help="Claude model for synthesis (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=6000,
        help="Chunk size in tokens (default: 6000, smaller than API due to local context limits)",
    )
    parser.add_argument(
        "--num-ctx", type=int, default=16384,
        help="Ollama context window size (default: 16384)",
    )
    parser.add_argument(
        "--no-notebooklm", action="store_true",
        help="Skip generating NotebookLM source file",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="Show recommended models and exit",
    )

    args = parser.parse_args()

    if args.list_models:
        print(RECOMMENDED_MODELS)
        sys.exit(0)

    if not args.filepath:
        parser.print_help()
        sys.exit(1)

    config = OllamaConfig(
        ollama_model=args.model,
        use_claude_synthesis=args.claude_synthesis,
        claude_model=args.claude_model,
        chunk_size=args.chunk_size,
        num_ctx=args.num_ctx,
        include_notebooklm_source=not args.no_notebooklm,
    )

    run_ollama_pipeline(
        filepath=args.filepath,
        book_title=args.title,
        author=args.author,
        output_path=args.output,
        config=config,
    )


if __name__ == "__main__":
    main()