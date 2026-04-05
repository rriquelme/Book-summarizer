#!/usr/bin/env python3
"""
Step 1: Read & Extract Book
============================
Extract text from a book file (PDF, EPUB, TXT, MD) and save to a raw text file.

This is the first, foundational step of the pipeline: extract the book's text cleanly
without any processing, chunking, or LLM involvement.

Usage:
  python 01_read_book.py /path/to/book.pdf
  python 01_read_book.py my_book.epub
  python 01_read_book.py document.txt

Output:
  Saves extracted text to: intermediate_files/raw_book_<book_name>.txt

Philosophy:
  Simple, Transparent, Clear — focus on text extraction, nothing else.
  Understand how text flows through the pipeline before adding complexity.
"""

import sys
import argparse
from pathlib import Path

# Import shared extraction functions from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from book_summarizer import extract_text


def main():
    """Extract book text and save to intermediate file."""
    parser = argparse.ArgumentParser(
        description="Step 1: Extract text from a book file (PDF, EPUB, TXT, MD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 01_read_book.py ~/Downloads/deep_work.pdf
  python 01_read_book.py book.epub
  python 01_read_book.py document.txt
        """,
    )
    parser.add_argument("filepath", help="Path to book file (PDF, EPUB, TXT, MD)")
    args = parser.parse_args()

    book_path = Path(args.filepath)

    # Validate input file
    if not book_path.exists():
        print(f"[ERROR] File not found: {book_path}")
        sys.exit(1)

    if book_path.is_dir():
        print(f"[ERROR] {book_path} is a directory, not a file")
        sys.exit(1)

    # Create intermediate_files directory
    output_dir = Path(__file__).parent / "intermediate_files"
    output_dir.mkdir(exist_ok=True)

    # Extract book name (without extension) for output filename
    book_name = book_path.stem  # e.g., "deep_work" from "deep_work.pdf"

    # Output file path
    output_file = output_dir / f"raw_book_{book_name}.txt"

    print(f"\n[READ] Reading: {book_path.name}")
    print(f"   Size: {book_path.stat().st_size / (1024*1024):.1f} MB")
    print(f"   Format: {book_path.suffix.lower()}")

    try:
        # Extract text
        print("\n[EXTRACT] Extracting text...")
        text = extract_text(str(book_path))

        # Calculate statistics
        char_count = len(text)
        token_estimate = char_count / 4  # Rough estimate: 1 token ≈ 4 chars
        line_count = text.count("\n")
        word_count = len(text.split())

        # Save to file
        print(f"[SAVE] Saving to: {output_file.relative_to(Path.cwd())}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)

        # Print summary
        print(f"\n[OK] Extraction Complete!\n")
        print(f"[STATS] Statistics:")
        print(f"   Characters: {char_count:,}")
        print(f"   Words: {word_count:,}")
        print(f"   Lines: {line_count:,}")
        print(f"   Estimated tokens: {token_estimate:,.0f} (÷4 ratio)")
        print(f"\n[OUTPUT] File: {output_file}")
        print(f"\n[NEXT] Next step: Run 01_chunk_book.py to chunk this text")

    except Exception as e:
        print(f"\n[ERROR] Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
