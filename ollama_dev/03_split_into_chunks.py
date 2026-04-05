#!/usr/bin/env python3
"""
Step 3: Split Preprocessed Text into Chunks
=============================================
Split cleaned book text into manageable chunks using intelligent hierarchical strategy.

Input:  intermediate_files/raw_preprocessed_<name>.txt
Output: intermediate_files/chunks_<name>/ with 01_<name>.txt, 02_<name>.txt, etc.

Usage:
  # Default: intelligent hierarchical splitting (recommended)
  python 03_split_into_chunks.py intermediate_files/raw_preprocessed_test_book.txt

  # Force fixed-size splitting (5000 chars per chunk)
  python 03_split_into_chunks.py intermediate_files/raw_preprocessed_test_book.txt --method fixed --chunk-size 5000

Chunking Hierarchy (default method):
  1. Try chapters/parts/sections (best coherence)
  2. Try paragraph boundaries (text blocks ~5000+ chars)
  3. Try page boundaries [Page X]
  4. Fall back to fixed-size 5000-char chunks

Philosophy:
  Maximize semantic coherence by splitting at natural boundaries.
  Preserve meaning and context in each chunk for better extraction/analysis.
"""

import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    number: int
    content: str
    start_line: int
    end_line: int
    title: str = ""

    def __len__(self) -> int:
        """Return character count of chunk."""
        return len(self.content)

    def char_count(self) -> int:
        """Return character count."""
        return len(self.content)


def detect_chapter_boundaries(text: str) -> List[Tuple[int, str]]:
    """
    Detect chapter/section/part boundaries in text.
    Returns list of (line_number, title) tuples.

    Patterns (in priority order):
    - "Chapter N: Title"
    - "Part N: Title"
    - "SECTION/FOREWORD/DEDICATION" (all caps)
    """
    lines = text.split('\n')
    boundaries = []

    # Regex patterns for chapters/sections (in priority order)
    # Use word boundaries (\b) to match complete words only
    # Examples: "Chapter", "Chapter 1", "Chapter 1. Title", "Chapter Title"
    # Won't match: "party", "chapter123" (word boundary prevents partial matches)
    patterns = [
        # Chapter patterns (all cases) - with or without number
        # \b ensures "Chapter" is a complete word, followed by space/number/dot/end of line
        (r'^\bCHAPTER\b\s*\d*\.?\s*(.*)$', 'chapter'),
        (r'^\bChapter\b\s*\d*\.?\s*(.*)$', 'chapter'),
        (r'^\bchapter\b\s*\d*\.?\s*(.*)$', 'chapter'),
        # Part patterns (all cases) - with or without number
        # \b ensures "Part" is complete word, not "party", "partial", etc.
        (r'^\bPART\b\s*\d*\.?\s*(.*)$', 'part'),
        (r'^\bPart\b\s*\d*\.?\s*(.*)$', 'part'),
        (r'^\bpart\b\s*\d*\.?\s*(.*)$', 'part'),
        # Section patterns (all cases) - word boundaries to ensure complete words
        (r'^\b(FOREWORD|DEDICATION|EPILOGUE|CONCLUSION|APPENDIX|BIBLIOGRAPHY|INTRODUCTION|PREFACE|PROLOGUE|AFTERWORD|NOTES|INDEX|GLOSSARY)\b\s*(.*)$', 'section'),
        (r'^\b(Foreword|Dedication|Epilogue|Conclusion|Appendix|Bibliography|Introduction|Preface|Prologue|Afterword|Notes|Index|Glossary)\b\s*(.*)$', 'section'),
        # Special case: "About The Author" (multi-word, needs exact match)
        (r'^(ABOUT\s+THE\s+AUTHOR|About\s+The\s+Author)$', 'section'),
    ]

    for i, line in enumerate(lines):
        stripped_line = line.strip()
        for pattern, kind in patterns:
            match = re.match(pattern, stripped_line)
            if match:
                title = match.group(1) if match.lastindex and match.lastindex >= 1 else ""
                if not title:
                    title = stripped_line
                boundaries.append((i, f"{kind}: {title}"))
                break

    return boundaries


def detect_page_boundaries(text: str) -> List[Tuple[int, str]]:
    """
    Detect page markers in text.
    Returns list of (line_number, title) tuples.

    Patterns:
    - "[Page N]"
    """
    lines = text.split('\n')
    boundaries = []

    for i, line in enumerate(lines):
        match = re.match(r'^\[Page\s+(\d+)\]$', line.strip())
        if match:
            page_num = match.group(1)
            boundaries.append((i, f"page: {page_num}"))

    return boundaries


def detect_paragraph_boundaries(text: str, min_size: int = 500) -> List[Tuple[int, str]]:
    """
    Detect paragraph/block boundaries in text.
    Large blocks of text separated by blank lines become chunks.

    Returns list of (line_number, title) tuples.
    Only returns boundaries that would create chunks >= min_size.
    """
    lines = text.split('\n')
    boundaries = []

    # Look for double newlines (paragraph breaks)
    # and track text blocks between them
    current_block_start = 0
    current_block_chars = 0

    for i, line in enumerate(lines):
        if line.strip() == '':  # Empty line = paragraph break
            # Only create boundary if block is large enough
            if current_block_chars >= min_size:
                boundaries.append((i, f"paragraph break at {current_block_chars} chars"))
                current_block_start = i + 1
                current_block_chars = 0
        else:
            current_block_chars += len(line) + 1  # +1 for newline

    return boundaries


def split_by_chapters(text: str) -> List[Chunk]:
    """
    Split text using hierarchical strategy:
    1. Try chapters/parts/sections
    2. If few chapters, try paragraph boundaries (text blocks 5000+ chars)
    3. If still not working, try page boundaries
    4. Fall back to fixed-size (5000 chars)

    Returns:
        List of Chunk objects
    """
    lines = text.split('\n')

    # Strategy 1: Try chapter/part/section detection
    print("[STRATEGY] Trying chapters/parts/sections...")
    chapter_boundaries = detect_chapter_boundaries(text)

    if len(chapter_boundaries) >= 3:  # At least 3 chapters/sections
        print(f"[SUCCESS] Found {len(chapter_boundaries)} chapters/sections")
        chunks = _split_by_boundaries(text, chapter_boundaries, lines, min_chunk_size=1000)
        if chunks:
            return chunks

    # Strategy 2: Try paragraph boundaries (large text blocks)
    print("[STRATEGY] Trying paragraph boundaries (blocks ~5000 chars)...")
    paragraph_boundaries = detect_paragraph_boundaries(text, min_size=5000)

    if len(paragraph_boundaries) >= 2:  # At least 2 significant paragraphs
        print(f"[SUCCESS] Found {len(paragraph_boundaries)} paragraph boundaries")
        chunks = _split_by_boundaries(text, paragraph_boundaries, lines, min_chunk_size=1000)
        if chunks and len(chunks) >= 2:
            return chunks

    # Strategy 3: Try page boundaries
    print("[STRATEGY] Trying page boundaries...")
    page_boundaries = detect_page_boundaries(text)

    if len(page_boundaries) >= 3:  # At least 3 pages
        print(f"[SUCCESS] Found {len(page_boundaries)} pages")
        chunks = _split_by_boundaries(text, page_boundaries, lines, min_chunk_size=1000)
        if chunks:
            return chunks

    # Strategy 4: Fall back to fixed-size chunking
    print("[STRATEGY] No clear boundaries found, using fixed-size chunking (5000 chars)")
    return split_by_fixed_size(text, chunk_size=5000)


def _split_by_boundaries(text: str, boundaries: List[Tuple[int, str]], lines: List[str], min_chunk_size: int = 500) -> List[Chunk]:
    """
    Helper: Split text by a list of (line_number, title) boundaries.
    Always splits at newlines - never cuts words.
    Merges small chunks (< min_chunk_size chars) with the next chunk to avoid fragmentation.

    Args:
        text: Raw text
        boundaries: List of (line_number, title) tuples
        lines: Text split into lines
        min_chunk_size: Minimum chars for a chunk. Smaller chunks merge with next chunk (default: 500)

    Returns:
        List of Chunk objects, or empty list if splitting fails
    """
    raw_chunks = []

    # First pass: create raw chunks from boundaries
    for idx, (boundary_line, title) in enumerate(boundaries):
        start_line = boundary_line
        end_line = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)

        # Extract chunk content - always use complete lines
        chunk_lines = lines[start_line:end_line]
        content = '\n'.join(chunk_lines).strip()

        if content:  # Only create chunk if content exists
            chunk = Chunk(
                number=len(raw_chunks) + 1,
                content=content,
                start_line=start_line,
                end_line=end_line,
                title=title
            )
            raw_chunks.append(chunk)

    # Second pass: merge small chunks with next chunk(s) until reaching min size
    chunks = []
    i = 0
    while i < len(raw_chunks):
        current_chunk = raw_chunks[i]
        current_size = len(current_chunk.content)

        # If chunk is too small, keep merging with next chunks until we reach min_chunk_size
        if current_size < min_chunk_size and i < len(raw_chunks) - 1:
            merged_content = current_chunk.content
            merged_end_line = current_chunk.end_line
            j = i + 1

            # Keep merging with subsequent chunks until we reach min_chunk_size or end
            while current_size < min_chunk_size and j < len(raw_chunks):
                next_chunk = raw_chunks[j]
                merged_content += '\n\n' + next_chunk.content
                current_size += len(next_chunk.content) + 2  # +2 for \n\n
                merged_end_line = next_chunk.end_line
                j += 1

            # Create merged chunk
            merged_chunk = Chunk(
                number=len(chunks) + 1,
                content=merged_content.strip(),
                start_line=current_chunk.start_line,
                end_line=merged_end_line,
                title=current_chunk.title  # Keep first chunk's title
            )
            chunks.append(merged_chunk)
            i = j  # Move past all merged chunks
        else:
            # Keep chunk as is
            current_chunk.number = len(chunks) + 1
            chunks.append(current_chunk)
            i += 1

    return chunks


def split_by_fixed_size(text: str, chunk_size: int = 5000, overlap: int = 0) -> List[Chunk]:
    """
    Split text into fixed-size chunks.
    Always breaks at newlines - never cuts words or sentences.

    Args:
        text: Raw text to split
        chunk_size: Target chunk size in characters (will break at nearest newline)
        overlap: Line overlap between chunks (0 = no overlap)

    Returns:
        List of Chunk objects
    """
    lines = text.split('\n')
    chunks = []
    chunk_num = 0
    line_position = 0

    while line_position < len(lines):
        # Accumulate lines until we reach target chunk_size
        current_chunk_lines = []
        current_size = 0

        while line_position < len(lines):
            line = lines[line_position]
            # +1 for newline character
            line_with_newline_size = len(line) + 1

            # If adding this line exceeds chunk_size and we already have content, stop
            if current_size + line_with_newline_size > chunk_size and current_chunk_lines:
                break

            current_chunk_lines.append(line)
            current_size += line_with_newline_size
            line_position += 1

        # Create chunk from accumulated lines
        if current_chunk_lines:
            chunk_num += 1
            content = '\n'.join(current_chunk_lines).strip()

            chunk = Chunk(
                number=chunk_num,
                content=content,
                start_line=line_position - len(current_chunk_lines),
                end_line=line_position,
                title=f"Chunk {chunk_num}"
            )
            chunks.append(chunk)

        # Apply overlap (move back N lines)
        if overlap > 0:
            line_position = max(line_position - overlap, 0)
        else:
            # No overlap, move to next unprocessed lines
            pass

        if line_position >= len(lines):
            break

    return chunks


def save_chunks(chunks: List[Chunk], output_dir: Path, book_name: str) -> int:
    """
    Save chunks to individual files.

    Args:
        chunks: List of Chunk objects
        output_dir: Directory to save chunks
        book_name: Name of the book (for filename)

    Returns:
        Number of chunks saved
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for chunk in chunks:
        # Format: 01_<book_name>.txt, 02_<book_name>.txt, etc.
        chunk_num_str = f"{chunk.number:02d}"
        filename = f"{chunk_num_str}_{book_name}.txt"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            # Optional: add metadata header
            if chunk.title:
                f.write(f"[{chunk.title}]\n\n")
            f.write(chunk.content)

        print(f"[SAVE] {filename} ({chunk.char_count():,} chars)")

    return len(chunks)


def process_book(
    preprocessed_file: Path,
    method: str = "smart",
    chunk_size: int = 5000,
    overlap: int = 0,
) -> bool:
    """
    Process a preprocessed book file and split into chunks.

    Args:
        preprocessed_file: Path to raw_preprocessed_*.txt
        method: "smart" (hierarchical) or "fixed" (fixed-size)
        chunk_size: Size for fixed-size method (default: 5000)
        overlap: Overlap for fixed-size method (default: 0)

    Returns:
        True if successful
    """
    # Validate input
    if not preprocessed_file.exists():
        print(f"[ERROR] File not found: {preprocessed_file}")
        return False

    # Read preprocessed text
    print(f"[READ] Reading: {preprocessed_file.name}")
    try:
        with open(preprocessed_file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return False

    text_size = len(text)
    print(f"[STATS] Input size: {text_size:,} characters")

    # Derive output directory
    book_name = preprocessed_file.name.replace('raw_preprocessed_', '').replace('.txt', '')
    output_dir = preprocessed_file.parent / f'chunks_{book_name}'

    print(f"\n[CHUNK] Splitting text using '{method}' method...")

    # Split into chunks
    if method == "smart":
        chunks = split_by_chapters(text)
    elif method == "fixed":
        chunks = split_by_fixed_size(text, chunk_size, overlap)
    else:
        print(f"[ERROR] Unknown method: {method}")
        return False

    if not chunks:
        print("[ERROR] No chunks created")
        return False

    print(f"[STATS] Created {len(chunks)} chunks")

    # Save chunks
    print(f"\n[SAVE] Saving chunks to: {output_dir}")
    saved_count = save_chunks(chunks, output_dir, book_name)

    # Statistics
    total_chars = sum(len(c) for c in chunks)
    avg_chunk_size = total_chars / len(chunks) if chunks else 0

    print(f"\n[OK] Chunking Complete!\n")
    print(f"[STATS] Total chunks: {len(chunks)}")
    print(f"[STATS] Average chunk size: {avg_chunk_size:,.0f} characters")
    print(f"[STATS] Smallest chunk: {min(len(c) for c in chunks):,} characters")
    print(f"[STATS] Largest chunk: {max(len(c) for c in chunks):,} characters")
    print(f"[OUTPUT] Directory: {output_dir}")
    print(f"\n[NEXT] Chunks are ready for extraction/synthesis!")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Step 3: Split preprocessed text into chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: intelligent hierarchical splitting (tries chapters → paragraphs → pages → fixed)
  python 03_split_into_chunks.py intermediate_files/raw_preprocessed_test_book.txt

  # Force fixed-size splitting (5000 chars per chunk)
  python 03_split_into_chunks.py intermediate_files/raw_preprocessed_test_book.txt --method fixed --chunk-size 5000

  # Force fixed-size with custom size and overlap
  python 03_split_into_chunks.py intermediate_files/raw_preprocessed_test_book.txt --method fixed --chunk-size 8000 --overlap 500

Methods:
  smart (default) - Hierarchical: chapters → paragraphs → pages → fixed-size
  fixed           - Fixed-size chunks with optional overlap
        """,
    )
    parser.add_argument("preprocessed_file", help="Path to raw_preprocessed_*.txt file")
    parser.add_argument(
        "--method",
        choices=["smart", "fixed"],
        default="smart",
        help="Chunking method (default: smart hierarchical)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Chunk size in characters (for fixed method, default: 5000)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=0,
        help="Overlap between chunks in characters (for fixed method, default: 0)",
    )
    args = parser.parse_args()

    preprocessed_file = Path(args.preprocessed_file)

    # Process
    success = process_book(
        preprocessed_file,
        method=args.method,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
