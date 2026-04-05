# UV Quick Reference

**UV** is a modern, fast Python package manager written in Rust. It replaces pip, venv, poetry, and pipx.

## Installation

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

Verify: `uv --version`

---

## First Clone Setup (5 seconds)

```bash
git clone <repo>
cd Book-summarizer
uv sync
```

That's it! UV creates `.venv` and installs everything.

---

## Daily Development

### Option A: No Manual Activation (Recommended)
```bash
# Just run commands directly with uv run
uv run python book_summarizer.py "book.pdf"
uv run python ollama_summarizer.py "book.pdf"
uv run python notebooklm_integration.py "book.pdf"
```

### Option B: Manual Activation
```bash
# Activate venv
source .venv/bin/activate          # macOS/Linux
.venv\Scripts\activate             # Windows

# Run normally
python book_summarizer.py "book.pdf"

# Deactivate when done
deactivate
```

---

## Common Commands

### Setup & Maintenance
```bash
uv sync              # Install/update all dependencies
uv sync --upgrade    # Update to latest versions
```

### Adding Packages
```bash
uv add package_name           # Add to project
uv add --dev pytest           # Add dev tool
uv remove package_name        # Remove a package
```

### Running Code
```bash
uv run python script.py       # Run a script
uv run python -c "code"       # Run Python code
uv run pip list               # List installed packages
```

### Python Versions
```bash
uv python install 3.11        # Install specific Python version
uv python pin 3.11            # Set Python version for project
uv python list                # See installed Python versions
```

### Pip Compatibility
```bash
uv pip install package        # Pip-style install
uv pip freeze                 # Show requirements format
uv pip compile requirements.txt  # Compile requirements
```

---

## Project Structure (After `uv sync`)

```
.venv/                # Virtual environment (created by uv sync)
pyproject.toml        # Project config & dependencies
uv.lock              # Locked dependencies (reproducibility)
.env                 # API keys (create manually, don't commit)
```

---

## Useful Tips

✅ **Never commit `.venv` or `uv.lock`** in personal projects (they're auto-generated)  
✅ **Always commit `uv.lock`** in team projects (ensures reproducibility)  
✅ **No need to activate .venv manually** — just use `uv run`  
✅ **Add dependencies as you go** — `uv add package_name` updates `pyproject.toml` + `uv.lock`  
✅ **Update from pyproject.toml** — `uv sync` always uses `pyproject.toml` as source of truth  

---

## When to Use UV vs pip

| Task | UV | pip |
|------|----|----|
| Create/sync environment | ✅ `uv sync` | ❌ Manual setup |
| Add dependencies | ✅ `uv add` | ❌ Manual edit + pip install |
| Lock reproducible builds | ✅ Auto `uv.lock` | ❌ Manual `pip freeze` |
| Run scripts quickly | ✅ `uv run` | ❌ Manual activate |
| Manage Python versions | ✅ `uv python` | ❌ Need pyenv |
| Install CLI tools | ✅ `uv tool install` | ❌ Separate venv |

---

## Speed Comparison

```
Traditional pip:    ~30 seconds (resolve + install)
UV:                 ~1-2 seconds

Traditional venv setup + pip:    ~2 minutes
UV sync:                         ~5 seconds
```

---

## If Something Goes Wrong

```bash
# Nuke and rebuild
rm -rf .venv uv.lock
uv sync

# Check what's installed
uv pip list

# Check project config
cat pyproject.toml

# Update everything
uv sync --upgrade
```

---

## Resources

- 📖 [Official UV Docs](https://docs.astral.sh/uv/)
- 📝 [Real Python Guide](https://realpython.com/python-uv/)
- 🔗 [GitHub: astral-sh/uv](https://github.com/astral-sh/uv)

---

**For more details, see README.md or CLAUDE.md**
