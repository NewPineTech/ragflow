# Memory System Implementation

## Tổng quan
Hệ thống lưu trữ và quản lý memory (bộ nhớ ngắn hạn) cho các cuộc hội thoại (conversation) trong RAGFlow chatbot, sử dụng Redis làm storage backend.

## Kiến trúc

### 1. Storage Layer (Redis)
- **Key format**: `conv_memory:{conversation_id}`
- **Expiration**: 24 giờ (có thể tùy chỉnh)
- **Value**: Text string chứa memory được tạo bởi LLM

### 2. Helper Functions (api/apps/api_app.py)

#### `get_memory_key(conversation_id)`
Tạo Redis key cho conversation memory.

#### `get_memory_from_redis(conversation_id)`
Lấy memory từ Redis cho một conversation.
- Return: `str` hoặc `None` nếu không tìm thấy

#### `save_memory_to_redis(conversation_id, memory, expire_hours=24)`
Lưu memory vào Redis với thời gian expire.
- Default: 24 giờ

#### `generate_and_save_memory_async(conversation_id, dialog, messages)`
Tạo memory bằng `short_memory()` và lưu vào Redis **asynchronously** (background thread).
- Không block response trả về client
- Chạy sau khi đã stream/return response

## Flow hoạt động

### Request Flow
```
1. Client gửi request → /completion endpoint
2. Lấy conversation_id từ request
3. Load memory từ Redis (nếu có)
4. Truyền memory vào chat() qua kwargs["short_memory"]
5. chat() thêm memory vào system prompt
6. LLM xử lý với context đầy đủ (knowledge + memory)
7. Stream/return response về client
```

### Memory Generation Flow (Async)
```
1. Response đã được gửi về client
2. Background thread được trigger
3. Gọi short_memory(tenant_id, llm_id, messages)
4. LLM tóm tắt conversation thành memory
5. Lưu memory vào Redis với key conv_memory:{conversation_id}
6. Memory sẽ được dùng cho request tiếp theo
```

## Chi tiết Implementation

### 1. API Layer (api/apps/api_app.py)

#### Streaming Mode
```python
conversation_id = req["conversation_id"]
memory = get_memory_from_redis(conversation_id)
if memory:
    req["short_memory"] = memory

def stream():
    for ans in chat(dia, msg, True, **req):
        yield ans
    # Sau khi stream xong, generate memory async
    generate_and_save_memory_async(conversation_id, dia, conv.message)
```

#### Non-streaming Mode
```python
conversation_id = req["conversation_id"]
memory = get_memory_from_redis(conversation_id)
if memory:
    req["short_memory"] = memory

for ans in chat(dia, msg, **req):
    answer = ans
    break

# Generate memory async sau khi return
generate_and_save_memory_async(conversation_id, dia, conv.message)
return get_json_result(data=answer)
```

### 2. Dialog Service Layer (api/db/services/dialog_service.py)

```python
# Trong hàm chat()
memory_text = kwargs.pop("short_memory", None)

# Format system prompt
system_content = f"{datetime_info}\n\n{system_content}"
if memory_text:
    system_content = f"{system_content}\n\n## Historical Memory:\n{memory_text}"
```

### 3. Memory Generation (rag/prompts/prompts.py)

Function `short_memory()` đã tồn tại, sử dụng LLM để:
- Phân tích conversation history
- Tóm tắt thành memory ngắn gọn
- Giữ lại context quan trọng

## Lợi ích

### 1. Performance
- **Non-blocking**: Memory generation chạy background, không làm chậm response
- **Efficient**: Chỉ generate memory sau response, không trước
- **Cached**: Memory được cache trong Redis, tái sử dụng cho các request sau

### 2. Memory Management
- **Auto-expire**: Memory tự động expire sau 24h
- **Per-conversation**: Mỗi conversation có memory riêng
- **Scalable**: Redis có thể scale dễ dàng

### 3. Context Awareness
- **Historical context**: LLM có thêm context từ các cuộc hội thoại trước
- **Better responses**: Câu trả lời nhất quán hơn với lịch sử chat
- **Personalization**: Có thể cá nhân hóa response dựa trên memory

## Configuration

### Redis TTL
Thay đổi thời gian expire của memory:
```python
save_memory_to_redis(conversation_id, memory, expire_hours=48)  # 48 giờ thay vì 24
```

### Disable Memory
Nếu không muốn dùng memory cho một request:
```python
# Trong completion endpoint, comment dòng này:
# req["short_memory"] = memory
```

## Testing

### Test Memory Storage
```python
# Lưu memory
save_memory_to_redis("test_conv_123", "User đã hỏi về sản phẩm X")

# Load memory
memory = get_memory_from_redis("test_conv_123")
print(memory)  # "User đã hỏi về sản phẩm X"
```

### Monitor Redis
```bash
# Xem tất cả conversation memories
redis-cli KEYS "conv_memory:*"

# Xem một memory cụ thể
redis-cli GET "conv_memory:abc-123"

# Xem TTL
redis-cli TTL "conv_memory:abc-123"
```

## Troubleshooting

### Memory không được load
1. Check Redis connection: `REDIS_CONN.health()`
2. Check key tồn tại: `redis-cli EXISTS conv_memory:{conversation_id}`
3. Check logs: Search "Using memory from Redis"

### Memory không được generate
1. Check logs: Search "Memory generated and saved"
2. Check thread có crash không
3. Check LLM có available không

### Performance issues
1. Reduce memory expiration time
2. Check Redis memory usage
3. Consider adding memory size limits

## Future Improvements

1. **Memory compression**: Nén memory để tiết kiệm Redis storage
2. **Memory summarization**: Tóm tắt lại memory khi quá dài
3. **Multi-level memory**: Short-term và long-term memory
4. **Memory search**: Semantic search trong memory history
5. **Memory analytics**: Phân tích hiệu quả của memory system
