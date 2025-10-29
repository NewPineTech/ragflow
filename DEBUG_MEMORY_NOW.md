# Debug Memory System - NOW

## ✅ Đã thêm Debug Prints

Code đã được update với **extensive print statements** để debug tại sao `generate_and_save_memory_async` không chạy.

## 🔍 Cách kiểm tra

### 1. Restart Server
```bash
# Stop và start lại server để load code mới
docker-compose restart ragflow-server

# Hoặc
docker restart ragflow-server
```

### 2. Monitor Logs Real-time
```bash
# Xem logs real-time
docker logs -f ragflow-server 2>&1 | grep -E "\[MEMORY|STREAM DEBUG|NON-STREAM DEBUG\]"
```

### 3. Send Test Request

**Streaming Request:**
```bash
curl -X POST http://localhost/api/completion \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "debug-test-001",
    "messages": [{"role": "user", "content": "Xin chào"}],
    "stream": true
  }'
```

**Non-streaming Request:**
```bash
curl -X POST http://localhost/api/completion \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "debug-test-002",
    "messages": [{"role": "user", "content": "Xin chào"}],
    "stream": false
  }'
```

## 📊 Expected Debug Output

### If Working Correctly:
```
[STREAM DEBUG] About to call generate_and_save_memory_async
[STREAM DEBUG] conversation_id: debug-test-001
[STREAM DEBUG] dia type: <class 'api.db.db_models.Dialog'>
[STREAM DEBUG] conv.message length: 2
============================================================
[MEMORY DEBUG] Function called for: debug-test-001
[MEMORY DEBUG] Dialog object: <Dialog object>
[MEMORY DEBUG] Messages count: 2
============================================================
[STREAM DEBUG] Returned from generate_and_save_memory_async

[MEMORY DEBUG] Creating thread...
[MEMORY DEBUG] Starting thread...
[MEMORY DEBUG] ✓ Thread started successfully!

[MEMORY THREAD] Inside thread for: debug-test-001
[MEMORY THREAD] About to call short_memory()...
[MEMORY THREAD] short_memory() returned: User đã chào hỏi...
[MEMORY THREAD] Calling save_memory_to_redis()...
[MEMORY THREAD] Save result: True
[MEMORY THREAD] ✓ SUCCESS - Memory saved!
```

### If NOT Working:
Look for where it stops:

**Scenario 1: Function không được gọi**
```
# Không thấy gì cả
# → Kiểm tra xem code có được gọi không
```

**Scenario 2: Thread không start**
```
[MEMORY DEBUG] Function called for: debug-test-001
[MEMORY DEBUG] Creating thread...
[MEMORY DEBUG] ✗ Failed to start thread: ...
# → Threading có vấn đề
```

**Scenario 3: Thread start nhưng không chạy**
```
[MEMORY DEBUG] ✓ Thread started successfully!
# Không thấy "[MEMORY THREAD] Inside thread"
# → Daemon thread bị kill ngay hoặc function không run
```

**Scenario 4: short_memory() fail**
```
[MEMORY THREAD] Inside thread for: debug-test-001
[MEMORY THREAD] About to call short_memory()...
[MEMORY THREAD] ✗ EXCEPTION: ...
# → LLM API có vấn đề
```

## 🐛 Common Issues

### Issue 1: Code không chạy (Không thấy prints)
**Problem:** File không được reload  
**Solution:**
```bash
# Force restart với clean
docker-compose down
docker-compose up -d

# Or rebuild
docker-compose build ragflow-server
docker-compose up -d ragflow-server
```

### Issue 2: Thread bị kill ngay
**Problem:** Daemon threads bị terminate khi main process done  
**Solution:** Thread đã là daemon=True, nhưng nếu vẫn bị kill:
```python
# Temporary test: Run synchronously
# Comment out threading, call directly:
_generate_memory()  # Instead of thread.start()
```

### Issue 3: short_memory() timeout hoặc error
**Problem:** LLM API slow hoặc không available  
**Solution:**
```python
# Add timeout in short_memory call
# Or check LLM API health first
```

### Issue 4: Generator stream issue
**Problem:** Stream generator có thể kết thúc trước khi thread start  
**Solution:** Đã được xử lý - memory generation sau khi stream xong

## 📝 Debug Checklist

- [ ] Restart server sau khi update code
- [ ] Send test request
- [ ] Check logs có `[MEMORY DEBUG]` không
- [ ] Check logs có `[MEMORY THREAD]` không
- [ ] Check Redis có key mới không: `redis-cli KEYS "conv_memory:*"`
- [ ] Check thread có start không
- [ ] Check LLM API có response không

## 🎯 Next Steps Based on Output

### If you see "[MEMORY DEBUG] Function called"
✓ Function được gọi  
→ Check thread có start không

### If you see "[MEMORY DEBUG] ✓ Thread started"
✓ Thread started  
→ Check thread có chạy không (tìm "[MEMORY THREAD]")

### If you see "[MEMORY THREAD] Inside thread"
✓ Thread đang chạy  
→ Check short_memory() có return không

### If you see "[MEMORY THREAD] ✓ SUCCESS"
✓✓✓ Everything works!  
→ Verify Redis: `redis-cli GET conv_memory:debug-test-001`

## 💡 Quick Fixes to Try

### Fix 1: Disable daemon mode (temporary test)
```python
thread = threading.Thread(target=_generate_memory, daemon=False, ...)
```

### Fix 2: Add sleep to keep process alive
```python
# After thread.start()
import time
time.sleep(0.1)  # Give thread time to start
```

### Fix 3: Run synchronously (temporary test)
```python
# Replace threading with direct call
_generate_memory()  # Run synchronously for testing
```

### Fix 4: Check if it's classify=GREET issue
```python
# Memory might only generate for KB chat, not solo chat
# Check if your test goes through chat() or chat_solo()
print(f"[DEBUG] Classify result: {classify}")
```

## 📞 If Still Not Working

1. **Capture full logs:**
```bash
docker logs ragflow-server > /tmp/ragflow-debug.log 2>&1
```

2. **Check prints:**
```bash
grep -E "MEMORY|STREAM|DEBUG" /tmp/ragflow-debug.log
```

3. **Check Python stdout:**
```bash
# Check if prints go to stdout or stderr
docker logs ragflow-server 2>&1 | grep "MEMORY DEBUG"
```

4. **Verify code is loaded:**
```bash
# Check file timestamp in container
docker exec ragflow-server ls -la /app/api/apps/api_app.py
```

## ✅ Success Indicators

- ✓ See `[MEMORY DEBUG] Function called`
- ✓ See `[MEMORY DEBUG] ✓ Thread started`  
- ✓ See `[MEMORY THREAD] Inside thread`
- ✓ See `[MEMORY THREAD] ✓ SUCCESS`
- ✓ Redis has key: `conv_memory:debug-test-001`

If you see all of these → **Memory system is working!** 🎉
