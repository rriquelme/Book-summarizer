# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Using UV in This Project

This project uses **UV**, a modern, fast Python package manager written in Rust. UV replaces pip, venv, poetry, and pipx.

**Quick start**:
```bash
uv sync              # First-time: creates .venv and installs dependencies
uv run python ...    # Run scripts directly (no manual activation needed)
uv add package_name  # Add new dependencies
```

**Why UV?**
- ⚡ 10-100x faster than pip
- 📦 Single tool replaces pip, venv, poetry, pipx, pyenv
- 🔒 Reproducible builds with `uv.lock`
- ✨ No need to manually activate virtual environments

**For detailed UV usage**, see:
- `GETTING_STARTED.md` — Step-by-step first setup
- `UV_QUICKSTART.md` — Command reference cheat sheet
- `README.md` — Workflow examples

## Project Overview

**Book Summarizer** — A token-efficient book summarization system with three approaches:
1. **book_summarizer.py** — Claude API pipeline (Haiku extraction + Sonnet synthesis)
2. **ollama_summarizer.py** — Local Ollama pipeline (zero-cost or Ollama + Claude hybrid)
3. **notebooklm_integration.py** — NotebookLM integration (upload summaries, generate artifacts)

Core strategy: Chunk books → extract key concepts per chunk (cheap/local) → synthesize into structured summary (expensive/smart).

## Architecture & Strategy

### Token-Efficient Chunking
- Split books into manageable chunks by chapter or fixed size (~8000 tokens)
- Use **Haiku** for per-chunk extraction (cheap: $1/$5 per M tokens)
- Use **Sonnet** for final synthesis (smart: $3/$15 per M tokens)
- Saves **80-90% on costs** vs. sending full book to Sonnet

### Three Execution Paths

| Script | Extraction | Synthesis | Cost | Use Case |
|--------|-----------|-----------|------|----------|
| `book_summarizer.py` | Claude Haiku | Claude Sonnet | ~$0.10-$0.50/book | Best quality, reasonable cost |
| `ollama_summarizer.py` (local) | Ollama (local) | Ollama (local) | FREE | Zero cost, works offline |
| `ollama_summarizer.py` (hybrid) | Ollama (local) | Claude Sonnet | ~$0.05/book | Best cost/quality tradeoff |
| `notebooklm_integration.py` | N/A | Claude + NotebookLM | ~$0.10 + browser auth | Interactive Q&A, podcasts, quizzes |

### Shared Components
- **Text extraction**: PDF, EPUB, TXT, Markdown — routes to appropriate parser
- **Chapter detection**: Regex patterns for common chapter formats
- **Extraction/synthesis prompts**: Reused across all pipelines (constants at top of `book_summarizer.py`)

## Running Each Pipeline

### Claude API Pipeline (Best Quality)
```bash
# Basic usage
python book_summarizer.py "book.pdf" --title "Deep Work" --author "Cal Newport"

# With output path and custom models
python book_summarizer.py book.pdf --output summary.md \
  --extraction-model claude-haiku-4-5-20251001 \
  --synthesis-model claude-sonnet-4-6

# Skip NotebookLM source generation
python book_summarizer.py book.pdf --no-notebooklm

# Custom chunking
python book_summarizer.py book.pdf --chunk-size 10000
```

**Requires**: `ANTHROPIC_API_KEY` env var

### Local Ollama Pipeline (Zero Cost)
```bash
# First ensure Ollama is running and model is downloaded
ollama serve
ollama pull qwen2.5:32b

# Fully local extraction & synthesis
python ollama_summarizer.py "book.pdf" --title "Deep Work" --author "Cal Newport"

# Local extraction + Claude synthesis (best quality/cost balance)
python ollama_summarizer.py book.pdf --claude-synthesis

# Use smaller/different model
python ollama_summarizer.py book.pdf --model "qwen2.5:14b"

# See recommended models
python ollama_summarizer.py --list-models
```

**Requires**: Ollama running locally, model downloaded, `ANTHROPIC_API_KEY` env var (only for `--claude-synthesis`)

### NotebookLM Integration
```bash
# First-time setup (browser auth, one-time)
notebooklm login
pip install "notebooklm-py[browser]"
playwright install chromium

# Full pipeline: book → summary → NotebookLM
python notebooklm_integration.py "book.pdf" --title "Deep Work" --author "Cal Newport"

# With audio overview
python notebooklm_integration.py book.pdf --title "Deep Work" --author "Cal Newport" --audio

# All artifacts: audio + quiz + flashcards + mind map
python notebooklm_integration.py book.pdf --title "Deep Work" --all-artifacts

# Upload existing summary to NotebookLM
python notebooklm_integration.py --upload-only summary.md --title "Deep Work"

# Interactive Q&A with existing notebook
python notebooklm_integration.py --qa NOTEBOOK_ID
```

**Requires**: Browser auth via `notebooklm login` (Google account)

## Configuration & Customization

### book_summarizer.py — Config Class
```python
@dataclass
class Config:
    extraction_model: str = "claude-haiku-4-5-20251001"    # cheap extraction
    synthesis_model: str = "claude-sonnet-4-6"              # quality synthesis
    chunk_size: int = 8000                  # tokens; ~32k chars per chunk
    chunk_overlap: int = 500                # tokens; context at boundaries
    extraction_max_tokens: int = 2000       # per-chunk output limit
    synthesis_max_tokens: int = 4096        # final summary output limit
    output_format: str = "obsidian"         # obsidian | plain | notebooklm
    include_notebooklm_source: bool = True  # generate NotebookLM-compatible file
    track_costs: bool = True                # show cost breakdown
```

Modify via CLI args (see `--help`) or edit `Config()` defaults.

### ollama_summarizer.py — OllamaConfig Class
```python
@dataclass
class OllamaConfig:
    ollama_model: str = "qwen2.5:32b"       # main model (20GB RAM)
    ollama_host: str = "http://localhost:11434"
    ollama_timeout: float = 300.0           # 5 min timeout
    use_claude_synthesis: bool = False      # local-only vs. hybrid
    claude_model: str = "claude-sonnet-4-6" # if hybrid
    chunk_size: int = 6000                  # slightly smaller for local
    num_ctx: int = 16384                    # Ollama context window
```

### Pricing Reference (March 2026)
```python
PRICING = {
    "claude-haiku-4-5-20251001":   {"input": $1.00, "output": $5.00},
    "claude-sonnet-4-6":            {"input": $3.00, "output": $15.00},
    "claude-opus-4-6":              {"input": $5.00, "output": $25.00},
}
```

Updated in `book_summarizer.py:389`. Recalculate cost savings after price changes.

## Dependencies

### Core
- `anthropic` — Claude API client
- `pypdf` — PDF text extraction
- `ebooklib`, `beautifulsoup4` — EPUB parsing
- `python-dotenv` — Load `.env` for `ANTHROPIC_API_KEY`

### Ollama Pipeline
- `ollama` — Python client for local Ollama

### NotebookLM Pipeline
- `notebooklm-py[browser]` — Unofficial NotebookLM API (uses Playwright)
- `playwright` — Browser automation for NotebookLM auth

### Optional
- Models in Ollama: `qwen2.5:32b`, `qwen2.5:14b`, `llama3:70b`, etc.

Install all with:
```bash
pip install anthropic pypdf ebooklib beautifulsoup4 python-dotenv
pip install ollama "notebooklm-py[browser]"
playwright install chromium
```

## Key Outputs

- **`{title}_summary.md`** — Final Obsidian-formatted summary with YAML frontmatter, headings, blockquotes, and wiki links
- **`{title}_notebooklm_source.md`** — Per-section analysis file (for NotebookLM upload or standalone reading)
- **`{title}_podcast.mp3`** — Audio overview (NotebookLM pipeline only)
- **`{title}_quiz.json`** / **`{title}_flashcards.md`** / **`{title}_mindmap.json`** — Artifacts from NotebookLM

## Cost Estimation

**Example: 100k-token book**
- Full API pipeline (Haiku + Sonnet): ~$0.40
- Ollama fully local: FREE
- Ollama + Claude: ~$0.05
- Naive Sonnet-only approach: ~$2.00

Cost breakdown is printed at end of each run.

## Supported File Formats
- PDF (`.pdf`) — via `pypdf`
- EPUB (`.epub`) — via `ebooklib` + BeautifulSoup
- Plain text (`.txt`, `.md`)

## Environment Variables
- `ANTHROPIC_API_KEY` — Required for Claude API (all pipelines except fully-local Ollama)
- `.env` file in repo root is auto-loaded by `load_dotenv()`

## NotebookLM Caveats
- Uses unofficial `notebooklm-py` library (undocumented Google APIs — can break)
- Requires one-time browser authentication (`notebooklm login`)
- Best for personal/research use, not production
- File uploads may time out; markdown/text preferred

## Development Notes

### Text Extraction Flow
1. `extract_text()` routes by file extension
2. Format-specific extractors clean/normalize output
3. Character count → approximate token estimate (÷4 ratio)

### Chunking Strategy
1. Tries `detect_chapters()` first (regex patterns for common formats)
2. Falls back to `_fixed_chunk()` if no chapters found
3. Breaks at paragraph/sentence boundaries when possible
4. Overlap ensures context isn't lost at chunk edges

### Prompt Engineering
- **Extraction**: "Deep analysis" of core arguments, evidence, takeaways, connections
- **Synthesis**: Build "comprehensive, actionable summary" for knowledge worker's wiki

Both prompts are structured (5-6 major sections) to ensure depth while staying under token limits.

### Cost Tracking
- `calculate_cost()` multiplies tokens × pricing
- Comparative cost shown: "Savings with pipeline approach: 80%"
- Update `PRICING` dict if Claude pricing changes

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ANTHROPIC_API_KEY not set` | Create `.env` file or `export ANTHROPIC_API_KEY="sk-..."` |
| Ollama "model not found" | Run `ollama pull qwen2.5:32b` |
| Ollama "cannot connect" | Ensure `ollama serve` is running |
| NotebookLM auth fails | Run `notebooklm login` in fresh terminal, restart script |
| PDF text corrupted | Try EPUB format or inspect with `pypdf` directly |
| OutOfMemory (Ollama) | Use smaller model (`qwen2.5:14b` or `llama3:8b`) |

## Recommended Setups

**For best quality**: `book_summarizer.py` (Haiku + Sonnet)  
**For zero cost**: `ollama_summarizer.py` with `qwen2.5:32b` (fully local)  
**For best balance**: `ollama_summarizer.py --claude-synthesis` (local extraction + Claude synthesis)  
**For interactive learning**: `notebooklm_integration.py` with `--all-artifacts` (notebooks, quizzes, audio)
