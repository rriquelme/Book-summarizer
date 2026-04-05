#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 4: Summarize Chunks with Local LLM
========================================
Summarize each chunk using a local Ollama LLM (qwen-coder-1.5b).

Input:  intermediate_files/chunks_<name>/ with 01_<name>.txt, 02_<name>.txt, etc.
Output: intermediate_files/summarized_chunks_<name>/ with same structure

Usage:
  python 04_summarize_chunks.py intermediate_files/chunks_test_book

  # Custom model and parameters
  python 04_summarize_chunks.py intermediate_files/chunks_test_book --model qwen2.5:14b --max-tokens 500

Requirements:
  - Ollama running locally: ollama serve
  - Model downloaded: ollama pull qwen-coder-1.5b

Philosophy:
  Extract key information and insights from each chunk locally.
  No API costs, works offline, maintains chunk structure.
"""

import sys
import io
import os
import re
import argparse
import json
from pathlib import Path
from typing import Optional, Tuple, Dict
import time

# Force UTF-8 encoding globally (critical on Windows)
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Force UTF-8 encoding for output on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import ollama
except ImportError:
    print("[ERROR] ollama package not found. Install with: pip install ollama")
    sys.exit(1)


# Configuration
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen-coder-1.5b"
DEFAULT_MAX_TOKENS = 300

SUMMARIZATION_PROMPT = """You are a practical summarizer. Extract ONLY information from the text provided.

SUMMARY MUST INCLUDE:
1. MAIN CONCEPTS: Core ideas explicitly mentioned
2. HOW TO USE: Where and when to apply (if mentioned)
3. EXAMPLES: Real examples from the text (do not invent)
4. TIPS: Practical advice given (only what is stated)

CRITICAL RULES:
- Use ONLY information from the provided text
- Do NOT invent or fabricate anything
- If section has no info in text, skip it
- No redundancy
- Be concise and useful

TEXT TO SUMMARIZE:
{text}

SUMMARY:
"""


def clean_chapter_name(name: str) -> str:
    """Clean up OCR artifacts in chapter names."""
    # Normalize whitespace first to handle multi-line titles
    cleaned = re.sub(r'\s+', ' ', name).strip()

    # Fix common OCR spacing issues - be aggressive with patterns
    fixes = [
        (r'BELIEVE\s*ALIE\b', 'BELIEVE A LIE'),
        (r'BELIEVEALIE', 'BELIEVE A LIE'),
        (r'YOURCAR', 'YOUR CAR'),
        (r'YOURBODY', 'YOUR BODY'),
        (r'ANDCONNECT', 'AND CONNECT'),
        (r'INFORMATIONDOWN', 'INFORMATION DOWN'),
        (r'ARTINMEMORY', 'ART IN MEMORY'),
        (r'INMEMORY', 'IN MEMORY'),
        (r'THEMETHODS', 'THE METHODS'),
        (r'TORENEW', 'TO RENEW'),
        (r'TORENEWING', 'TO RENEWING'),
        (r'HERE?\s+NOW', 'HERE NOW'),
        (r'HERENOW', 'HERE NOW'),
        (r'TOREMEMBER', 'TO REMEMBER'),
        (r'I\s+N\s+THE\s+FIRSTPLACE', 'IN THE FIRST PLACE'),
        (r'I\s+NTHE\s+FIRSTPLACE', 'IN THE FIRST PLACE'),
        (r'INTHEFIRSTPLACE', 'IN THE FIRST PLACE'),
        (r'I\s+N\s+THE', 'IN THE'),
        (r'I\s+NTHE', 'IN THE'),
        (r'INTHE', 'IN THE'),
    ]

    for pattern, replacement in fixes:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # Normalize whitespace again
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Title case: capitalize properly
    words = cleaned.split()
    if words:
        # Capitalize first word always
        if len(words[0]) > 0:
            words[0] = words[0][0].upper() + words[0][1:].lower()

        # Capitalize other words, keeping small words lowercase
        small_words = {'and', 'or', 'the', 'a', 'an', 'in', 'to', 'for', 'of', 'with', 'at', 'by', 'is'}
        for i in range(1, len(words)):
            word_lower = words[i].lower()
            # Also capitalize words after periods (they're usually chapter numbers or titles)
            if word_lower in small_words and i > 0 and not words[i-1].endswith('.'):
                words[i] = word_lower
            else:
                words[i] = words[i][0].upper() + words[i][1:].lower() if len(words[i]) > 0 else words[i]

    return ' '.join(words)


def extract_chapter_name(chunk_text: str) -> str:
    """
    Extract chapter/section name from chunk text.
    If multiple titles found, picks the most significant one (CHAPTER > PART > SECTION).
    Handles cases where titles may span multiple lines due to OCR issues.

    Returns:
        Chapter/section name, or "Unknown" if not found
    """
    lines = chunk_text.split('\n')

    # Look for [chapter: ...] or [section: ...] metadata line
    # Metadata is more reliable than parsing TOC or complex structures
    metadata_type = None
    for line in lines[:3]:
        match = re.match(r'\[(?:chapter|section):\s*([^\]]+)\]', line, re.IGNORECASE)
        if match:
            metadata_type = match.group(1).strip()
            # If metadata found and it's meaningful (not just "chapter"), use it immediately
            if metadata_type.lower() not in ['chapter', 'part', 'section', '']:
                return clean_chapter_name(metadata_type)
            break

    # Find ALL chapter/part/section boundaries in the chunk
    # If multiple exist, pick the most significant one
    found_titles = []

    for i, line in enumerate(lines[1:20], start=1):
        line_stripped = line.strip()

        # Skip empty lines and page markers
        if not line_stripped or line_stripped.startswith('[Page'):
            continue

        # Check if this line starts with a title keyword
        match = re.match(r'^(CHAPTER|Chapter|PART|Part|SECTION|Section|INTRODUCTION|Introduction|FOREWORD|DEDICATION)',
                        line_stripped, re.IGNORECASE)
        if match:
            kind = match.group(1).lower()
            if kind.startswith('chapter'):
                kind = 'chapter'
            elif kind.startswith('part'):
                kind = 'part'
            else:
                kind = 'section'

            # Collect this line and potentially the next several non-empty lines
            title_parts = [line_stripped]

            # Look ahead for continuation (in case title spans multiple lines)
            for next_line in lines[i+1:i+6]:
                next_stripped = next_line.strip()
                # Skip empty lines
                if not next_stripped:
                    continue
                # Stop if we hit a quote (start of actual content)
                if next_stripped.startswith('"'):
                    break
                # Stop if we hit page marker
                if next_stripped.startswith('[Page'):
                    break
                # Check if it looks like a title continuation
                if re.match(r'^[\d\w\.\s\-:,]+$', next_stripped) and len(next_stripped) < 80:
                    title_parts.append(next_stripped)
                else:
                    break

            title = ' '.join(title_parts)
            title = re.sub(r'\s+', ' ', title).strip()
            title = clean_chapter_name(title)

            if len(title) > 3 and len(title) < 150:
                # Count lines after this title to determine significance
                content_after = len(lines) - i
                found_titles.append((kind, title, content_after, i))

    # Pick the most significant title
    if found_titles:
        # Priority: CHAPTER > PART > SECTION
        # If same type, pick the one with most content after it
        kind_priority = {'chapter': 3, 'part': 2, 'section': 1}
        found_titles.sort(key=lambda x: (kind_priority.get(x[0], 0), x[2]), reverse=True)
        return found_titles[0][1]

    # Fallback to metadata if found and meaningful
    if metadata_type and metadata_type.lower() not in ['chapter', 'part', 'section']:
        return clean_chapter_name(metadata_type)

    return "Unknown"


def check_ollama_connection(host: str = OLLAMA_HOST) -> bool:
    """Check if Ollama is running and accessible."""
    try:
        response = ollama.list()
        return response is not None
    except Exception as e:
        print(f"[ERROR] Cannot connect to Ollama at {host}")
        print(f"  Make sure Ollama is running: ollama serve")
        print(f"  Error: {e}")
        return False


def check_model_available(model: str) -> bool:
    """Check if the required model is available."""
    try:
        response = ollama.list()
        available_models = [m["name"].split(":")[0] for m in response.get("models", [])]
        model_base = model.split(":")[0]
        return model_base in available_models
    except Exception as e:
        print(f"[WARNING] Could not check available models: {e}")
        return False


def summarize_chunk(text: str, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS) -> Optional[str]:
    """
    Summarize a chunk of text using Ollama.

    Args:
        text: Raw text to summarize
        model: Ollama model to use
        max_tokens: Maximum tokens in summary

    Returns:
        Summarized text or None if error
    """
    if not text.strip():
        return ""

    try:
        # Ensure text is properly encoded (UTF-8)
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')

        prompt = SUMMARIZATION_PROMPT.format(text=text, max_tokens=max_tokens)

        response = ollama.generate(
            model=model,
            prompt=prompt,
            stream=False,
            options={
                "temperature": 0.3,  # Low temp for consistency
                "top_p": 0.9,
                "top_k": 40,
            },
        )

        if response and "response" in response:
            summary = response["response"].strip()
            return summary
        else:
            print(f"[WARNING] Empty response from Ollama")
            return None

    except Exception as e:
        print(f"[ERROR] Ollama summarization failed: {e}")
        return None


def process_chunks_folder(
    chunks_dir: Path,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> bool:
    """
    Process all chunks in a directory and create summarized versions.

    Args:
        chunks_dir: Directory containing chunk files
        model: Ollama model to use
        max_tokens: Max tokens for summaries

    Returns:
        True if successful
    """
    # Validate input directory
    if not chunks_dir.exists():
        print(f"[ERROR] Directory not found: {chunks_dir}")
        return False

    if not chunks_dir.is_dir():
        print(f"[ERROR] Not a directory: {chunks_dir}")
        return False

    # Get chunk files
    chunk_files = sorted(chunks_dir.glob("*.txt"))
    if not chunk_files:
        print(f"[ERROR] No chunk files found in: {chunks_dir}")
        return False

    print(f"[READ] Found {len(chunk_files)} chunk files")

    # Derive output directory
    book_name = chunks_dir.name.replace("chunks_", "")
    output_dir = chunks_dir.parent / f"summarized_chunks_{book_name}"

    # Check Ollama connection
    print(f"\n[OLLAMA] Checking connection to {OLLAMA_HOST}...")
    if not check_ollama_connection():
        return False

    print(f"[OLLAMA] Checking model: {model}...")
    if not check_model_available(model):
        print(f"[WARNING] Model {model} not found. Download with:")
        print(f"  ollama pull {model}")
        print(f"[INFO] Continuing anyway - will attempt to use model...\n")
    else:
        print(f"[OLLAMA] Model {model} available ✓\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Statistics
    stats = {
        "total_chunks": len(chunk_files),
        "successful": 0,
        "failed": 0,
        "total_input_chars": 0,
        "total_output_chars": 0,
        "total_time": 0,
    }

    # Metadata for chapters/sections
    chapter_metadata: Dict[int, str] = {}

    # Process each chunk
    print(f"[PROCESS] Summarizing {len(chunk_files)} chunks...\n")
    for idx, chunk_file in enumerate(chunk_files, 1):
        chunk_num = idx
        filename = chunk_file.name

        try:
            # Read chunk
            with open(chunk_file, 'r', encoding='utf-8', errors='replace') as f:
                chunk_content = f.read()

            input_size = len(chunk_content)
            stats["total_input_chars"] += input_size

            # Extract chapter/section name
            chapter_name = extract_chapter_name(chunk_content)
            chapter_metadata[chunk_num] = chapter_name

            # Summarize
            start_time = time.time()
            summary = summarize_chunk(chunk_content, model, max_tokens)
            elapsed = time.time() - start_time
            stats["total_time"] += elapsed

            if summary is None:
                print(f"[FAIL] Chunk {chunk_num:02d} ({filename}): Summarization failed")
                stats["failed"] += 1
                continue

            output_size = len(summary)
            stats["total_output_chars"] += output_size
            reduction_pct = (1 - output_size / input_size) * 100 if input_size > 0 else 0

            # Save summary with UTF-8 encoding and handle all characters
            output_file = output_dir / filename
            try:
                # Force UTF-8 encoding and replace any problematic chars
                with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
                    # Clean summary: encode to UTF-8 bytes then decode back, replacing bad chars
                    if isinstance(summary, str):
                        f.write(summary)
                    else:
                        f.write(str(summary))
            except UnicodeEncodeError as e:
                # Fallback: write with ASCII and replace non-ASCII characters
                with open(output_file, 'w', encoding='ascii', errors='replace') as f:
                    f.write(summary)

            print(f"[OK] {chunk_num:02d}. {filename}: {input_size:,} → {output_size:,} chars ({reduction_pct:.1f}% reduction, {elapsed:.1f}s)")
            stats["successful"] += 1

        except Exception as e:
            print(f"[ERROR] Chunk {chunk_num:02d} ({filename}): {e}")
            stats["failed"] += 1

    # Save chapter metadata
    metadata_file = output_dir / "chapter_metadata.json"
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(chapter_metadata, f, ensure_ascii=False, indent=2)
        print(f"[OK] Metadata saved: {metadata_file}")
    except Exception as e:
        print(f"[WARNING] Could not save metadata: {e}")

    # Statistics
    print(f"\n{'='*70}")
    print(f"[OK] Summarization Complete!\n")
    print(f"[STATS] Chunks processed: {stats['successful']}/{stats['total_chunks']}")
    print(f"[STATS] Failed: {stats['failed']}")
    print(f"[STATS] Total input: {stats['total_input_chars']:,} characters")
    print(f"[STATS] Total output: {stats['total_output_chars']:,} characters")
    if stats["total_input_chars"] > 0:
        overall_reduction = (1 - stats["total_output_chars"] / stats["total_input_chars"]) * 100
        print(f"[STATS] Overall reduction: {overall_reduction:.1f}%")
    print(f"[STATS] Total time: {stats['total_time']:.1f} seconds")
    if stats["successful"] > 0:
        avg_time = stats["total_time"] / stats["successful"]
        print(f"[STATS] Average time per chunk: {avg_time:.1f} seconds")
    print(f"\n[OUTPUT] Directory: {output_dir}")
    print(f"\n[NEXT] Use summarized chunks for final synthesis step!")

    return stats["failed"] == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Step 4: Summarize chunks with local Ollama LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: use qwen-coder-1.5b
  python 04_summarize_chunks.py intermediate_files/chunks_test_book

  # Use larger model
  python 04_summarize_chunks.py intermediate_files/chunks_test_book --model qwen2.5:14b

  # Custom max tokens for longer summaries
  python 04_summarize_chunks.py intermediate_files/chunks_test_book --max-tokens 500

Setup (one-time):
  ollama serve                              # Start Ollama in another terminal
  ollama pull qwen-coder-1.5b               # Download the lightweight model (~1GB)

This uses local Ollama for summarization - no API costs, works offline.
        """,
    )
    parser.add_argument("chunks_dir", help="Path to chunks_<book_name> directory")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Maximum tokens in each summary (default: {DEFAULT_MAX_TOKENS})",
    )
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)

    # Process
    success = process_chunks_folder(
        chunks_dir,
        model=args.model,
        max_tokens=args.max_tokens,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
