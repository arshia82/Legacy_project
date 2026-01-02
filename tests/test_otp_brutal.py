# tests/test_otp_brutal.py
"""
Brutal OTP Security Test - FIXED

Kavenegar API Key:
"""
from kavenegar import *
api = KavenegarAPI('6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D')
params = { 'sender' : '2000660110', 'receptor': '09031517191', 'message' :'.My FITA is AT YOUR SERVICE' }

import requests
import time

BASE_URL = "http://127.0.0.1:8000/api/auth"
TEST_PHONE = "09031517191"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class BrutalOTPTest:
    def __init__(self):
        self.session = requests.Session()
        self.results = {'passed': 0, 'failed': 0}
    
    def log(self, msg, color=RESET):
        print(f"{color}{msg}{RESET}")
    
    def log_result(self, name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        color = GREEN if passed else RED
        self.log(f"[{status}] {name} {detail}", color)
        if passed:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
    
    def reset_all(self):
        """Reset everything before tests."""
        try:
            self.session.post(f"{BASE_URL}/test/reset-limits/", timeout=5)
            time.sleep(0.5)
        except Exception as e:
            self.log(f"  Warning: Could not reset: {e}", YELLOW)

    def test_local_delivery(self):
        self.log(f"\n{YELLOW}TEST 1: Local OTP Delivery{RESET}")
        self.log("="*50)
        
        self.reset_all()
        
        resp = self.session.post(f"{BASE_URL}/otp/send/", json={"phone": TEST_PHONE})
        
        if resp.status_code != 200:
            self.log_result("Local Delivery", False, f"Send failed: {resp.status_code}")
            return
        
        time.sleep(0.5)
        
        otp_resp = self.session.get(f"{BASE_URL}/test/last-otp/?phone={TEST_PHONE}")
        
        if otp_resp.status_code == 404:
            self.log_result("Local Delivery", False, "Test endpoint not found - check urls.py")
            return
        
        try:
            otp_data = otp_resp.json()
            if otp_data.get('code'):
                self.log(f"  📱 OTP Received: {otp_data.get('code')}", BLUE)
                self.log_result("Local Delivery", True, "OTP delivered")
            else:
                self.log_result("Local Delivery", False, "No OTP received")
        except:
            self.log_result("Local Delivery", False, "Invalid response")

    def test_full_flow(self):
        self.log(f"\n{YELLOW}TEST 2: Full OTP Flow{RESET}")
        self.log("="*50)
        
        self.reset_all()
        
        resp = self.session.post(f"{BASE_URL}/otp/send/", json={"phone": TEST_PHONE})
        if resp.status_code != 200:
            self.log_result("Full Flow", False, f"Send failed: {resp.status_code}")
            return
        
        self.log("  ✓ OTP Sent", GREEN)
        time.sleep(0.5)
        
        otp_resp = self.session.get(f"{BASE_URL}/test/last-otp/?phone={TEST_PHONE}")
        
        try:
            otp_data = otp_resp.json()
            code = otp_data.get('code')
        except:
            self.log_result("Full Flow", False, "Could not retrieve OTP from test endpoint")
            return
        
        if not code:
            self.log_result("Full Flow", False, "Could not get OTP")
            return
        
        self.log(f"  ✓ OTP Retrieved: {code}", GREEN)
        
        verify_resp = self.session.post(
            f"{BASE_URL}/otp/verify/",
            json={"phone": TEST_PHONE, "code": code}
        )
        
        try:
            verify_data = verify_resp.json()
            if verify_resp.status_code == 200 and verify_data.get('verified'):
                self.log("  ✓ OTP Verified", GREEN)
                self.log_result("Full Flow", True, "Complete flow working")
            else:
                self.log_result("Full Flow", False, f"Verify failed: {verify_resp.status_code}")
        except:
            self.log_result("Full Flow", False, "Invalid verify response")

    def test_rate_limiting(self):
        self.log(f"\n{YELLOW}TEST 3: Rate Limiting{RESET}")
        self.log("="*50)
        
        self.reset_all()
        blocked = False
        
        for i in range(1, 10):
            resp = self.session.post(f"{BASE_URL}/otp/send/", json={"phone": TEST_PHONE})
            
            if resp.status_code == 200:
                self.log(f"  Request {i}: Accepted (200)")
            elif resp.status_code == 429:
                self.log(f"  Request {i}: {GREEN}BLOCKED (429){RESET}")
                blocked = True
                break
            
            time.sleep(0.1)
        
        self.log_result("Rate Limiting", blocked, 
                       "Rate limiter working" if blocked else "No rate limiting")

    def test_lockout(self):
        self.log(f"\n{YELLOW}TEST 4: Brute Force Protection{RESET}")
        self.log("="*50)
        
        self.reset_all()
        test_phone = "09039999999"
        
        # Send OTP first
        self.session.post(f"{BASE_URL}/otp/send/", json={"phone": test_phone})
        time.sleep(0.5)
        
        locked = False
        
        for i in range(1, 8):
            resp = self.session.post(
                f"{BASE_URL}/otp/verify/",
                json={"phone": test_phone, "code": "000000"}
            )
            
            if resp.status_code == 400:
                self.log(f"  Attempt {i}: Invalid code (400)")
            elif resp.status_code in [403, 429]:
                self.log(f"  Attempt {i}: {GREEN}LOCKED OUT ({resp.status_code}){RESET}")
                locked = True
                break
            
            time.sleep(0.1)
        
        self.log_result("Brute Force Protection", locked,
                       "Lockout working" if locked else "No lockout!")

    def test_anti_enumeration(self):
        self.log(f"\n{YELLOW}TEST 5: Anti-Enumeration{RESET}")
        self.log("="*50)
        
        self.reset_all()
        
        resp1 = self.session.post(f"{BASE_URL}/otp/send/", json={"phone": "09031111111"})
        try:
            msg1 = resp1.json().get('detail')
        except:
            msg1 = None
        
        time.sleep(1)
        self.reset_all()
        
        resp2 = self.session.post(f"{BASE_URL}/otp/send/", json={"phone": "09032222222"})
        try:
            msg2 = resp2.json().get('detail')
        except:
            msg2 = None
        
        self.log(f"  Phone 1 response: {msg1}")
        self.log(f"  Phone 2 response: {msg2}")
        self.log(f"  Time difference: {abs(resp1.elapsed.total_seconds() - resp2.elapsed.total_seconds()):.3f}s")
        
        same = (msg1 == msg2) and (resp1.status_code == resp2.status_code)
        self.log_result("Anti-Enumeration", same,
                       "Responses identical" if same else "Enumeration possible!")

    def test_timing_attack(self):
        self.log(f"\n{YELLOW}TEST 6: Timing Attack Prevention{RESET}")
        self.log("="*50)
        
        times = []
        phones = ["09111111111", "09222222222", "09031517191"]
        
        for phone in phones:
            self.reset_all()
            time.sleep(0.3)
            
            resp = self.session.post(f"{BASE_URL}/otp/send/", json={"phone": phone})
            elapsed = resp.elapsed.total_seconds()
            times.append(elapsed)
            self.log(f"  Phone {phone[:5]}***: {elapsed:.3f}s")
        
        variance = max(times) - min(times)
        self.log(f"  Timing variance: {variance:.3f}s")
        
        passed = variance < 0.5
        self.log_result("Timing Attack Prevention", passed,
                       f"Variance {variance:.3f}s" + (" (Good)" if passed else " (VULNERABLE!)"))

    def run_all(self):
        self.log(f"\n{'='*60}")
        self.log(f"💀 {RED}BRUTAL OTP SECURITY TEST SUITE{RESET}")
        self.log(f"Target: {BASE_URL}")
        self.log(f"Mode: LOCAL (No real SMS)")
        self.log(f"{'='*60}")
        
        try:
            self.session.get(f"{BASE_URL}/otp/send/", timeout=2)
        except:
            self.log(f"\n{RED}ERROR: Server not running!{RESET}")
            return
        
        self.test_local_delivery()
        time.sleep(1)
        
        self.test_full_flow()
        time.sleep(1)
        
        self.test_rate_limiting()
        time.sleep(1)
        
        self.test_lockout()
        time.sleep(1)
        
        self.test_anti_enumeration()
        time.sleep(1)
        
        self.test_timing_attack()
        
        # Summary
        self.log(f"\n{'='*60}")
        self.log(f"📊 TEST SUMMARY")
        self.log(f"{'='*60}")
        
        total = self.results['passed'] + self.results['failed']
        score = int((self.results['passed'] / total) * 100) if total > 0 else 0
        
        self.log(f"Tests Passed: {GREEN}{self.results['passed']}{RESET}")
        self.log(f"Tests Failed: {RED}{self.results['failed']}{RESET}")
        self.log(f"\n🎯 SECURITY SCORE: {score}/100")
        
        if score == 100:
            self.log(f"\n{GREEN}✅ ALL SYSTEMS SECURE{RESET}")
        else:
            self.log(f"\n{RED}❌ VULNERABILITIES DETECTED{RESET}")


if __name__ == "__main__":
    tester = BrutalOTPTest()
    tester.run_all()