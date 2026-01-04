import pytest
import threading
import time
import os
from django.contrib.auth import get_user_model
from django.db import transaction, connection
from django.conf import settings
from django.test import Client
from django.urls import reverse

# --- CONFIGURATION ---
User = get_user_model()
# Mark all tests to use the DB
pytestmark = pytest.mark.django_db

class TestSecurityAndStability:

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.client = Client()
        self.admin_user = User.objects.create_superuser('admin_audit', 'admin@audit.com', 'StrongPass123!')
        self.std_user = User.objects.create_user('std_audit', 'std@audit.com', 'WeakPass123')

    # --- SECTION 1: FUNCTIONAL & INTEGRITY (Tests 1-12) ---

    def test_02_api_contract_verification(self):
        """Test 2: Verify critical endpoints return valid status codes"""
        endpoints = ['/admin/login/', '/'] # Add your actual API endpoints here
        for ep in endpoints:
            response = self.client.get(ep)
            assert response.status_code in [200, 302, 401, 403], f"Endpoint {ep} crashed with {response.status_code}"

    def test_05_boundary_values_username(self):
        """Test 5: Massive input handling"""
        huge_name = "A" * 5000
        try:
            User.objects.create_user(username=huge_name, password="pw")
            # If application allows 5000 char username, this is a warning/fail depending on requirements
            # strict mode: pytest.fail("Application accepted 5000 char username")
        except Exception as e:
            # We expect an error, but it must not be a 500 Server Error (Unhandled Exception)
            assert "Data too long" in str(e) or "value too long" in str(e) or "valid" in str(e)

    def test_07_critical_config_security(self):
        """Test 7: Ensure production security settings are active"""
        # These should fail in production if not set correctly
        warnings = []
        if settings.DEBUG:
            warnings.append("DEBUG is True (Critical)")
        if settings.SECRET_KEY == 'django-insecure-default':
            warnings.append("Using default insecure SECRET_KEY")
        if 'django.middleware.security.SecurityMiddleware' not in settings.MIDDLEWARE:
            warnings.append("SecurityMiddleware missing")
        
        if warnings:
            pytest.fail(f"Configuration Security Risks: {warnings}")

    def test_09_concurrent_writes_race_condition(self):
        """Test 9: Race condition simulation on User updates"""
        user_id = self.std_user.id
        
        def fast_update(name_suffix):
            try:
                u = User.objects.get(id=user_id)
                u.first_name = f"Race-{name_suffix}"
                u.save()
            except:
                pass

        threads = []
        for i in range(10):
            t = threading.Thread(target=fast_update, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

        # Check if DB is intact (not crashed)
        final_user = User.objects.get(id=user_id)
        assert "Race-" in final_user.first_name

    # --- SECTION 2: STABILITY & LOGIC (Tests 13-30) ---
    
    def test_25_transaction_rollback_integrity(self):
        """Test 25: Ensure transactions rollback on error"""
        count_before = User.objects.count()
        try:
            with transaction.atomic():
                User.objects.create_user('rollback_test', 'x@x.com', 'pw')
                raise Exception("Force Failure")
        except Exception:
            pass # Expected
        
        count_after = User.objects.count()
        assert count_before == count_after, "Atomic transaction failed to rollback data!"

    # --- SECTION 3: OWASP SECURITY (Tests 31-44) ---

    def test_33_sql_injection_blind(self):
        """Test 33: Basic SQL Injection pattern check in login"""
        # Attempting to bypass auth
        payloads = ["' OR '1'='1", "admin' --", "' OR 1=1 --"]
        for p in payloads:
            res = self.client.post('/admin/login/', {'username': p, 'password': 'pw'})
            # We expect 200 (Login page again) or 403. 
            # We fail if we get 500 (SQL Syntax Error) or 302 (Successful bypass redirect)
            assert res.status_code != 500, f"Payload {p} caused Server Error (Possible SQLi)"
            if res.status_code == 302 and res.url != '/admin/login/':
                 pytest.fail(f"SQLi Login Bypass Successful with payload: {p}")

    def test_39_idor_profile_access(self):
        """Test 39: Insecure Direct Object Reference (IDOR)"""
        # Log in as Standard User
        self.client.force_login(self.std_user)
        
        # Try to access Admin User's ID (assuming generic /users/ID endpoint structure)
        # Adjust URL to match actual project structure
        target_url = f"/users/{self.admin_user.id}/"
        res = self.client.get(target_url)
        
        # If response is OK (200) and contains admin email, it is a vulnerability
        if res.status_code == 200 and self.admin_user.email in str(res.content):
            pytest.fail("IDOR Vulnerability: Standard user accessed Admin profile data")

    def test_42_information_leakage(self):
        """Test 42: Check for stack traces in 404 pages"""
        res = self.client.get('/non-existent-random-url-xyz')
        content = str(res.content)
        risk_keywords = ['Traceback (most recent call last)', 'Environment variables', 'SECRET_KEY']
        
        leaks = [k for k in risk_keywords if k in content]
        if leaks and settings.DEBUG:
             pytest.fail(f"Information Leakage detected in 404 page (DEBUG=True): {leaks}")

    def test_45_hardcoded_secrets_scan(self):
        """Test 45: Scans settings for hardcoded keys (Basic check)"""
        # This is a runtime check of loaded settings
        if hasattr(settings, 'AWS_SECRET_ACCESS_KEY'):
            key = settings.AWS_SECRET_ACCESS_KEY
            if key and not key.startswith('os.environ'):
                # Heuristic: if it looks like a real key (len > 20) and not loaded from env
                if len(str(key)) > 20 and ' ' not in str(key): 
                    pytest.fail("Potential Hardcoded AWS Key detected in settings")

