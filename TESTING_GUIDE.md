# Testing Guide

## Prerequisites

1. Make sure you're in the project directory:
```bash
cd C:\Users\nikop\Documents\GitHub\cf-autopost-feed
```

2. Install all dependencies:
```bash
pip install -r requirements.txt
```

---

## Test 1: Unit Tests

**Purpose**: Verify quality gate logic works correctly

```bash
pytest tests/test_quality_gates.py -v
```

**Expected Output**: All tests should pass (green checkmarks)
```
test_quality_gates.py::TestQualityGate::test_rejects_dialogue_markers PASSED
test_quality_gates.py::TestQualityGate::test_rejects_meta_markers PASSED
test_quality_gates.py::TestQualityGate::test_accepts_clean_second_person PASSED
...
==================== XX passed in X.XXs ====================
```

---

## Test 2: Health Check

**Purpose**: Verify all system files and RSS feed are valid

```bash
python health_check.py
```

**Expected Output**: Should show all checks passing
```
2025-01-13T... [INFO] health_check: ✓ PASS: File: Main RSS Feed - rss.xml
2025-01-13T... [INFO] health_check: ✓ PASS: File: Configuration - ops/config.json
2025-01-13T... [INFO] health_check: ✓ PASS: RSS Structure - Valid RSS 2.0 feed
...
==================================================
Health Check Results: X/X passed
Success Rate: 100.0%
==================================================
```

---

## Test 3: Logging System

**Purpose**: Verify logging works correctly

```bash
python -c "from logger_config import get_logger; logger = get_logger('test'); logger.info('Test message'); logger.warning('Test warning'); logger.error('Test error')"
```

**Expected Output**: Timestamped log messages
```
2025-01-13T12:34:56.789 [INFO] test: Test message
2025-01-13T12:34:56.790 [WARNING] test: Test warning
2025-01-13T12:34:56.791 [ERROR] test: Test error
```

---

## Test 4: Backup System

**Purpose**: Verify backup/restore functionality

```bash
python -c "from backup_manager import backup_file, list_backups; backup_file('rss.xml'); print('Backups:', list_backups('rss.xml'))"
```

**Expected Output**: Shows backup was created
```
2025-01-13T... [INFO] backup_manager: Created backup: backups/rss_20250113_123456.xml
Backups: ['backups/rss_20250113_123456.xml', ...]
```

**Verify backup directory exists**:
```bash
ls -la backups/
```

---

## Test 5: Constants Module

**Purpose**: Verify constants are accessible

```bash
python -c "from constants import ContentLimits, OpenAIConfig, Paths; print('X Limit:', ContentLimits.X_EFFECTIVE_LIMIT); print('Default Model:', OpenAIConfig.DEFAULT_MODEL); print('Config Path:', Paths.CONFIG)"
```

**Expected Output**:
```
X Limit: 230
Default Model: gpt-4o
Config Path: ops/config.json
```

---

## Test 6: Build RSS (Dry Run - WITHOUT API Call)

**Purpose**: Test that the script loads without errors (will fail at API call, which is expected without key)

```bash
python build_rss.py
```

**Expected Behavior**:
- Should load successfully and show logging
- Will fail with clear error about missing OPENAI_API_KEY
- This is CORRECT behavior - validates our API key check works!

**Expected Output**:
```
2025-01-13T... [INFO] __main__: Loaded JSON from ops/config.json
2025-01-13T... [INFO] __main__: Loaded JSON from ops/rules.json
2025-01-13T... [INFO] __main__: Loaded JSON from ops/bandit.json
2025-01-13T... [ERROR] __main__: OPENAI_API_KEY environment variable is not set
...
ValueError: OPENAI_API_KEY environment variable is required
```

---

## Test 7: Build RSS (Full Run - WITH API Key)

**Purpose**: Generate actual content with OpenAI

**⚠️ WARNING**: This will use OpenAI API credits!

```bash
# Set your API key
export OPENAI_API_KEY="your-api-key-here"

# Run the generator
python build_rss.py
```

**Expected Output** (successful run):
```
2025-01-13T... [INFO] __main__: Loaded JSON from ops/config.json
2025-01-13T... [INFO] __main__: Loaded JSON from ops/rules.json
2025-01-13T... [INFO] __main__: Quality gate attempt 1/3
2025-01-13T... [INFO] __main__: Attempting content generation with model: gpt-4o
2025-01-13T... [INFO] __main__: Successfully generated content with model: gpt-4o
2025-01-13T... [INFO] __main__: Quality gate passed on attempt 1
2025-01-13T... [INFO] __main__: Selected topic: ..., style: ...
2025-01-13T... [INFO] backup_manager: Created backup: backups/rss_...xml
Generated: [Your generated title here]
```

**Verify changes**:
```bash
# Check that RSS was updated
ls -lh rss.xml

# Check that backup was created
ls -la backups/

# Check that fingerprint was saved
cat analytics/fingerprints.json | tail -20
```

---

## Test 8: Code Formatting (Optional)

**Purpose**: Verify formatting tools work

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Check formatting
black --check .

# Check linting
ruff check .
```

**Expected Output**: Should report on any formatting issues

---

## Test 9: GitHub Actions Syntax (Local Validation)

**Purpose**: Ensure workflow files are valid YAML

```bash
# Install yamllint if you don't have it
pip install yamllint

# Validate all workflows
yamllint .github/workflows/*.yml
```

**Expected Output**: No syntax errors

---

## Test 10: Import All Modules

**Purpose**: Verify all Python files can be imported without errors

```bash
python -c "import build_rss; import logger_config; import backup_manager; import health_check; import constants; print('✓ All modules imported successfully')"
```

**Expected Output**:
```
✓ All modules imported successfully
```

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'tenacity'`
**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: `ModuleNotFoundError: No module named 'openai'`
**Solution**:
```bash
pip install openai>=1.40.0
```

### Issue: Tests fail with import errors
**Solution**: Make sure you're in the project root directory
```bash
cd C:\Users\nikop\Documents\GitHub\cf-autopost-feed
export PYTHONPATH=.
pytest tests/ -v
```

### Issue: Health check fails "No recent post"
**Solution**: This is expected if you haven't generated content in 24 hours. Run `build_rss.py` to generate new content.

### Issue: Permission denied on backups directory
**Solution**:
```bash
mkdir -p backups
chmod 755 backups
```

---

## Quick Verification Checklist

Run these commands in order for a complete system check:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run unit tests
pytest tests/ -v

# 3. Run health check
python health_check.py

# 4. Test logging
python -c "from logger_config import get_logger; logger = get_logger('test'); logger.info('✓ Logging works')"

# 5. Test backups
python -c "from backup_manager import backup_file; backup_file('rss.xml'); print('✓ Backup works')"

# 6. Test constants
python -c "from constants import OpenAIConfig; print('✓ Constants work -', OpenAIConfig.DEFAULT_MODEL)"

# 7. Test import all modules
python -c "import build_rss, logger_config, backup_manager, health_check, constants; print('✓ All imports successful')"

# 8. Dry run build (will fail at API - this is expected)
python build_rss.py 2>&1 | head -20
```

---

## What Success Looks Like

✅ **All unit tests pass** - Quality gates work correctly
✅ **Health check passes** - All system files valid
✅ **Logging shows timestamps** - Proper structured logging
✅ **Backups are created** - Disaster recovery works
✅ **Constants are accessible** - Magic numbers centralized
✅ **API key validation works** - Clear error if missing
✅ **No import errors** - All modules load cleanly

---

## Next Steps After Testing

1. **Commit changes** to git:
```bash
git add .
git commit -m "feat: comprehensive production improvements

- Add logging infrastructure
- Add backup/rollback system
- Add retry logic with exponential backoff
- Add health checks
- Add unit tests
- Fix gpt-5 model references
- Add workflow concurrency controls
- Add pip caching
- Extract magic numbers to constants
"
```

2. **Push to GitHub**:
```bash
git push origin main
```

3. **Monitor first automated run** in GitHub Actions

4. **Run health check periodically**:
```bash
# Add to cron or run manually
python health_check.py
```

---

## Troubleshooting GitHub Actions

If workflows fail after pushing:

1. Check Actions tab in GitHub
2. Look for error messages in logs
3. Common issues:
   - Missing secrets (OPENAI_API_KEY)
   - Permission issues (workflows need write access)
   - Concurrent runs conflicting (fixed by concurrency groups)

---

**Last Updated**: 2025-01-13
**Status**: Ready for testing
