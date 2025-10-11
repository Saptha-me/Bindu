# Security Scanning

Bindu uses automated security scanning integrated into pre-commit hooks to catch security issues and secrets before they reach the repository.

## Tools

### 1. Bandit - Python Security Linter
Scans Python code for common security issues (SQL injection, hardcoded passwords, etc.)

### 2. detect-secrets - Secret Detection
Prevents secrets (API keys, passwords, tokens) from being committed

## Baseline Management

Both tools use **baseline files** to track known/accepted issues:
- `.secrets.baseline` - Known secrets (false positives, test data)
- `.bandit.baseline` - Known security issues (accepted risks)

### Why Baselines?

Baselines allow you to:
1. **Accept false positives** without disabling checks
2. **Track security debt** in a controlled manner
3. **Fail only on NEW issues** in CI/CD

## Workflow

### Initial Setup

```bash
# Install pre-commit hooks
pre-commit install

# First run will auto-create baselines if missing
git commit -m "test"
```

### Daily Development

Pre-commit hooks run automatically on `git commit`:

1. **Baseline auto-creation**: If `.secrets.baseline` doesn't exist, it's created automatically
2. **Secret detection**: New secrets are blocked
3. **Security scanning**: New Bandit issues are reported (with baseline comparison)

### When New Secrets Are Detected

If detect-secrets finds a new secret:

```bash
# Option 1: Remove the secret (recommended)
# Edit the file and remove the actual secret

# Option 2: Mark as false positive (audit)
pre-commit run audit-secrets-baseline --hook-stage manual

# This opens an interactive audit where you can:
# - Mark secrets as true/false positives
# - Add context/comments
```

### When New Security Issues Are Found

If Bandit finds new security issues:

```bash
# View the full report
bandit -r bindu -c bandit.yaml -ll -b .bandit.baseline

# Option 1: Fix the issue (recommended)
# Address the security concern in your code

# Option 2: Accept the risk (update baseline)
bandit -r bindu -c bandit.yaml -f json -o .bandit.baseline
git add .bandit.baseline
git commit -m "Accept security baseline update"
```

## Manual Commands

### Audit Secrets Baseline

Interactively review all secrets in the baseline:

```bash
pre-commit run audit-secrets-baseline --hook-stage manual
```

### Update Secrets Baseline

Regenerate the baseline with current secrets:

```bash
pre-commit run update-secrets-baseline --hook-stage manual
```

### Update Bandit Baseline

```bash
bandit -r bindu -c bandit.yaml -f json -o .bandit.baseline
```

## CI/CD Integration

In CI/CD pipelines, security scans should **fail on any new issues**:

```yaml
# Example GitHub Actions
- name: Security Scan
  run: |
    pre-commit run --all-files bandit
    pre-commit run --all-files detect-secrets
```

The baseline files (`.secrets.baseline`, `.bandit.baseline`) should be:
- ✅ **Committed to git** (tracked for audit trail)
- ✅ **Reviewed in PRs** (changes indicate new accepted risks)
- ✅ **Updated deliberately** (not automatically in CI)

## Configuration

### Bandit Configuration (`bandit.yaml`)

```yaml
skips:
  - B101  # Allow asserts in tests

exclude_dirs:
  - tests
  - examples
  - .venv
```

### detect-secrets Configuration

Configured via `.secrets.baseline` file which includes:
- Plugins used
- Files scanned
- Known secrets with metadata

## Best Practices

### ✅ DO

- **Commit baseline files** to track security posture over time
- **Review baseline changes** in PRs carefully
- **Fix issues** rather than adding to baseline when possible
- **Document accepted risks** when updating baselines
- **Run audits regularly** to review accepted secrets

### ❌ DON'T

- **Auto-update baselines in CI** (defeats the purpose)
- **Ignore security warnings** without investigation
- **Commit real secrets** even if in baseline (use env vars)
- **Disable hooks** to bypass checks

## Troubleshooting

### "Baseline file not found" error

The baseline is auto-created on first run. If you see this error:

```bash
# Manually create baseline
detect-secrets scan --baseline .secrets.baseline
```

### False positive in detect-secrets

```bash
# Audit and mark as false positive
pre-commit run audit-secrets-baseline --hook-stage manual
```

### Bandit baseline not working

Ensure you're using the correct arguments:

```bash
bandit -r bindu -c bandit.yaml -ll -b .bandit.baseline
```

The `-b` flag loads the baseline for comparison.

## Security Scanning Levels

### Bandit Severity Levels

- **HIGH**: Critical security issues (must fix)
- **MEDIUM**: Important security concerns (should fix)
- **LOW**: Minor issues or best practices (review)

The `-ll` flag in pre-commit config means "Low Level" - reports LOW and above.

### detect-secrets Confidence

- **High confidence**: Likely a real secret
- **Medium confidence**: Possibly a secret
- **Low confidence**: Probably false positive

## Maintenance

### Monthly Security Audit

```bash
# 1. Review secrets baseline
pre-commit run audit-secrets-baseline --hook-stage manual

# 2. Review Bandit baseline
bandit -r bindu -c bandit.yaml -ll -b .bandit.baseline

# 3. Check for outdated issues
# Review if baseline items have been fixed but not removed

# 4. Update documentation
# Document any accepted security risks
```

### Updating Tools

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Regenerate baselines after major updates
detect-secrets scan --baseline .secrets.baseline
bandit -r bindu -c bandit.yaml -f json -o .bandit.baseline
```

## Additional Resources

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
- [Pre-commit Documentation](https://pre-commit.com/)
