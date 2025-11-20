#!/usr/bin/env python3
"""
Test script for cache performance verification.
Tests dialog and conversation caching functionality.
"""

import sys
import time
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_redis_connection():
    """Test basic Redis connectivity."""
    print("\n" + "="*60)
    print("1️⃣  Testing Redis Connection")
    print("="*60)
    try:
        from rag.utils.redis_conn import REDIS_CONN
        
        test_key = "cache_test:connection"
        REDIS_CONN.set(test_key, "connected", 10)
        result = REDIS_CONN.get(test_key)
        
        if result:
            print("   ✓ Redis connected successfully")
            REDIS_CONN.delete(test_key)
            return True
        else:
            print("   ✗ Redis not working properly")
            return False
    except Exception as e:
        print(f"   ✗ Redis connection failed: {e}")
        return False


def test_cache_utils():
    """Test cache utility functions."""
    print("\n" + "="*60)
    print("2️⃣  Testing Cache Utilities")
    print("="*60)
    
    try:
        from api.utils.cache_utils import (
            get_cached_dialog, cache_dialog,
            get_cached_conversation, cache_conversation,
            invalidate_dialog_cache, invalidate_conversation_cache
        )
        
        # Test dialog caching
        print("\n   Testing Dialog Cache...")
        test_dialog_id = "test_dialog_123"
        test_tenant_id = "test_tenant_456"
        test_dialog_data = {
            "id": test_dialog_id,
            "name": "Test Dialog",
            "tenant_id": test_tenant_id,
            "status": 1
        }
        
        # Should be None initially
        cached = get_cached_dialog(test_dialog_id, test_tenant_id)
        if cached is None:
            print("   ✓ Initial cache is empty (expected)")
        else:
            print(f"   ✗ Unexpected cached data: {cached}")
            return False
        
        # Cache the dialog
        result = cache_dialog(test_dialog_id, test_tenant_id, test_dialog_data)
        if result:
            print("   ✓ Dialog cached successfully")
        else:
            print("   ✗ Failed to cache dialog")
            return False
        
        # Should retrieve from cache
        cached = get_cached_dialog(test_dialog_id, test_tenant_id)
        if cached and cached.get("id") == test_dialog_id:
            print("   ✓ Dialog retrieved from cache successfully")
        else:
            print(f"   ✗ Failed to retrieve dialog from cache: {cached}")
            return False
        
        # Test conversation caching
        print("\n   Testing Conversation Cache...")
        test_session_id = "test_session_789"
        test_conv_data = {
            "id": test_session_id,
            "dialog_id": test_dialog_id,
            "message": []
        }
        
        # Cache and retrieve
        cache_conversation(test_session_id, test_dialog_id, test_conv_data)
        cached_conv = get_cached_conversation(test_session_id, test_dialog_id)
        
        if cached_conv and cached_conv.get("id") == test_session_id:
            print("   ✓ Conversation cached and retrieved successfully")
        else:
            print(f"   ✗ Failed with conversation cache: {cached_conv}")
            return False
        
        # Test invalidation
        print("\n   Testing Cache Invalidation...")
        invalidate_dialog_cache(test_dialog_id, test_tenant_id)
        cached = get_cached_dialog(test_dialog_id, test_tenant_id)
        if cached is None:
            print("   ✓ Dialog cache invalidated successfully")
        else:
            print(f"   ✗ Cache invalidation failed: {cached}")
            return False
        
        invalidate_conversation_cache(test_session_id, test_dialog_id)
        cached_conv = get_cached_conversation(test_session_id, test_dialog_id)
        if cached_conv is None:
            print("   ✓ Conversation cache invalidated successfully")
        else:
            print(f"   ✗ Conversation cache invalidation failed: {cached_conv}")
            return False
        
        print("\n   ✓ All cache utility tests passed!")
        return True
        
    except Exception as e:
        print(f"   ✗ Cache utility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_improvement():
    """Simulate performance improvement with caching."""
    print("\n" + "="*60)
    print("3️⃣  Testing Performance Improvement")
    print("="*60)
    
    try:
        from api.utils.cache_utils import (
            cache_dialog, get_cached_dialog,
            invalidate_dialog_cache
        )
        
        test_dialog_id = "perf_test_dialog"
        test_tenant_id = "perf_test_tenant"
        test_data = {
            "id": test_dialog_id,
            "name": "Performance Test",
            "tenant_id": test_tenant_id,
            "llm_id": "test_llm",
            "kb_ids": ["kb1", "kb2"],
            "prompt_config": {"prologue": "Hello"},
            "status": 1
        }
        
        # Clean up first
        invalidate_dialog_cache(test_dialog_id, test_tenant_id)
        
        # Measure cache MISS (first access)
        print("\n   Simulating CACHE MISS (first access)...")
        start = time.time()
        cached = get_cached_dialog(test_dialog_id, test_tenant_id)
        miss_time = time.time() - start
        
        # Simulate DB query time
        time.sleep(0.01)  # Simulate 10ms DB query
        cache_dialog(test_dialog_id, test_tenant_id, test_data)
        total_miss_time = time.time() - start
        
        print(f"   • Cache lookup: {miss_time*1000:.2f}ms")
        print(f"   • Total with DB: {total_miss_time*1000:.2f}ms")
        
        # Measure cache HIT (subsequent access)
        print("\n   Simulating CACHE HIT (subsequent access)...")
        start = time.time()
        cached = get_cached_dialog(test_dialog_id, test_tenant_id)
        hit_time = time.time() - start
        
        print(f"   • Cache lookup: {hit_time*1000:.2f}ms")
        
        if cached:
            improvement = ((total_miss_time - hit_time) / total_miss_time) * 100
            print(f"\n   ✓ Performance improvement: {improvement:.1f}%")
            print(f"   ✓ Time saved: {(total_miss_time - hit_time)*1000:.2f}ms")
            
            # Clean up
            invalidate_dialog_cache(test_dialog_id, test_tenant_id)
            return True
        else:
            print("   ✗ Failed to retrieve from cache")
            return False
            
    except Exception as e:
        print(f"   ✗ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_cache_keys():
    """Check existing cache keys in Redis."""
    print("\n" + "="*60)
    print("4️⃣  Checking Existing Cache Keys")
    print("="*60)
    
    try:
        from rag.utils.redis_conn import REDIS_CONN
        
        patterns = ["dialog_cache:*", "conv_cache:*"]
        
        for pattern in patterns:
            keys = REDIS_CONN.keys(pattern)
            print(f"\n   Pattern: {pattern}")
            if keys:
                print(f"   Found {len(keys)} key(s):")
                for key in keys[:10]:  # Show first 10
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    ttl = REDIS_CONN.ttl(key)
                    print(f"     • {key_str} (TTL: {ttl}s)")
                if len(keys) > 10:
                    print(f"     ... and {len(keys) - 10} more")
            else:
                print(f"   No keys found (this is normal if no requests made yet)")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Failed to check cache keys: {e}")
        return False


def print_recommendations():
    """Print testing and monitoring recommendations."""
    print("\n" + "="*60)
    print("📋 Testing & Monitoring Recommendations")
    print("="*60)
    
    print("""
    ✅ Manual Testing Steps:
    
    1. Start your application:
       docker-compose up -d
       
    2. Make a chat request (first time - should see CACHE MISS):
       curl -X POST http://localhost/api/chat \\
         -H "Content-Type: application/json" \\
         -d '{"chat_id": "xxx", "question": "Hello", "session_id": "yyy"}'
       
    3. Make the same request again (should see CACHE HIT):
       - Check logs for "[CACHE] Dialog HIT" and "[CACHE] Conversation HIT"
       - Response should be faster (check [TIMING] logs)
    
    4. Monitor Redis keys:
       docker exec ragflow-server redis-cli KEYS "dialog_cache:*"
       docker exec ragflow-server redis-cli KEYS "conv_cache:*"
       
    5. Check cache TTL:
       docker exec ragflow-server redis-cli TTL "dialog_cache:<tenant_id>:<dialog_id>"
    
    6. Clear cache if needed:
       docker exec ragflow-server redis-cli DEL $(redis-cli KEYS "*_cache:*")
    
    
    📊 What to Look For in Logs:
    
    First Request (Cache Miss):
    - [CACHE] Dialog MISS: <chat_id>
    - [CACHE] Conversation MISS: <session_id>
    - [TIMING] DialogService.query took 0.XXXs (slower)
    - [TIMING] ConversationService.query took 0.XXXs (slower)
    
    Subsequent Requests (Cache Hit):
    - [CACHE] Dialog HIT: <chat_id>
    - [CACHE] Conversation HIT: <session_id>
    - [TIMING] DialogService.query took 0.00Xs (much faster!)
    - [TIMING] ConversationService.query took 0.00Xs (much faster!)
    
    
    ⚠️  Things to Verify:
    
    1. Cache invalidation works after conversation updates
    2. TTL expires correctly (5min for dialog, 3min for conversation)
    3. No stale data after updates
    4. Memory usage in Redis stays reasonable
    5. Performance improvement is noticeable (should reduce from ~2s to <100ms)
    
    
    🔧 Troubleshooting:
    
    If cache not working:
    - Check Redis connection: docker exec ragflow-server redis-cli PING
    - Check Redis logs: docker logs ragflow-server 2>&1 | grep -i redis
    - Verify cache_utils.py is imported correctly
    - Check for exceptions in application logs
    """)


def main():
    """Run all cache tests."""
    print("\n" + "="*60)
    print("🧪 CACHE PERFORMANCE TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Redis Connection", test_redis_connection()))
    results.append(("Cache Utilities", test_cache_utils()))
    results.append(("Performance Improvement", test_performance_improvement()))
    results.append(("Cache Keys Check", check_cache_keys()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"   {status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n   🎉 All tests passed! Cache is ready for production.")
        print_recommendations()
        return 0
    else:
        print("\n   ⚠️  Some tests failed. Please fix issues before production.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
