# rag/utils/cache_utils.py
import hashlib
import json
import time
from functools import wraps, lru_cache
from rag.utils.redis_conn import REDIS_CONN


def _make_cache_key(func_name, query, kb_ids, top_k, **kwargs):
    base = {
        "func": func_name,
        "query": query,
        "kb_ids": kb_ids,
        "top_k": top_k,
        "extra": {k: kwargs.get(k) for k in sorted(kwargs.keys()) if k not in ["embd_mdl", "rerank_mdl"]}
    }
    return hashlib.md5(json.dumps(base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cache_retrieval(ttl: int = 60):
    """
    Decorator to cache retrieval results for a short time.
    ttl: seconds to keep cache alive (default 60s)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            query = args[0] if len(args) > 0 else kwargs.get("query", "")
            kb_ids = kwargs.get("kb_ids", [])
            top_k = kwargs.get("top", 5)
            cache_key = _make_cache_key(func.__name__, query, kb_ids, top_k, **kwargs)

            # Try Redis first
            if REDIS_CONN:
                data = REDIS_CONN.get(cache_key)
                if data:
                    try:
                        result = json.loads(data)
                        result["_cached"] = True
                        return result
                    except Exception:
                        pass

            # Try LRU cache fallback (in-memory)
            if cache_key in _cache_memory:
                result, ts = _cache_memory[cache_key]
                if time.time() - ts < ttl:
                    result["_cached"] = True
                    return result

            # Actual retrieval
            result = func(*args, **kwargs)
            try:
                if isinstance(result, dict):
                    cache_data = json.dumps(result, ensure_ascii=False, default=str)
                    if REDIS_CONN:
                        REDIS_CONN.setex(cache_key, ttl, cache_data)
                    else:
                        _cache_memory[cache_key] = (result, time.time())
            except Exception as e:
                print(f"[CACHE] Serialization failed: {e}")

            return result
        return wrapper
    _cache_memory = {}
    return decorator
