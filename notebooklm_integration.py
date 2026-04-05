#!/usr/bin/env python3
"""
NotebookLM Integration for Book Summarizer
===========================================
Automates the full pipeline: book → Claude summary → NotebookLM notebook
with audio overview, quiz, flashcards, and mind map generation.

Uses the unofficial `notebooklm-py` library (https://github.com/teng-lin/notebooklm-py).

Prerequisites:
  pip install "notebooklm-py[browser]" anthropic pypdf python-dotenv
  playwright install chromium
  notebooklm login          # one-time browser authentication

Usage:
  # Full pipeline: summarize book + create NotebookLM notebook
  python notebooklm_integration.py "Deep_Work.pdf" --title "Deep Work" --author "Cal Newport"

  # Only upload an existing summary to NotebookLM
  python notebooklm_integration.py --upload-only "deep_work_notebooklm_source.md" --title "Deep Work"

  # Create notebook + generate audio overview (podcast)
  python notebooklm_integration.py "book.pdf" --title "Book" --audio

  # Generate everything: audio, quiz, flashcards, mind map
  python notebooklm_integration.py "book.pdf" --title "Book" --all-artifacts

WARNING:
  notebooklm-py uses undocumented Google APIs that can break at any time.
  This is best for personal/research use. Not recommended for production.
"""

import os
import sys
import asyncio
import argparse
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the book summarizer (from the main pipeline script)
# ---------------------------------------------------------------------------
try:
    from book_summarizer import run_pipeline, Config, _slugify
except ImportError:
    # If book_summarizer.py is not in the same directory, provide guidance
    print("ERROR: book_summarizer.py must be in the same directory or on PYTHONPATH.")
    print("Download it from the pipeline package first.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# NotebookLM Client Wrapper
# ---------------------------------------------------------------------------

class NotebookLMIntegration:
    """
    Wraps notebooklm-py to provide a simple interface for book processing.

    Requires prior authentication via `notebooklm login` CLI command.
    """

    def __init__(self):
        self.client = None

    async def connect(self):
        """Initialize the NotebookLM client from stored auth."""
        try:
            from notebooklm import NotebookLMClient
        except ImportError:
            print("\nERROR: notebooklm-py is not installed.")
            print("Install it with:")
            print('  pip install "notebooklm-py[browser]"')
            print("  playwright install chromium")
            print("  notebooklm login  # one-time browser auth")
            sys.exit(1)

        try:
            self.client = await NotebookLMClient.from_storage()
            print("  Connected to NotebookLM successfully.")
        except Exception as e:
            print(f"\nERROR: Could not authenticate with NotebookLM: {e}")
            print("Run 'notebooklm login' first to authenticate via browser.")
            sys.exit(1)

        return self.client

    async def create_book_notebook(
        self,
        title: str,
        source_filepath: str,
        generate_audio: bool = False,
        generate_quiz: bool = False,
        generate_flashcards: bool = False,
        generate_mind_map: bool = False,
        output_dir: str = ".",
    ) -> dict:
        """
        Create a NotebookLM notebook for a book and populate it.

        Args:
            title: Book title (used as notebook name)
            source_filepath: Path to the markdown source file to upload
            generate_audio: Generate an Audio Overview (podcast)
            generate_quiz: Generate a quiz
            generate_flashcards: Generate flashcards
            generate_mind_map: Generate a mind map

        Returns:
            Dict with notebook_id and paths to generated artifacts
        """
        if not self.client:
            await self.connect()

        client = self.client
        results = {"notebook_id": None, "artifacts": {}}

        # Step 1: Create the notebook
        print(f"\n  Creating notebook: '{title}'...")
        nb = await client.notebooks.create(title)
        results["notebook_id"] = nb.id
        print(f"  Notebook created: {nb.id}")

        # Step 2: Add the source file
        # notebooklm-py supports adding text/markdown as pasted text
        print(f"  Adding source: {source_filepath}...")
        source_path = Path(source_filepath)

        if source_path.suffix.lower() in (".md", ".txt"):
            # Read content and add as pasted text
            with open(source_filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # notebooklm-py supports adding text content directly
            # The add_text method pastes text as a source
            await client.sources.add_text(
                nb.id,
                content,
                title=f"{title} — Analysis",
            )
            print("  Source added successfully.")
        elif source_path.suffix.lower() == ".pdf":
            # For PDFs, use the file upload method
            await client.sources.add_file(nb.id, str(source_path))
            print("  PDF source added successfully.")
        else:
            print(f"  WARNING: Unsupported source type {source_path.suffix}")
            print("  Supported: .md, .txt, .pdf")

        # Step 3: Run an initial Q&A to verify the source was indexed
        print("  Verifying source indexing...")
        try:
            verify = await client.chat.ask(nb.id, "What is this document about?")
            print(f"  NotebookLM says: {verify.answer[:150]}...")
        except Exception as e:
            print(f"  Verification skipped (source may still be indexing): {e}")

        # Step 4: Generate artifacts
        if generate_audio:
            print("\n  Generating Audio Overview (podcast)...")
            try:
                status = await client.artifacts.generate_audio(
                    nb.id,
                    instructions="Create an engaging discussion about the key ideas "
                                 "and practical takeaways from this book analysis. "
                                 "Focus on actionable insights.",
                )
                print("  Waiting for audio generation (this can take 2-5 minutes)...")
                await client.artifacts.wait_for_completion(nb.id, status.task_id)

                audio_path = os.path.join(output_dir, f"{_slugify(title)}_podcast.mp3")
                await client.artifacts.download_audio(nb.id, audio_path)
                results["artifacts"]["audio"] = audio_path
                print(f"  Audio saved to: {audio_path}")
            except Exception as e:
                print(f"  Audio generation failed: {e}")

        if generate_quiz:
            print("\n  Generating quiz...")
            try:
                status = await client.artifacts.generate_quiz(
                    nb.id,
                    difficulty="medium",
                )
                await client.artifacts.wait_for_completion(nb.id, status.task_id)

                quiz_path = os.path.join(output_dir, f"{_slugify(title)}_quiz.json")
                await client.artifacts.download_quiz(
                    nb.id, quiz_path, output_format="json"
                )
                results["artifacts"]["quiz"] = quiz_path
                print(f"  Quiz saved to: {quiz_path}")
            except Exception as e:
                print(f"  Quiz generation failed: {e}")

        if generate_flashcards:
            print("\n  Generating flashcards...")
            try:
                status = await client.artifacts.generate_flashcards(nb.id)
                await client.artifacts.wait_for_completion(nb.id, status.task_id)

                cards_path = os.path.join(output_dir, f"{_slugify(title)}_flashcards.md")
                await client.artifacts.download_flashcards(
                    nb.id, cards_path, output_format="markdown"
                )
                results["artifacts"]["flashcards"] = cards_path
                print(f"  Flashcards saved to: {cards_path}")
            except Exception as e:
                print(f"  Flashcard generation failed: {e}")

        if generate_mind_map:
            print("\n  Generating mind map...")
            try:
                status = await client.artifacts.generate_mind_map(nb.id)
                await client.artifacts.wait_for_completion(nb.id, status.task_id)

                map_path = os.path.join(output_dir, f"{_slugify(title)}_mindmap.json")
                await client.artifacts.download_mind_map(
                    nb.id, map_path, output_format="json"
                )
                results["artifacts"]["mind_map"] = map_path
                print(f"  Mind map saved to: {map_path}")
            except Exception as e:
                print(f"  Mind map generation failed: {e}")

        return results

    async def ask_book_questions(
        self,
        notebook_id: str,
        questions: list[str],
    ) -> list[dict]:
        """
        Ask a series of questions about a book in NotebookLM.
        Useful for targeted extraction after the summary is uploaded.
        """
        if not self.client:
            await self.connect()

        answers = []
        conversation_id = None

        for q in questions:
            print(f"\n  Q: {q}")
            result = await self.client.chat.ask(
                notebook_id, q, conversation_id=conversation_id
            )
            conversation_id = result.conversation_id
            print(f"  A: {result.answer[:200]}...")
            answers.append({
                "question": q,
                "answer": result.answer,
                "references": [
                    {"citation": r.citation_number, "source_id": r.source_id}
                    for r in (result.references or [])
                ],
            })

        return answers

    async def close(self):
        """Close the client connection."""
        if self.client:
            # The client context manager handles cleanup
            pass


# ---------------------------------------------------------------------------
# Full Pipeline: Book → Summary → NotebookLM
# ---------------------------------------------------------------------------

async def full_pipeline(
    filepath: str,
    title: str,
    author: str,
    output_dir: str = ".",
    generate_audio: bool = False,
    generate_all: bool = False,
):
    """Run the complete pipeline: extract, summarize, upload to NotebookLM."""

    print("=" * 60)
    print("  FULL PIPELINE: Book → Claude Summary → NotebookLM")
    print("=" * 60)

    # Step 1: Run the Claude summarization pipeline
    config = Config(include_notebooklm_source=True)
    summary_path = os.path.join(output_dir, f"{_slugify(title)}_summary.md")

    result = run_pipeline(
        filepath=filepath,
        book_title=title,
        author=author,
        output_path=summary_path,
        config=config,
    )

    nlm_source = result.get("notebooklm_source_path")
    if not nlm_source:
        print("ERROR: NotebookLM source file was not generated.")
        return

    # Step 2: Upload to NotebookLM and generate artifacts
    nlm = NotebookLMIntegration()
    async with await nlm.connect():
        nlm_result = await nlm.create_book_notebook(
            title=f"{title} — {author}",
            source_filepath=nlm_source,
            generate_audio=generate_audio or generate_all,
            generate_quiz=generate_all,
            generate_flashcards=generate_all,
            generate_mind_map=generate_all,
            output_dir=output_dir,
        )

    # Step 3: Summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Obsidian summary:    {summary_path}")
    print(f"  NotebookLM source:   {nlm_source}")
    print(f"  NotebookLM notebook: {nlm_result['notebook_id']}")
    for name, path in nlm_result.get("artifacts", {}).items():
        print(f"  {name:20s}: {path}")
    print(f"  Claude API cost:     ${result['total_cost']:.4f}")


async def upload_only(
    source_filepath: str,
    title: str,
    generate_audio: bool = False,
    generate_all: bool = False,
    output_dir: str = ".",
):
    """Upload an existing source file to NotebookLM."""
    nlm = NotebookLMIntegration()
    await nlm.connect()

    result = await nlm.create_book_notebook(
        title=title,
        source_filepath=source_filepath,
        generate_audio=generate_audio or generate_all,
        generate_quiz=generate_all,
        generate_flashcards=generate_all,
        generate_mind_map=generate_all,
        output_dir=output_dir,
    )

    print(f"\n  Notebook created: {result['notebook_id']}")
    for name, path in result.get("artifacts", {}).items():
        print(f"  {name}: {path}")

    await nlm.close()


# ---------------------------------------------------------------------------
# Interactive Q&A Mode
# ---------------------------------------------------------------------------

async def interactive_qa(notebook_id: str):
    """Open an interactive Q&A session with a NotebookLM notebook."""
    nlm = NotebookLMIntegration()
    await nlm.connect()

    print(f"\n  Interactive Q&A with notebook: {notebook_id}")
    print("  Type 'quit' to exit.\n")

    conversation_id = None
    while True:
        question = input("  You: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        result = await nlm.client.chat.ask(
            notebook_id, question, conversation_id=conversation_id
        )
        conversation_id = result.conversation_id
        print(f"\n  NotebookLM: {result.answer}\n")

    await nlm.close()
    print("  Session ended.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Integrate book summarization with NotebookLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Full pipeline: book → summary → NotebookLM
              python notebooklm_integration.py book.pdf --title "Deep Work" --author "Cal Newport"

              # Full pipeline with audio podcast
              python notebooklm_integration.py book.pdf --title "Deep Work" --author "Cal Newport" --audio

              # Full pipeline with ALL artifacts (audio, quiz, flashcards, mind map)
              python notebooklm_integration.py book.pdf --title "Deep Work" --author "Cal Newport" --all-artifacts

              # Upload existing source to NotebookLM only
              python notebooklm_integration.py --upload-only source.md --title "Deep Work"

              # Interactive Q&A with existing notebook
              python notebooklm_integration.py --qa NOTEBOOK_ID

            Setup (one-time):
              pip install "notebooklm-py[browser]" anthropic pypdf python-dotenv
              playwright install chromium
              notebooklm login
        """),
    )

    parser.add_argument("filepath", nargs="?", help="Path to book file or source file")
    parser.add_argument("--title", default="", help="Book title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    parser.add_argument("--audio", action="store_true", help="Generate audio overview")
    parser.add_argument("--all-artifacts", action="store_true",
                        help="Generate all artifacts (audio, quiz, flashcards, mind map)")
    parser.add_argument("--upload-only", metavar="FILE",
                        help="Upload existing source file to NotebookLM (skip summarization)")
    parser.add_argument("--qa", metavar="NOTEBOOK_ID",
                        help="Start interactive Q&A with a NotebookLM notebook")

    args = parser.parse_args()

    if args.qa:
        asyncio.run(interactive_qa(args.qa))
    elif args.upload_only:
        title = args.title or Path(args.upload_only).stem.replace("_", " ").title()
        asyncio.run(upload_only(
            source_filepath=args.upload_only,
            title=title,
            generate_audio=args.audio,
            generate_all=args.all_artifacts,
            output_dir=args.output_dir,
        ))
    elif args.filepath:
        title = args.title or Path(args.filepath).stem.replace("_", " ").title()
        author = args.author or "Unknown Author"
        asyncio.run(full_pipeline(
            filepath=args.filepath,
            title=title,
            author=author,
            output_dir=args.output_dir,
            generate_audio=args.audio,
            generate_all=args.all_artifacts,
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()