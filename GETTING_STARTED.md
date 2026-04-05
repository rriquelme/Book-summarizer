# Getting Started Checklist

Follow this checklist to get up and running in minutes.

---

## ✅ First-Time Setup (After Clone)

### 1. Install UV (if not already installed)
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify**: `uv --version`

### 2. Clone & Navigate
```bash
git clone https://github.com/your-username/Book-summarizer.git
cd Book-summarizer
```

### 3. Sync Dependencies (Creates `.venv` + installs everything)
```bash
uv sync
```

✅ **You're ready!** This took ~30 seconds.

---

## 🎯 Pick Your Pipeline

### Pipeline 1: Best Quality (Cloud API)
Uses Claude API for smart synthesis. Costs ~$0.10–$0.50 per book.

**Prerequisites**: `ANTHROPIC_API_KEY` in `.env`

```bash
# Create .env file
echo 'ANTHROPIC_API_KEY=sk-ant-your-key-here' > .env
```

**Run**:
```bash
uv run python book_summarizer.py "path/to/book.pdf" \
  --title "Book Title" \
  --author "Author Name"
```

---

### Pipeline 2: Zero Cost (Local Ollama)
Runs entirely on your machine. Free, no API costs.

**Prerequisites**: Ollama installed and running

```bash
# Install Ollama from https://ollama.ai
# Then start the server
ollama serve
```

**In another terminal, download a model** (one-time):
```bash
ollama pull qwen2.5:32b
```

**Run** (fully local, zero cost):
```bash
uv run python ollama_summarizer.py "path/to/book.pdf" \
  --title "Book Title"
```

---

### Pipeline 3: Best Value (Local + Claude)
Extract locally (free), synthesize with Claude (cheap). ~$0.05 per book.

**Prerequisites**: Ollama running + `ANTHROPIC_API_KEY` in `.env`

**Run**:
```bash
uv run python ollama_summarizer.py "path/to/book.pdf" \
  --claude-synthesis
```

---

### Pipeline 4: Interactive Learning (NotebookLM)
Upload summaries, generate podcasts, quizzes, flashcards. Costs ~$0.10 + browser auth.

**One-time setup**:
```bash
notebooklm login   # Browser-based Google auth
```

**Run**:
```bash
uv run python notebooklm_integration.py "path/to/book.pdf" \
  --title "Book Title" \
  --all-artifacts
```

---

## 📚 Examples by Use Case

### "I want the best summary quality"
```bash
# Setup
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env

# Run
uv run python book_summarizer.py "deep_work.pdf" --title "Deep Work"
```

### "I want zero cost"
```bash
# Setup (one-time)
ollama serve &
ollama pull qwen2.5:32b

# Run
uv run python ollama_summarizer.py "deep_work.pdf"
```

### "I want fast setup + good quality for cheap"
```bash
# Setup (one-time)
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
ollama serve &
ollama pull qwen2.5:32b

# Run
uv run python ollama_summarizer.py "deep_work.pdf" --claude-synthesis
```

### "I want to study the book interactively"
```bash
# Setup (one-time)
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
notebooklm login

# Run
uv run python notebooklm_integration.py "deep_work.pdf" \
  --title "Deep Work" --all-artifacts
```

---

## 🔄 Resuming Work Tomorrow

```bash
# Option A: Just run with uv (no activation)
uv run python book_summarizer.py "book.pdf"

# Option B: Activate venv manually
source .venv/bin/activate
python book_summarizer.py "book.pdf"
deactivate
```

That's it! No need to reinstall anything unless dependencies changed.

---

## 📝 Environment Variables (`.env` file)

Create a `.env` file in the repo root:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx-your-actual-key
```

⚠️ **Never commit this file** — it's in `.gitignore` for security.

---

## ❓ Troubleshooting

### "uv command not found"
→ Install UV first: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### "ModuleNotFoundError" when running scripts
→ Run `uv sync` to install dependencies

### "ANTHROPIC_API_KEY not found"
→ Create `.env` file with your Claude API key

### "Ollama connection refused"
→ Make sure `ollama serve` is running in another terminal

### "Model not found"
→ Download it first: `ollama pull qwen2.5:32b`

---

## 🚀 Next Steps

1. **Pick a pipeline** (see "Pick Your Pipeline" above)
2. **Read the full documentation**:
   - `README.md` — Complete guides and workflows
   - `CLAUDE.md` — Architecture and advanced config
   - `UV_QUICKSTART.md` — UV command reference
3. **Run your first book**:
   ```bash
   uv run python book_summarizer.py "your_book.pdf"
   ```
4. **Check the outputs**:
   - `*_summary.md` — Your Obsidian-ready summary
   - `*_notebooklm_source.md` — Source for NotebookLM upload
   - Cost breakdown at the end of the run

---

## 💡 Pro Tips

✅ Use `uv run` to avoid manual venv activation  
✅ Check `--help` for each script to see all options  
✅ Smaller `--chunk-size` = more detailed extractions  
✅ Keep `uv.lock` committed for reproducibility in teams  
✅ Use `ollama_summarizer.py` for testing (free, fast feedback)  

---

**Happy summarizing! 📚**

For detailed architecture, see `CLAUDE.md`.  
For quick UV commands, see `UV_QUICKSTART.md`.
