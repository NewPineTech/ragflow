# Knowledges Flow trong RAGFlow

## 📌 `knowledges` là gì?

`knowledges` là một **list các đoạn text (chunks)** được retrieve từ Knowledge Base (KB), dùng để cung cấp context cho LLM khi trả lời câu hỏi.

## 🔄 Flow hoàn chỉnh trong `chat()` function:

### 1️⃣ **Khởi tạo** (Line 525)
```python
knowledges = []
```
- Bắt đầu với list rỗng

### 2️⃣ **Retrieval từ KB** (Lines 527-580)

**Có 2 cách lấy knowledges:**

#### **A. Deep Reasoning Mode** (Lines 530-552)
```python
if prompt_config.get("reasoning", False):
    reasoner = DeepResearcher(...)
    for think in reasoner.thinking(kbinfos, " ".join(questions)):
        if isinstance(think, str):
            thought = think
            knowledges = [t for t in think.split("\n") if t]
```
- Dùng AI để suy luận sâu
- Tạo nhiều queries khác nhau
- Tổng hợp kết quả thành knowledge chunks

#### **B. Standard Retrieval Mode** (Lines 554-580)
```python
else:
    if embd_mdl:
        kbinfos = retriever.retrieval(
            " ".join(questions),
            embd_mdl,
            tenant_ids,
            dialog.kb_ids,
            ...
        )
    knowledges = kb_prompt(kbinfos, max_tokens)
```
- **Bước 1:** Vector search trong Elasticsearch
  - Encode question thành vector
  - Tìm chunks tương tự
  - Rerank nếu có rerank model
  
- **Bước 2:** `kb_prompt()` format chunks
  - Lấy chunks từ `kbinfos["chunks"]`
  - Format thành text dễ đọc
  - Limit theo `max_tokens`

**Kết quả:** `knowledges` là list string, mỗi string là 1 chunk:
```python
knowledges = [
    "Chunk 1: Phật giáo là gì...",
    "Chunk 2: Bát quan trai...",
    "Chunk 3: Tu tập..."
]
```

### 3️⃣ **Check empty** (Lines 585-588)
```python
if not knowledges and prompt_config.get("empty_response"):
    empty_res = prompt_config["empty_response"]
    yield {"answer": empty_res, ...}
    return
```
- Nếu không tìm thấy knowledge → Trả về empty response
- VD: "Xin lỗi, tôi không tìm thấy thông tin..."

### 4️⃣ **Thêm vào System Prompt** (Line 590)
```python
kwargs["knowledge"] = "\n------\n" + "\n\n------\n\n".join(knowledges)
```

**Format:**
```
------
Chunk 1: Phật giáo là gì...

------

Chunk 2: Bát quan trai...

------

Chunk 3: Tu tập...
```

Sau đó format vào system prompt:
```python
system_content = prompt_config["system"].format(**kwargs)
```

**System prompt sẽ có dạng:**
```
Bạn là trợ lý AI...

## Knowledge Base:
------
Chunk 1: Phật giáo là gì...

------

Chunk 2: Bát quan trai...
```

### 5️⃣ **Dùng để generate citation** (Lines 614-615, 647-660)
```python
if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
    prompt4citation = citation_prompt()
```

**Citation prompt yêu cầu LLM:**
- Trích dẫn nguồn bằng `[ID:0]`, `[ID:1]`
- Map ID với chunk index

**Sau khi LLM trả lời:**
```python
if knowledges and prompt_config.get("quote"):
    idx = set([])
    # Insert citations vào answer
    answer, idx = retriever.insert_citations(
        answer,
        [ck["content_ltks"] for ck in kbinfos["chunks"]],
        [ck["vector"] for ck in kbinfos["chunks"]],
        embd_mdl,
        ...
    )
```

**Kết quả:**
```
Answer text với citations [ID:0] và [ID:2]
```

## 📊 Ví dụ cụ thể:

### Input:
```
User: "Bát quan trai là gì?"
```

### Retrieval:
```python
kbinfos = {
    "chunks": [
        {
            "content_ltks": "bát quan trai là giới luật...",
            "content_with_weight": "Bát quan trai là 8 giới luật tu tập...",
            "similarity": 0.95,
            ...
        },
        {
            "content_ltks": "tu tập phật pháp...",
            "content_with_weight": "Tu tập phật pháp cần có...",
            "similarity": 0.85,
            ...
        }
    ]
}

knowledges = kb_prompt(kbinfos, max_tokens=8192)
# Result:
knowledges = [
    "Bát quan trai là 8 giới luật tu tập...",
    "Tu tập phật pháp cần có..."
]
```

### System Prompt:
```
Hôm nay là Thứ Tư, ngày 30, tháng 10, năm 2025, lúc 14:30:00.

Bạn là trợ lý AI của Thầy Thích Nhất Hạnh...

## Knowledge Base:
------
Bát quan trai là 8 giới luật tu tập...

------

Tu tập phật pháp cần có...

## Historical Memory:
User đã hỏi về phật pháp trước đó...
```

### LLM Response:
```
Bát quan trai là 8 giới luật tu tập trong Phật giáo [ID:0].
Khi tu tập, cần có lòng tin và tinh tấn [ID:1].
```

### Final Answer:
```
{
  "answer": "Bát quan trai là 8 giới luật tu tập trong Phật giáo [ID:0]...",
  "reference": {
    "chunks": [
      {"chunk_id": "...", "content": "Bát quan trai là 8...", "doc_name": "Phật Pháp.pdf"},
      {"chunk_id": "...", "content": "Tu tập phật pháp...", "doc_name": "Tu Tập.pdf"}
    ],
    "doc_aggs": [
      {"doc_name": "Phật Pháp.pdf", "count": 1},
      {"doc_name": "Tu Tập.pdf", "count": 1}
    ]
  }
}
```

## 🎯 Tại sao cần `knowledges`?

### ✅ **1. Cung cấp Context cho LLM:**
- LLM không biết nội dung trong KB
- `knowledges` = "cheat sheet" cho LLM
- Giúp trả lời chính xác dựa trên dữ liệu thật

### ✅ **2. Giảm Hallucination:**
- Không có knowledge → LLM tự bịa
- Có knowledge → LLM dựa trên facts

### ✅ **3. Citation/Trích dẫn:**
- User biết info từ đâu
- Có thể verify nguồn
- Tăng độ tin cậy

### ✅ **4. Token Optimization:**
- Chỉ gửi relevant chunks
- Không gửi toàn bộ KB
- Fit trong context window

## 🔧 Tuning Parameters:

### Số lượng chunks:
```python
dialog.top_n = 6  # Lấy top 6 chunks
dialog.top_k = 1024  # Search trong 1024 docs
```

### Similarity threshold:
```python
dialog.similarity_threshold = 0.2  # Min similarity
dialog.vector_similarity_weight = 0.3  # Vector vs Text weight
```

### Max tokens:
```python
knowledges = kb_prompt(kbinfos, max_tokens=8192)
```
- Auto truncate để fit context window

## 🐛 Debug:

### Xem knowledges được retrieve:
```python
logging.debug("{}->{}".format(" ".join(questions), "\n->".join(knowledges)))
```

### Check empty knowledges:
```python
if not knowledges:
    print("No knowledge retrieved!")
```

### Check cache hit:
```python
if kbinfos.get("_cached"):
    print("Knowledge from cache!")
```

## 📈 Performance:

### Without Cache:
```
Retrieval: 1500-3000ms
├─ Vector search: ~1000ms
├─ Reranking: ~500ms
└─ Format chunks: ~50ms
```

### With Cache:
```
Retrieval: 5-10ms (450x faster!)
└─ Redis lookup: ~5ms
```

## 🎉 Summary:

`knowledges` = **Context từ Knowledge Base** được:
1. ✅ Retrieve từ vector search
2. ✅ Rerank theo relevance
3. ✅ Format thành text chunks
4. ✅ Thêm vào system prompt
5. ✅ LLM dùng để generate answer
6. ✅ Insert citations vào answer
7. ✅ Return với references

**Vai trò:** Bridge giữa Knowledge Base và LLM để tạo RAG (Retrieval-Augmented Generation)

---
**File:** `api/db/services/dialog_service.py`  
**Function:** `chat()`  
**Lines:** 525-660
