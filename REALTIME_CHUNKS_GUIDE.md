# Real-Time Chunk Saving Guide

**NEW:** Save chunk analyses in real-time as they're processed, with input and output clearly separated!

---

## What's New

When you use `--save-chunks`, each chunk file now shows:

1. **What Goes IN** (Input)
   - Original text from the book
   - Number of characters
   - Preview of content

2. **What Comes OUT** (Output)
   - Analysis from Ollama
   - Token counts (input/output)
   - Processing time

---

## Quick Start

```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks
```

---

## What You'll See

### Console Output

```
[3/4] Extracting insights per chunk (using glm-4.7-flash:latest)...

  Chunk 1/5: Chapter 1: The Value of Deep Work...
    Input: 24,356 chars (6,089 tokens)
    Output: 6234 in → 1876 out
    Speed: 12.3s (152.6 tok/s)
    [SAVED] deep_work_chunks/01_chapter_1_the_value_of_deep_work.md

  Chunk 2/5: Chapter 2: Rules of Deep Work...
    Input: 25,123 chars (6,280 tokens)
    Output: 6280 in → 2034 out
    Speed: 13.1s (155.3 tok/s)
    [SAVED] deep_work_chunks/02_chapter_2_rules_of_deep_work.md

  ... (continues for all chunks)

  Extraction complete: 1m 5s total, 13.1s avg per chunk
```

---

## File Structure

Each chunk file (e.g., `01_chapter_1_the_value_of_deep_work.md`):

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
increasingly rare. In a world of constant distraction—email, social media, 
and notifications—deep work stands out as a superpower...

---

## Output (What came out)

**Input Tokens:** 6234
**Output Tokens:** 1876
**Processing Time:** 12.3s

### Analysis

**Core Arguments & Thesis:**
Cal Newport argues that deep work—professional activities performed in a 
state of unbroken concentration—is becoming increasingly valuable while 
simultaneously becoming rarer...

[Full analysis continues...]

---

**Generated at:** 12.3s
```

---

## Real-Time Benefits

### 1. **Monitor Progress**
Watch chunks being saved as they're processed:

```bash
# Terminal 1: Run summarizer
uv run python ollama_summarizer.py book.pdf --save-chunks ...

# Terminal 2: Watch chunks appear
watch -n 1 "ls -1 deep_work_chunks/ | wc -l"
```

### 2. **See Input/Output Ratio**
Each file shows what went in vs what came out:

```
Input:  6,234 tokens
Output: 1,876 tokens (30% compression ratio)
```

This helps you understand:
- How much the book was compressed
- Analysis quality vs original content
- Token efficiency per chunk

### 3. **Quick Verification**
Check if Ollama is working correctly:

```bash
# Read first chunk immediately (no need to wait for all)
cat deep_work_chunks/01_*.md
```

### 4. **Resume if Interrupted**
If processing stops, you can:
- See how many chunks were completed
- Check the last successful chunk
- Resume from where you left off manually

---

## Console Output Explained

```
  Chunk 1/5: Chapter 1...
    Input: 24,356 chars (6,089 tokens)   ← How much text from the book
    Output: 6234 in → 1876 out           ← Tokens sent to Ollama → tokens received
    Speed: 12.3s (152.6 tok/s)           ← Time taken & tokens per second
    [SAVED] deep_work_chunks/01_....md   ← File saved immediately
```

---

## Example: Deep Work Book

Running:
```bash
uv run python ollama_summarizer.py deep_work.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --author "Cal Newport" \
  --save-chunks
```

Console output:
```
[3/4] Extracting insights per chunk (using glm-4.7-flash:latest)...

  Chunk 1/5: Chapter 1: The Value of Deep Work...
    Input: 24,356 chars (6,089 tokens)
    Output: 6234 in → 1876 out
    Speed: 12.3s (152.6 tok/s)
    [SAVED] deep_work_chunks/01_chapter_1_the_value_of_deep_work.md

  Chunk 2/5: Chapter 2: Rules of Deep Work...
    Input: 25,123 chars (6,280 tokens)
    Output: 6280 in → 2034 out
    Speed: 13.1s (155.3 tok/s)
    [SAVED] deep_work_chunks/02_chapter_2_rules_of_deep_work.md

  Chunk 3/5: Chapter 3: Deep Work Strategies...
    Input: 26,445 chars (6,611 tokens)
    Output: 6611 in → 1945 out
    Speed: 12.9s (150.7 tok/s)
    [SAVED] deep_work_chunks/03_chapter_3_deep_work_strategies.md

  Chunk 4/5: Chapter 4: Philosophies...
    Input: 23,098 chars (5,774 tokens)
    Output: 5774 in → 1823 out
    Speed: 11.2s (162.8 tok/s)
    [SAVED] deep_work_chunks/04_chapter_4_philosophies.md

  Chunk 5/5: Conclusion...
    Input: 18,234 chars (4,558 tokens)
    Output: 4558 in → 1654 out
    Speed: 8.9s (185.8 tok/s)
    [SAVED] deep_work_chunks/05_conclusion.md

  Extraction complete: 58s total, 11.7s avg per chunk
```

Files created:
```
deep_work_chunks/
├── 01_chapter_1_the_value_of_deep_work.md
├── 02_chapter_2_rules_of_deep_work.md
├── 03_chapter_3_deep_work_strategies.md
├── 04_chapter_4_philosophies.md
└── 05_conclusion.md
```

---

## View Chunk Input/Output

```bash
# See what went IN (original text)
grep -A 20 "## Input" deep_work_chunks/01_*.md

# See what came OUT (analysis)
grep -A 50 "## Output" deep_work_chunks/01_*.md | head -60

# Compare input size across chapters
for f in deep_work_chunks/*.md; do
  chars=$(grep "**Characters:**" "$f" | grep -o "[0-9]*" | head -1)
  echo "$(basename $f): $chars chars"
done
```

---

## Processing Time Analysis

Each chunk shows processing speed:

```bash
# Extract processing times for all chunks
grep "Speed:" deep_work_chunks/*.md

# Average speed
grep "Speed:" deep_work_chunks/*.md | \
  sed 's/.*Speed: //; s/s.*//' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count "s"}'
```

Example output:
```
deep_work_chunks/01_*.md: 12.3s
deep_work_chunks/02_*.md: 13.1s
deep_work_chunks/03_*.md: 12.9s
Average: 12.8s per chunk
```

---

## Troubleshooting

### Chunks not being saved
- Check that `--save-chunks` flag is used
- Verify extraction is running (not skipped)
- Check file permissions on output directory

### Chunk files are empty
- Verify Ollama is running (`ollama serve`)
- Check console for error messages
- Try with a test book first

### Can't see "Input" section
- Make sure you're reading a fresh chunk file (generated after update)
- Old chunk files won't have input/output separation

---

## Compare with Previous Behavior

### Before (chunks saved at end)
```
[3/4] Extracting...
  Chunk 1/5: ...
  Chunk 2/5: ...
  ... (wait until all done)
[4/4] Synthesizing...
  Writing chunks...
```

Chunks weren't visible until the entire extraction was done.

### After (real-time saving)
```
[3/4] Extracting...
  Chunk 1/5: ...
    [SAVED] 01_chapter_1.md  ← Saved immediately!
  Chunk 2/5: ...
    [SAVED] 02_chapter_2.md  ← Saved immediately!
  ...
```

Chunks are visible in real-time as they're processed!

---

## Advanced: Monitor Processing

### Terminal 1: Run summarizer
```bash
uv run python ollama_summarizer.py book.pdf --save-chunks ...
```

### Terminal 2: Watch progress
```bash
# See number of chunks saved
watch -n 1 "ls -1 deep_work_chunks/ | wc -l"

# Or see chunk names and sizes as they appear
watch "ls -lh deep_work_chunks/ | tail -5"

# Or see the latest chunk being edited
watch "ls -lt deep_work_chunks/*.md | head -1"
```

### Terminal 3: Review chunk as it's created
```bash
# Wait 30 seconds, then show first chunk
sleep 30 && cat deep_work_chunks/01_*.md | less
```

---

## Tips

✅ **Real-time chunks are always saved** during extraction (no extra flag needed to enable real-time)

✅ **Combined with other options:**
```bash
uv run python ollama_summarizer.py book.pdf \
  --save-chunks \
  --claude-synthesis \
  --output "summaries/book.md"
```

✅ **Monitor performance:**
```bash
# Find slowest chunk
grep "Speed:" deep_work_chunks/*.md | \
  sed 's/:.*Speed: /: /' | \
  sort -t':' -k2 -rn | head -1

# Find fastest chunk
grep "Speed:" deep_work_chunks/*.md | \
  sed 's/:.*Speed: /: /' | \
  sort -t':' -k2 -n | head -1
```

✅ **Extract stats:**
```bash
# Total input/output tokens across all chunks
echo "Total Input Tokens:"
grep "Input Tokens:" deep_work_chunks/*.md | \
  grep -o "[0-9]*" | awk '{sum+=$1} END {print sum}'

echo "Total Output Tokens:"
grep "Output Tokens:" deep_work_chunks/*.md | \
  grep -o "[0-9]*" | awk '{sum+=$1} END {print sum}'
```

---

## See Also

- `CHUNK_FILES_GUIDE.md` — Full guide to chunk features
- `SAVE_CHUNKS_QUICKREF.md` — Quick reference
- `README.md` — Main project guide

---

**Enjoy real-time chunk monitoring!** 📊
