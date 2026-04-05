#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 5: Validate and Correct Summaries (Quality Assurance Loop)
===============================================================
Validate each summarized chunk against the original to catch hallucinations
and ensure accuracy. This feedback loop corrects summaries based on actual content.

Input:
  - intermediate_files/chunks_<name>/ (original chunks)
  - intermediate_files/summarized_chunks_<name>/ (summarized versions)

Output:
  - intermediate_files/validated_chunks_<name>/ (corrected summaries)

Usage:
  python 05_validate_summaries.py intermediate_files/chunks_test_book

Philosophy:
  Verify summaries against originals. If summary contains inaccuracies or
  hallucinations, ask the LLM to fix based on the actual content.
"""

import sys
import io
import os
import re
import json
import argparse
from pathlib import Path
from typing import Optional, Tuple, Dict
import time

# Force UTF-8 encoding globally
os.environ['PYTHONIOENCODING'] = 'utf-8'

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

VALIDATION_PROMPT = """Review the original text and the summary provided.

ORIGINAL TEXT:
{original_text}

---

CURRENT SUMMARY:
{summary}

---

YOUR TASK:
1. Identify what the original text is actually about
2. Check if the summary accurately reflects the original content
3. Look for hallucinations, fabrications, or incorrect information in the summary

RESPOND WITH:
- Content Analysis: What is the original text about? (2-3 sentences)
- Has Useful Information: Yes/No - Is there valuable content to extract?
- Accuracy Check: Are there any errors or hallucinations in the summary?
- Corrections Needed: If yes to errors, provide a corrected version using ONLY actual content from the original text

Be strict about accuracy. Only keep information that is explicitly in the original text.
"""


def validate_chunk(original_text: str, summary: str, model: str = DEFAULT_MODEL) -> Tuple[bool, str]:
    """
    Validate a summary against its original chunk.

    Returns:
        (has_useful_info, corrected_summary)
    """
    if not original_text.strip() or not summary.strip():
        return False, ""

    try:
        prompt = VALIDATION_PROMPT.format(original_text=original_text, summary=summary)

        response = ollama.generate(
            model=model,
            prompt=prompt,
            stream=False,
            options={
                "temperature": 0.2,  # Very low for strict validation
                "top_p": 0.9,
                "top_k": 40,
            },
        )

        if response and "response" in response:
            validation_result = response["response"].strip()
            return True, validation_result
        else:
            return False, ""

    except Exception as e:
        print(f"[ERROR] Validation failed: {e}")
        return False, ""


def extract_corrected_summary(validation_result: str) -> str:
    """
    Extract the corrected summary from the validation result.
    Returns None if no corrections are needed.
    """
    result_lower = validation_result.lower()

    # Check if "Corrections Needed:" section says "None" or "No"
    corrections_match = re.search(
        r"Corrections\s+Needed:?\s*(None|No|N/A|none needed|no corrections|no corrections needed)",
        validation_result,
        re.IGNORECASE | re.DOTALL
    )
    if corrections_match:
        return None

    # Check for "No corrections" anywhere
    if "no corrections" in result_lower or "no correction" in result_lower:
        return None

    # Look for actual corrected version section
    patterns = [
        r"Corrections Needed:?\s*(.*?)(?:$|---|\n\n)",
        r"Corrected.*?Summary:?\s*(.*?)(?:$|---|\n\n)",
        r"Corrected.*?:?\s*(.*?)(?:$|---|\n\n)",
    ]

    for pattern in patterns:
        match = re.search(pattern, validation_result, re.DOTALL | re.IGNORECASE)
        if match:
            corrected = match.group(1).strip()
            # Make sure it's actual content, not "None" or similar
            if len(corrected) > 50 and corrected.lower() not in ["none", "no", "n/a"]:
                return corrected

    # If nothing found, it's likely accurate - return None
    return None


def process_validation(
    chunks_dir: Path,
    summarized_dir: Path,
    model: str = DEFAULT_MODEL,
) -> bool:
    """
    Validate all summaries against their originals.

    Args:
        chunks_dir: Directory with original chunks
        summarized_dir: Directory with summarized chunks
        model: Ollama model to use

    Returns:
        True if successful
    """
    # Validate input directories
    if not chunks_dir.exists() or not summarized_dir.exists():
        print(f"[ERROR] One or both directories not found")
        return False

    # Get chunk files
    chunk_files = sorted(chunks_dir.glob("*.txt"))
    if not chunk_files:
        print(f"[ERROR] No chunk files found")
        return False

    print(f"[READ] Found {len(chunk_files)} chunks to validate")

    # Derive output directory
    book_name = chunks_dir.name.replace("chunks_", "")
    output_dir = chunks_dir.parent / f"validated_chunks_{book_name}"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load chapter metadata if available
    metadata_file = summarized_dir / "chapter_metadata.json"
    chapter_metadata: Dict[str, str] = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                chapter_metadata = json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not load metadata: {e}")

    # Statistics
    stats = {
        "total_chunks": len(chunk_files),
        "accurate": 0,
        "corrected": 0,
        "skipped": 0,
        "total_time": 0,
    }

    # Process each chunk
    print(f"\n[VALIDATE] Validating {len(chunk_files)} summaries...\n")
    for idx, chunk_file in enumerate(chunk_files, 1):
        filename = chunk_file.name
        summarized_file = summarized_dir / filename

        if not summarized_file.exists():
            print(f"[SKIP] {idx:02d}. {filename}: No corresponding summary found")
            stats["skipped"] += 1
            continue

        try:
            # Read original and summary
            with open(chunk_file, 'r', encoding='utf-8', errors='replace') as f:
                original = f.read()

            with open(summarized_file, 'r', encoding='utf-8', errors='replace') as f:
                summary = f.read()

            # Validate
            start_time = time.time()
            has_info, validation = validate_chunk(original, summary, model)
            elapsed = time.time() - start_time
            stats["total_time"] += elapsed

            if not has_info:
                print(f"[SKIP] {idx:02d}. {filename}: No useful information to extract")
                stats["skipped"] += 1
                continue

            # Check if correction needed
            correction = extract_corrected_summary(validation)

            if correction is None:
                # Summary is accurate
                print(f"[OK] {idx:02d}. {filename}: Accurate ({elapsed:.1f}s)")
                # Save original summary as validated
                output_file = output_dir / filename
                with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(summary)
                stats["accurate"] += 1

            else:
                # Summary needs correction
                print(f"[CORRECT] {idx:02d}. {filename}: Corrected ({elapsed:.1f}s)")
                # Save corrected version
                output_file = output_dir / filename
                with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(correction)
                stats["corrected"] += 1

        except Exception as e:
            print(f"[ERROR] {idx:02d}. {filename}: {e}")
            stats["skipped"] += 1

    # Save chapter metadata to output
    if chapter_metadata:
        output_metadata_file = output_dir / "chapter_metadata.json"
        try:
            with open(output_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(chapter_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Could not save output metadata: {e}")

    # Statistics
    print(f"\n{'='*70}")
    print(f"[OK] Validation Complete!\n")
    print(f"[STATS] Total chunks: {stats['total_chunks']}")
    print(f"[STATS] Accurate: {stats['accurate']}")
    print(f"[STATS] Corrected: {stats['corrected']}")
    print(f"[STATS] Skipped: {stats['skipped']}")
    print(f"[STATS] Total time: {stats['total_time']:.1f} seconds")
    if (stats['accurate'] + stats['corrected']) > 0:
        avg_time = stats['total_time'] / (stats['accurate'] + stats['corrected'])
        print(f"[STATS] Average validation time: {avg_time:.1f} seconds")
    print(f"\n[OUTPUT] Directory: {output_dir}")
    print(f"\n[NEXT] Validated summaries ready for final synthesis!")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Step 5: Validate and correct summarized chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: validate all summaries
  python 05_validate_summaries.py intermediate_files/chunks_test_book

Setup:
  Make sure Ollama is running: ollama serve
  Make sure you've run step 4 (04_summarize_chunks.py) first

This step provides quality assurance by:
1. Comparing each summary against the original chunk
2. Identifying hallucinations and inaccuracies
3. Correcting summaries based on actual content
4. Creating validated versions for final synthesis
        """,
    )
    parser.add_argument("chunks_dir", help="Path to chunks_<book_name> directory")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    summarized_dir = chunks_dir.parent / chunks_dir.name.replace("chunks_", "summarized_chunks_")

    # Check Ollama connection
    print(f"[OLLAMA] Checking connection to {OLLAMA_HOST}...")
    try:
        response = ollama.list()
        print(f"[OLLAMA] Connection OK\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to Ollama: {e}")
        return False

    # Process
    success = process_validation(chunks_dir, summarized_dir, model=args.model)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
