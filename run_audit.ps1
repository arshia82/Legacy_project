Write-Host ">>> STARTING LEGACY_PROJECT LOCAL AUDIT <<<" -ForegroundColor Cyan

# A. Environment Setup
if (-not (Test-Path "venv")) {
    Write-Host "[*] Creating Python Virtual Environment..."
    python -m venv venv
}
Write-Host "[*] Activating Venv..."
& .\venv\Scripts\Activate.ps1

Write-Host "[*] Installing Security Tools..."
pip install -r requirements-audit.txt --quiet --disable-pip-version-check

# B. Static Analysis (SAST)
Write-Host "
--- [PHASE 1] STATIC ANALYSIS ---" -ForegroundColor Yellow
Write-Host "[*] Running Bandit (Code Security Scan)..."
bandit -r . -f txt -o audit_reports/bandit_report.txt --exit-zero --exclude ./venv,./tests
Write-Host "    -> Report saved to audit_reports/bandit_report.txt"

Write-Host "[*] Running Safety (Dependency Scan)..."
safety check > audit_reports/safety_report.txt
Write-Host "    -> Report saved to audit_reports/safety_report.txt"

# C. Functional & Security Tests
Write-Host "
--- [PHASE 2] PYTEST SECURITY SUITE ---" -ForegroundColor Yellow
# Try to auto-detect Django settings if not set
    Write-Host "    -> Assumed DJANGO_SETTINGS_MODULE='core.settings'. Change in run_audit.ps1 if needed."
}

$env:DJANGO_SETTINGS_MODULE = 'tests.audit_settings'
pytest tests/audit_suite.py --verbose --junitxml=audit_reports/test_results.xml
if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] All Security Tests Passed." -ForegroundColor Green
} else {
    Write-Host "[WARNING] Vulnerabilities or Defects Found! Check logs above." -ForegroundColor Red
}

Write-Host "
>>> AUDIT COMPLETE. Review 'audit_reports/' folder." -ForegroundColor Cyan


