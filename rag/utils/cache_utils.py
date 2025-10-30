import json, time, hashlib
from functools import wraps
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


# ---- FIX: JSON encoder hỗ trợ numpy, ORM object, etc. ----
class SafeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        try:
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
        except Exception:
            pass
        return str(obj)

# ---- Cập nhật decorator ----
def cache_retrieval(ttl: int = 60):
    """Cache decorator cho retrieval với Redis hoặc memory fallback."""
    _cache_memory = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            query = args[0] if len(args) > 0 else kwargs.get("query", "")
            kb_ids = kwargs.get("kb_ids", [])
            top_k = kwargs.get("top", 5)
            cache_key = _make_cache_key(func.__name__, query, kb_ids, top_k, **kwargs)

            # Redis
            if REDIS_CONN:
                data = REDIS_CONN.get(cache_key)
                if data:
                    try:
                        result = json.loads(data)
                        result["_cached"] = True
                        return result
                    except Exception:
                        pass

            # Memory fallback
            if cache_key in _cache_memory:
                result, ts = _cache_memory[cache_key]
                if time.time() - ts < ttl:
                    result["_cached"] = True
                    return result

            # Thực thi thật
            result = func(*args, **kwargs)

            try:
                cache_data = json.dumps(result, ensure_ascii=False, cls=SafeJSONEncoder)
                if REDIS_CONN:
                    REDIS_CONN.setex(cache_key, ttl, cache_data)
                else:
                    _cache_memory[cache_key] = (result, time.time())
            except Exception as e:
                print(f"[CACHE] Serialization failed: {e}")

            return result
        return wrapper
    return decorator
