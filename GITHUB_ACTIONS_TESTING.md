# Testing via GitHub Actions (No Local Setup Required!)

## Step 1: Commit and Push Your Changes

1. **Open terminal/command prompt** in your project folder:
   ```bash
   cd C:\Users\nikop\Documents\GitHub\cf-autopost-feed
   ```

2. **Add all files**:
   ```bash
   git add .
   ```

3. **Commit changes**:
   ```bash
   git commit -m "feat: add production improvements and fixes"
   ```

4. **Push to GitHub**:
   ```bash
   git push origin main
   ```

---

## Step 2: Verify OpenAI API Key Secret

1. Go to your repository on GitHub: `https://github.com/nikopastore/cf-autopost-feed`

2. Click **Settings** (top right menu)

3. In left sidebar, click **Secrets and variables** → **Actions**

4. Verify you see `OPENAI_API_KEY` in the list
   - ✅ If it exists, you're good!
   - ❌ If missing, click **New repository secret**:
     - Name: `OPENAI_API_KEY`
     - Value: Your OpenAI API key
     - Click **Add secret**

---

## Step 3: Test Using GitHub Actions Buttons

### Test 1: Generate RSS Content (Main Workflow)

1. Go to **Actions** tab in GitHub
2. Click **"Generate and publish RSS item (AM/PM)"** in left sidebar
3. Click **"Run workflow"** button (right side)
4. Click green **"Run workflow"** button in dropdown
5. **Wait 1-2 minutes** for it to complete
6. Click on the workflow run to see logs

**✅ Success looks like:**
```
Run python build_rss.py
2025-01-13T... [INFO] __main__: Loaded JSON from ops/config.json
2025-01-13T... [INFO] __main__: Quality gate attempt 1/3
2025-01-13T... [INFO] __main__: Attempting content generation with model: gpt-4o
2025-01-13T... [INFO] __main__: Successfully generated content with model: gpt-4o
2025-01-13T... [INFO] __main__: Quality gate passed on attempt 1
2025-01-13T... [INFO] backup_manager: Created backup: backups/rss_...xml
Generated: [Your content title]
```

**What to check:**
- ✅ Workflow completes with green checkmark
- ✅ You see logging output with timestamps
- ✅ "Quality gate passed" message appears
- ✅ "Generated: [title]" at the end
- ✅ Commit created with new RSS content

---

### Test 2: Build Analytics

1. Go to **Actions** tab
2. Click **"Build Analytics Hub"** in left sidebar
3. Click **"Run workflow"** button
4. Click green **"Run workflow"** button
5. **Wait 30-60 seconds**

**✅ Success looks like:**
- Green checkmark
- Analytics files updated
- New commit with "analytics: update reports..."

---

### Test 3: Harvest Trends

1. Go to **Actions** tab
2. Click **"Harvest Trends"** in left sidebar
3. Click **"Run workflow"** button
4. Click green **"Run workflow"** button
5. **Wait 20-30 seconds**

**✅ Success looks like:**
- Green checkmark
- Trends harvested from Google News
- New commit with "chore(trends): refresh trends"

---

### Test 4: Weekly Newsletter

1. Go to **Actions** tab
2. Click **"Build Weekly Digest"** in left sidebar
3. Click **"Run workflow"** button
4. Click green **"Run workflow"** button
5. **Wait 20-30 seconds**

**✅ Success looks like:**
- Green checkmark
- Newsletter.md updated
- New commit with "newsletter: weekly digest"

---

## Step 4: Verify Everything Works

### Check Logs for New Features

Click on any completed workflow run, then click on the **"build-feed"** or **"analytics"** job to see logs.

**Look for these indicators that improvements are working:**

✅ **Logging Infrastructure Working:**
```
2025-01-13T12:34:56.789 [INFO] __main__: Loaded JSON from ops/config.json
2025-01-13T12:34:56.790 [INFO] __main__: Quality gate attempt 1/3
```

✅ **API Key Validation Working:**
If you remove the secret, you'll see:
```
[ERROR] __main__: OPENAI_API_KEY environment variable is not set
ValueError: OPENAI_API_KEY environment variable is required
```

✅ **Backup System Working:**
```
[INFO] backup_manager: Created backup: backups/rss_20250113_123456.xml
```

✅ **Retry Logic Working:**
If API fails temporarily:
```
[WARNING] __main__: Model gpt-4o failed: timeout
[INFO] __main__: Attempting content generation with model: gpt-4o
```

✅ **Quality Gates Working:**
```
[INFO] __main__: Quality gate passed on attempt 1
```
or
```
[WARNING] __main__: Quality gate failed on attempt 1: dialogue/meta markers
```

✅ **Pip Caching Working:**
```
Run actions/setup-python@v5
Restored cache for pip dependencies
```

---

### Check Generated Files

1. Go to your repository main page
2. Check these files were updated:
   - ✅ `rss.xml` - New item added
   - ✅ `rss_x.xml`, `rss_fb.xml`, `rss_li.xml` - Platform feeds updated
   - ✅ `analytics/fingerprints.json` - New fingerprint added

3. **Important**: Check for `backups/` directory:
   - Click through repository files
   - Look for `backups/` folder
   - Should contain `rss_YYYYMMDD_HHMMSS.xml` files

---

## Step 5: Test Concurrency (Advanced)

**Purpose**: Verify workflows don't conflict

1. Go to **Actions** tab
2. Quickly run multiple workflows:
   - Click **"Generate and publish RSS item"** → Run workflow
   - Immediately click **"Build Analytics Hub"** → Run workflow
   - Immediately click **"Harvest Trends"** → Run workflow

**✅ Expected behavior:**
- Workflows should **queue** instead of running simultaneously
- Each has a different concurrency group, so they can run in parallel
- No merge conflicts in commits

---

## Step 6: Monitor Automated Runs

Your workflows run automatically on schedule:
- **07:40 & 14:10 (Phoenix time)** - Content generation
- **08:05 & 14:35 (Phoenix time)** - Analytics
- **06:00 daily (Phoenix time)** - Trends
- **Monday 09:00 (Phoenix time)** - Newsletter, bandit updates, cron optimization

**To monitor:**
1. Go to **Actions** tab
2. You'll see workflows running automatically
3. Click on any to see logs

---

## Troubleshooting

### ❌ Workflow fails with "OPENAI_API_KEY not set"
**Solution**: Add secret in Settings → Secrets → Actions → New repository secret

### ❌ Workflow fails with "Permission denied"
**Solution**:
1. Go to Settings → Actions → General
2. Scroll to "Workflow permissions"
3. Select "Read and write permissions"
4. Click Save

### ❌ Workflows run simultaneously and conflict
**Solution**: This is now fixed with concurrency groups! If it still happens, check that workflows have been updated with the concurrency sections.

### ❌ No backups directory visible
**Solution**: Backups are created locally in workflows but may not be committed to git (they're in `.gitignore`). This is correct - backups are for the CI/CD environment.

### ❌ Tests fail with import errors
**Solution**: Make sure `requirements.txt` was pushed:
```bash
git status
git add requirements.txt logger_config.py backup_manager.py
git commit -m "fix: add missing files"
git push
```

---

## Quick Visual Guide

```
1. Push Code              2. Go to Actions         3. Run Workflow
┌─────────────┐          ┌─────────────────┐      ┌──────────────────┐
│ git add .   │          │ Click "Actions" │      │ Click workflow   │
│ git commit  │   ───>   │ tab in GitHub   │ ───> │ Click "Run       │
│ git push    │          │ repository      │      │ workflow" button │
└─────────────┘          └─────────────────┘      └──────────────────┘
                                                            │
                                                            ▼
                    4. Watch Logs                 5. Verify Success
                    ┌──────────────────┐          ┌─────────────────┐
                    │ Click on running │          │ Green checkmark │
                    │ workflow to see  │   ───>   │ New commits     │
                    │ detailed logs    │          │ Files updated   │
                    └──────────────────┘          └─────────────────┘
```

---

## What Success Looks Like

### ✅ Successful Workflow Run

![Success Indicators]
- Green checkmark next to workflow name
- All jobs show green checkmarks
- Logs show structured logging with timestamps
- New commit created (for workflows that modify files)
- No error messages in logs

### ✅ Logs Show New Features Working

```
Run python build_rss.py
  2025-01-13T15:30:45.123 [INFO] __main__: Loaded JSON from ops/config.json
  2025-01-13T15:30:45.234 [INFO] __main__: Loaded JSON from ops/rules.json
  2025-01-13T15:30:45.345 [INFO] __main__: Loaded JSON from ops/bandit.json
  2025-01-13T15:30:45.456 [INFO] __main__: Quality gate attempt 1/3
  2025-01-13T15:30:45.567 [INFO] __main__: Attempting content generation with model: gpt-4o
  2025-01-13T15:30:52.123 [INFO] __main__: Successfully generated content with model: gpt-4o
  2025-01-13T15:30:52.234 [INFO] __main__: Quality gate passed on attempt 1
  2025-01-13T15:30:52.345 [INFO] __main__: Selected topic: Interview frameworks, style: coach_tip
  2025-01-13T15:30:52.456 [INFO] backup_manager: Created backup: backups/rss_20250113_153052.xml
  Generated: ✅ Your STAR answer template: Use: "I improved X by Y% when Z happened." Keep scope tight. 📈🎯
```

### ✅ Commits Created Automatically

Look for commits like:
- "Add RSS item [skip ci]"
- "Update platform feeds [skip ci]"
- "analytics: update reports, bandit, cron suggestion [skip ci]"
- "chore(trends): refresh trends [skip ci]"

---

## Pro Tips

1. **Watch first run carefully** - Click on running workflow immediately to watch logs in real-time

2. **Check multiple tabs**:
   - Actions tab - See all runs
   - Code tab - See updated files
   - Commits - See what changed

3. **Enable notifications**:
   - Click "Watch" → "Custom" → Check "Actions"
   - Get emails when workflows fail

4. **Download logs**:
   - Click on completed workflow
   - Click "..." (three dots) in top right
   - Click "Download log archive"

5. **Cancel stuck workflows**:
   - Click on running workflow
   - Click "Cancel workflow" (top right)

---

## Summary: The Easiest Way

**Just do this:**

1. Push code: `git add . && git commit -m "improvements" && git push`
2. Go to GitHub → Actions tab
3. Click any workflow → Run workflow button
4. Watch it run and verify green checkmark
5. Check logs to see new logging/backup features working

**That's it!** No local setup needed.

---

**Last Updated**: 2025-01-13
