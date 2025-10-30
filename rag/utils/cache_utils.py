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
            query = args[0] if len(args) > 0 else kwargs.get("query", "")
            kb_ids = kwargs.get("kb_ids", [])
            top_k = kwargs.get("top", 5)
            cache_key = _make_cache_key(func.__name__, query, kb_ids, top_k, **kwargs)

            # 1️⃣ Kiểm tra Redis
            if REDIS_CONN:
                data = REDIS_CONN.get(cache_key)
                if data:
                    try:
                        result = json.loads(data)
                        result["_cached"] = True
                        return result
                    except Exception:
                        pass

            # 2️⃣ Kiểm tra memory cache
            if cache_key in _cache_memory:
                result, ts = _cache_memory[cache_key]
                if time.time() - ts < ttl:
                    result["_cached"] = True
                    return result

            # 3️⃣ Chạy thật
            result = func(*args, **kwargs)

            # 4️⃣ Serialize an toàn
            try:
                safe_data = safe_serialize(result)
                cache_data = json.dumps(safe_data, ensure_ascii=False)
                if REDIS_CONN:
                    REDIS_CONN.set(cache_key, cache_data, ex=ttl)
                else:
                    _cache_memory[cache_key] = (result, time.time())
            except Exception as e:
                print(f"[CACHE][ERROR] Serialization failed for {func.__name__}: {e}")

            return result

        return wrapper
    return decorator
