import os
import requests
import json
from dotenv import load_dotenv

# Load environment
load_dotenv(r"C:\Users\user\Documents\My Python\.env")
API_KEY = os.getenv("ZHIPU_API_KEY")

print("=" * 60)
print("ZHIPU AI API DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Check API key
print("\n[TEST 1] Checking API Key...")
if API_KEY:
    print(f"✅ API Key loaded: {API_KEY[:20]}...{API_KEY[-10:]}")
else:
    print("❌ API Key NOT found in .env")
    exit()

# Test 2: Simple API call
print("\n[TEST 2] Testing Zhipu AI API Connection...")
print(f"Using API Key: {API_KEY[:30]}...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "Hello, test message"}],
    "temperature": 0.7,
}

print(f"\nHeaders: {headers}")
print(f"Payload: {payload}")

try:
    print("\nMaking API call...")
    response = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print(f"\n✅ Response Status: {response.status_code}")
    print(f"Response Content: {response.text[:500]}")
    
    if response.status_code == 200:
        result = response.json()
        message = result['choices'][0]['message']['content']
        print(f"\n✅ SUCCESS! Zhipu AI Response:")
        print(f"   {message}")
    else:
        print(f"\n❌ ERROR: Status {response.status_code}")
        print(f"   Full response: {response.json()}")

except requests.exceptions.Timeout:
    print("❌ TIMEOUT: API took too long to respond")
except requests.exceptions.ConnectionError:
    print("❌ CONNECTION ERROR: Cannot reach Zhipu AI")
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "=" * 60)