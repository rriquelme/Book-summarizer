# Book Summarizer

A token-efficient book summarization system with three powerful approaches: Claude API (best quality), local Ollama (zero cost), and NotebookLM integration (interactive learning).

**Goal**: Summarize books using minimal tokens/API costs, saving 80-90% compared to naive approaches.

---

## Quick Start: UV Setup Guide

**UV** is a modern, fast Python package manager written in Rust. It replaces pip, venv, and Poetry with a single tool that's 10-100x faster. This project uses UV for dependency management.

### 1️⃣ First Clone: Initial Setup

#### Step 1: Install UV
If you don't have UV installed, grab it in seconds:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip (if you prefer)
pip install uv
```

Verify installation:
```bash
uv --version
```

#### Step 2: Clone & Navigate
```bash
git clone https://github.com/your-username/Book-summarizer.git
cd Book-summarizer
```

#### Step 3: Create Virtual Environment & Install Dependencies
UV automatically creates and manages a virtual environment for you:

```bash
# Sync dependencies (creates .venv, installs all packages)
uv sync
```

That's it! ✅ UV has:
- Created a `.venv` directory with Python
- Installed all dependencies from `pyproject.toml`
- Generated a `uv.lock` file (dependency lockfile for reproducibility)

#### Step 4: Verify Setup
Test that everything works:
```bash
# View your virtual environment info
uv venv

# Run a quick test
uv run python --version
```

---

### 2️⃣ Resuming Work: Daily Development

After your first setup, resuming is simple:

```bash
# Just activate the virtual environment
source .venv/bin/activate          # macOS/Linux
# OR
.venv\Scripts\activate             # Windows PowerShell

# Then run your script
python book_summarizer.py --help
```

**Or, skip activation entirely** and use `uv run` (UV's recommended approach):
```bash
# Run any script directly without activating manually
uv run python book_summarizer.py "book.pdf" --title "Deep Work"

# Run Ollama pipeline
uv run python ollama_summarizer.py "book.pdf" --claude-synthesis

# Run NotebookLM integration
uv run python notebooklm_integration.py "book.pdf" --title "Book"
```

**If dependencies were added since you last worked:**
```bash
# Update your local environment to match uv.lock
uv sync
```

---

## UV Commands Cheat Sheet

| Task | Command | Notes |
|------|---------|-------|
| **First-time setup** | `uv sync` | Creates `.venv` and installs everything |
| **Run a script** | `uv run python script.py` | No manual venv activation needed |
| **Add a package** | `uv add package_name` | Adds to `pyproject.toml` + updates `uv.lock` |
| **Add dev package** | `uv add --dev pytest` | For dev tools (testing, linting, etc.) |
| **Update dependencies** | `uv sync` | Pulls latest from `uv.lock` |
| **Activate venv manually** | `source .venv/bin/activate` | If you prefer manual activation |
| **Install from pip format** | `uv pip install package` | Fallback for pip compatibility |
| **List installed packages** | `uv pip list` | See what's installed |
| **Lock dependencies** | `uv lock` | Regenerates `uv.lock` (auto-done by `uv add`) |
| **Python version mgmt** | `uv python install 3.11` | Install specific Python versions |

---

## Why UV?

✅ **10-100x faster** — Instant installs, parallel resolution  
✅ **Single tool** — Replaces pip, venv, poetry, pipx, pyenv  
✅ **Reproducible** — `uv.lock` ensures exact dependencies everywhere  
✅ **No activation required** — `uv run` just works  
✅ **Better error messages** — Clear dependency conflict explanations  

---

## Project Structure

```
Book-summarizer/
├── README.md                      # This file
├── CLAUDE.md                      # Claude Code guidance
├── pyproject.toml                 # Project metadata & dependencies
├── uv.lock                        # Locked dependencies (auto-generated)
├── .venv/                         # Virtual environment (created by uv sync)
│
├── book_summarizer.py             # Claude API pipeline (Haiku + Sonnet)
├── ollama_summarizer.py           # Local Ollama pipeline (zero-cost)
└── notebooklm_integration.py      # NotebookLM artifacts (audio, quizzes, etc)
```

---

## The Three Pipelines

### 🚀 Pipeline 1: Claude API (Best Quality)
Uses cheap Haiku model for extraction, smart Sonnet for synthesis.

```bash
uv run python book_summarizer.py "book.pdf" \
  --title "Deep Work" \
  --author "Cal Newport" \
  --output summary.md
```

**Cost**: ~$0.10–$0.50 per book | **Time**: ~2-5 min per 100k-token book

---

### 💻 Pipeline 2: Local Ollama (Zero Cost)
Extract locally with Ollama, optionally synthesize with Claude.

**Prerequisites**:
```bash
# Install and run Ollama (https://ollama.ai)
ollama serve

# In another terminal, download a model (one-time)
ollama pull qwen2.5:32b
```

**Fully local** (zero cost):
```bash
uv run python ollama_summarizer.py "book.pdf" \
  --title "Deep Work" \
  --model qwen2.5:32b
```

**Local + Claude synthesis** (best balance, ~$0.05):
```bash
uv run python ollama_summarizer.py "book.pdf" \
  --claude-synthesis
```

**Cost**: FREE (local) or ~$0.05 (hybrid) | **Time**: 5-20 min (depends on your CPU/GPU)

---

### 🎓 Pipeline 3: NotebookLM Integration (Interactive Learning)
Upload summaries, generate podcasts, quizzes, flashcards, mind maps.

**One-time setup**:
```bash
notebooklm login   # Browser-based Google auth
uv pip install "notebooklm-py[browser]"
```

**Generate summary + upload to NotebookLM**:
```bash
uv run python notebooklm_integration.py "book.pdf" \
  --title "Deep Work" \
  --author "Cal Newport"
```

**Generate ALL artifacts** (audio, quiz, flashcards, mind map):
```bash
uv run python notebooklm_integration.py "book.pdf" \
  --title "Deep Work" \
  --all-artifacts
```

**Cost**: ~$0.10 (Claude) + browser auth | **Interactive**: Yes (podcast, Q&A, flashcards)

---

## Environment Setup

### API Keys

Create a `.env` file in the repo root:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

UV and the scripts automatically load this via `python-dotenv`.

**Never commit `.env`** — it's already in `.gitignore`.

### Ollama Setup

Ollama runs locally and is completely separate from the cloud. Install from [ollama.ai](https://ollama.ai):

```bash
# Start Ollama server (runs in background)
ollama serve

# Download a model (one-time, ~20GB for qwen2.5:32b)
ollama pull qwen2.5:32b

# See available models
ollama list
```

---

## Common Workflows

### 📖 Summarize a Single Book (Best Quality)
```bash
uv run python book_summarizer.py my_book.pdf --title "Title" --author "Author"
```

### 🎯 Batch Process Books (Low Cost)
```bash
# Loop through PDFs in a folder
for book in books/*.pdf; do
  uv run python ollama_summarizer.py "$book" --claude-synthesis
done
```

### 🔧 Modify & Experiment
```bash
# Activate venv for interactive development
source .venv/bin/activate

# Or use uv run for one-off commands
uv run python -c "import book_summarizer; print(book_summarizer.Config())"
```

### 📊 Check Extraction Quality
```bash
# Run just the extraction step with custom prompt
# Edit EXTRACTION_PROMPT in book_summarizer.py, then run
uv run python book_summarizer.py --chunk-size 4000  # smaller chunks for more detail
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: uv` | Install UV: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ModuleNotFoundError` after cloning | Run `uv sync` to install dependencies |
| `ANTHROPIC_API_KEY not found` | Create `.env` file with your key (see "Environment Setup") |
| Ollama "model not found" | Run `ollama pull qwen2.5:32b` (or desired model) |
| Ollama "cannot connect" | Ensure `ollama serve` is running in another terminal |
| `.venv` issues | Delete `.venv` folder, re-run `uv sync` |

---

## VS Code Integration

Want to run scripts and debug from VS Code without typing commands?

**2-minute setup**:
1. Install "Python" extension (by Microsoft)
2. Run `uv sync` 
3. VS Code auto-detects `.venv` ✅

**Then**:
- Press F5 to debug scripts
- Press Ctrl+Shift+P → "UV: Run book_summarizer" to run interactively
- New terminal auto-activates `.venv`

👉 **See `VSCODE_SETUP.md` for detailed guide** (debugging, tasks, terminal integration, etc.)

---

## Next Steps

1. **For VS Code users**: Read `VSCODE_SETUP.md` (2-minute setup)
2. **Read CLAUDE.md** — Complete architecture and configuration guide
3. **Try Pipeline 1** — Run `uv run python book_summarizer.py --help` to see all options
4. **Explore Ollama** — Test locally with `ollama_summarizer.py` (free, fast)
5. **Check cost savings** — See end-of-run reports showing token/cost breakdowns

---

## Resources

- [UV Official Documentation](https://docs.astral.sh/uv/)
- [Real Python: Managing Projects with UV](https://realpython.com/python-uv/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Ollama Models](https://ollama.ai)
- [NotebookLM](https://notebooklm.google.com/)

---

## License

Summarize books responsibly. Respect copyright and author attribution.

---

**Happy summarizing! 📚** If you hit issues, check `CLAUDE.md` for detailed troubleshooting, or run `uv run python <script>.py --help` for script-specific guidance.
