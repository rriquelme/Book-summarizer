# Individual Chunk Files Feature

The `--save-chunks` flag saves each chunk analysis to its own individual file, creating a neat folder structure organized by chapter/section.

---

## Usage

### Basic Command
```bash
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks
```

### With Other Options
```bash
# Save chunks + Claude synthesis
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --save-chunks \
  --claude-synthesis

# Save chunks + custom output folder
uv run python ollama_summarizer.py book.pdf \
  --model glm-4.7-flash:latest \
  --title "Deep Work" \
  --output "summaries/deep_work_summary.md" \
  --save-chunks
```

---

## Output Structure

When you run with `--save-chunks`, you'll get:

```
current_directory/
├── deep_work_summary.md              # Final synthesized summary
├── deep_work_notebooklm_source.md    # All analyses combined (for NotebookLM)
│
└── deep_work_chunks/                 # NEW! Individual chunk files
    ├── 01_chapter_1_the_value_of_deep_work.md
    ├── 02_chapter_2_rules_of_deep_work.md
    ├── 03_chapter_3_deep_work_strategies.md
    ├── 04_chapter_4_philosophies.md
    ├── 05_conclusion.md
    └── ... (one file per chunk)
```

---

## What's in Each Chunk File

Each file contains:

```markdown
# Chapter 1: The Value of Deep Work

**Book:** Deep Work
**Author:** Cal Newport
**Chunk:** 1 of 5

---

## Analysis

[Full analysis from Ollama]
[All arguments, evidence, takeaways, connections...]

---

**Tokens:** 5234 input, 1876 output
**Processing time:** 12.3s
```

---

## Why Use This Feature?

### 1. **Easy to Review Chunk-by-Chunk**
Review each section's analysis without scrolling through the entire file.

```bash
# View just one chunk
cat deep_work_chunks/01_chapter_1.md

# View all chunks in order
ls deep_work_chunks/ | xargs -I {} cat deep_work_chunks/{}
```

### 2. **Edit Individual Sections**
Fix or expand specific chapter analyses without touching others:

```bash
# Edit chapter 3 analysis
code deep_work_chunks/03_chapter_3_deep_work_strategies.md
```

### 3. **Selective Sharing**
Share specific chapters with colleagues or friends:

```bash
# Send just chapter 2
send_to_colleague deep_work_chunks/02_chapter_2_rules_of_deep_work.md
```

### 4. **Organization & Backup**
Keep modular, organized backups of your analyses:

```bash
# Backup chunks separately
cp -r deep_work_chunks/ backups/deep_work_chunks_backup/

# Version chunks by date
mkdir -p archives/deep_work_2026_04_05
mv deep_work_chunks/ archives/deep_work_2026_04_05/
```

### 5. **Combine with Other Tools**
Process individual chunks with other tools:

```bash
# Count tokens per chapter
for f in deep_work_chunks/*.md; do
  echo "$(basename $f): $(wc -w < $f) words"
done

# Extract just the analysis sections
grep -h "^## Analysis" deep_work_chunks/*.md
```

---

## File Naming Convention

Files are named: `{NUMBER}_{SLUGIFIED_TITLE}.md`

- `{NUMBER}`: Chunk order (01, 02, 03, ...)
- `{SLUGIFIED_TITLE}`: Clean, lowercase version of chapter title
  - Spaces → underscores
  - Special chars removed
  - Parentheses cleaned

Examples:
- `01_chapter_1_the_value.md`
- `02_chapter_2_rules_deep_work.md`
- `03_conclusion_and_takeaways.md`

---

## Comparison: With and Without `--save-chunks`

### Without `--save-chunks` (default)
```
Outputs:
  - deep_work_summary.md               (final summary only)
  - deep_work_notebooklm_source.md     (all analyses in one file)

Good for:
  - Quick single-file review
  - Uploading to NotebookLM
  - Minimal disk space
```

### With `--save-chunks`
```
Outputs:
  - deep_work_summary.md               (final summary)
  - deep_work_notebooklm_source.md     (all analyses combined)
  - deep_work_chunks/                  (individual files)
      ├── 01_chapter_1.md
      ├── 02_chapter_2.md
      └── ...

Good for:
  - Chapter-by-chapter review
  - Individual editing
  - Modular organization
  - Selective sharing
```

---

## Examples

### Example 1: Review Each Chapter Separately
```bash
# List all chunks
ls -1 deep_work_chunks/

# Read chunk 3
less deep_work_chunks/03_chapter_3.md

# Search for keyword in all chunks
grep -r "Deep Work" deep_work_chunks/
```

### Example 2: Extract Summaries from Chunks
```bash
# Get just the first 100 lines of each chunk
for file in deep_work_chunks/*.md; do
  echo "=== $(basename $file) ==="
  head -20 "$file"
  echo ""
done
```

### Example 3: Combine Specific Chunks
```bash
# Create a custom summary with chapters 1, 3, 5
cat deep_work_chunks/01_*.md deep_work_chunks/03_*.md deep_work_chunks/05_*.md > custom_summary.md
```

### Example 4: Monitor Processing
While the script runs, you can see chunks being created in real-time:

```bash
# In another terminal, watch the chunks directory grow
watch -n 1 "ls -1 deep_work_chunks/ | wc -l"

# Or list new files as they're created
while true; do find deep_work_chunks/ -mmin -1 -ls; sleep 2; done
```

---

## Tips

✅ **Combine with other flags:**
```bash
uv run python ollama_summarizer.py book.pdf \
  --title "Book" \
  --model glm-4.7-flash:latest \
  --save-chunks \
  --claude-synthesis \
  --output "custom_folder/book_summary.md"
```

✅ **Keep chunks organized:**
```bash
mkdir -p summaries/books
uv run python ollama_summarizer.py book.pdf \
  --title "Deep Work" \
  --output "summaries/books/deep_work_summary.md" \
  --save-chunks

# Result:
# summaries/books/deep_work_summary.md
# summaries/books/deep_work_chunks/01_chapter_1.md
# etc.
```

✅ **Batch process with chunks:**
```bash
for book in library/*.pdf; do
  title=$(basename "$book" .pdf)
  uv run python ollama_summarizer.py "$book" \
    --title "$title" \
    --model glm-4.7-flash:latest \
    --output "summaries/${title}_summary.md" \
    --save-chunks
done
```

---

## Performance Notes

- **No extra cost:** Saving chunks is free (just file I/O)
- **No extra time:** Minimal overhead (< 1 second for saving files)
- **Storage:** Chunks folder ~same size as notebooklm_source.md (both have same content)

---

## Troubleshooting

### Chunks folder not created
- Make sure you used `--save-chunks` flag
- Check that output directory is writable
- Verify Ollama extraction completed successfully

### Chunks folder is empty
- Check that chunks were actually extracted (look at console output)
- Verify the extraction step completed

### Can't find specific chunk
- Use `ls -1 deep_work_chunks/ | grep keyword` to search by filename
- Use `grep -r "keyword" deep_work_chunks/` to search by content

---

## See Also

- `OLLAMA_FIX_SUMMARY.md` — Model detection fixes
- `README.md` — Main project guide
- `UV_QUICKSTART.md` — UV commands

---

**Enjoy organized, modular chunk analyses!** 📚
