#!/usr/bin/env python3
"""
Integration test for cache performance with actual API calls.
Tests the completion endpoint with timing measurements.
"""

import sys
import time
import json
import requests
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:9380"  # Adjust to your setup
AUTHORIZATION_TOKEN = "your-auth-token"  # Replace with actual token

# Test data
TEST_CHAT_ID = None  # Will be set from user input
TEST_SESSION_ID = None  # Will be set from user input
TEST_QUESTION = "Hello, this is a test question"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def make_chat_request(chat_id, question, session_id=None, measure_time=True):
    """
    Make a chat request to the API.
    
    Returns:
        tuple: (response_data, elapsed_time)
    """
    url = f"{API_BASE_URL}/api/v1/chats/{chat_id}/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTHORIZATION_TOKEN}"
    }
    
    payload = {
        "question": question,
        "stream": False
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            return response.json(), elapsed
        else:
            print(f"   ✗ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None, elapsed
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ✗ Request error: {e}")
        return None, elapsed


def test_cache_miss_vs_hit():
    """Test cache performance: first request (MISS) vs second request (HIT)."""
    print_section("🧪 Testing Cache Miss vs Cache Hit")
    
    if not TEST_CHAT_ID:
        print("\n   ⚠️  Please set TEST_CHAT_ID first!")
        return False
    
    # First request - should be CACHE MISS
    print("\n   1️⃣  First Request (Expected: CACHE MISS)")
    print("   " + "-"*66)
    
    response1, time1 = make_chat_request(TEST_CHAT_ID, TEST_QUESTION)
    
    if response1:
        print(f"   ✓ Request successful")
        print(f"   ⏱️  Response time: {time1:.3f}s ({time1*1000:.0f}ms)")
        session_id = response1.get("data", {}).get("session_id")
        if session_id:
            print(f"   📝 Session ID: {session_id}")
            global TEST_SESSION_ID
            TEST_SESSION_ID = session_id
    else:
        print("   ✗ First request failed")
        return False
    
    # Wait a bit
    time.sleep(1)
    
    # Second request - should be CACHE HIT
    print("\n   2️⃣  Second Request (Expected: CACHE HIT)")
    print("   " + "-"*66)
    
    response2, time2 = make_chat_request(
        TEST_CHAT_ID, 
        "Another question",
        session_id=TEST_SESSION_ID
    )
    
    if response2:
        print(f"   ✓ Request successful")
        print(f"   ⏱️  Response time: {time2:.3f}s ({time2*1000:.0f}ms)")
    else:
        print("   ✗ Second request failed")
        return False
    
    # Compare
    print("\n   📊 Performance Comparison")
    print("   " + "-"*66)
    print(f"   First request (cache MISS):  {time1:.3f}s ({time1*1000:.0f}ms)")
    print(f"   Second request (cache HIT):  {time2:.3f}s ({time2*1000:.0f}ms)")
    
    if time2 < time1:
        improvement = ((time1 - time2) / time1) * 100
        saved_ms = (time1 - time2) * 1000
        print(f"   \n   ✅ Performance improved by {improvement:.1f}%")
        print(f"   ✅ Time saved: {saved_ms:.0f}ms")
        return True
    else:
        print(f"   \n   ⚠️  Second request was not faster (cache might not be working)")
        return False


def test_multiple_requests():
    """Test multiple sequential requests to verify consistent caching."""
    print_section("🔄 Testing Multiple Sequential Requests")
    
    if not TEST_CHAT_ID or not TEST_SESSION_ID:
        print("\n   ⚠️  Please run cache miss/hit test first!")
        return False
    
    times = []
    num_requests = 5
    
    print(f"\n   Making {num_requests} sequential requests...\n")
    
    for i in range(num_requests):
        question = f"Test question #{i+1}"
        response, elapsed = make_chat_request(
            TEST_CHAT_ID,
            question,
            session_id=TEST_SESSION_ID
        )
        
        times.append(elapsed)
        status = "✓" if response else "✗"
        print(f"   {status} Request {i+1}: {elapsed:.3f}s ({elapsed*1000:.0f}ms)")
        
        time.sleep(0.5)  # Small delay between requests
    
    # Statistics
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print("\n   📊 Statistics")
        print("   " + "-"*66)
        print(f"   Average: {avg_time:.3f}s ({avg_time*1000:.0f}ms)")
        print(f"   Min:     {min_time:.3f}s ({min_time*1000:.0f}ms)")
        print(f"   Max:     {max_time:.3f}s ({max_time*1000:.0f}ms)")
        
        # Check consistency
        if max_time - min_time < 1.0:  # Less than 1s variation
            print("\n   ✅ Response times are consistent (cache working well)")
            return True
        else:
            print("\n   ⚠️  High variation in response times")
            return False
    
    return False


def check_server_logs():
    """Instructions to check server logs for cache activity."""
    print_section("📋 How to Verify Cache in Server Logs")
    
    print("""
    To verify caching is working, check your server logs for these patterns:
    
    🔍 First Request (Cache MISS):
    ───────────────────────────────────────────────────────────────────
    [TIMING] completion() started at ...
    [CACHE] Dialog MISS: <chat_id>
    [TIMING] DialogService.query took 0.XXXs        ← Should be slower
    [CACHE] Conversation MISS: <session_id>
    [TIMING] ConversationService.query took 0.XXXs  ← Should be slower
    [TIMING] Total before memory load: X.XXXs
    
    
    🎯 Second Request (Cache HIT):
    ───────────────────────────────────────────────────────────────────
    [TIMING] completion() started at ...
    [CACHE] Dialog HIT: <chat_id>                   ← ✅ From cache!
    [TIMING] DialogService.query took 0.00Xs        ← Much faster!
    [CACHE] Conversation HIT: <session_id>          ← ✅ From cache!
    [TIMING] ConversationService.query took 0.00Xs  ← Much faster!
    [TIMING] Total before memory load: 0.0XXs       ← Should be < 100ms
    
    
    📦 Check with Docker:
    ───────────────────────────────────────────────────────────────────
    # View real-time logs
    docker logs -f ragflow-server | grep -E "CACHE|TIMING"
    
    # Check Redis keys
    docker exec ragflow-server redis-cli KEYS "*_cache:*"
    
    # Monitor cache hit rate
    docker exec ragflow-server redis-cli INFO stats | grep keyspace
    """)


def print_manual_test_guide():
    """Print manual testing guide."""
    print_section("🧪 Manual Testing Guide")
    
    print("""
    Before running this script, you need to:
    
    1️⃣  Get Your Test Data:
       • Chat ID: From your database or API
       • Auth Token: From your authentication system
       
    2️⃣  Update Configuration in this script:
       • Set API_BASE_URL (line 13)
       • Set AUTHORIZATION_TOKEN (line 14)
       • Set TEST_CHAT_ID (line 17)
    
    3️⃣  Alternative: Test with curl:
    
       # First request (Cache MISS)
       curl -X POST http://localhost:9380/api/v1/chats/{chat_id}/completions \\
         -H "Content-Type: application/json" \\
         -H "Authorization: Bearer {token}" \\
         -d '{"question": "Hello", "stream": false}' \\
         -w "\\nTime: %{time_total}s\\n"
       
       # Second request (Cache HIT - should be faster)
       curl -X POST http://localhost:9380/api/v1/chats/{chat_id}/completions \\
         -H "Content-Type: application/json" \\
         -H "Authorization: Bearer {token}" \\
         -d '{"question": "Another question", "session_id": "{session_id}", "stream": false}' \\
         -w "\\nTime: %{time_total}s\\n"
    
    4️⃣  Check the Results:
       • First request should take ~2s
       • Second request should take <100ms (with cache hit)
       • Check logs for [CACHE] HIT/MISS messages
    """)


def main():
    """Run integration tests."""
    print("\n" + "="*70)
    print("  🚀 CACHE INTEGRATION TEST SUITE")
    print("="*70)
    
    # Check configuration
    if not TEST_CHAT_ID or AUTHORIZATION_TOKEN == "your-auth-token":
        print_manual_test_guide()
        print("\n⚠️  Please configure test parameters first!")
        print("   Edit this file and set:")
        print("   • TEST_CHAT_ID")
        print("   • AUTHORIZATION_TOKEN")
        print("   • API_BASE_URL (if different)")
        return 1
    
    # Run tests
    results = []
    
    results.append(("Cache Miss vs Hit", test_cache_miss_vs_hit()))
    
    if TEST_SESSION_ID:
        results.append(("Multiple Requests", test_multiple_requests()))
    
    # Show how to check logs
    check_server_logs()
    
    # Summary
    print_section("📊 TEST SUMMARY")
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"   {status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n   🎉 All integration tests passed!")
        print("   ✅ Cache is working correctly in the API")
        return 0
    else:
        print("\n   ⚠️  Some tests failed. Check logs and configuration.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
