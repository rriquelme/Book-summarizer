#!/usr/bin/env python3
"""
Step 2: Preprocessing & Text Cleanup (Dictionary-Based)
========================================================
Clean raw book text using only a word dictionary - no LLM required.

This step fixes common OCR/extraction issues:
  - Split words: "U NLIMITED" -> "UNLIMITED", "M EMORY" -> "MEMORY"
  - Extra whitespace and formatting issues
  - Line breaks that break words
  - Maintains paragraph structure

Input:  intermediate_files/raw_book_<name>.txt
Output: intermediate_files/raw_preprocessed_<name>.txt

Usage:
  python 02_preprocessing_dictionary.py <raw_book_file>
  python 02_preprocessing_dictionary.py intermediate_files/raw_book_test_book.txt

Requirements:
  - None! Uses only Python stdlib + nltk (lightweight, one-time download)

Philosophy:
  Use simple pattern matching and a word dictionary to fix common OCR errors.
  No LLM, no Ollama, no freezing. Fast, reliable, educational.
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Set
from collections import defaultdict

# Try to load NLTK word list
try:
    from nltk.corpus import words
    nltk_available = True
except ImportError:
    nltk_available = False
    print("[WARNING] nltk not found. Using fallback dictionary.")
    print("  To install: pip install nltk")
    print("  Or NLTK will auto-download on first run.\n")


def get_word_set() -> Set[str]:
    """
    Load a set of valid English words for validation.

    Returns:
        Set of lowercase English words
    """
    if nltk_available:
        try:
            word_set = set(w.lower() for w in words.words())
            print(f"[DICT] Loaded {len(word_set)} words from NLTK")
            return word_set
        except LookupError:
            print("[WARNING] NLTK word list not downloaded. Downloading...")
            import nltk
            nltk.download("words", quiet=True)
            word_set = set(w.lower() for w in words.words())
            print(f"[DICT] Loaded {len(word_set)} words from NLTK")
            return word_set

    # Fallback: basic English word list (subset)
    fallback = {
        "the", "and", "to", "of", "a", "in", "is", "that", "it", "was",
        "for", "be", "on", "with", "as", "by", "at", "this", "have", "are",
        "from", "but", "not", "or", "an", "will", "my", "one", "all", "would",
        "there", "their", "what", "so", "up", "out", "if", "about", "who",
        "get", "which", "me", "when", "make", "can", "like", "time", "no",
        "just", "him", "know", "take", "people", "into", "year", "your",
        "good", "some", "could", "them", "see", "other", "than", "then",
        "now", "look", "only", "come", "its", "over", "think", "also",
        "back", "use", "two", "how", "our", "work", "first", "well", "way",
        "even", "new", "want", "because", "any", "these", "give", "day",
        "most", "us", "is", "has", "had", "does", "did", "do", "such",
        "where", "book", "memory", "unlimited", "chapter", "page", "text",
        "read", "write", "learn", "understand", "important", "key", "point",
    }
    print(f"[DICT] Using fallback dictionary ({len(fallback)} core words)")
    return fallback


def fix_split_words(text: str, word_dict: Set[str]) -> str:
    """
    Fix split words with letters separated by newlines/spaces.
    Handles:
    - "U\nNLIMITED" -> "UNLIMITED"
    - "J\ne\nt" -> "Jet"
    - "M\nEMORY" -> "MEMORY"

    Args:
        text: Raw text possibly containing split words
        word_dict: Set of valid words to match against

    Returns:
        Text with split words rejoined
    """

    # First pass: Handle simple case of single letter + word on next line
    # E.g., "U\nNLIMITED" or "S\nTRATEGIES" (very common in OCR)
    def rejoin_single_letter_word(match):
        """Rejoin single letter + multi-letter word"""
        letter = match.group(1)
        word = match.group(2)
        candidate = (letter + word).lower()

        # Rejoin if:
        # 1. Word is in dictionary, OR
        # 2. It's clearly an OCR split (single letter + 3+ letter word with common endings)
        is_obvious_split = (
            len(word) >= 3 and  # Rest is at least 3 letters
            len(candidate) >= 4  # Total is reasonable word length
        )

        if candidate in word_dict or is_obvious_split:
            return letter + word
        return match.group(0)

    # Match: single capital letter + newline + 2+ letters (capitals or mixed)
    # This handles "U\nNLIMITED" and "S\nTRATEGIES"
    text = re.sub(r'([A-Z])\n([A-Z][A-Za-z]+)', rejoin_single_letter_word, text)

    def rejoin_fragmented_word(match):
        """Rejoin heavily fragmented words, preserving word boundaries."""
        phrase = match.group(0)

        # Extract just the letters (remove all whitespace)
        letters_only = re.sub(r'[\n\s\t]+', '', phrase)

        # Only proceed if this looks like a fragmented word:
        # - Must have 3+ characters total
        # - Must contain a single letter at the start or multiple single letters in sequence
        # This avoids breaking up normal word sequences
        fragments = re.split(r'[\n\s\t]+', phrase.strip())

        # Check if this looks like a real fragmentation pattern
        # (first fragment is 1-2 chars, or we have 3+ fragments with avg length < 3)
        is_fragmented = False
        if len(fragments) >= 2:
            first_len = len(fragments[0])
            avg_len = sum(len(f) for f in fragments) / len(fragments)
            if first_len <= 2 or avg_len < 3:  # Signs of fragmentation
                is_fragmented = True

        if not is_fragmented:
            return phrase

        # Try matching sequences that form valid words
        words_found = []
        i = 0
        while i < len(letters_only):
            # Try progressively longer substrings (5, 4, 3, 2 letters)
            found = False
            for length in range(5, 1, -1):  # Try 5-2 char words
                if i + length <= len(letters_only):
                    potential_word = letters_only[i:i+length].lower()
                    if potential_word in word_dict and 2 <= length <= 5:
                        words_found.append(potential_word)
                        i += length
                        found = True
                        break

            if not found:
                # Couldn't find valid word starting at this position
                # Return original phrase (preserves the text even if we can't fix it)
                return phrase

        # If we successfully broke it into words, rejoin with spaces
        if 1 <= len(words_found) <= 10:  # Sanity check: 1-10 words
            return ' '.join(words_found)

        # Default: return original phrase if we couldn't make sense of it
        return phrase

    # Match: sequences of letter fragments (1-4 chars) separated by newlines/spaces
    # This catches fragmented words like:
    # - "U\nNLIMITED" -> "Unlimited" (2 fragments)
    # - "J\ne\nt" -> "Jet" (3 fragments)
    # - "O\nNE\n L\nAST\n T\nHING" -> "One Last Thing" (6 fragments)
    # Pattern: (1-4 letter chars) + (newline/space + 1-4 letter chars) repeated 1+ times (2+ fragments total)
    pattern = r'[A-Za-z]{1,4}(?:[\n\s]+[A-Za-z]{1,4}){1,}'
    result = re.sub(pattern, rejoin_fragmented_word, text)

    return result


def fix_whitespace(text: str) -> str:
    """
    Fix whitespace issues in a specific order:
    1. Convert all tabs to spaces
    2. Merge all consecutive whitespaces (multiple spaces) into 1
    3. Remove leading whitespace from lines that start with whitespace
    4. Remove empty lines
    """
    # Step 1: Convert all tabs to spaces
    text = text.replace('\t', ' ')

    # Step 2: Merge all consecutive whitespaces (multiple spaces) into 1 space
    # Do this per-line to preserve newlines
    lines = text.split('\n')
    lines = [re.sub(r' +', ' ', line) for line in lines]
    text = '\n'.join(lines)

    # Step 3: Remove leading whitespace from lines that start with whitespace
    lines = text.split('\n')
    lines = [line.lstrip() for line in lines]
    text = '\n'.join(lines)

    # Step 4: Remove empty lines
    lines = text.split('\n')
    lines = [line for line in lines if line.strip()]
    text = '\n'.join(lines)

    return text


def fix_line_breaks_in_words(text: str) -> str:
    """
    Fix line breaks that split words.
    E.g., "unli-\nmited" -> "unlimited"
    """
    # Hyphen at end of line -> join with next line
    text = re.sub(r'-\n+', '', text)

    # Also catch cases where word breaks without hyphen
    # This is trickier - only join if it looks like a word break
    # (short line ending in lowercase, next line starting with lowercase)
    def rejoin_broken_words(match):
        word1 = match.group(1)
        word2 = match.group(2)
        return word1 + word2

    # Line ending lowercase, newline, line starting lowercase, likely same word
    text = re.sub(r'([a-z]{2,})\n([a-z])', rejoin_broken_words, text)

    return text


def rejoin_space_split_words(text: str, word_dict: Set[str]) -> str:
    """
    Fix remaining space-split words like "S TRATEGIES" -> "STRATEGIES".

    This handles cases where a single letter is followed by whitespace (space/tab)
    and then the rest of the word.
    """
    def try_rejoin(match):
        letter = match.group(1)
        ws = match.group(2)  # captured whitespace
        rest = match.group(3)
        candidate = (letter + rest).lower()

        # Rejoin if it forms a valid word
        if candidate in word_dict:
            return letter + rest
        else:
            # Keep with single space
            return letter + ' ' + rest

    # Match: single letter + any whitespace (space/tab) + remaining word (all caps)
    # E.g., "S TRATEGIES" or "G RANDMASTER" or "H\tORSLEY"
    # Capture whitespace separately to normalize it
    pattern = r'([A-Z])([ \t]+)([A-Z]{2,})'
    result = re.sub(pattern, try_rejoin, text)

    return result


def preprocess_text(raw_text: str, word_dict: Set[str]) -> str:
    """
    Apply all preprocessing steps in order.

    Args:
        raw_text: Raw extracted text
        word_dict: Set of valid words

    Returns:
        Cleaned text
    """
    steps = [
        ("Fixing whitespace", fix_whitespace),
        ("Fixing split words", lambda t: fix_split_words(t, word_dict)),
        ("Fixing line breaks in words", fix_line_breaks_in_words),
        ("Fixing space-split words", lambda t: rejoin_space_split_words(t, word_dict)),
    ]

    result = raw_text
    for step_name, step_func in steps:
        print(f"[PROCESS] {step_name}...")
        result = step_func(result)

    return result


def process_full_book(raw_file: Path, output_file: Path) -> bool:
    """
    Process entire book using dictionary-based preprocessing.

    Args:
        raw_file: Path to raw_book_*.txt
        output_file: Path to save raw_preprocessed_*.txt

    Returns:
        True if successful, False otherwise
    """
    # Load dictionary
    print("[START] Loading word dictionary...")
    word_dict = get_word_set()

    # Read raw text
    print(f"\n[READ] Reading: {raw_file.name}")
    try:
        with open(raw_file, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return False

    original_size = len(raw_text)
    print(f"[STATS] Input size: {original_size:,} characters")

    # Preprocess
    print(f"\n[PREPROCESS] Running preprocessing steps...")
    cleaned_text = preprocess_text(raw_text, word_dict)

    # Save output
    print(f"\n[SAVE] Saving to: {output_file}")
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")
        return False

    # Statistics
    cleaned_size = len(cleaned_text)
    reduction = original_size - cleaned_size
    reduction_pct = (reduction / original_size * 100) if original_size > 0 else 0

    print(f"\n[OK] Preprocessing Complete!\n")
    print(f"[STATS] Input size: {original_size:,} characters")
    print(f"[STATS] Output size: {cleaned_size:,} characters")
    print(f"[STATS] Size reduction: {reduction:,} chars")
    print(f"[STATS] Reduction percentage: {reduction_pct:.2f}%")
    print(f"[OUTPUT] File: {output_file}")
    print(f"\n[NEXT] Next step: Run 03_chunk_book.py to chunk the cleaned text")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Step 2: Preprocess raw book text using dictionary (no LLM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 02_preprocessing_dictionary.py intermediate_files/raw_book_test_book.txt
  python 02_preprocessing_dictionary.py intermediate_files/raw_book_unlimited_memory.txt

This uses only a word dictionary - no LLM, no Ollama, no resource freezing.
Much faster than the Ollama version.
        """,
    )
    parser.add_argument("raw_book_file", help="Path to raw_book_*.txt file")
    args = parser.parse_args()

    raw_file = Path(args.raw_book_file)

    # Validate input
    if not raw_file.exists():
        print(f"[ERROR] File not found: {raw_file}")
        sys.exit(1)

    # Derive output filename
    book_name = raw_file.name.replace("raw_book_", "").replace(".txt", "")
    output_dir = raw_file.parent
    output_file = output_dir / f"raw_preprocessed_{book_name}.txt"

    # Process
    success = process_full_book(raw_file, output_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
