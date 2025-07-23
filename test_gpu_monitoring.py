#!/usr/bin/env python3
"""
GPU Monitoring Test Script

This script tests the GPU monitoring functionality by making requests
to the TTS service and demonstrating the GPU logging features.
"""

import requests
import time
import json
from typing import Dict, Any

# Base URL for the API
BASE_URL = "http://localhost:8880"

def test_gpu_endpoint():
    """Test the GPU stats endpoint"""
    print("🖥️ Testing GPU stats endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/debug/gpu", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ GPU endpoint working")
            print(f"   📊 Found {data.get('gpu_count', 0)} GPU(s)")
            
            for gpu in data.get('gpus', []):
                print(f"   🔹 GPU {gpu['id']}: {gpu['name']}")
                print(f"      Utilization: {gpu['utilization_percent']}%")
                print(f"      Memory: {gpu['memory']['used_mb']:.0f}MB/{gpu['memory']['total_mb']:.0f}MB ({gpu['memory']['percent']}%)")
                if 'temperature_celsius' in gpu:
                    print(f"      Temperature: {gpu['temperature_celsius']}°C")
                if 'power_watts' in gpu:
                    print(f"      Power: {gpu['power_watts']}W")
        else:
            print(f"   ❌ GPU endpoint returned {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ GPU endpoint failed: {e}")

def test_tts_with_gpu_logging():
    """Test TTS generation while monitoring GPU stats"""
    print("\n🎤 Testing TTS with GPU monitoring...")
    
    # Test data
    tts_data = {
        "model": "kokoro",
        "input": "Testing GPU monitoring with Kokoro TTS. This is a longer sentence to ensure some GPU utilization during generation.",
        "voice": "af_heart",
        "response_format": "mp3"
    }
    
    try:
        print("   📝 Making TTS request...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/v1/audio/speech",
            json=tts_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            audio_size = len(response.content)
            print(f"   ✅ TTS completed in {duration:.2f}s")
            print(f"   📊 Generated {audio_size} bytes of audio")
            print("   💡 Check server logs for GPU utilization during this request")
        else:
            print(f"   ❌ TTS failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ TTS request failed: {e}")

def test_concurrent_tts_gpu_monitoring():
    """Test concurrent TTS requests to see GPU utilization under load"""
    print("\n🔄 Testing concurrent TTS requests...")
    
    import threading
    import concurrent.futures
    
    def make_tts_request(request_id: int):
        """Make a single TTS request"""
        tts_data = {
            "model": "kokoro",
            "input": f"Concurrent GPU test request number {request_id}. Testing GPU utilization under load.",
            "voice": "af_heart",
            "response_format": "mp3"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/audio/speech",
                json=tts_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            return {
                "id": request_id,
                "status": response.status_code,
                "size": len(response.content) if response.status_code == 200 else 0,
                "success": response.status_code == 200
            }
        except Exception as e:
            return {
                "id": request_id,
                "status": 0,
                "size": 0,
                "success": False,
                "error": str(e)
            }
    
    print("   🚀 Starting 5 concurrent TTS requests...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_tts_request, i) for i in range(1, 6)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    duration = time.time() - start_time
    successful = len([r for r in results if r["success"]])
    
    print(f"   ✅ Completed {successful}/5 requests in {duration:.2f}s")
    print("   💡 Check server logs for GPU utilization patterns during concurrent load")

def monitor_gpu_during_load():
    """Monitor GPU stats while generating load"""
    print("\n📊 Monitoring GPU stats during TTS load...")
    
    def generate_load():
        """Generate continuous TTS load"""
        for i in range(3):
            tts_data = {
                "model": "kokoro",
                "input": f"Load generation request {i+1}. This is a longer text to ensure sustained GPU utilization for monitoring purposes.",
                "voice": "af_heart", 
                "response_format": "mp3"
            }
            
            try:
                requests.post(
                    f"{BASE_URL}/v1/audio/speech",
                    json=tts_data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                time.sleep(1)  # Brief pause between requests
            except:
                pass
    
    import threading
    
    # Start load generation in background
    load_thread = threading.Thread(target=generate_load)
    load_thread.start()
    
    # Monitor GPU stats while load is running
    print("   🔄 Generating TTS load and monitoring GPU...")
    for i in range(6):  # Monitor for ~30 seconds
        try:
            response = requests.get(f"{BASE_URL}/debug/gpu", timeout=5)
            if response.status_code == 200:
                data = response.json()
                for gpu in data.get('gpus', []):
                    print(f"   📊 T+{i*5}s: GPU {gpu['id']} - {gpu['utilization_percent']}% | Mem: {gpu['memory']['percent']:.1f}%", end="")
                    if 'temperature_celsius' in gpu:
                        print(f" | Temp: {gpu['temperature_celsius']}°C", end="")
                    print()
        except:
            print(f"   ⚠️ T+{i*5}s: Failed to get GPU stats")
        
        time.sleep(5)
    
    # Wait for load generation to complete
    load_thread.join()
    print("   ✅ GPU monitoring during load complete")

def main():
    """Main test function"""
    print("🧪 GPU Monitoring Test Suite")
    print("=" * 50)
    
    # Test 1: GPU endpoint
    test_gpu_endpoint()
    
    # Test 2: Single TTS with GPU logging
    test_tts_with_gpu_logging()
    
    # Test 3: Concurrent requests
    test_concurrent_tts_gpu_monitoring()
    
    # Test 4: GPU monitoring during load
    monitor_gpu_during_load()
    
    print("\n" + "=" * 50)
    print("🎉 GPU MONITORING TESTS COMPLETE!")
    print("=" * 50)
    print("\nWhat to check in the server logs:")
    print("1. 🖥️ GPU initialization messages at startup")
    print("2. 📊 Periodic GPU stats (if GPU_STATS_INTERVAL > 0)")
    print("3. 🔄 Request logs with GPU stats (if LOG_GPU_ON_REQUESTS=true)")
    print("4. 📈 GPU utilization changes during TTS generation")
    print("5. 🌡️ Temperature monitoring during sustained load")
    
    print("\nConfiguration tips:")
    print("- Set LOG_GPU_ON_REQUESTS=true to see GPU stats in request logs")
    print("- Set GPU_STATS_INTERVAL=10 for frequent periodic monitoring")
    print("- Check /debug/gpu endpoint for real-time GPU information")

if __name__ == "__main__":
    main()
