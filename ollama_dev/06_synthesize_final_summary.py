#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 6: Combine Validated Summaries
====================================
Combine all validated chunk summaries into a single, organized document.
Preserves original practical structure without re-summarization.

Input:
  - intermediate_files/validated_chunks_<name>/ (corrected summaries)

Output:
  - <book_name>_final_summary.md (organized document with all summaries)

Usage:
  python 06_synthesize_final_summary.py intermediate_files/chunks_test_book

Philosophy:
  Load all validated, accurate chunk summaries and organize them into
  a cohesive document with table of contents and clear structure.
  No re-summarization - just organization and grouping.
"""

import sys
import io
import os
import json
import re
import argparse
from pathlib import Path
from typing import Dict
import time

# Force UTF-8 encoding globally
os.environ['PYTHONIOENCODING'] = 'utf-8'

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_validated_chunks(validated_dir: Path) -> tuple[Dict[int, str], Dict[str, str]]:
    """
    Load all validated chunk summaries and chapter metadata.

    Returns:
        (chunks dict, chapter_metadata dict)
    """
    chunk_files = sorted(validated_dir.glob("*.txt"))
    chunks = {}

    for chunk_file in chunk_files:
        # Extract chunk number from filename (e.g., "01_test_book.txt" -> 1)
        try:
            chunk_num = int(chunk_file.name.split("_")[0])
            with open(chunk_file, 'r', encoding='utf-8', errors='replace') as f:
                chunks[chunk_num] = f.read().strip()
        except (ValueError, IndexError):
            print(f"[WARNING] Could not parse chunk number from {chunk_file.name}")

    # Load chapter metadata if available
    chapter_metadata = {}
    metadata_file = validated_dir / "chapter_metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                chapter_metadata = json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not load metadata: {e}")

    return chunks, chapter_metadata


def generate_table_of_contents(chunks: Dict[int, str], chapter_metadata: Dict[str, str]) -> str:
    """Generate table of contents from chunk summaries with chapter names."""
    toc = "## Table of Contents\n\n"
    for num in sorted(chunks.keys()):
        # Get chapter name from metadata or use default
        chapter_name = chapter_metadata.get(str(num), f"Section {num}")
        # Sanitize for anchor link: lowercase, replace spaces/dots with hyphens, remove special chars
        anchor = re.sub(r'[^\w\s-]', '', chapter_name.lower())
        anchor = re.sub(r'\s+', '-', anchor)[:50]
        toc += f"- [{chapter_name}](#{anchor})\n"
    return toc + "\n"


def format_combined_summary(book_name: str, chunks: Dict[int, str], chapter_metadata: Dict[str, str]) -> str:
    """Format all summaries as a single organized document with chapter names."""
    title = book_name.replace('_', ' ').title()

    markdown = f"""# {title} - Summary

**Generated from**: {len(chunks)} validated sections
**Summary Date**: {time.strftime('%Y-%m-%d')}
**Format**: Direct combination of validated chunk summaries

---

"""

    # Add table of contents
    markdown += generate_table_of_contents(chunks, chapter_metadata)

    markdown += "---\n\n"

    # Add all summaries in order
    for num in sorted(chunks.keys()):
        # Get chapter name from metadata or use default
        chapter_name = chapter_metadata.get(str(num), f"Section {num}")
        markdown += f"## {chapter_name}\n\n"
        markdown += chunks[num]
        markdown += "\n\n---\n\n"

    # Add footer
    markdown += """---

*This document was generated through a multi-step pipeline:*
1. Text extraction and chunking
2. Local LLM analysis per chunk (preserving chapter/section names)
3. Quality assurance validation with corrections
4. Direct combination preserving original structure and chapter organization
"""

    return markdown


def process_combination(validated_dir: Path) -> bool:
    """
    Combine all validated summaries into final document.

    Args:
        validated_dir: Directory with validated chunk summaries

    Returns:
        True if successful
    """
    # Validate input directory
    if not validated_dir.exists():
        print(f"[ERROR] Directory not found: {validated_dir}")
        return False

    # Load all validated chunks and metadata
    print(f"[READ] Loading validated chunks from {validated_dir}...")
    chunks, chapter_metadata = load_validated_chunks(validated_dir)

    if not chunks:
        print(f"[ERROR] No validated chunk files found")
        return False

    print(f"[READ] Found {len(chunks)} validated chunks")
    if chapter_metadata:
        print(f"[READ] Found chapter metadata for organization\n")
    else:
        print(f"[WARNING] No chapter metadata found - using default section names\n")

    # Combine
    print(f"[COMBINE] Organizing {len(chunks)} summaries into final document...")
    start_time = time.time()
    combined_content = format_combined_summary(
        validated_dir.name.replace("validated_chunks_", ""),
        chunks,
        chapter_metadata
    )
    elapsed = time.time() - start_time

    if not combined_content:
        print(f"[ERROR] Combination produced empty result")
        return False

    print(f"[OK] Combination complete ({elapsed:.1f}s)\n")

    # Derive book name and output path
    book_name = validated_dir.name.replace("validated_chunks_", "")
    output_file = Path(f"{book_name}_final_summary.md")

    # Save
    try:
        with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
            f.write(combined_content)
    except Exception as e:
        print(f"[ERROR] Failed to write output: {e}")
        return False

    # Statistics
    print(f"{'='*70}")
    print(f"[OK] Final Summary Document Created!\n")
    print(f"[STATS] Sections combined: {len(chunks)}")
    print(f"[STATS] Document size: {len(combined_content):,} characters")
    print(f"[STATS] Combination time: {elapsed:.1f} seconds")
    print(f"\n[OUTPUT] File: {output_file}")
    print(f"\n[COMPLETE] Book summarization pipeline finished!")
    print(f"[NEXT] Review the final summary and use as needed!")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Step 6: Combine validated summaries into final document",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Combine validated chunks into final summary
  python 06_synthesize_final_summary.py intermediate_files/validated_chunks_test_book

Setup:
  Make sure you've run step 5 (05_validate_summaries.py) first

This is the final step that:
1. Loads all validated chunk summaries
2. Organizes them into a single document
3. Preserves original practical structure
4. Adds table of contents and clear section breaks
        """,
    )
    parser.add_argument("validated_dir", help="Path to validated_chunks_<book_name> directory")
    args = parser.parse_args()

    validated_dir = Path(args.validated_dir)

    # Process
    success = process_combination(validated_dir)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
