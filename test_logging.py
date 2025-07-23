#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced logging features
"""

import requests
import time
import json

# Base URL for the API
BASE_URL = "http://localhost:8880"

def test_logging_features():
    """Test various endpoints to demonstrate logging"""
    
    print("🧪 Testing Kokoro-FastAPI Enhanced Logging Features")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   ✅ Health check: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Health check failed: {e}")
    
    time.sleep(1)
    
    # Test 2: Test endpoint
    print("\n2. Testing test endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/v1/test", timeout=5)
        print(f"   ✅ Test endpoint: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Test endpoint failed: {e}")
    
    time.sleep(1)
    
    # Test 3: Models endpoint
    print("\n3. Testing models endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/v1/models", timeout=5)
        print(f"   ✅ Models endpoint: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Models endpoint failed: {e}")
    
    time.sleep(1)
    
    # Test 4: TTS endpoint (this will show request body logging)
    print("\n4. Testing TTS endpoint with request body...")
    try:
        tts_data = {
            "model": "kokoro",
            "input": "Hello, this is a test of the enhanced logging system!",
            "voice": "af_heart",
            "response_format": "mp3"
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/audio/speech",
            json=tts_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"   ✅ TTS endpoint: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ TTS endpoint failed: {e}")
    
    time.sleep(1)
    
    # Test 5: Invalid endpoint (should show 404)
    print("\n5. Testing invalid endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/invalid-endpoint", timeout=5)
        print(f"   ✅ Invalid endpoint: {response.status_code} (expected 404)")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Invalid endpoint test failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Logging test complete! Check the server logs to see the enhanced logging output.")
    print("\nYou should see:")
    print("- 🔄 for incoming requests")
    print("- ✅ for successful responses") 
    print("- ❌ for error responses")
    print("- 📝 for request body logging (debug level)")
    print("- Processing times for all requests")

if __name__ == "__main__":
    test_logging_features()
