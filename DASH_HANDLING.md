# Dash Handling in Posts

## Summary

✅ **Dashes ARE ALLOWED in regular content**
❌ **Dashes are NOT ALLOWED in hashtags**

## How It Works

### 1. Content Generation (AI Instructions)
The AI is instructed to:
- ✅ **Use dashes freely** in post content (e.g., "high-quality", "well-crafted", "data-driven")
- ❌ **Avoid dashes in tags** - Use compound words instead (e.g., "jobsearch" not "job-search")

**AI Prompt says:**
```
- x_line: SINGLE line for X (<= 230 chars), second-person, 2–4 tasteful emojis,
  no hashtags/links/dialogue/meta. Dashes are OK in content.
- tags: 2 short lowercase tags WITHOUT dashes or hyphens
  (use single words like 'resume' or 'jobsearch', NOT 'job-search'). No '#' symbol.
```

### 2. Hashtag Formatting (build_rss.py:334)
When hashtags are created from tags, dashes are automatically removed:

```python
# Remove dashes from tags when formatting as hashtags (dashes break hashtag linking)
tag_str = " ".join([f"#{t.replace('-', '')}" for t in tags_raw]) if tags_raw else ""
```

**Example:**
- AI generates tag: `"jobsearch"` → Hashtag: `#jobsearch` ✅ Works!
- If AI accidentally generates: `"job-search"` → Hashtag: `#jobsearch` ✅ Fixed automatically!

### 3. Quality Gates (build_rss.py:201-224)
Quality gates do NOT check for dashes in content. They only check:
- ❌ Dialogue markers (You:, Them:, Q:, A:)
- ❌ Meta markers (in this thread, see below)
- ❌ Tense conflicts (When...I...achieved)
- ❌ First-person outside quotes
- ❌ Banned phrases

**Dashes are completely allowed in regular content!**

## Examples

### ✅ CORRECT - Dash in Content
```
Post: "Your data-driven resume needs metrics—not buzzwords. Add 3-5 quantifiable wins. 📈✅"
Tags: ["resume", "jobsearch"]
Hashtags: #resume #jobsearch
```
**Result:** Posted successfully! Dashes in content are fine.

### ✅ CORRECT - Compound Word Tag
```
Post: "High-quality networking beats spray-and-pray applications every time. 🎯🤝"
Tags: ["networking", "jobsearch"]
Hashtags: #networking #jobsearch
```
**Result:** Posted successfully! Tags use compound words without dashes.

### ✅ FIXED AUTOMATICALLY - Dash in Tag
```
AI generates:
Tags: ["job-search", "career-tips"]

System converts to:
Hashtags: #jobsearch #careertips
```
**Result:** Posted successfully! Dashes removed from hashtags automatically.

### ❌ WOULD BREAK (but we handle it)
```
If we didn't remove dashes:
Hashtag: #job-search

Problem: Social platforms interpret this as:
- Hashtag: #job
- Regular text: -search
```
**Our solution:** We strip dashes so it becomes `#jobsearch` ✅

## Why This Matters

### Social Platform Behavior
Most social platforms treat dashes in hashtags inconsistently:
- **X/Twitter**: `#job-search` → only `#job` is clickable
- **LinkedIn**: `#job-search` → may work but inconsistent
- **Facebook**: `#job-search` → unreliable linking

### Our Solution
1. **Tell AI:** Use compound words without dashes in tags
2. **Safeguard:** Remove any dashes that slip through
3. **Allow:** Dashes everywhere else in content

## Testing

### Test 1: Content with Dashes
```bash
# Content: "Well-crafted resume with data-driven results"
# Expected: ✅ Passes quality gates
# Reason: Dashes allowed in content
```

### Test 2: Tag with Dash (should auto-fix)
```bash
# AI generates tag: "career-tips"
# Expected: ✅ Converted to #careertips
# Reason: Dashes stripped during hashtag formatting
```

### Test 3: Compound Tag (ideal)
```bash
# AI generates tag: "careertips"
# Expected: ✅ Becomes #careertips
# Reason: No dashes to strip
```

## Configuration

No configuration needed! This behavior is:
1. **Instructed** to the AI in the prompt
2. **Enforced** by the hashtag formatter
3. **Not checked** by quality gates (dashes are OK in content)

## Common Questions

**Q: Will my post be rejected if it contains dashes?**
A: No! Dashes are perfectly fine in content. Only hashtags have dashes removed.

**Q: What if the AI generates a tag with a dash?**
A: No problem! We automatically remove dashes when creating hashtags.

**Q: Can I use em-dashes (—) in content?**
A: Yes! All types of dashes are allowed in content.

**Q: What about underscores in tags?**
A: Underscores are allowed. They work fine in hashtags on most platforms.

## Summary

| Location | Dash Allowed? | Why |
|----------|---------------|-----|
| Post content | ✅ YES | Natural language uses dashes |
| Tag values (internal) | ✅ YES (but discouraged) | We strip them anyway |
| Hashtags (displayed) | ❌ NO | Breaks social platform linking |
| Quality gates | ✅ IGNORED | Not part of validation |

---

**Last Updated**: 2025-01-13
**Status**: Working as intended
