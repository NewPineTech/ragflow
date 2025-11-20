#!/bin/bash
# Quick cache test script - runs inside Docker container

echo "=========================================="
echo "Testing Cache Implementation in Docker"
echo "=========================================="

# Check if running in Docker
if [ -f "/.dockerenv" ]; then
    echo "✓ Running inside Docker container"
else
    echo "⚠️  Not in Docker container"
    echo "Running: docker exec -it ragflow-server bash -c 'bash test_cache_quick.sh'"
    exit 0
fi

echo ""
echo "1️⃣  Testing Redis Connection..."
python3 << 'PYEOF'
try:
    from rag.utils.redis_conn import REDIS_CONN
    test_key = "quick_test_key"
    REDIS_CONN.set(test_key, "test_value", 10)
    result = REDIS_CONN.get(test_key)
    if result:
        print("   ✓ Redis connection OK")
        REDIS_CONN.delete(test_key)
    else:
        print("   ✗ Redis not working")
except Exception as e:
    print(f"   ✗ Redis error: {e}")
PYEOF

echo ""
echo "2️⃣  Testing Cache Utils Import..."
python3 << 'PYEOF'
try:
    from api.utils.cache_utils import (
        get_cached_dialog, cache_dialog,
        get_cached_conversation, cache_conversation
    )
    print("   ✓ Cache utils imported successfully")
except Exception as e:
    print(f"   ✗ Import error: {e}")
PYEOF

echo ""
echo "3️⃣  Testing Dialog Cache Functions..."
python3 << 'PYEOF'
try:
    from api.utils.cache_utils import get_cached_dialog, cache_dialog, invalidate_dialog_cache
    
    test_dialog_id = "test_dialog_quick"
    test_tenant_id = "test_tenant_quick"
    test_data = {"id": test_dialog_id, "name": "Test", "tenant_id": test_tenant_id}
    
    # Clear first
    invalidate_dialog_cache(test_dialog_id, test_tenant_id)
    
    # Should be None
    cached = get_cached_dialog(test_dialog_id, test_tenant_id)
    if cached is None:
        print("   ✓ Initial cache empty")
    else:
        print(f"   ✗ Unexpected data: {cached}")
        
    # Cache it
    cache_dialog(test_dialog_id, test_tenant_id, test_data)
    cached = get_cached_dialog(test_dialog_id, test_tenant_id)
    
    if cached and cached.get("id") == test_dialog_id:
        print("   ✓ Dialog cached and retrieved")
    else:
        print(f"   ✗ Cache failed: {cached}")
    
    # Clean up
    invalidate_dialog_cache(test_dialog_id, test_tenant_id)
    cached = get_cached_dialog(test_dialog_id, test_tenant_id)
    
    if cached is None:
        print("   ✓ Cache invalidation works")
    else:
        print(f"   ✗ Invalidation failed: {cached}")
        
except Exception as e:
    print(f"   ✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "4️⃣  Checking Redis Cache Keys..."
python3 << 'PYEOF'
try:
    from rag.utils.redis_conn import REDIS_CONN
    
    dialog_keys = REDIS_CONN.keys("dialog_cache:*")
    conv_keys = REDIS_CONN.keys("conv_cache:*")
    
    print(f"   • Dialog cache keys: {len(dialog_keys)}")
    print(f"   • Conversation cache keys: {len(conv_keys)}")
    
    if len(dialog_keys) > 0:
        print(f"   Sample: {dialog_keys[0]}")
except Exception as e:
    print(f"   ✗ Error: {e}")
PYEOF

echo ""
echo "=========================================="
echo "✅ Quick test completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Make some API requests to generate cache"
echo "2. Check logs: docker logs ragflow-server | grep CACHE"
echo "3. Monitor timing: docker logs ragflow-server | grep TIMING"
echo ""
