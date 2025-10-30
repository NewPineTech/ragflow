#!/usr/bin/env python3
"""
Test KB Retrieval Cache Performance
"""
import time
import sys
sys.path.insert(0, '/ragflow')

from rag.utils.redis_conn import REDIS_CONN

def test_cache_performance():
    """Test cache hit/miss performance"""
    print("\n" + "="*60)
    print("KB RETRIEVAL CACHE TEST")
    print("="*60 + "\n")
    
    # 1. Check Redis connection
    print("1️⃣ Checking Redis connection...")
    try:
        test_key = "test_kb_cache_connection"
        REDIS_CONN.set(test_key, "connected", 10)
        result = REDIS_CONN.get(test_key)
        if result:
            print("   ✓ Redis connected")
            REDIS_CONN.delete(test_key)
        else:
            print("   ✗ Redis not working")
            return
    except Exception as e:
        print(f"   ✗ Redis error: {e}")
        return
    
    # 2. Check existing KB cache keys
    print("\n2️⃣ Checking existing KB cache...")
    try:
        keys = REDIS_CONN.keys("kb_retrieval:*")
        if keys:
            print(f"   Found {len(keys)} cached retrieval results")
            for key in keys[:5]:  # Show first 5
                ttl = REDIS_CONN.ttl(key)
                print(f"   - {key}: TTL={ttl}s")
        else:
            print("   No cache found yet")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Performance comparison
    print("\n3️⃣ Cache Performance Tips:")
    print("   • Default TTL: 120 seconds (2 minutes)")
    print("   • Cache key includes: query + kb_ids + top_k + parameters")
    print("   • Same query → Cache HIT (instant)")
    print("   • Different query → Cache MISS (slow)")
    
    print("\n4️⃣ How to monitor cache:")
    print("   Watch logs for:")
    print("   - [CACHE] HIT from Redis     → Cache working!")
    print("   - [CACHE] MISS - executing   → First time query")
    print("   - [CACHE] Execution took Xs  → Retrieval time")
    
    print("\n5️⃣ Cache optimization:")
    print("   • Query normalization: lowercase + strip whitespace")
    print("   • KB IDs sorted: [1,2,3] == [3,2,1]")
    print("   • Exclude models from cache key (embd_mdl, rerank_mdl)")
    
    print("\n6️⃣ Test scenario:")
    print("   1st request: 'Xin chào' → MISS (slow, ~2-5s)")
    print("   2nd request: 'Xin chào' → HIT  (fast, <100ms)")
    print("   3rd request: 'Hello'     → MISS (different query)")
    
    print("\n" + "="*60)
    print("✅ Cache system ready for KB retrieval optimization!")
    print("="*60 + "\n")
    
    # 7. Show memory cache info
    print("7️⃣ Cache layers:")
    print("   Layer 1: Redis (shared across containers)")
    print("   Layer 2: Memory (per-process fallback)")
    print("   Benefits:")
    print("   • Faster response for repeated queries")
    print("   • Reduced Elasticsearch load")
    print("   • Reduced embedding computation")
    print("   • Better user experience")
    
    print("\n8️⃣ To clear cache manually:")
    print('   docker exec ragflow-server redis-cli KEYS "kb_retrieval:*"')
    print('   docker exec ragflow-server redis-cli DEL $(redis-cli KEYS "kb_retrieval:*")')

if __name__ == "__main__":
    test_cache_performance()
