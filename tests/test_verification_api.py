# tests/test_verification_api.py
"""
Quick API test script - Run with: python tests/test_verification_api.py
"""
import requests
import time

BASE_URL = "http://127.0.0.1:8000/api/auth"

# Colors
G, R, Y, B, N = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[0m'


def test_verification_flow():
    print(f"\n{Y}=== COACH VERIFICATION API TEST ==={N}\n")
    
    # 1. Get OTP for coach
    print(f"{B}1. Sending OTP...{N}")
    resp = requests.post(f"{BASE_URL}/otp/send/", json={"phone": "09121111111"})
    print(f"   Status: {resp.status_code}")
    
    # 2. Get OTP from test endpoint
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/test/last-otp/?phone=09121111111")
    if resp.status_code != 200:
        print(f"{R}   Failed to get OTP{N}")
        return
    
    code = resp.json().get('code')
    print(f"   OTP: {code}")
    
    # 3. Verify OTP
    print(f"{B}2. Verifying OTP...{N}")
    resp = requests.post(f"{BASE_URL}/otp/verify/", json={
        "phone": "09121111111",
        "code": code
    })
    
    if resp.status_code != 200:
        print(f"{R}   Verification failed{N}")
        return
    
    token = resp.json().get('access')
    print(f"   {G}Token received{N}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 4. Update user to coach role (if needed)
    print(f"{B}3. Setting role to coach...{N}")
    resp = requests.patch(f"{BASE_URL}/me/", json={"role": "coach"}, headers=headers)
    
    # 5. Create verification request
    print(f"{B}4. Creating verification request...{N}")
    resp = requests.post(f"{BASE_URL}/verification/", json={
        "coach_message": "Please verify my coaching credentials",
        "specializations": ["fitness", "yoga"],
        "years_experience": 5
    }, headers=headers)
    
    if resp.status_code == 201:
        req_id = resp.json().get('id')
        req_num = resp.json().get('request_number')
        print(f"   {G}Created: {req_num}{N}")
    else:
        print(f"   {R}Failed: {resp.json()}{N}")
        return
    
    # 6. Upload documents
    print(f"{B}5. Uploading documents...{N}")
    for doc_type in ['id_card', 'certificate']:
        files = {'file': (f'{doc_type}.pdf', b'test pdf content', 'application/pdf')}
        data = {'document_type': doc_type}
        resp = requests.post(
            f"{BASE_URL}/verification/{req_id}/documents/",
            files=files, data=data, headers=headers
        )
        status = G + "OK" + N if resp.status_code == 201 else R + "FAIL" + N
        print(f"   {doc_type}: {status}")
    
    # 7. Submit request
    print(f"{B}6. Submitting request...{N}")
    resp = requests.post(f"{BASE_URL}/verification/{req_id}/submit/", headers=headers)
    status = G + "OK" + N if resp.status_code == 200 else R + "FAIL" + N
    print(f"   Submit: {status}")
    
    # 8. Get request status
    print(f"{B}7. Checking status...{N}")
    resp = requests.get(f"{BASE_URL}/verification/{req_id}/", headers=headers)
    if resp.status_code == 200:
        print(f"   Status: {resp.json().get('status')}")
        print(f"   Documents: {resp.json().get('document_count')}")
    
    print(f"\n{G}=== TEST COMPLETE ==={N}\n")


if __name__ == "__main__":
    # Reset first
    requests.post(f"{BASE_URL}/test/reset-limits/")
    test_verification_flow()