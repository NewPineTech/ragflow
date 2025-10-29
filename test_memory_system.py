#!/usr/bin/env python3
"""
Test script for Memory System
Kiểm tra tính năng lưu/load memory từ Redis
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.utils.redis_conn import REDIS_CONN


def test_memory_key():
    """Test memory key generation"""
    from api.apps.api_app import get_memory_key
    
    conv_id = "test-conv-123"
    key = get_memory_key(conv_id)
    expected = f"conv_memory:{conv_id}"
    
    assert key == expected, f"Expected {expected}, got {key}"
    print(f"✓ Memory key generation: {key}")


def test_save_and_load_memory():
    """Test save and load memory from Redis"""
    from api.apps.api_app import save_memory_to_redis, get_memory_from_redis
    
    conv_id = "test-conv-456"
    test_memory = "User đã hỏi về sản phẩm iPhone 15. Họ quan tâm về camera và pin."
    
    # Save memory
    success = save_memory_to_redis(conv_id, test_memory, expire_hours=1)
    assert success, "Failed to save memory to Redis"
    print(f"✓ Memory saved to Redis")
    
    # Load memory
    loaded_memory = get_memory_from_redis(conv_id)
    assert loaded_memory == test_memory, f"Expected '{test_memory}', got '{loaded_memory}'"
    print(f"✓ Memory loaded from Redis: {loaded_memory[:50]}...")
    
    # Clean up
    REDIS_CONN.REDIS.delete(f"conv_memory:{conv_id}")
    print(f"✓ Test memory cleaned up")


def test_redis_connection():
    """Test Redis connection"""
    try:
        result = REDIS_CONN.health()
        print(f"✓ Redis connection healthy")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


def test_memory_expiration():
    """Test memory expiration"""
    from api.apps.api_app import save_memory_to_redis, get_memory_from_redis
    import time
    
    conv_id = "test-conv-expire"
    test_memory = "This should expire"
    
    # Save with 2 seconds expiration
    save_memory_to_redis(conv_id, test_memory, expire_hours=2/3600)  # 2 seconds
    print(f"✓ Memory saved with 2s expiration")
    
    # Should exist
    memory = get_memory_from_redis(conv_id)
    assert memory == test_memory, "Memory should exist"
    print(f"✓ Memory exists immediately after save")
    
    # Wait 3 seconds
    print("  Waiting 3 seconds for expiration...")
    time.sleep(3)
    
    # Should be expired
    memory = get_memory_from_redis(conv_id)
    assert memory is None, "Memory should be expired"
    print(f"✓ Memory expired after 3 seconds")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Memory System Tests")
    print("=" * 60)
    print()
    
    # Test 1: Redis connection
    print("Test 1: Redis Connection")
    if not test_redis_connection():
        print("\n✗ Tests failed: Redis not available")
        return 1
    print()
    
    # Test 2: Memory key generation
    print("Test 2: Memory Key Generation")
    try:
        test_memory_key()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return 1
    print()
    
    # Test 3: Save and load
    print("Test 3: Save and Load Memory")
    try:
        test_save_and_load_memory()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return 1
    print()
    
    # Test 4: Memory expiration
    print("Test 4: Memory Expiration")
    try:
        test_memory_expiration()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return 1
    print()
    
    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
