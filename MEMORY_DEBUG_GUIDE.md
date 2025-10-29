# Memory System Debugging Guide

## Quick Check Commands

### 1. Check Logs for Memory Operations

```bash
# In Docker container
docker exec -it ragflow-server bash

# Check if memory is being loaded
grep "\[MEMORY\]" /path/to/logs/ragflow.log | tail -20

# Or if using docker logs
docker logs ragflow-server 2>&1 | grep "\[MEMORY\]" | tail -20
```

Expected log patterns:
```
[MEMORY] Attempting to load memory for conversation: abc-123
[MEMORY] No existing memory found for conversation: abc-123
[MEMORY] Starting memory generation for conversation: abc-123
[MEMORY] Memory generated successfully: User đã hỏi về...
[MEMORY] ✓ Memory saved to Redis for conversation: abc-123
```

### 2. Check Redis Directly

```bash
# Connect to Redis
redis-cli

# List all conversation memories
KEYS conv_memory:*

# Get specific memory
GET conv_memory:abc-123

# Check TTL (time to live in seconds)
TTL conv_memory:abc-123

# Count total memories
EVAL "return #redis.call('keys', 'conv_memory:*')" 0
```

### 3. Check Redis from Python

```python
from rag.utils.redis_conn import REDIS_CONN

# Test connection
REDIS_CONN.health()

# List all memory keys
keys = REDIS_CONN.REDIS.keys("conv_memory:*")
print(f"Found {len(keys)} memories")

# Get a specific memory
memory = REDIS_CONN.get("conv_memory:abc-123")
print(memory)
```

## Common Issues & Solutions

### Issue 1: Memory không được generate

**Symptoms:**
- Không thấy log `[MEMORY] Starting memory generation`
- Không có memory trong Redis

**Debug Steps:**
1. Check xem `generate_and_save_memory_async()` có được gọi không:
   ```bash
   grep "Background thread started" logs
   ```

2. Check thread có crash không:
   ```bash
   grep "Exception in memory generation" logs
   ```

3. Add temporary print statement:
   ```python
   # In api/apps/api_app.py, trong hàm stream() hoặc non-stream
   print(f"DEBUG: About to call generate_and_save_memory_async({conversation_id})")
   generate_and_save_memory_async(conversation_id, dia, conv.message)
   print(f"DEBUG: Called generate_and_save_memory_async")
   ```

**Solutions:**
- Verify `short_memory()` function có hoạt động:
  ```python
  from rag.prompts.prompts import short_memory
  memory = short_memory(tenant_id, llm_id, messages)
  print(memory)
  ```

- Check LLM API có available không
- Check `dialog.tenant_id` và `dialog.llm_id` có valid không

### Issue 2: Memory được generate nhưng không save vào Redis

**Symptoms:**
- Thấy log `[MEMORY] Memory generated successfully`
- KHÔNG thấy log `[MEMORY] ✓ Memory saved to Redis`
- Redis không có key

**Debug Steps:**
```python
from api.apps.api_app import save_memory_to_redis

# Test save directly
result = save_memory_to_redis("test-123", "Test memory content")
print(f"Save result: {result}")

# Check if saved
from rag.utils.redis_conn import REDIS_CONN
memory = REDIS_CONN.get("conv_memory:test-123")
print(f"Retrieved: {memory}")
```

**Solutions:**
- Check Redis connection: `REDIS_CONN.health()`
- Check Redis memory limit: `redis-cli INFO memory`
- Check Redis logs for errors

### Issue 3: Memory không được load trong request tiếp theo

**Symptoms:**
- Memory có trong Redis (verify bằng `redis-cli GET`)
- Không thấy log `[MEMORY] ✓ Using memory from Redis`
- Bot không có context từ câu hỏi trước

**Debug Steps:**
1. Verify conversation_id giống nhau:
   ```python
   # Add log trong completion endpoint
   logging.info(f"Request conversation_id: {req['conversation_id']}")
   ```

2. Check memory có được pass vào `chat()`:
   ```python
   # Add log trước khi call chat()
   logging.info(f"req keys before chat: {req.keys()}")
   logging.info(f"short_memory in req: {'short_memory' in req}")
   ```

3. Check trong `dialog_service.py`:
   ```python
   # In chat() function
   memory_text = kwargs.pop("short_memory", None)
   logging.info(f"[DIALOG] Memory received: {memory_text[:100] if memory_text else 'None'}")
   ```

**Solutions:**
- Ensure conversation_id consistent across requests
- Check memory không bị expire (TTL > 0)
- Verify `req["short_memory"]` được set đúng

### Issue 4: Background thread không chạy

**Symptoms:**
- Không thấy bất kỳ log nào từ background thread
- Thread start log có nhưng không có logs tiếp theo

**Debug Steps:**
```python
import threading

# Check active threads
threads = threading.enumerate()
print(f"Active threads: {[t.name for t in threads]}")

# Check for MemoryGen threads
memory_threads = [t for t in threads if "MemoryGen" in t.name]
print(f"Memory generation threads: {memory_threads}")
```

**Solutions:**
- Check Python threading có hoạt động trong Docker không
- Try synchronous version để test:
  ```python
  # Temporary: Comment out threading, run directly
  # thread = threading.Thread(target=_generate_memory, daemon=True)
  # thread.start()
  _generate_memory()  # Run directly for testing
  ```

- Check daemon threads có bị kill không

### Issue 5: Memory quá dài hoặc quá ngắn

**Symptoms:**
- Memory text quá dài (> 1000 chars)
- Memory text quá ngắn (< 50 chars)
- Memory không có ích cho context

**Debug Steps:**
```python
# Check memory content
memory = REDIS_CONN.get("conv_memory:abc-123")
print(f"Memory length: {len(memory)}")
print(f"Memory content: {memory}")
```

**Solutions:**
- Tune `short_memory()` prompt trong `rag/prompts/prompts.py`
- Add length validation:
  ```python
  if len(memory) > 1000:
      memory = memory[:1000] + "..."
  if len(memory) < 20:
      logging.warning("Memory too short, skipping save")
      return
  ```

## Manual Testing Workflow

### Test 1: First Conversation (No Memory)
```bash
# Request 1
curl -X POST http://localhost/api/completion \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-conv-001",
    "messages": [{"role": "user", "content": "Tôi muốn mua iPhone 15"}]
  }'

# Wait 2-3 seconds for memory generation

# Check Redis
redis-cli GET conv_memory:test-conv-001
# Expected: Memory about iPhone 15 inquiry
```

### Test 2: Second Request (With Memory)
```bash
# Request 2 - Same conversation_id
curl -X POST http://localhost/api/completion \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-conv-001",
    "messages": [{"role": "user", "content": "Pin của nó thế nào?"}]
  }'

# Check logs
grep "test-conv-001" logs | grep MEMORY
# Expected: "Using memory from Redis"
```

## Performance Monitoring

### Monitor Memory Generation Time
```bash
# Check logs for timing
grep "Memory generated successfully" logs | tail -10

# Time from request to memory save
grep -A 5 "Starting memory generation" logs | tail -20
```

### Monitor Redis Memory Usage
```bash
redis-cli INFO memory | grep used_memory_human

# Check memory keys
redis-cli --scan --pattern "conv_memory:*" | wc -l
```

### Monitor Thread Count
```python
import threading
print(f"Active threads: {threading.active_count()}")
print(f"Thread names: {[t.name for t in threading.enumerate()]}")
```

## Cleanup Commands

### Clear All Memory
```bash
# Delete all conversation memories
redis-cli KEYS "conv_memory:*" | xargs redis-cli DEL

# Or using SCAN (safer for production)
redis-cli --scan --pattern "conv_memory:*" | xargs redis-cli DEL
```

### Clear Specific Conversation
```bash
redis-cli DEL conv_memory:abc-123
```

### Clear Expired Keys
```bash
# Redis automatically removes expired keys
# Check TTL
redis-cli TTL conv_memory:abc-123
# -1 = no expiration, -2 = doesn't exist, >0 = seconds remaining
```

## Enable Debug Mode

### Temporary Debug Logging
Add to `api/apps/api_app.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or just for memory
memory_logger = logging.getLogger('memory')
memory_logger.setLevel(logging.DEBUG)
```

### Add Debug Endpoint
```python
@manager.route('/debug/memory/<conversation_id>', methods=['GET'])
def debug_memory(conversation_id):
    """Debug endpoint to check memory status"""
    memory = get_memory_from_redis(conversation_id)
    key = get_memory_key(conversation_id)
    ttl = REDIS_CONN.REDIS.ttl(key)
    
    return get_json_result(data={
        "conversation_id": conversation_id,
        "memory_key": key,
        "memory_exists": memory is not None,
        "memory_length": len(memory) if memory else 0,
        "memory_content": memory[:200] if memory else None,
        "ttl_seconds": ttl
    })
```

## Contact & Support

If issues persist:
1. Check logs: `docker logs ragflow-server 2>&1 | grep "\[MEMORY\]"`
2. Check Redis: `redis-cli KEYS "conv_memory:*"`
3. Run test: `python test_memory_system.py`
4. Review implementation: `MEMORY_IMPLEMENTATION.md`
