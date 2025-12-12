import json, time, hashlib, re
from functools import wraps
from rag.utils.redis_conn import REDIS_CONN

# Vietnamese stopwords - các từ phổ biến không mang nghĩa quan trọng
VIETNAMESE_STOPWORDS = {
    "và", "của", "có", "được", "đã", "để", "trong", "với", "cho", "từ",
    "về", "theo", "như", "khi", "vì", "hay", "hoặc", "nhưng", "nếu", "mà",
    "thì", "là", "một", "các", "này", "đó", "những", "bởi", "nên", "sẽ",
    "đang", "rất", "còn", "vào", "ra", "không", "chỉ", "cũng", "đều", "sau",
    "trước", "giữa", "bên", "ngoài", "bao", "nhiều", "ít", "cả", "mọi",
    # English common stopwords
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "is", "are",
    "was", "were", "been", "be", "have", "has", "had", "do", "does", "did"
}

def _normalize_query(query: str) -> str:
    """
    Normalize query để tăng cache hit rate:
    1. Lowercase
    2. Remove extra whitespace
    3. Remove punctuation
    4. Remove stopwords
    5. Sort words (để "A và B" == "B và A")
    """
    if not isinstance(query, str):
        return query
    
    # 1. Lowercase
    normalized = query.lower().strip()
    
    # 2. Remove punctuation, giữ lại chữ cái, số, khoảng trắng
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # 3. Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # 4. Split thành words
    words = normalized.split()
    
    # 5. Remove stopwords
    words = [w for w in words if w not in VIETNAMESE_STOPWORDS]
    
    # 6. Sort words để "phật giáo là gì" == "gì là phật giáo"
    words.sort()
    
    # 7. Join lại
    return ' '.join(words)

def _make_cache_key(func_name, query, kb_ids, top_k, similarity_threshold=None, vector_similarity_weight=None, **kwargs):
    """Generate cache key from function parameters"""
    # Sort kb_ids để đảm bảo cache key giống nhau cho cùng KB set
    kb_ids_sorted = sorted(kb_ids) if isinstance(kb_ids, list) else kb_ids
    
    # Normalize query để tăng cache hit
    normalized_query = _normalize_query(query)
    
    # Extract critical similarity parameters that affect results
    # Try to get from explicit params first, then from kwargs, then use defaults
    if similarity_threshold is None:
        similarity_threshold = kwargs.get("similarity_threshold", 0.2)
    if vector_similarity_weight is None:
        vector_similarity_weight = kwargs.get("vector_similarity_weight", 0.3)
    
    base = {
        "func": func_name,
        "query": normalized_query,
        "kb_ids": kb_ids_sorted,
        "top_k": top_k,
        # Include similarity parameters in cache key
        "similarity_threshold": similarity_threshold,
        "vector_similarity_weight": vector_similarity_weight,
        # Chỉ cache những params quan trọng khác, skip models và các params đã extract
        "extra": {k: kwargs.get(k) for k in sorted(kwargs.keys()) 
                 if k not in ["embd_mdl", "rerank_mdl", "self", "similarity_threshold", "vector_similarity_weight"]}
    }
    cache_str = json.dumps(base, sort_keys=True, ensure_ascii=False)
    return f"kb_retrieval:{hashlib.md5(cache_str.encode()).hexdigest()}"


def cache_retrieval(ttl: int = 60):
    _cache_memory = {}

    def safe_serialize(obj, _path="root"):
        """
        Đệ quy chuyển mọi đối tượng thành JSON-safe.
        _path giúp ghi log vị trí trong cấu trúc khi lỗi.
        """
        import numpy as np

        try:
            # Các kiểu cơ bản
            if isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj

            # numpy
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()

            # dict
            if isinstance(obj, dict):
                return {safe_serialize(k, f"{_path}.{k}"): safe_serialize(v, f"{_path}.{k}") for k, v in obj.items()}

            # list / tuple / set
            if isinstance(obj, (list, tuple, set)):
                return [safe_serialize(i, f"{_path}[{idx}]") for idx, i in enumerate(obj)]

            # Có phương thức to_dict
            if hasattr(obj, "to_dict"):
                try:
                    return safe_serialize(obj.to_dict(), f"{_path}.to_dict()")
                except Exception as e:
                    print(f"[CACHE][WARN] to_dict() failed at {_path}: {e}")

            # Có __dict__
            if hasattr(obj, "__dict__"):
                try:
                    return safe_serialize(obj.__dict__, f"{_path}.__dict__")
                except Exception as e:
                    print(f"[CACHE][WARN] __dict__ failed at {_path}: {e}")

            # Cuối cùng fallback sang str
            print(f"[CACHE][WARN] Non-serializable object at {_path}: {type(obj).__name__} → using str()")
            return str(obj)

        except Exception as e:
            print(f"[CACHE][ERROR] Failed to serialize {_path} ({type(obj).__name__}): {e}")
            return str(obj)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip 'self' for instance methods
            start_idx = 0
            if len(args) > 0 and hasattr(args[0], '__dict__'):
                start_idx = 1  # Skip self
            
            # Parse args based on retrieval() signature:
            # def retrieval(self, question, embd_mdl, tenant_ids, kb_ids, page, page_size, similarity_threshold=0.2,
            #               vector_similarity_weight=0.3, top=1024, doc_ids=None, aggs=True, ...)
            query = args[start_idx] if len(args) > start_idx else kwargs.get("question", kwargs.get("query", ""))
            kb_ids = args[start_idx + 3] if len(args) > start_idx + 3 else kwargs.get("kb_ids", [])
            
            # Get similarity params from args if available (positional args at index 6 and 7 after self)
            similarity_threshold = args[start_idx + 6] if len(args) > start_idx + 6 else kwargs.get("similarity_threshold", 0.2)
            vector_similarity_weight = args[start_idx + 7] if len(args) > start_idx + 7 else kwargs.get("vector_similarity_weight", 0.3)
            top_k = args[start_idx + 8] if len(args) > start_idx + 8 else kwargs.get("top", 5)
            
            # Generate cache key
            cache_key = _make_cache_key(func.__name__, query, kb_ids, top_k, 
                                       similarity_threshold, vector_similarity_weight, **kwargs)
            
            print(f"[CACHE] Key: {cache_key}... for query: {str(query)[:50]}...")
            print(f"[CACHE] Params: similarity_threshold={similarity_threshold}, vector_weight={vector_similarity_weight}")

            # 1️⃣ Kiểm tra Redis cache
            if REDIS_CONN:
                try:
                    data = REDIS_CONN.get(cache_key)
                    if data:
                        result = json.loads(data)
                        result["_cached"] = True
                        print(f"[CACHE] ✓ HIT from Redis for {func.__name__}")
                        return result
                except Exception as e:
                    print(f"[CACHE] Redis read error: {e}")

            # 2️⃣ Kiểm tra memory cache (fallback)
            if cache_key in _cache_memory:
                result, ts = _cache_memory[cache_key]
                if time.time() - ts < ttl:
                    result["_cached"] = True
                    print(f"[CACHE] ✓ HIT from memory for {func.__name__}")
                    return result
                else:
                    # Expired, remove it
                    del _cache_memory[cache_key]

            # 3️⃣ Cache MISS - chạy function thật
            print(f"[CACHE] MISS - executing {func.__name__}")
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            #print(f"[CACHE] Execution took {elapsed:.2f}s")

            # 4️⃣ Lưu vào cache
            try:
                safe_data = safe_serialize(result)
                cache_data = json.dumps(safe_data, ensure_ascii=False)
                
                if REDIS_CONN:
                    # RedisDB.set(key, value, expire_seconds)
                    success = REDIS_CONN.set(cache_key, cache_data, ttl)
                    if success:
                        print(f"[CACHE] ✓ Saved to Redis (TTL: {ttl}s)")
                    else:
                        #print(f"[CACHE] ✗ Failed to save to Redis")
                        # Fallback to memory
                        _cache_memory[cache_key] = (result, time.time())
                        #print(f"[CACHE] ✓ Saved to memory cache")
                else:
                    _cache_memory[cache_key] = (result, time.time())
                    #print(f"[CACHE] ✓ Saved to memory cache (TTL: {ttl}s)")
                    
            except Exception as e:
                print(f"[CACHE][ERROR] Failed to cache result: {e}")
                import traceback
                traceback.print_exc()

            return result

        return wrapper
    return decorator
