# Security & Code Quality Hooks

**Comprehensive automated security and code analysis for GapSense platform**

---

## Overview

GapSense handles sensitive student data under Ghana Data Protection Act compliance. These hooks enforce security best practices automatically.

---

## Tools Installed

### Security Tools
- **bandit** `^1.7` - Python security linter (detects hardcoded passwords, SQL injection, etc.)
- **safety** `^3.0` - Dependency vulnerability scanner (checks for CVEs)
- **detect-secrets** `^1.4` - Secret detection (API keys, tokens, passwords)

### Code Analysis Tools
- **vulture** `^2.11` - Dead code detection (unused functions, classes, variables)
- **deptry** `^0.19` - Dependency management (unused/missing dependencies)

---

## Pre-Commit Hooks (Fast - Every Commit)

**Duration:** ~10 seconds

### Dependency Integrity Checks
1. **Poetry Lock File Check** - CRITICAL for CI/CD stability
   - Verifies `poetry.lock` matches `pyproject.toml`
   - Prevents CI/CD failures from outdated lock files
   - Fix: Run `poetry lock --no-update` if check fails

### Security Checks
2. **Detect Secrets** - Scans for API keys, tokens, passwords before commit
   - Uses baseline: `.secrets.baseline`
   - Detects: AWS keys, GitHub tokens, JWT, Basic Auth, etc.

3. **Private Key Detection** - Prevents committing SSH/PGP private keys

4. **Merge Conflict Detection** - Catches unresolved merge markers

5. **Branch Protection** - Blocks direct commits to `main` branch

### Code Quality Checks
- Ruff linting (auto-fixes safe issues)
- Ruff formatting
- YAML/JSON/TOML validation
- Trailing whitespace removal
- End-of-file fixing
- **Block code smells** (FIXME, HACK, XXX, TEMP, WIP)
- **Warn on TODOs** (encourages fixing, allows commit)
- **Coding standards checklist** (reminds of error handling, PII, type safety, etc.)

---

## Pre-Push Hooks (Thorough - Before Push)

**Duration:** ~45 seconds

### Security Scans (CRITICAL)
1. **Bandit Security Scan**
   - Scans: `src/` directory
   - Config: `pyproject.toml`
   - Detects:
     - Hardcoded passwords
     - SQL injection vulnerabilities
     - Shell injection risks
     - Insecure crypto usage
     - Insecure temp file usage

2. **Safety Vulnerability Check**
   - Scans all dependencies for known CVEs
   - Uses Safety DB (commercial + open source)
   - Alerts on critical/high severity issues

### Code Analysis
3. **Vulture Dead Code Detection**
   - Minimum confidence: 80%
   - Finds unused:
     - Functions
     - Classes
     - Variables
     - Properties
     - Imports

4. **Deptry Dependency Analysis**
   - Detects unused dependencies in `pyproject.toml`
   - Detects missing dependencies (imported but not declared)
   - Excludes: tests, migrations, infrastructure

### Quality Checks
- MyPy strict type checking
- Pytest with ≥80% coverage requirement
- Alembic migration validation

---

## CI/CD Pipeline (GitHub Actions)

**Mirrors all pre-push hooks** - catches anyone who bypassed hooks with `--no-verify`

### Jobs
1. **Quality** - Ruff, MyPy
2. **Test** - Pytest with coverage (≥80%)
3. **Migrations** - Alembic check
4. **Security** - NEW: Bandit, Safety, Detect-Secrets, Vulture, Deptry

All jobs must pass before merge allowed.

---

## Configuration Files

### `.pre-commit-config.yaml`
Main hook configuration with 11 hooks across 3 stages:
- Pre-commit: 8 fast checks
- Pre-push: 7 thorough checks

### `.secrets.baseline`
Baseline file for detect-secrets. Contains known false positives.

**Update baseline:**
```bash
detect-secrets scan --exclude-files '\.git/|\.venv/' > .secrets.baseline
```

### `pyproject.toml`
Tool configurations:
```toml
[tool.bandit]
exclude_dirs = ["tests", "migrations"]
severity = "medium"

[tool.vulture]
min_confidence = 80
paths = ["src"]
exclude = ["tests/", "migrations/"]

[tool.deptry]
extend_exclude = ["tests", "migrations", "infrastructure"]
```

---

## Usage

### Test All Hooks
```bash
./scripts/test_hooks.sh
```

### Test Specific Hooks
```bash
# Security
poetry run pre-commit run detect-secrets --all-files
poetry run pre-commit run bandit --all-files
poetry run pre-commit run safety --all-files

# Code Analysis
poetry run pre-commit run vulture --all-files
poetry run pre-commit run deptry --all-files
```

### Bypass Hooks (Emergency Only)
```bash
# Skip pre-commit
git commit --no-verify -m "WIP: emergency hotfix"

# Skip pre-push
git push --no-verify
```

**⚠️  WARNING:** Bypassing hooks is tracked in CI/CD. All checks still run on GitHub.

---

## Code Quality Markers Policy

### BLOCKED Markers (Commit Fails)

These markers indicate **broken or temporary code** that should never be committed:

| Marker | Meaning | Action Required |
|--------|---------|-----------------|
| `FIXME` | Something is broken | Fix the bug before commit |
| `XXX` | Dangerous/hacky code | Refactor or remove |
| `HACK` | Temporary workaround | Implement proper solution |
| `TEMP` | Temporary code | Remove or make permanent |
| `WIP` | Work in progress | Complete or remove |

**Example (commit will FAIL):**
```python
# FIXME: This crashes on empty input
def process(data):
    return data[0]  # XXX: No validation
```

**Hook output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ COMMIT BLOCKED: Found code smells that must be fixed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/gapsense/module.py:42:  # FIXME: This crashes on empty input
src/gapsense/module.py:44:  return data[0]  # XXX: No validation

Fix the issues above or use TODO(name) for future work
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### WARNED Markers (Commit Allowed, Strongly Encouraged to Fix)

TODOs are **allowed** but **loudly warned** to encourage fixing:

**Good TODO formats:**
```python
# TODO: Add rate limiting                        ⚠️  Basic
# TODO(maku): Optimize this query                ✅ Better (has owner)
# TODO(maku): Add caching [JIRA-456]            ✅ Best (owner + ticket)
```

**Hook output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  WARNING: Found 3 TODO(s) in your code
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/gapsense/api.py:67:  # TODO: Add rate limiting
src/gapsense/diagnostic.py:142:  # TODO(maku): Optimize query
tests/test_api.py:23:  # TODO: Add test for edge case

🔔 REMINDER: Please consider fixing these before pushing!

Best practices:
  • Fix simple TODOs now (takes <5 min)
  • Format: # TODO(username): Description [ISSUE-123]
  • Create ticket for complex TODOs
  • Remove stale TODOs

📊 Technical debt accumulates fast - fix early!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Commit proceeds** - developer sees warning but can continue.

---

## What Gets Blocked

### Secrets
- AWS access keys
- Anthropic API keys
- WhatsApp API tokens
- Database passwords
- JWT tokens
- Private SSH keys
- GitHub tokens

### Security Issues
- Hardcoded passwords in code
- SQL injection vulnerabilities
- Shell command injection
- Weak crypto (MD5, DES)
- Insecure randomness (`random` instead of `secrets`)
- Pickle usage (unsafe deserialization)
- `eval()` / `exec()` usage

### Code Quality Issues
- Type errors (MyPy strict mode)
- Test coverage below 80%
- Unused code (functions, variables)
- Unused dependencies
- Missing dependencies
- Direct commits to `main` branch

---

## Ghana Data Protection Act Compliance

These security hooks help ensure:

1. **Data Protection** - Bandit prevents insecure data handling
2. **Encryption** - Detects weak crypto usage
3. **Secret Management** - Prevents API key leaks
4. **Dependency Security** - Safety blocks vulnerable packages
5. **Audit Trail** - All security checks logged in CI/CD

---

## Troubleshooting

### False Positive in detect-secrets
```bash
# Add to baseline
detect-secrets scan --update .secrets.baseline

# Or mark as false positive
# Add `# pragma: allowlist secret` comment above line
```

### Bandit False Positive
```bash
# Add comment to suppress
# nosec B101 - Reason for suppression
```

### Safety Check Fails
```bash
# Check specific vulnerability
poetry run safety check --json

# Update dependency
poetry update package-name
```

### Vulture False Positive (used via string, reflection)
```python
# Add to pyproject.toml
[tool.vulture]
ignore_names = ["function_used_by_reflection"]
```

---

## Performance Impact

| Stage | Before | After | Increase |
|-------|--------|-------|----------|
| Pre-commit | ~8s | ~10s | +2s |
| Pre-push | ~30s | ~45s | +15s |
| CI/CD | ~3min | ~4min | +1min |

**Trade-off:** +17 seconds total for comprehensive security scanning.

---

## Maintenance

### Update Tools
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update Python tools
poetry update bandit safety detect-secrets vulture deptry
```

### Review Security Findings
```bash
# Generate security report
poetry run bandit -r src/ -f html -o security-report.html
```

---

## References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://docs.pyup.io/docs/safety-20-overview)
- [detect-secrets](https://github.com/Yelp/detect-secrets)
- [Vulture](https://github.com/jendrikseipp/vulture)
- [Deptry](https://github.com/fpgmaas/deptry)
- [Ghana Data Protection Act](https://www.dataprotection.org.gh/)

---

**Last Updated:** 2026-02-14
**Status:** ✅ Active and enforced
