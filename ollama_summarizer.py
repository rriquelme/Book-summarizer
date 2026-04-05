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
  # See what models you have installed
  python ollama_summarizer.py --list-installed

  # Fully local (zero cost) - using your installed model
  python ollama_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport" \
    --model glm-4.7-flash:latest

  # Save raw chunks (original book text BEFORE LLM processing)
  python ollama_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport" \
    --model glm-4.7-flash:latest --save-raw-chunks

  # Save LLM output chunks (analysis AFTER LLM processing)
  python ollama_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport" \
    --model glm-4.7-flash:latest --save-chunks

  # Save BOTH raw input and LLM output chunks
  python ollama_summarizer.py book.pdf --title "Deep Work" --author "Cal Newport" \
    --model glm-4.7-flash:latest --save-raw-chunks --save-chunks

  # Local extraction + Claude synthesis (best quality, ~$0.05 per book)
  python ollama_summarizer.py book.pdf --title "Deep Work" --claude-synthesis \
    --model glm-4.7-flash:latest

  # Use a different model
  python ollama_summarizer.py book.pdf --model "qwen2.5-coder:14b"

  # Show recommended models
  python ollama_summarizer.py --list-models
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
    save_individual_chunks: bool = False   # Save LLM analysis to individual files?
    save_raw_chunks: bool = False          # Save raw input chunks (before LLM)?

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
            models_response = client.list()
            model_names = self._extract_model_names(models_response)

            if not model_names:
                print(f"\n  ERROR: No models found. Make sure Ollama is running and you have pulled a model.")
                print(f"  Run: ollama pull qwen2.5:32b")
                return False

            # Check if our model is available (handle tag variations)
            target = self.config.ollama_model
            found = self._find_matching_model(target, model_names)

            if not found:
                print(f"\n  WARNING: Model '{target}' not found locally.")
                print(f"\n  Available models:")
                for name in sorted(model_names):
                    print(f"    - {name}")
                print(f"\n  Use one of the available models, e.g.:")
                print(f"    python ollama_summarizer.py book.pdf --model {model_names[0]}")
                return False

            print(f"  [OK] Model '{target}' is available.")
            return True

        except Exception as e:
            print(f"\n  ERROR: Cannot connect to Ollama at {self.config.ollama_host}")
            print(f"  Make sure Ollama is running: ollama serve")
            print(f"  Error: {e}")
            return False

    def _extract_model_names(self, models_response) -> list[str]:
        """Extract model names from ollama client response."""
        model_names = []

        # Handle both dict and object responses
        if isinstance(models_response, dict):
            models_list = models_response.get("models", [])
        else:
            models_list = getattr(models_response, "models", [])

        for m in models_list:
            try:
                # Try dict access first (some API versions return dict)
                if isinstance(m, dict):
                    name = m.get("model") or m.get("name")
                else:
                    # Try object attribute access (ollama._types.ListResponse.Model)
                    # The ollama library uses .model attribute, not .name
                    name = getattr(m, "model", None) or getattr(m, "name", None)

                # Ensure we got a non-empty string
                if name and isinstance(name, str) and name.strip():
                    model_names.append(name.strip())
            except Exception:
                # Skip models that can't be parsed
                continue

        return model_names

    def _find_matching_model(self, target: str, available: list[str]) -> bool:
        """Find if target model matches any available model (handles tag variations)."""
        target_base = target.split(":")[0]  # e.g., "qwen2.5-coder" from "qwen2.5-coder:32b"

        for model_name in available:
            # Exact match
            if model_name == target:
                return True
            # Match base name (ignoring tags)
            if model_name.split(":")[0] == target_base:
                return True
            # Match if target is contained in model name
            if target.lower() in model_name.lower():
                return True

        return False

    def list_available_models(self) -> list[str]:
        """Return list of all available Ollama models."""
        client = self._get_client()
        try:
            models_response = client.list()
            return self._extract_model_names(models_response)
        except Exception as e:
            print(f"ERROR listing models: {e}")
            return []

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
# Save Raw Input Chunks (No Processing)
# ---------------------------------------------------------------------------

def save_raw_chunk_file(
    book_title: str,
    author: str,
    chunk_number: int,
    total_chunks: int,
    chunk: dict,
    output_dir: str,
) -> str:
    """
    Save the raw, unprocessed chunk text from the book.
    This is the input BEFORE it goes to the LLM.
    """
    chunks_dir = os.path.join(output_dir, f"{_slugify(book_title)}_raw_chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    chunk_title = chunk["title"].replace(" (part ", "_p").replace(")", "")
    filename = f"{chunk_number:02d}_{_slugify(chunk_title)}.txt"
    filepath = os.path.join(chunks_dir, filename)

    # Create content with metadata header
    content = f"""{"=" * 70}
BOOK: {book_title}
AUTHOR: {author}
CHAPTER/SECTION: {chunk["title"]}
CHUNK: {chunk_number} of {total_chunks}
CHARACTERS: {len(chunk["content"]):,}
TOKENS (estimated): {len(chunk["content"]) // 4:,}
{"=" * 70}

{chunk["content"]}

{"=" * 70}
END OF CHUNK {chunk_number}
{"=" * 70}
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


# ---------------------------------------------------------------------------
# Save Individual Chunk Files (Real-time)
# ---------------------------------------------------------------------------

def save_chunk_file_realtime(
    book_title: str,
    author: str,
    chunk_number: int,
    total_chunks: int,
    chunk: dict,
    analysis: dict,
    output_dir: str,
) -> str:
    """
    Save a single chunk file in real-time as it's processed.
    Shows what goes in (input) and what comes out (analysis).
    """
    chunks_dir = os.path.join(output_dir, f"{_slugify(book_title)}_chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    # Create filename: 01_Chapter Title.md, 02_Chapter Two.md, etc.
    chunk_title = chunk["title"].replace(" (part ", "_p").replace(")", "")
    filename = f"{chunk_number:02d}_{_slugify(chunk_title)}.md"
    filepath = os.path.join(chunks_dir, filename)

    # Create markdown content with input and output sections
    input_preview = chunk["content"][:500] + "..." if len(chunk["content"]) > 500 else chunk["content"]

    content = f"""# {chunk["title"]}

**Book:** {book_title}
**Author:** {author}
**Chunk:** {chunk_number} of {total_chunks}

---

## Input (What went in)

**Characters:** {len(chunk["content"]):,}
**Title:** {chunk["title"]}

**Content Preview:**
{input_preview}

---

## Output (What came out)

**Input Tokens:** {analysis.get('input_tokens', 0)}
**Output Tokens:** {analysis.get('output_tokens', 0)}
**Processing Time:** {analysis.get('duration_ms', 0) / 1000:.1f}s

### Analysis

{analysis['analysis']}

---

**Generated at:** {analysis.get('duration_ms', 0) / 1000:.1f}s
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


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

    # Save raw chunks if requested (BEFORE LLM processing)
    if config.save_raw_chunks:
        print("\n  Saving raw input chunks...")
        for i, chunk in enumerate(chunks, 1):
            save_raw_chunk_file(
                book_title, author, i, len(chunks), chunk, output_dir
            )
        raw_chunks_dir = os.path.join(output_dir, f"{_slugify(book_title)}_raw_chunks")
        print(f"  Raw chunks saved to: {raw_chunks_dir}/")

    # Step 3: Per-chunk extraction with Ollama
    print(f"\n[3/4] Extracting insights per chunk (using {config.ollama_model})...")
    chunk_analyses = []
    total_duration = 0.0

    for i, chunk in enumerate(chunks):
        print(f"\n  Chunk {i+1}/{len(chunks)}: {chunk['title'][:50]}...")
        print(f"    Input: {len(chunk['content']):,} chars ({len(chunk['content']) // 4} tokens)")

        result = extract_from_chunk_ollama(ollama_client, chunk)
        chunk_analyses.append(result)

        duration_s = result["duration_ms"] / 1000
        total_duration += duration_s
        tokens_per_sec = (
            result["output_tokens"] / duration_s if duration_s > 0 else 0
        )
        print(f"    Output: {result['input_tokens']} in → {result['output_tokens']} out")
        print(f"    Speed: {duration_s:.1f}s ({tokens_per_sec:.1f} tok/s)")

        # Save chunk file in real-time if flag is set
        if config.save_individual_chunks:
            chunk_file = save_chunk_file_realtime(
                book_title, author, i + 1, len(chunks), chunk, result, output_dir
            )
            print(f"    [SAVED] {os.path.relpath(chunk_file)}")

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

    # Note: Individual chunk files are saved in real-time during extraction
    chunks_dir = None
    if config.save_individual_chunks:
        chunks_dir = os.path.join(output_dir, f"{_slugify(book_title)}_chunks")
        print(f"  Individual chunk files saved to: {chunks_dir}/")

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
        "chunks_dir": chunks_dir,
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
              # See your installed models (RECOMMENDED - start here!)
              python ollama_summarizer.py --list-installed

              # Fully local, zero cost (pick one from --list-installed)
              python ollama_summarizer.py book.pdf --title "Deep Work" \\
                --model glm-4.7-flash:latest

              # Save LLM output chunks (analysis)
              python ollama_summarizer.py book.pdf --title "Deep Work" \\
                --model glm-4.7-flash:latest --save-chunks

              # Save raw input chunks (before LLM processing)
              python ollama_summarizer.py book.pdf --title "Deep Work" \\
                --model glm-4.7-flash:latest --save-raw-chunks

              # Save both raw input AND LLM output chunks
              python ollama_summarizer.py book.pdf --title "Deep Work" \\
                --model glm-4.7-flash:latest --save-chunks --save-raw-chunks

              # Local extraction + Claude synthesis (best quality, ~$0.05)
              python ollama_summarizer.py book.pdf --title "Deep Work" \\
                --claude-synthesis --model glm-4.7-flash:latest

              # Use a specific model
              python ollama_summarizer.py book.pdf --model qwen2.5-coder:32b

              # Show recommended models (for reference)
              python ollama_summarizer.py --list-models

            Prerequisites:
              pip install ollama pypdf ebooklib beautifulsoup4 python-dotenv
              ollama serve              # start Ollama server
              ollama pull glm-4.7-flash:latest  # or your model choice
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
        "--save-chunks", action="store_true",
        help="Save each chunk analysis (LLM output) to its own file",
    )
    parser.add_argument(
        "--save-raw-chunks", action="store_true",
        help="Save raw input chunks (before LLM processing) to individual text files",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="Show recommended models and exit",
    )
    parser.add_argument(
        "--list-installed", action="store_true",
        help="Show your locally installed models and exit",
    )

    args = parser.parse_args()

    if args.list_models:
        print(RECOMMENDED_MODELS)
        sys.exit(0)

    if args.list_installed:
        print("\n" + "="*60)
        print("  INSTALLED OLLAMA MODELS")
        print("="*60 + "\n")
        client = OllamaClient(OllamaConfig())
        installed = client.list_available_models()
        if installed:
            for model in sorted(installed):
                print(f"  [OK] {model}")
            print(f"\n  Use any of these models with:")
            print(f"    python ollama_summarizer.py book.pdf --model <model-name>")
        else:
            print("  No models found. Install one with:")
            print("    ollama pull qwen2.5:32b")
        print("=" * 60 + "\n")
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
        save_individual_chunks=args.save_chunks,
        save_raw_chunks=args.save_raw_chunks,
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