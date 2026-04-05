# Save Chunks Feature - Quick Reference

## What's New?

**New `--save-chunks` flag** saves each chunk analysis to its own individual file!

---

## Quick Examples

### Basic Usage
```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks
```

### With Claude Synthesis
```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks \
  --claude-synthesis
```

### With Custom Output Folder
```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --output "summaries/deep_work_summary.md" \
  --save-chunks
```

---

## Output Files

```
Current directory/
├── deep_work_summary.md              # Final summary (always created)
├── deep_work_notebooklm_source.md    # All chunks combined (always created)
│
└── deep_work_chunks/                 # NEW! Individual files (--save-chunks only)
    ├── 01_chapter_1_the_value.md
    ├── 02_chapter_2_rules.md
    ├── 03_chapter_3_strategies.md
    ├── 04_conclusion.md
    └── ... (one file per chunk)
```

---

## View/Work with Chunks

```bash
# List all chunks
ls -1 deep_work_chunks/

# View a specific chunk
cat deep_work_chunks/01_chapter_1.md

# View all chunks in order
for f in deep_work_chunks/*.md; do cat "$f"; echo "---"; done

# Search for keyword in all chunks
grep -r "Deep Work" deep_work_chunks/

# Edit a specific chunk
code deep_work_chunks/03_chapter_3.md
```

---

## Why Use It?

| Benefit | How |
|---------|-----|
| **Review chapter-by-chapter** | Open individual files instead of one giant file |
| **Edit specific sections** | Fix or expand individual chapter analyses |
| **Share selectively** | Send specific chapters to friends/colleagues |
| **Organize modularly** | Keep analyses in separate files |
| **Batch process** | Use chunks with other tools |

---

## File Contents

Each chunk file includes:

```markdown
# Chapter Title

**Book:** Book Name
**Author:** Author Name
**Chunk:** 1 of 5

---

## Analysis

[Full Ollama analysis here]
[Arguments, evidence, examples, takeaways, etc.]

---

**Tokens:** 5234 input, 1876 output
**Processing time:** 12.3s
```

---

## What You Get

| Files | Purpose |
|-------|---------|
| `*_summary.md` | Final synthesized summary |
| `*_notebooklm_source.md` | All analyses in one file (for NotebookLM upload) |
| `*_chunks/` | Individual chunk files (ONE per chapter/section) |

**All 3 are created by default!** The `--save-chunks` flag just adds the individual files folder.

---

## Performance

✅ **No extra cost** — Just file I/O  
✅ **No extra time** — < 1 second overhead  
✅ **No extra processing** — Saves what was already extracted  

---

## Example: Deep Work Book

After running:
```bash
uv run python ollama_summarizer.py deep_work.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --author "Cal Newport" \
  --save-chunks
```

You get:
```
deep_work_summary.md                    (4-5 KB, final summary)
deep_work_notebooklm_source.md          (50-100 KB, all analyses)
deep_work_chunks/                       (folder)
  ├── 01_chapter_1_value_deep_work.md   (8 KB)
  ├── 02_chapter_2_rules_deep_work.md   (9 KB)
  ├── 03_chapter_3_deep_work_strategies.md (10 KB)
  ├── 04_part_1_conclusion.md           (7 KB)
  └── ... (one per chapter/section)
```

---

## Combine Specific Chunks

```bash
# Create custom summary: chapters 2 and 3 only
cat deep_work_chunks/02_*.md deep_work_chunks/03_*.md > chapters_2_and_3.md

# Create chapters-only version (skip conclusion)
cat deep_work_chunks/0[1-4]_*.md > main_chapters_only.md
```

---

## Monitor While Running

Watch chunks being created in real-time:

```bash
# Terminal 1: Run the summarizer
uv run python ollama_summarizer.py book.pdf --save-chunks ...

# Terminal 2: Monitor chunks folder
watch -n 1 "ls -1 deep_work_chunks/ | wc -l"

# Or check new files:
while true; do find deep_work_chunks/ -mmin -1; sleep 2; done
```

---

## See Full Guide

👉 **`CHUNK_FILES_GUIDE.md`** for complete documentation and examples

---

**Enjoy your modular analyses!** 📚
