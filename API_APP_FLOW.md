# API App Flow Documentation

**File:** `api/apps/api_app.py`  
**Purpose:** External API endpoints for RAGFlow with token-based authentication

---

## 📑 Table of Contents
1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Main Chat Flow](#main-chat-flow)
4. [Memory System Integration](#memory-system-integration)
5. [Authentication](#authentication)
6. [Response Formats](#response-formats)

---

## 🎯 Overview

This file provides **16 REST API endpoints** for external applications to interact with RAGFlow:
- Token management (create, list, delete)
- Conversation APIs (chat, history)
- Document management (upload, parse, delete)
- Knowledge base retrieval
- Statistics and monitoring

**Key Features:**
- ✅ Token-based authentication
- ✅ Streaming SSE support
- ✅ Memory system integration
- ✅ Agent/Canvas mode support
- ✅ Citation and reference tracking
- ✅ Async background tasks

---

## 🔌 API Endpoints

### 1. Token Management

#### `POST /new_token` (Line 55)
**Purpose:** Create new API token for dialog or canvas

**Request:**
```json
{
  "dialog_id": "dialog_uuid",
  // OR
  "canvas_id": "canvas_uuid"
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "tenant_id": "tenant_uuid",
    "token": "generated_token",
    "dialog_id": "dialog_uuid",
    "source": "agent",  // or null for dialog
    "create_time": 1699999999,
    "create_date": "2025-11-14"
  }
}
```

**Authentication:** `@login_required` (session-based)

---

#### `GET /token_list` (Line 85)
**Purpose:** List all tokens for a dialog/canvas

**Query Parameters:**
- `dialog_id` or `canvas_id`

**Response:**
```json
{
  "code": 0,
  "data": [
    {
      "token": "token_string",
      "create_time": 1699999999,
      ...
    }
  ]
}
```

**Authentication:** `@login_required`

---

#### `POST /rm` (Line 100)
**Purpose:** Remove/delete API token

**Request:**
```json
{
  "tokens": ["token1", "token2"]
}
```

**Response:**
```json
{
  "code": 0,
  "data": true
}
```

**Authentication:** `@login_required`

---

### 2. Conversation APIs

#### `GET /new_conversation` (Line 145)
**Purpose:** Create new conversation session

**Query Parameters:**
- `user_id` (optional)

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "code": 0,
  "data": {
    "id": "conversation_uuid",
    "dialog_id": "dialog_uuid",
    "name": "New conversation",
    "message": [],
    "reference": [],
    "source": "dialog"
  }
}
```

**Flow:**
1. Validate API token
2. Get dialog/canvas from token
3. Create conversation record
4. Return conversation_id

---

#### `POST /completion` ⭐ (Line 185)
**Purpose:** Main chat API with streaming support

**Request:**
```json
{
  "conversation_id": "conversation_uuid",
  "messages": [
    {"role": "user", "content": "Question here", "id": "msg_uuid"}
  ],
  "quote": true,
  "stream": true
}
```

**Headers:**
- `Authorization: Bearer <token>`

**Response (Non-streaming):**
```json
{
  "code": 0,
  "data": {
    "id": "message_uuid",
    "answer": "Generated answer with citations [ID:0]",
    "reference": {
      "chunks": [
        {
          "doc_name": "document.pdf",
          "content": "Chunk text...",
          "content_with_weight": "Highlighted text",
          "doc_id": "doc_uuid",
          "similarity": 0.95,
          "img_id": "bucket-image_id",
          "positions": ["page_1"]
        }
      ],
      "doc_aggs": [
        {"doc_name": "document.pdf", "count": 3}
      ]
    }
  }
}
```

**Response (Streaming - SSE):**
```
data: {"code":0,"message":"","data":{"answer":"text chunk 1","reference":[]}}

data: {"code":0,"message":"","data":{"answer":"text chunk 2","reference":[...]}}

data: {"code":0,"message":"","data":true}
```

**Flow:** See [Main Chat Flow](#main-chat-flow)

---

#### `GET /conversation/<conversation_id>` (Line 360)
**Purpose:** Get conversation details and history

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "code": 0,
  "data": {
    "id": "conversation_uuid",
    "name": "Conversation name",
    "message": [
      {"role": "user", "content": "Question", "id": "msg1"},
      {"role": "assistant", "content": "Answer", "id": "msg2"}
    ],
    "reference": [
      {"chunks": [...], "doc_aggs": [...]}
    ]
  }
}
```

---

#### `GET /stats` (Line 114)
**Purpose:** Get conversation statistics

**Query Parameters:**
- `fromDate` (YYYY-MM-DD)
- `toDate` (YYYY-MM-DD)

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "code": 0,
  "data": {
    "pv": 150,           // Total messages
    "uv": 45,            // Active users
    "speed": 28.5,       // Avg tokens/sec
    "tokens": 125000,    // Total tokens used
    "round": 50,         // Total conversations
    "thumbUp": 0.85      // Satisfaction rate
  }
}
```

---

### 3. Document Management

#### `POST /document/upload` (Line 391)
**Purpose:** Upload files to knowledge base

**Request (multipart/form-data):**
```
file: <binary>
kb_id: "kb_uuid"
```

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "code": 0,
  "data": {
    "file_id": "file_uuid",
    "file_name": "document.pdf",
    "task_id": "task_uuid",
    "status": "queued"
  }
}
```

**Flow:**
1. Validate token and KB access
2. Check file type (pdf, docx, txt, etc.)
3. Upload to storage (MinIO/S3)
4. Create File + Task records
5. Queue for parsing

**Supported File Types:**
- PDF, DOCX, PPTX, XLSX
- TXT, MD, JSON, CSV
- Images: PNG, JPG, JPEG, GIF
- And more (see VALID_FILE_TYPES)

---

#### `POST /document/upload_and_parse` (Line 504)
**Purpose:** Upload and automatically parse documents

**Request (multipart/form-data):**
```
file: <binary>
kb_id: "kb_uuid"
parser_config: {"chunk_token_count": 128, "layout_recognize": true}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "doc_id": "doc_uuid",
    "task_id": "task_uuid"
  }
}
```

**Difference from `/upload`:**
- Automatically triggers parsing
- Can specify parser config
- Returns doc_id instead of file_id

---

#### `POST /document/infos` (Line 645)
**Purpose:** Get document metadata

**Request:**
```json
{
  "doc_ids": ["doc_uuid1", "doc_uuid2"]
}
```

**Response:**
```json
{
  "code": 0,
  "data": [
    {
      "id": "doc_uuid",
      "name": "document.pdf",
      "size": 1024000,
      "chunk_count": 156,
      "status": "completed",
      "parser_config": {...}
    }
  ]
}
```

---

#### `DELETE /document` (Line 659)
**Purpose:** Delete documents from knowledge base

**Request:**
```json
{
  "doc_ids": ["doc_uuid1", "doc_uuid2"]
}
```

**Response:**
```json
{
  "code": 0,
  "data": true
}
```

**Side Effects:**
- Deletes document records
- Deletes associated chunks
- Removes from vector DB (Elasticsearch)
- Deletes files from storage

---

### 4. Chunk/KB Management

#### `POST /list_chunks` (Line 527)
**Purpose:** List all chunks in documents

**Request:**
```json
{
  "doc_ids": ["doc_uuid"],
  "page": 1,
  "size": 30
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "total": 156,
    "chunks": [
      {
        "id": "chunk_uuid",
        "content": "Chunk text...",
        "doc_id": "doc_uuid",
        "positions": ["page_1"],
        "create_time": 1699999999
      }
    ]
  }
}
```

---

#### `GET /get_chunk/<chunk_id>` (Line 566)
**Purpose:** Get specific chunk details

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "code": 0,
  "data": {
    "id": "chunk_uuid",
    "content": "Full chunk text...",
    "content_with_weight": "Highlighted version",
    "doc_id": "doc_uuid",
    "img_id": "bucket-image_id",
    "positions": ["page_1", "page_2"]
  }
}
```

---

#### `POST /list_kb_docs` (Line 592)
**Purpose:** List all documents in knowledge base

**Request:**
```json
{
  "kb_id": "kb_uuid",
  "page": 1,
  "size": 30,
  "orderby": "create_time",
  "desc": true,
  "name": "search keyword"
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "total": 45,
    "docs": [
      {
        "id": "doc_uuid",
        "name": "document.pdf",
        "size": 1024000,
        "chunk_count": 156,
        "status": "completed",
        "create_time": 1699999999
      }
    ]
  }
}
```

---

### 5. Special APIs

#### `POST /completion_aibotk` (Line 723)
**Purpose:** Custom API for AIBOTK integration with image support

**Request:**
```json
{
  "Authorization": "token_string",
  "conversation_id": "conversation_uuid",
  "word": "Question here",
  "quote": true
}
```

**Response:**
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "type": 1,
      "content": "Text answer without citations"
    },
    {
      "type": 3,
      "url": "data:image/png;base64,iVBORw0KG..."
    }
  ]
}
```

**Special Features:**
- Removes citation markers (`##\d$$`) from answer
- Extracts first image from cited chunk
- Returns base64-encoded image
- Custom response format for AIBOTK client

**Data Types:**
- `type: 1` = Text content
- `type: 3` = Base64 image

---

#### `POST /retrieval` (Line 865)
**Purpose:** Direct knowledge base retrieval without chat

**Request:**
```json
{
  "kb_id": ["kb_uuid1", "kb_uuid2"],
  "question": "Search query",
  "doc_ids": ["doc_uuid"],
  "page": 1,
  "page_size": 30,
  "similarity_threshold": 0.2,
  "vector_similarity_weight": 0.3,
  "top_k": 1024,
  "rerank_id": "rerank_model_name",
  "keyword": true,
  "highlight": true
}
```

**Response:**
```json
{
  "code": 0,
  "data": {
    "total": 156,
    "chunks": [
      {
        "content": "Chunk text...",
        "content_with_weight": "Highlighted",
        "doc_id": "doc_uuid",
        "doc_name": "document.pdf",
        "similarity": 0.95,
        "positions": ["page_1"]
      }
    ],
    "total_time": 1.234
  }
}
```

**Parameters:**
- `kb_id`: List of KB IDs to search
- `doc_ids`: Filter by specific documents (optional)
- `similarity_threshold`: Min similarity (0.0-1.0)
- `vector_similarity_weight`: Vector vs keyword weight
- `top_k`: Max candidates before rerank
- `rerank_id`: Rerank model name (optional)
- `keyword`: Extract keywords from query (optional)
- `highlight`: Highlight query terms (optional)

**Use Cases:**
- Search KB without generating answer
- Get raw chunks for custom processing
- Test retrieval quality
- Build custom UIs

---

## 🔄 Main Chat Flow

### `/completion` Endpoint Flow:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Request Validation                                       │
├─────────────────────────────────────────────────────────────┤
│ • Validate Authorization header                             │
│ • Check API token in database                               │
│ • Get tenant_id from token                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Load Conversation                                        │
├─────────────────────────────────────────────────────────────┤
│ • Get conversation by conversation_id                       │
│ • Check if source is "agent" or "dialog"                    │
│ • Load dialog/canvas configuration                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Prepare Messages                                         │
├─────────────────────────────────────────────────────────────┤
│ • Filter out system messages                                │
│ • Skip leading assistant messages                           │
│ • Generate message_id if missing                            │
│ • Append to conversation.message                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │ Source? │
                    └────┬────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│ AGENT MODE       │           │ DIALOG MODE      │
│ (Canvas)         │           │ (Standard Chat)  │
└────────┬─────────┘           └────────┬─────────┘
         │                               │
         ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4a. Agent Flow                                              │
├─────────────────────────────────────────────────────────────┤
│ • Load Canvas DSL (Domain Specific Language)                │
│ • Initialize Canvas object                                  │
│ • canvas.add_user_input(message)                            │
│ • canvas.run(stream=True/False)                             │
│   ├─ Execute workflow nodes                                 │
│   ├─ Handle intermediate results                            │
│   └─ Generate final answer                                  │
│ • Update Canvas state                                       │
│ • Save DSL back to database                                 │
└─────────────────────────────────────────────────────────────┘
         │
         │                               ┌─────────────────────────────────────────────────────────────┐
         │                               │ 4b. Dialog Flow                                             │
         │                               ├─────────────────────────────────────────────────────────────┤
         │                               │ • Call chat(dia, msg, stream, **req)                        │
         │                               │   ↓                                                         │
         │                               │ dialog_service.chat():                                      │
         │                               │   1. Extract memory from kwargs                             │
         │                               │   2. Get datetime info                                      │
         │                               │   3. Check if KB retrieval needed                           │
         │                               │   4. If needed:                                             │
         │                               │      ├─ retriever.retrieval() [CACHED]                      │
         │                               │      ├─ Format knowledges                                   │
         │                               │      └─ Add to system prompt                                │
         │                               │   5. Prepare messages:                                      │
         │                               │      ├─ If memory exists: Only last user message            │
         │                               │      └─ Else: Full history                                  │
         │                               │   6. Generate answer with LLM                               │
         │                               │   7. Insert citations [ID:n]                                │
         │                               │   8. Return with references                                 │
         └───────────────────────────────┴─────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Response Handling                                        │
├─────────────────────────────────────────────────────────────┤
│ • If stream=true:                                           │
│   ├─ Create SSE generator                                   │
│   ├─ Yield chunks as they arrive                            │
│   ├─ Update conversation after completion                   │
│   └─ Return Response with SSE headers                       │
│                                                             │
│ • If stream=false:                                          │
│   ├─ Wait for full answer                                   │
│   ├─ Update conversation                                    │
│   └─ Return JSON response                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Post-Processing                                          │
├─────────────────────────────────────────────────────────────┤
│ • fillin_conv(ans):                                         │
│   ├─ Add answer to conversation.message                     │
│   ├─ Add references to conversation.reference               │
│   └─ Set message_id                                         │
│                                                             │
│ • rename_field(ans):                                        │
│   └─ Convert 'docnm_kwd' → 'doc_name' for compatibility    │
│                                                             │
│ • Save conversation to database                             │
│                                                             │
│ • 🎯 generate_and_save_memory_async():                      │
│   ├─ Create background thread                               │
│   ├─ Call short_memory(tenant_id, llm_id, messages)        │
│   ├─ Generate conversation summary via LLM                  │
│   ├─ Truncate to 100 words max                              │
│   └─ Save to Redis (key: conv_memory:{conversation_id})    │
│       └─ TTL: 24 hours (86400 seconds)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Memory System Integration

### Overview:
The memory system creates **conversation summaries** using LLM and stores them in Redis for future context.

### Flow:

```python
# Line 312-313 (Stream mode)
generate_and_save_memory_async(conversation_id, dia, conv.message)

# Line 350-351 (Non-stream mode)
generate_and_save_memory_async(conversation_id, dia, conv.message)
```

### Process:

```
┌─────────────────────────────────────────┐
│ 1. After Chat Response Sent             │
│    (Non-blocking)                       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 2. Create Background Thread             │
│    • daemon=True                        │
│    • name="MemoryGen-{conv_id}"         │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 3. Call short_memory()                  │
│    • LLM summarizes conversation        │
│    • Input: Full message history        │
│    • Output: Concise summary (~100 words)│
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 4. Save to Redis                        │
│    • Key: conv_memory:{conversation_id} │
│    • Value: Memory text                 │
│    • TTL: 24 hours (86400 seconds)      │
└─────────────────────────────────────────┘
```

### Memory Usage in Chat:

**Location:** `dialog_service.chat()` (Line 494)

```python
memory_text = kwargs.pop("short_memory", None)

if memory_text:
    system_content += f"\n\n## Historical Memory:\n{memory_text}\n"
    
    # Optimization: Only send last message when memory exists
    messages_to_send = msg[-1:]  # Only last user message
else:
    # Send full history
    messages_to_send = msg
```

### Benefits:
1. **Context Preservation:** Maintains conversation context across sessions
2. **Token Optimization:** Reduces tokens by summarizing history
3. **Non-Blocking:** Doesn't slow down response time
4. **Automatic Expiry:** Redis TTL prevents stale data

---

## 🔒 Authentication

### Token-Based Authentication:

All API endpoints (except token management) require:

```
Authorization: Bearer <token>
```

### Validation Flow:

```python
# Line 189-192
token = request.headers.get('Authorization').split()[1]
objs = APIToken.query(token=token)
if not objs:
    return get_json_result(
        data=False, 
        message='Authentication error: API key is invalid!"', 
        code=RetCode.AUTHENTICATION_ERROR
    )
```

### Token Structure:

```python
APIToken {
    tenant_id: str       # Organization ID
    token: str          # Generated token (UUID-based)
    dialog_id: str      # Associated dialog/canvas ID
    source: str         # "agent" or null
    create_time: int    # Unix timestamp
    create_date: str    # YYYY-MM-DD
}
```

### Security Considerations:
- ✅ Tokens are tenant-specific
- ✅ Tokens are dialog-specific (can't access other dialogs)
- ✅ No expiration (manual deletion only)
- ⚠️  Store tokens securely (treat like passwords)
- ⚠️  Use HTTPS in production

---

## 📤 Response Formats

### Standard JSON Response:

```json
{
  "code": 0,           // 0 = success, >0 = error
  "message": "",       // Error message if any
  "data": {...}        // Response data
}
```

### Error Codes:

```python
RetCode.SUCCESS = 0
RetCode.AUTHENTICATION_ERROR = 100
RetCode.ARGUMENT_ERROR = 101
RetCode.DATA_ERROR = 102
RetCode.OPERATION_ERROR = 103
RetCode.SERVER_ERROR = 500
```

### Error Response Example:

```json
{
  "code": 100,
  "message": "Authentication error: API key is invalid!",
  "data": false
}
```

### Streaming (SSE) Format:

**Content-Type:** `text/event-stream; charset=utf-8`

**Headers:**
```
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**Stream Format:**
```
data: <JSON payload>\n\n
```

**Example:**
```
data: {"code":0,"message":"","data":{"answer":"Hello","reference":[]}}

data: {"code":0,"message":"","data":{"answer":" world","reference":[]}}

data: {"code":0,"message":"","data":true}

```

**Final Message:** `{"code":0,"data":true}` indicates stream completion

---

## 📊 Common Parameters

### Pagination:
```json
{
  "page": 1,
  "size": 30,
  "orderby": "create_time",
  "desc": true
}
```

### Retrieval Parameters:
```json
{
  "similarity_threshold": 0.2,      // Min similarity (0.0-1.0)
  "vector_similarity_weight": 0.3,  // Vector vs keyword weight
  "top_k": 1024,                    // Max candidates
  "rerank_id": "model_name"         // Optional reranker
}
```

### Chat Parameters:
```json
{
  "stream": true,          // Enable SSE streaming
  "quote": true,           // Show citations
  "temperature": 0.7,      // LLM creativity (0.0-1.0)
  "top_p": 0.95,          // Nucleus sampling
  "max_tokens": 2048      // Max response length
}
```

---

## 🎯 Use Cases

### 1. Simple Chatbot Integration:
```bash
# Create conversation
curl -X GET "http://api/new_conversation" \
  -H "Authorization: Bearer <token>"

# Send message
curl -X POST "http://api/completion" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_id",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### 2. Streaming Chat:
```javascript
const eventSource = new EventSource('/api/completion', {
  headers: {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    conversation_id: 'conv_id',
    messages: [{role: 'user', content: 'Question'}],
    stream: true
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.data === true) {
    eventSource.close();
  } else {
    console.log(data.data.answer);
  }
};
```

### 3. Document Upload + Search:
```bash
# Upload document
curl -X POST "http://api/document/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "kb_id=kb_uuid"

# Search KB
curl -X POST "http://api/retrieval" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": ["kb_uuid"],
    "question": "Search query",
    "top_k": 10
  }'
```

### 4. Multi-Session Chat with Memory:
```bash
# Session 1
curl -X POST "http://api/completion" \
  -H "Authorization: Bearer <token>" \
  -d '{"conversation_id": "conv1", "messages": [...]}'
# → Memory saved to Redis after response

# Session 2 (later)
curl -X POST "http://api/completion" \
  -H "Authorization: Bearer <token>" \
  -d '{"conversation_id": "conv1", "messages": [...]}'
# → Memory loaded from Redis, used as context
```

---

## 🔧 Configuration

### Environment Variables:
- `REDIS_HOST`: Redis server for memory storage
- `ELASTICSEARCH_HOST`: Vector DB for retrieval
- `STORAGE_IMPL`: MinIO/S3 for file storage

### Dialog Configuration:
Each dialog has configuration for:
- LLM model and parameters
- Knowledge base IDs
- Retrieval settings (top_k, similarity)
- Prompt templates
- Quote/citation settings

### Canvas Configuration:
Agent-based workflows use DSL (JSON):
```json
{
  "nodes": [...],
  "edges": [...],
  "variables": {...}
}
```

---

## 📝 Notes

### Performance Considerations:
1. **Caching:** KB retrieval is cached (120s TTL)
2. **Memory:** Async generation doesn't block responses
3. **Streaming:** Reduces perceived latency
4. **Pagination:** Limit result sizes

### Error Handling:
- All endpoints have try-catch blocks
- Returns consistent error format
- Logs to application logger
- Client-friendly error messages

### Future Enhancements:
- Token expiration support
- Rate limiting per token
- Webhook notifications
- Batch operations
- Multi-language support

---

**Last Updated:** November 14, 2025  
**File Version:** Based on latest commit  
**Maintainer:** RAGFlow Team
