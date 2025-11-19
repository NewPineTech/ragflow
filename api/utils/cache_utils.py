#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
Caching utilities for database queries.
Handles Redis-based caching for frequently accessed data.
"""

import logging
import json
from typing import Optional, Dict, Any
from rag.utils.redis_conn import REDIS_CONN

# Cache TTL in seconds
DIALOG_CACHE_TTL = 300  # 5 minutes
CONVERSATION_CACHE_TTL = 180  # 3 minutes


def get_dialog_cache_key(dialog_id: str, tenant_id: str) -> str:
    """Generate Redis key for dialog cache."""
    return f"dialog_cache:{tenant_id}:{dialog_id}"


def get_conversation_cache_key(session_id: str, dialog_id: str) -> str:
    """Generate Redis key for conversation cache."""
    return f"conv_cache:{dialog_id}:{session_id}"


def get_cached_dialog(dialog_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached dialog from Redis.
    
    Args:
        dialog_id: Dialog ID
        tenant_id: Tenant ID
        
    Returns:
        Dialog data if found, None otherwise
    """
    try:
        key = get_dialog_cache_key(dialog_id, tenant_id)
        cached = REDIS_CONN.get(key)
        if cached:
            data = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached)
            logging.debug(f"[CACHE] Dialog HIT: {dialog_id}")
            return data
        logging.debug(f"[CACHE] Dialog MISS: {dialog_id}")
        return None
    except Exception as e:
        logging.error(f"[CACHE] Failed to get dialog cache: {e}")
        return None


def cache_dialog(dialog_id: str, tenant_id: str, dialog_data: Dict[str, Any]) -> bool:
    """
    Cache dialog data to Redis.
    
    Args:
        dialog_id: Dialog ID
        tenant_id: Tenant ID
        dialog_data: Dialog data to cache
        
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        key = get_dialog_cache_key(dialog_id, tenant_id)
        result = REDIS_CONN.set(key, json.dumps(dialog_data), DIALOG_CACHE_TTL)
        if result:
            logging.debug(f"[CACHE] Dialog cached: {dialog_id}")
        return result
    except Exception as e:
        logging.error(f"[CACHE] Failed to cache dialog: {e}")
        return False


def get_cached_conversation(session_id: str, dialog_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached conversation from Redis.
    
    Args:
        session_id: Session/Conversation ID
        dialog_id: Dialog ID
        
    Returns:
        Conversation data if found, None otherwise
    """
    try:
        key = get_conversation_cache_key(session_id, dialog_id)
        cached = REDIS_CONN.get(key)
        if cached:
            data = json.loads(cached.decode('utf-8') if isinstance(cached, bytes) else cached)
            logging.debug(f"[CACHE] Conversation HIT: {session_id}")
            return data
        logging.debug(f"[CACHE] Conversation MISS: {session_id}")
        return None
    except Exception as e:
        logging.error(f"[CACHE] Failed to get conversation cache: {e}")
        return None


def cache_conversation(session_id: str, dialog_id: str, conv_data: Dict[str, Any]) -> bool:
    """
    Cache conversation data to Redis.
    
    Args:
        session_id: Session/Conversation ID
        dialog_id: Dialog ID
        conv_data: Conversation data to cache
        
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        key = get_conversation_cache_key(session_id, dialog_id)
        result = REDIS_CONN.set(key, json.dumps(conv_data), CONVERSATION_CACHE_TTL)
        if result:
            logging.debug(f"[CACHE] Conversation cached: {session_id}")
        return result
    except Exception as e:
        logging.error(f"[CACHE] Failed to cache conversation: {e}")
        return False


def invalidate_dialog_cache(dialog_id: str, tenant_id: str) -> bool:
    """
    Invalidate dialog cache.
    
    Args:
        dialog_id: Dialog ID
        tenant_id: Tenant ID
        
    Returns:
        True if invalidated successfully, False otherwise
    """
    try:
        key = get_dialog_cache_key(dialog_id, tenant_id)
        REDIS_CONN.delete(key)
        logging.debug(f"[CACHE] Dialog cache invalidated: {dialog_id}")
        return True
    except Exception as e:
        logging.error(f"[CACHE] Failed to invalidate dialog cache: {e}")
        return False


def invalidate_conversation_cache(session_id: str, dialog_id: str) -> bool:
    """
    Invalidate conversation cache.
    
    Args:
        session_id: Session/Conversation ID
        dialog_id: Dialog ID
        
    Returns:
        True if invalidated successfully, False otherwise
    """
    try:
        key = get_conversation_cache_key(session_id, dialog_id)
        REDIS_CONN.delete(key)
        logging.debug(f"[CACHE] Conversation cache invalidated: {session_id}")
        return True
    except Exception as e:
        logging.error(f"[CACHE] Failed to invalidate conversation cache: {e}")
        return False
