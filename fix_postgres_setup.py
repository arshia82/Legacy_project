import os
import sys
from pathlib import Path

print(">>> FIXING AUDIT CONFIGURATION (PYTHON MODE) <<<")

# 1. Get Credentials (press Enter to accept defaults)
print("\n--- Database Setup ---")
dbname = input("Enter Database Name [default: myfita]: ").strip() or "myfita"
user = input("Enter Database User [default: postgres]: ").strip() or "postgres"
password = input("Enter Database Password [default: postgres]: ").strip() or "postgres"
host = input("Enter Host [default: localhost]: ").strip() or "localhost"
port = input("Enter Port [default: 5432]: ").strip() or "5432"

# 2. Define the content EXACTLY (No indentation errors)
content = f"""import os
import sys
from pathlib import Path

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Try to import base settings (ignore errors to prevent crash)
try:
    from config.settings.base import *
except ImportError:
    pass

# --- AUDIT OVERRIDES ---
DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '{dbname}',
        'USER': '{user}',
        'PASSWORD': '{password}',
        'HOST': '{host}',
        'PORT': '{port}',
    }}
}}

# Ensure we have a secret key
if not locals().get('SECRET_KEY'):
    SECRET_KEY = 'audit-override-secret-key-xyz'

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Email backend that doesn't send real emails
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
"""

# 3. Write file cleanly
path = Path("tests/audit_settings.py")
try:
    path.parent.mkdir(exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"\n[+] Successfully generated 'tests/audit_settings.py' with correct indentation.")
except Exception as e:
    print(f"[-] Error writing file: {e}")
    sys.exit(1)

# 4. Update run_audit.ps1 to ensure it uses this file
ps_path = Path("run_audit.ps1")
if ps_path.exists():
    ps_content = ps_path.read_text(encoding="utf-8")
    # Clean previous env var injections
    lines = ps_content.splitlines()
    new_lines = [line for line in lines if "$env:DJANGO_SETTINGS_MODULE" not in line]
    
    # Inject the correct env var before pytest runs
    final_lines = []
    for line in new_lines:
        if "pytest tests/audit_suite.py" in line:
            final_lines.append("$env:DJANGO_SETTINGS_MODULE = 'tests.audit_settings'")
            final_lines.append(line)
        else:
            final_lines.append(line)
            
    ps_path.write_text("\n".join(final_lines), encoding="utf-8")
    print("[+] Updated 'run_audit.ps1' configuration.")

print("\n>>> SETUP COMPLETE. Run this command now:")
print(".\\run_audit.ps1")
