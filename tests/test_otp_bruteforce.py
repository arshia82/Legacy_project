# tests/test_otp_bruteforce.py
"""
OTP Brute-Force Test

Kavenegar API Key:
"""
from kavenegar import *
api = KavenegarAPI('6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D')
params = { 'sender' : '2000660110', 'receptor': '09031517191', 'message' :'.My FITA is AT YOUR SERVICE' }

import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000/api/auth"
TEST_PHONE = "09031517191"


def reset_all():
    try:
        requests.post(f"{BASE_URL}/test/reset-limits/", timeout=5)
        time.sleep(0.5)
    except:
        pass


def test_anti_enumeration():
    logger.info("="*50)
    logger.info("TEST: Anti-Enumeration (Invalid Phone)")
    logger.info("="*50)
    
    reset_all()
    
    resp1 = requests.post(f"{BASE_URL}/otp/send/", json={"phone": "09111111111"})
    msg1 = resp1.json().get('detail') if resp1.status_code == 200 else None
    
    time.sleep(1)
    reset_all()
    
    resp2 = requests.post(f"{BASE_URL}/otp/send/", json={"phone": "09222222222"})
    msg2 = resp2.json().get('detail') if resp2.status_code == 200 else None
    
    logger.info(f"Invalid phone response: {msg1}")
    logger.info(f"Valid phone response: {msg2}")
    
    if msg1 == msg2 and resp1.status_code == resp2.status_code:
        print("[PASS] ✅ PASS: Responses are identical (anti-enumeration)")
        return True
    else:
        print("[FAIL] ❌ FAIL: Responses differ (enumeration possible)")
        return False


def test_rate_limiting():
    logger.info("="*50)
    logger.info("TEST: Rate Limiting (OTP Send)")
    logger.info("="*50)
    
    reset_all()
    blocked = False
    
    for i in range(1, 11):
        resp = requests.post(f"{BASE_URL}/otp/send/", json={"phone": TEST_PHONE})
        
        if resp.status_code == 200:
            logger.info(f"Request {i}: OK (200)")
        elif resp.status_code == 429:
            logger.info(f"Request {i}: RATE LIMITED (429)")
            blocked = True
            break
        
        time.sleep(0.1)
    
    if blocked:
        print("[PASS] ✅ PASS: Rate limiting is working")
        return True
    else:
        print("[FAIL] ❌ FAIL: Rate limiting not effective")
        return False


def test_progressive_lockout():
    logger.info("="*50)
    logger.info("TEST: Progressive Lockout (Wrong OTP)")
    logger.info("="*50)
    
    reset_all()
    test_phone = "09039999999"
    
    requests.post(f"{BASE_URL}/otp/send/", json={"phone": test_phone})
    time.sleep(0.5)
    
    locked = False
    
    for i in range(1, 8):
        resp = requests.post(
            f"{BASE_URL}/otp/verify/",
            json={"phone": test_phone, "code": "000000"}
        )
        
        try:
            data = resp.json()
        except:
            data = {}
        
        if resp.status_code == 400:
            logger.info(f"Attempt {i}: 400 - {data.get('detail', '')}")
        elif resp.status_code in [403, 429]:
            logger.info(f"Attempt {i}: {resp.status_code} - {data.get('detail', '')}")
            logger.info(f"🔒 Locked after {i} attempts")
            locked = True
            break
        
        time.sleep(0.1)
    
    if locked:
        print("[PASS] ✅ PASS: Lockout is working")
        return True
    else:
        print("[FAIL] ❌ FAIL: No lockout after failed attempts")
        return False


def test_timing_attack():
    logger.info("="*50)
    logger.info("TEST: Timing Attack Prevention")
    logger.info("="*50)
    
    times = []
    phones = ["09111111111", "09222222222", "09031517191"]
    
    for phone in phones:
        reset_all()
        time.sleep(0.3)
        
        resp = requests.post(f"{BASE_URL}/otp/send/", json={"phone": phone})
        elapsed = resp.elapsed.total_seconds()
        times.append(elapsed)
        logger.info(f"Phone {phone[:5]}***: {elapsed:.3f}s")
    
    variance = max(times) - min(times)
    
    if variance < 0.5:
        print(f"[PASS] ✅ PASS: Timing consistent (variance: {variance:.3f}s)")
        return True
    else:
        print(f"[WARN] ⚠️ WARN: Timing variance detected ({variance:.3f}s)")
        return False


def main():
    logger.info("="*60)
    logger.info("🔥 OTP BRUTE-FORCE TEST SUITE")
    logger.info("Business Plan: Risk Mitigation (p.14)")
    logger.info("="*60)
    
    results = []
    
    results.append(test_anti_enumeration())
    time.sleep(1)
    
    results.append(test_rate_limiting())
    time.sleep(1)
    
    results.append(test_progressive_lockout())
    time.sleep(1)
    
    results.append(test_timing_attack())
    
    logger.info("="*60)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(results)
    total = len(results)
    score = int((passed / total) * 100)
    
    logger.info(f"Tests Run: {total}")
    logger.info(f"Tests Passed: {passed}")
    logger.info(f"Tests Failed: {total - passed}")
    
    if passed < total:
        print("[WARN] ⚠️ VULNERABILITIES FOUND:")
        if not results[0]:
            print("[WARN]   - Phone enumeration possible")
        if not results[1]:
            print("[WARN]   - Rate limiting not working")
        if not results[2]:
            print("[WARN]   - Lockout not working")
        if not results[3]:
            print("[WARN]   - Timing variance detected")
    
    print(f"\n🎯 SECURITY SCORE: {score}/100")


if __name__ == "__main__":
    main()