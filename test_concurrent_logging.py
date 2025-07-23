#!/usr/bin/env python3
"""
Enhanced Concurrent Request Testing Script

This script tests the improved request logging middleware by sending
many concurrent requests and demonstrates the request correlation features.
"""

import asyncio
import aiohttp
import time
import random
import json
from typing import List, Dict, Any

# Base URL for the API
BASE_URL = "http://localhost:8880"

class ConcurrentTester:
    def __init__(self, base_url: str = BASE_URL, max_concurrent: int = 50):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.results = []
        
    async def make_request(self, session: aiohttp.ClientSession, request_type: str, request_id: int) -> Dict[str, Any]:
        """Make a single request and record results"""
        start_time = time.time()
        
        try:
            if request_type == "health":
                async with session.get(f"{self.base_url}/health") as response:
                    result = {
                        "request_id": request_id,
                        "type": request_type,
                        "status": response.status,
                        "duration": time.time() - start_time,
                        "success": True
                    }
                    
            elif request_type == "models":
                async with session.get(f"{self.base_url}/v1/models") as response:
                    result = {
                        "request_id": request_id,
                        "type": request_type,
                        "status": response.status,
                        "duration": time.time() - start_time,
                        "success": True
                    }
                    
            elif request_type == "tts":
                # Small TTS request to test body logging
                data = {
                    "model": "kokoro",
                    "input": f"Test message number {request_id} for concurrent testing",
                    "voice": "af_heart",
                    "response_format": "mp3"
                }
                
                async with session.post(
                    f"{self.base_url}/v1/audio/speech",
                    json=data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = {
                        "request_id": request_id,
                        "type": request_type,
                        "status": response.status,
                        "duration": time.time() - start_time,
                        "success": True,
                        "body_size": len(json.dumps(data))
                    }
                    
            elif request_type == "debug":
                async with session.get(f"{self.base_url}/debug/system") as response:
                    result = {
                        "request_id": request_id,
                        "type": request_type,
                        "status": response.status,
                        "duration": time.time() - start_time,
                        "success": True
                    }
                    
            else:  # invalid endpoint
                async with session.get(f"{self.base_url}/invalid-endpoint-{request_id}") as response:
                    result = {
                        "request_id": request_id,
                        "type": request_type,
                        "status": response.status,
                        "duration": time.time() - start_time,
                        "success": response.status < 500
                    }
                    
        except Exception as e:
            result = {
                "request_id": request_id,
                "type": request_type,
                "status": 0,
                "duration": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
            
        return result
    
    async def run_concurrent_test(self, num_requests: int = 100) -> List[Dict[str, Any]]:
        """Run concurrent requests and collect results"""
        print(f"🚀 Starting concurrent test with {num_requests} requests...")
        print(f"📊 Max concurrent connections: {self.max_concurrent}")
        
        # Define request types and their probabilities
        request_types = [
            ("health", 0.3),    # 30% health checks (fast)
            ("models", 0.2),    # 20% model queries (medium)
            ("tts", 0.3),       # 30% TTS requests (slow, with body)
            ("debug", 0.1),     # 10% debug endpoints (medium)
            ("invalid", 0.1),   # 10% invalid endpoints (fast, 404s)
        ]
        
        # Generate request plan
        requests_to_make = []
        for i in range(num_requests):
            # Choose request type based on probability
            rand = random.random()
            cumulative = 0
            for req_type, prob in request_types:
                cumulative += prob
                if rand <= cumulative:
                    requests_to_make.append((req_type, i))
                    break
        
        # Shuffle to randomize execution order
        random.shuffle(requests_to_make)
        
        # Create semaphore to limit concurrent connections
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def bounded_request(session, req_type, req_id):
            async with semaphore:
                return await self.make_request(session, req_type, req_id)
        
        # Run all requests concurrently
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            start_time = time.time()
            
            tasks = [
                bounded_request(session, req_type, req_id)
                for req_type, req_id in requests_to_make
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
        
        # Filter out exceptions and process results
        valid_results = [r for r in results if isinstance(r, dict)]
        
        print(f"✅ Completed {len(valid_results)} requests in {total_time:.2f} seconds")
        print(f"📈 Average throughput: {len(valid_results) / total_time:.2f} requests/second")
        
        return valid_results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> None:
        """Analyze and display test results"""
        if not results:
            print("❌ No results to analyze")
            return
            
        print("\n" + "="*60)
        print("📊 CONCURRENT TEST ANALYSIS")
        print("="*60)
        
        # Group by request type
        by_type = {}
        total_requests = len(results)
        successful_requests = len([r for r in results if r["success"]])
        
        for result in results:
            req_type = result["type"]
            if req_type not in by_type:
                by_type[req_type] = []
            by_type[req_type].append(result)
        
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
        print(f"Failed: {total_requests - successful_requests}")
        
        print("\n📋 BY REQUEST TYPE:")
        for req_type, type_results in by_type.items():
            count = len(type_results)
            success_count = len([r for r in type_results if r["success"]])
            avg_duration = sum(r["duration"] for r in type_results) / count
            
            status_codes = {}
            for r in type_results:
                status = r["status"]
                status_codes[status] = status_codes.get(status, 0) + 1
            
            print(f"\n  {req_type.upper()}:")
            print(f"    Count: {count}")
            print(f"    Success: {success_count}/{count} ({success_count/count*100:.1f}%)")
            print(f"    Avg Duration: {avg_duration:.3f}s")
            print(f"    Status Codes: {dict(sorted(status_codes.items()))}")
        
        # Timing analysis
        durations = [r["duration"] for r in results]
        durations.sort()
        
        print(f"\n⏱️  TIMING ANALYSIS:")
        print(f"    Fastest: {min(durations):.3f}s")
        print(f"    Slowest: {max(durations):.3f}s")
        print(f"    Median: {durations[len(durations)//2]:.3f}s")
        print(f"    95th percentile: {durations[int(len(durations)*0.95)]:.3f}s")
        
        # Concurrent logging analysis
        print(f"\n🔍 LOGGING ANALYSIS:")
        print("    Check the server logs to see:")
        print("    - Request IDs in format [a1b2c3d4]")
        print("    - Request/response correlation")
        print("    - Timing categories [FAST], [MEDIUM], [SLOW]")
        print("    - Request body logging for TTS requests")
        print("    - No log message corruption or mixing")

async def main():
    """Main test function"""
    print("🧪 Enhanced Concurrent Request Logging Test")
    print("="*50)
    
    tester = ConcurrentTester(max_concurrent=20)
    
    # Test different scenarios
    scenarios = [
        {"name": "Light Load", "requests": 50, "concurrent": 10},
        {"name": "Medium Load", "requests": 100, "concurrent": 20},
        {"name": "Heavy Load", "requests": 200, "concurrent": 50},
    ]
    
    for scenario in scenarios:
        print(f"\n🎯 Testing {scenario['name']}")
        print("-" * 30)
        
        tester.max_concurrent = scenario["concurrent"]
        
        try:
            results = await tester.run_concurrent_test(scenario["requests"])
            tester.analyze_results(results)
            
            # Small delay between scenarios
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Scenario failed: {e}")
    
    print("\n" + "="*60)
    print("🎉 CONCURRENT TESTING COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Review the server logs to see request correlation")
    print("2. Look for [request_id] in all log messages")
    print("3. Verify no log corruption during concurrent requests")
    print("4. Check timing categories and performance patterns")

if __name__ == "__main__":
    asyncio.run(main())
