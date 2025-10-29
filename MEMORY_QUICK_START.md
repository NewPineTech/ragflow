# Memory System - Quick Start Guide

## Giới thiệu
Hệ thống Memory tự động lưu trữ bối cảnh hội thoại (conversation context) vào Redis và sử dụng lại cho các câu hỏi tiếp theo, giúp chatbot có context awareness tốt hơn.

## Cách hoạt động

### 1. First Request (Không có memory)
```
User: "Tôi muốn mua iPhone 15"
Bot: [Retrieve từ KB] "iPhone 15 có 3 phiên bản: Pro, Pro Max, và Standard..."
→ Sau khi response, system tự động generate memory async:
   "User quan tâm mua iPhone 15"
```

### 2. Second Request (Có memory từ Redis)
```
User: "Pin của nó thế nào?"
Bot: [Load memory từ Redis] → Biết "nó" là iPhone 15
Bot: "Pin của iPhone 15 Standard là 3200mAh..."
```

## Setup

### 1. Kiểm tra Redis
```bash
# Trong Docker container
redis-cli ping
# Expected: PONG
```

### 2. Run Test
```bash
python test_memory_system.py
```

Expected output:
```
============================================================
Memory System Tests
============================================================

Test 1: Redis Connection
✓ Redis connection healthy

Test 2: Memory Key Generation
✓ Memory key generation: conv_memory:test-conv-123

Test 3: Save and Load Memory
✓ Memory saved to Redis
✓ Memory loaded from Redis: User đã hỏi về sản phẩm iPhone 15. Họ quan ...
✓ Test memory cleaned up

Test 4: Memory Expiration
✓ Memory saved with 2s expiration
✓ Memory exists immediately after save
  Waiting 3 seconds for expiration...
✓ Memory expired after 3 seconds

============================================================
✓ All tests passed!
============================================================
```

## API Usage

### Request với Memory
```json
POST /api/completion
Headers:
  Authorization: Bearer <token>
  
Body:
{
  "conversation_id": "abc-123",
  "messages": [
    {"role": "user", "content": "Pin của nó thế nào?"}
  ]
}
```

### Response
```json
{
  "code": 0,
  "data": {
    "answer": "Pin của iPhone 15 Standard là 3200mAh, hỗ trợ sạc nhanh 20W...",
    "reference": {...}
  }
}
```

## Monitoring

### Check Redis Keys
```bash
# List all conversation memories
redis-cli KEYS "conv_memory:*"

# Get specific memory
redis-cli GET "conv_memory:abc-123"

# Check TTL (time to live)
redis-cli TTL "conv_memory:abc-123"
# Output: 86400 (24 hours in seconds)
```

### Check Logs
```bash
# Memory được load
grep "Using memory from Redis" /path/to/logs

# Memory được generate
grep "Memory generated and saved" /path/to/logs
```

## Configuration

### Thay đổi Expiration Time
Edit `api/apps/api_app.py`:
```python
def save_memory_to_redis(conversation_id, memory, expire_hours=24):
    # Thay 24 thành số giờ bạn muốn
```

### Disable Memory (temporary)
Comment trong hàm `completion()`:
```python
# memory = get_memory_from_redis(conversation_id)
# if memory:
#     req["short_memory"] = memory
```

## Troubleshooting

### Problem: Memory không được load
**Symptoms**: Bot không nhớ context từ câu hỏi trước

**Solutions**:
1. Check Redis running: `redis-cli ping`
2. Check logs có "Using memory from Redis" không
3. Check conversation_id có giống nhau không
4. Check TTL: `redis-cli TTL conv_memory:{conversation_id}`

### Problem: Memory generation chậm
**Symptoms**: Response trả về chậm

**Note**: Memory được generate **async**, không ảnh hưởng response time. Nếu chậm, có thể do:
1. LLM API chậm (không liên quan memory system)
2. Network latency
3. KB retrieval chậm

### Problem: Redis memory đầy
**Solutions**:
1. Giảm expire time: `expire_hours=12` thay vì 24
2. Clear old memories: `redis-cli DEL conv_memory:*`
3. Tăng Redis memory limit trong config

## Best Practices

### 1. Conversation ID Management
- Mỗi conversation phải có ID unique
- Giữ nguyên conversation_id cho cùng một cuộc hội thoại
- Reset conversation_id khi bắt đầu chủ đề mới

### 2. Memory Size
- Memory được LLM tự động tóm tắt, thường < 500 chars
- Nếu quá dài, cân nhắc thêm length limit trong `short_memory()`

### 3. Privacy
- Memory chứa conversation history
- Set TTL phù hợp với privacy policy
- Clear memory khi user request

### 4. Performance
- Memory generation chạy background, không block
- Redis cache rất nhanh (< 1ms)
- Chỉ generate memory sau khi response xong

## Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ Request (conversation_id)
       ▼
┌─────────────────────────────┐
│   /api/completion           │
│  1. Load memory from Redis  │
│  2. Pass to chat()          │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   chat() in dialog_service  │
│  Add memory to system prompt│
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   LLM Processing            │
│  (KB retrieval + Memory)    │
└──────┬──────────────────────┘
       │
       ▼ Response to Client
       │
       └──→ ┌──────────────────────────┐
            │  Background Thread       │
            │  1. Generate new memory  │
            │  2. Save to Redis        │
            └──────────────────────────┘
```

## Files Modified

1. **api/apps/api_app.py**
   - Added memory helper functions
   - Modified `completion()` endpoint
   - Added async memory generation

2. **api/db/services/dialog_service.py**
   - Modified `chat()` to accept `short_memory`
   - Added memory to system prompt

3. **MEMORY_IMPLEMENTATION.md**
   - Detailed technical documentation

4. **test_memory_system.py**
   - Test suite for memory system

## Support

Nếu có vấn đề, check:
1. Logs: `/path/to/logs` hoặc `docker logs`
2. Redis: `redis-cli monitor` để xem real-time operations
3. Documentation: `MEMORY_IMPLEMENTATION.md`
