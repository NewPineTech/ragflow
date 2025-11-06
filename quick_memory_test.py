#!/usr/bin/env python3
"""
Quick test to verify memory system is working
Run this inside Docker container or with proper environment
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all imports work"""
    print("Testing imports...")
    try:
        from rag.utils.redis_conn import REDIS_CONN
        print("✓ Redis import OK")
        
        from rag.prompts.generator import short_memory
        print("✓ short_memory import OK")
        
        from api.apps.api_app import get_memory_key, save_memory_to_redis, get_memory_from_redis
        print("✓ Memory helper functions import OK")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_redis():
    """Test Redis connection"""
    print("\nTesting Redis connection...")
    try:
        from rag.utils.redis_conn import REDIS_CONN
        REDIS_CONN.health()
        print("✓ Redis connection OK")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False

def test_memory_functions():
    """Test memory helper functions"""
    print("\nTesting memory functions...")
    try:
        from api.apps.api_app import get_memory_key, save_memory_to_redis, get_memory_from_redis
        
        # Test key generation
        key = get_memory_key("test-123")
        assert key == "conv_memory:test-123", f"Key mismatch: {key}"
        print("✓ Memory key generation OK")
        
        # Test save
        success = save_memory_to_redis("test-quick-123", "Test memory", expire_hours=1)
        assert success, "Save failed"
        print("✓ Memory save OK")
        
        # Test load
        memory = get_memory_from_redis("test-quick-123")
        assert memory == "Test memory", f"Memory mismatch: {memory}"
        print("✓ Memory load OK")
        
        # Cleanup
        from rag.utils.redis_conn import REDIS_CONN
        REDIS_CONN.REDIS.delete("conv_memory:test-quick-123")
        print("✓ Cleanup OK")
        
        return True
    except Exception as e:
        print(f"✗ Memory functions failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("Quick Memory System Test")
    print("="*60)
    
    results = []
    
    # Test imports
    results.append(test_imports())
    if not results[-1]:
        print("\n⚠️  Import failed. Check Python environment.")
        sys.exit(1)
    
    # Test Redis
    results.append(test_redis())
    if not results[-1]:
        print("\n⚠️  Redis not available. Check Redis connection.")
        sys.exit(1)
    
    # Test memory functions
    results.append(test_memory_functions())
    
    # Summary
    print("\n" + "="*60)
    if all(results):
        print("✓ All quick tests passed!")
        print("\nMemory system is ready to use.")
        print("\nNext steps:")
        print("1. Check logs: grep '[MEMORY]' /path/to/logs")
        print("2. Test with API: POST /api/completion")
        print("3. Monitor Redis: redis-cli KEYS 'conv_memory:*'")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        print("\nSee MEMORY_DEBUG_GUIDE.md for troubleshooting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
