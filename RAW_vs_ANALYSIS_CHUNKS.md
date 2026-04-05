# Raw vs Analysis Chunks Guide

## Overview

The Ollama Summarizer now supports saving **two different types of chunks**:

1. **Raw Chunks** (`--save-raw-chunks`) — The original input text
2. **Analysis Chunks** (`--save-chunks`) — The LLM output/analysis

---

## 📊 Quick Comparison

| Feature | Raw Chunks | Analysis Chunks |
|---------|-----------|-----------------|
| **What** | Original book text (no processing) | Ollama analysis (LLM output) |
| **When saved** | After chunking, BEFORE LLM | After LLM processing |
| **File type** | `.txt` (plain text) | `.md` (markdown) |
| **Folder** | `book_title_raw_chunks/` | `book_title_chunks/` |
| **Purpose** | Inspect input | Review analysis |
| **Use case** | Test prompts, verify extraction | Read final output |

---

## 🎯 Raw Chunks (`--save-raw-chunks`)

### What You Get

**Pure, unprocessed text from the book** with minimal metadata.

### Example File: `01_chapter_1.txt`

```
======================================================================
BOOK: Deep Work
AUTHOR: Cal Newport
CHAPTER/SECTION: Chapter 1: The Value of Deep Work
CHUNK: 1 of 5
CHARACTERS: 24,356
TOKENS (estimated): 6,089
======================================================================

The ability to focus intently on a cognitively demanding task is becoming 
increasingly rare. In a world of constant distraction—email, social media, 
and notifications—deep work stands out as a superpower. Cal Newport argues 
that the ability to concentrate on cognitively demanding tasks is becoming 
increasingly valuable while simultaneously becoming rarer...

[... rest of original book text ...]

======================================================================
END OF CHUNK 1
======================================================================
```

### Command

```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-raw-chunks
```

### Files Created

```
deep_work_raw_chunks/
├── 01_chapter_1.txt
├── 02_chapter_2.txt
├── 03_chapter_3.txt
└── ...
```

### Use Cases

✅ **Inspect what was extracted** — Verify chunking worked correctly  
✅ **Test different prompts** — Use raw chunks with different extraction prompts  
✅ **Data analysis** — Analyze original text (word count, sentiment, etc.)  
✅ **Backup original content** — Archive the source material  
✅ **Share input** — Show colleagues exactly what the LLM received  

---

## 📝 Analysis Chunks (`--save-chunks`)

### What You Get

**Ollama's analysis with input preview and output sections.**

### Example File: `01_chapter_1.md`

```markdown
# Chapter 1: The Value of Deep Work

**Book:** Deep Work
**Author:** Cal Newport
**Chunk:** 1 of 5

---

## Input (What went in)

**Characters:** 24,356
**Title:** Chapter 1: The Value of Deep Work

**Content Preview:**
The ability to focus intently on a cognitively demanding task is becoming 
increasingly rare...

---

## Output (What came out)

**Input Tokens:** 6234
**Output Tokens:** 1876
**Processing Time:** 12.3s

### Analysis

**Core Arguments & Thesis:**
Cal Newport argues that deep work—professional activities performed in a 
state of unbroken concentration on cognitively demanding tasks—is becoming 
increasingly valuable while simultaneously becoming rarer...

**Key Concepts & Frameworks:**
- Deep Work: Unbroken concentration on cognitively demanding tasks
- Shallow Work: Easy, interruptible activities with little value
...

---

**Generated at:** 12.3s
```

### Command

```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks
```

### Files Created

```
deep_work_chunks/
├── 01_chapter_1.md
├── 02_chapter_2.md
├── 03_chapter_3.md
└── ...
```

### Use Cases

✅ **Read the analysis** — Review what Ollama extracted  
✅ **Edit sections** — Improve or correct analysis  
✅ **Share findings** — Send chapter analysis to others  
✅ **Compare quality** — See output across different models  
✅ **Quick review** — Read formatted markdown  

---

## 🎯 Use Both Together!

### Command

```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-raw-chunks \
  --save-chunks
```

### Result

You get **both folders**:

```
deep_work_raw_chunks/          (BEFORE LLM)
├── 01_chapter_1.txt           (raw text)
├── 02_chapter_2.txt           (raw text)
└── ...

deep_work_chunks/              (AFTER LLM)
├── 01_chapter_1.md            (analysis)
├── 02_chapter_2.md            (analysis)
└── ...

deep_work_summary.md           (final summary)
deep_work_notebooklm_source.md (all analyses combined)
```

### Benefits

This lets you:
- **Compare side-by-side** — Input vs Output
- **Verify accuracy** — Check if analysis matches original
- **Iterate** — Re-run different prompts on same raw chunks
- **Audit trail** — See exactly what went in and came out
- **Data science** — Analyze both input and output

---

## 📋 Example Workflow

### Step 1: Extract and save raw chunks

```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-raw-chunks
```

### Step 2: Inspect raw chunks

```bash
# View first raw chunk
cat deep_work_raw_chunks/01_*.txt

# Count words in all raw chunks
wc -w deep_work_raw_chunks/*.txt

# Search for keyword in raw input
grep -r "Deep Work" deep_work_raw_chunks/
```

### Step 3: Process with analysis

```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks
```

### Step 4: Compare input vs output

```bash
# View raw input
head -50 deep_work_raw_chunks/01_*.txt

# View LLM analysis
head -50 deep_work_chunks/01_*.md

# Full comparison (side by side)
echo "=== RAW INPUT ===" && cat deep_work_raw_chunks/01_*.txt && \
echo "=== ANALYSIS ===" && cat deep_work_chunks/01_*.md
```

---

## 🔍 File Format Differences

### Raw Chunks (`.txt`)

```
Raw, plain text format
- Header with metadata
- Original book text
- Footer
- No markdown
- No LLM processing
```

**Best for:**
- Data analysis
- Text processing
- Backup/archival
- Verification

### Analysis Chunks (`.md`)

```
Markdown format
- Formatted headings
- Structured sections
- Input preview
- Output analysis
- Metadata
```

**Best for:**
- Reading
- Sharing
- Documentation
- Review

---

## 💡 Advanced Use Cases

### 1. Test Different Extraction Prompts

```bash
# Save raw chunks once
uv run python ollama_summarizer.py book.pdf --save-raw-chunks

# Then manually create custom extraction scripts using raw chunks
# (modify EXTRACTION_PROMPT and re-process same raw chunks)
```

### 2. Compare Models

```bash
# Extract and save raw chunks
uv run python ollama_summarizer.py book.pdf --save-raw-chunks

# Then run same raw chunks through different models
uv run python ollama_summarizer.py book.pdf \
  --model qwen2.5-coder:14b --save-chunks

# And again with different model
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest --save-chunks

# Compare outputs
diff deep_work_chunks/01_*.md deep_work_chunks_alt/01_*.md
```

### 3. Data Quality Audit

```bash
# Check raw chunk extraction quality
for f in deep_work_raw_chunks/*.txt; do
  chars=$(grep "CHARACTERS:" "$f" | grep -o "[0-9]*")
  echo "$(basename $f): $chars characters"
done

# Verify all chunks are reasonable size
find deep_work_raw_chunks -name "*.txt" -exec wc -c {} + | sort -n
```

### 4. Full Content Pipeline

```bash
# Save everything
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-raw-chunks \
  --save-chunks \
  --claude-synthesis

# Result: Raw input, LLM analysis, Claude synthesis, final summary
# Complete audit trail of the entire pipeline!
```

---

## 📊 Console Output

When using both flags:

```
[2/4] Chunking text...
  Created 5 chunks

  Saving raw input chunks...
  Raw chunks saved to: deep_work_raw_chunks/

[3/4] Extracting insights per chunk...
  Chunk 1/5: Chapter 1...
    Input: 24,356 chars (6,089 tokens)
    Output: 6234 in → 1876 out
    Speed: 12.3s (152.6 tok/s)
    [SAVED] deep_work_chunks/01_chapter_1.md
  
  ... (continues for all chunks)
```

---

## 🎯 Quick Command Reference

```bash
# Only raw chunks
uv run python ollama_summarizer.py book.pdf --save-raw-chunks

# Only analysis chunks
uv run python ollama_summarizer.py book.pdf --save-chunks

# Both
uv run python ollama_summarizer.py book.pdf --save-raw-chunks --save-chunks

# With Claude synthesis
uv run python ollama_summarizer.py book.pdf \
  --save-raw-chunks --save-chunks --claude-synthesis

# Custom output folder
uv run python ollama_summarizer.py book.pdf \
  --output "summaries/book_summary.md" \
  --save-raw-chunks --save-chunks
```

---

## 📈 Performance Notes

- **Raw chunks**: Saved immediately after chunking (very fast)
- **Analysis chunks**: Saved in real-time during LLM processing
- **No extra cost**: Just file I/O overhead
- **Storage**: Raw chunks ≈ same size as analysis chunks (both have same text content)

---

## 🚀 Summary

| Want to... | Use... |
|-----------|---------|
| **Inspect original text** | `--save-raw-chunks` |
| **Read Ollama analysis** | `--save-chunks` |
| **Audit full pipeline** | Both flags together |
| **Test extraction** | `--save-raw-chunks` → modify script |
| **Compare models** | Save raw once → process multiple times |
| **Backup content** | `--save-raw-chunks` |
| **Share findings** | `--save-chunks` |

---

**Use both flags together for maximum insight into your summarization pipeline!** 🎯
