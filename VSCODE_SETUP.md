# VS Code Setup for UV

Configure VS Code to work seamlessly with UV. This guide covers interpreter selection, running scripts, debugging, and terminal integration.

---

## ✅ Quick Setup (2 minutes)

### 1. Install Required Extensions

Open VS Code and install these from the Extensions marketplace:

- **Python** (ms-python.python) — Official Python extension
- **Ruff** (charliermarsh.ruff) — Fast linter & formatter
- (Optional) **Pylance** for advanced IntelliSense

### 2. Run `uv sync`

```bash
uv sync
```

This creates `.venv/` in your project. VS Code auto-detects it.

### 3. Select Python Interpreter

**Option A: Auto-Detection (Recommended)**
- Open any Python file
- VS Code should automatically detect `.venv/bin/python`

**Option B: Manual Selection**
- Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
- Type "Python: Select Interpreter"
- Choose `./.venv/bin/python` (or the .venv path shown)

✅ **Done!** VS Code is now using the UV virtual environment.

---

## 🎯 What You Get

### ✨ Features Enabled

| Feature | What It Does |
|---------|-------------|
| **Code Completion** | IntelliSense uses UV's `.venv` packages |
| **Linting** | Ruff checks code on save (configured in `pyproject.toml`) |
| **Formatting** | Auto-format on save using Ruff |
| **Debugging** | F5 to debug with proper environment |
| **Terminal** | New terminal activates `.venv` automatically |
| **Type Checking** | Basic type hints shown inline |

### 🚀 Run Scripts from VS Code

**Press `Ctrl+Shift+P` and run tasks**:
- "UV: Sync Dependencies" — Install packages
- "UV: Run book_summarizer" — Interactive script runner
- "UV: Run ollama_summarizer" — Interactive script runner
- "UV: Python REPL" — Start Python interactive shell
- "UV: List Installed Packages" — Show what's installed

**Example**: Press `Ctrl+Shift+P`, type "UV: Run book_summarizer", enter book path, done!

---

## 🐛 Debugging

### Debug a Script

1. Open the script (e.g., `book_summarizer.py`)
2. Set breakpoints by clicking line numbers (red dots appear)
3. Press **F5** or go to Run → Start Debugging
4. Choose a configuration:
   - `Python: book_summarizer` — Debug with sample args
   - `Python: ollama_summarizer` — Debug Ollama pipeline
   - `Python: Current File` — Debug any open file

### Debug with Custom Arguments

Edit `.vscode/launch.json` and modify the `"args"` array:

```json
"args": [
    "my_book.pdf",
    "--title", "My Book Title",
    "--author", "Author Name"
]
```

Then press F5 to debug with those arguments.

---

## 🖥️ Terminal Integration

### Auto-Activate `.venv` on Terminal Open

VS Code automatically activates your UV virtual environment when you open a new terminal.

**In VS Code terminal**:
```bash
# .venv is already active!
python --version           # Shows your project's Python
python book_summarizer.py  # Runs without 'uv run'
```

### If Auto-Activation Doesn't Work

Add this to `.vscode/settings.json` (already included):
```json
"python.terminal.executeInFileDir": true,
"python.terminal.focusAfterLaunch": true
```

---

## 🔧 Customizing VS Code

### Edit `.vscode/settings.json`

Common customizations:

```json
{
    // Use 4 spaces for indentation
    "editor.insertSpaces": true,
    "editor.tabSize": 4,

    // Format on save
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "charliermarsh.ruff"
    },

    // Word wrap for long lines
    "editor.wordWrap": "on",

    // Show whitespace
    "editor.renderWhitespace": "all",

    // Python-specific settings
    "python.analysis.typeCheckingMode": "basic",
    "python.linting.enabled": true
}
```

### Edit `.vscode/launch.json` (Debugging)

Add new debug configs for different scenarios:

```json
{
    "name": "Python: Debug with Ollama",
    "type": "python",
    "request": "launch",
    "program": "${workspaceFolder}/ollama_summarizer.py",
    "console": "integratedTerminal",
    "args": ["test.pdf", "--model", "qwen2.5:14b"]
}
```

### Edit `.vscode/tasks.json` (Custom Tasks)

Tasks are like shortcuts. Press `Ctrl+Shift+P` → "Run Task" to see them.

Example task:
```json
{
    "label": "My Custom Task",
    "type": "shell",
    "command": "uv",
    "args": ["run", "python", "book_summarizer.py"],
    "presentation": {
        "reveal": "always",
        "panel": "new"
    }
}
```

---

## ❓ Troubleshooting

### "Python interpreter not found"

1. **Check VS Code has Python extension**:
   - Open Extensions (Ctrl+Shift+X)
   - Search for "Python" (by Microsoft)
   - Click Install

2. **Run `uv sync` in terminal**:
   ```bash
   uv sync
   ```

3. **Manually select interpreter**:
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose `./.venv/bin/python`

### "Module not found" when running scripts

- Run `uv sync` to install dependencies
- Reload VS Code (Ctrl+R or Cmd+R)
- Select interpreter again (see above)

### Linting not working

1. **Install Ruff extension**:
   - Extensions → Search "Ruff"
   - Install "Ruff" by Astral

2. **Check pyproject.toml**:
   - Ruff settings are read from `pyproject.toml`
   - Verify `[tool.ruff]` section exists

3. **Restart VS Code**:
   ```
   Ctrl+Shift+P → "Developer: Reload Window"
   ```

### Formatting not auto-saving

Add to `.vscode/settings.json`:
```json
"editor.formatOnSave": true,
"[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
}
```

### Terminal doesn't activate `.venv`

Make sure `.vscode/settings.json` includes:
```json
"python.terminal.executeInFileDir": true
```

Then open a new terminal (Ctrl+`).

---

## 📚 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+P` | Command Palette (find tasks, settings, etc.) |
| `F5` | Start debugging |
| `Ctrl+K Ctrl+0` | Fold all regions |
| `Ctrl+Shift+F` | Format entire file (uses Ruff) |
| `Ctrl+.` | Quick fix / suggestions |
| `Ctrl+`` | Open terminal |
| `Ctrl+J` | Toggle bottom panel (terminal) |

---

## 🎯 Workflow: Development Loop

### 1. Edit Code
```
Open file → Make changes → Ctrl+Shift+F (format)
```

### 2. Run & Debug
```
F5 (or Ctrl+Shift+P → "UV: Run...")
```

### 3. Check Output
```
Output appears in terminal at bottom
```

### 4. Add Dependencies
```
Ctrl+Shift+P → "UV: Add Package" → Type package name
```

---

## 🌟 Pro Tips

✅ **Use F5 to debug** instead of print statements  
✅ **Ctrl+Shift+P** is your best friend—use it often  
✅ **Right-click on a .py file** → "Run Python File in Terminal"  
✅ **Set breakpoints** by clicking line numbers, then F5  
✅ **Hover over variables** during debugging to inspect values  
✅ **Tasks** (Ctrl+Shift+P → "Run Task") are faster than typing commands  
✅ **Watch** variables during debugging (click Watch panel while paused)  

---

## 📖 Related Files

- `GETTING_STARTED.md` — First-time setup guide
- `UV_QUICKSTART.md` — UV command reference
- `README.md` — Complete project guide
- `pyproject.toml` — Dependencies and Ruff config
- `.vscode/` — Configuration files (settings, tasks, launch)

---

## 🔗 Resources

- [VS Code Python Documentation](https://code.visualstudio.com/docs/languages/python)
- [VS Code Debugging](https://code.visualstudio.com/docs/editor/debugging)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [UV Documentation](https://docs.astral.sh/uv/)

---

**You're all set! Start coding with VS Code + UV.** 🚀
