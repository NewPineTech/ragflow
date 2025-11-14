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
Memory management utilities for conversation history.
Handles Redis-based storage and LLM-powered memory generation.
"""

import logging
import threading
import traceback
from typing import Optional
from rag.utils.redis_conn import REDIS_CONN

from rag.prompts.generator import short_memory

def get_memory_key(conversation_id: str) -> str:
    """
    Generate Redis key for conversation memory.
    
    Args:
        conversation_id: Unique conversation identifier
        
    Returns:
        Redis key string in format 'conv_memory:{conversation_id}'
    """
    return f"conv_memory:{conversation_id}"


def get_memory_from_redis(conversation_id: str) -> Optional[str]:
    """
    Load memory from Redis for a conversation.
    
    Args:
        conversation_id: Unique conversation identifier
        
    Returns:
        Memory text if found, None otherwise
    """
    try:
        key = get_memory_key(conversation_id)
        memory = REDIS_CONN.get(key)
        if memory:
            return memory.decode('utf-8') if isinstance(memory, bytes) else memory
        return None
    except Exception as e:
        logging.error(f"[MEMORY] Failed to get memory from Redis: {e}")
        return None


def save_memory_to_redis(conversation_id: str, memory: str, expire_hours: int = 720) -> bool:
    """
    Save memory to Redis with expiration.
    
    Args:
        conversation_id: Unique conversation identifier
        memory: Memory text to save
        expire_hours: TTL in hours (default: 24)
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        key = get_memory_key(conversation_id)
        # RedisDB.set(k, v, exp) - exp is in seconds (positional argument)
        expire_seconds = expire_hours * 3600
        result = REDIS_CONN.set(key, memory, expire_seconds)
        if result:
            logging.info(f"[MEMORY] Successfully saved memory to Redis: {key}")
        return result
    except Exception as e:
        logging.error(f"[MEMORY] Failed to save memory to Redis: {e}")
        return False


def generate_and_save_memory_async(conversation_id: str, dialog, messages: list, old_memory=None) -> None:
    """
    Generate memory summary using LLM and save to Redis asynchronously.
    This runs in a background thread to avoid blocking the response.
    
    Args:
        conversation_id: Unique conversation identifier
        dialog: Dialog object containing tenant_id and llm_id
        messages: List of conversation messages
    """
    print(f"\n{'='*60}")
    print(f"[MEMORY DEBUG] Function called for: {conversation_id}")
    print(f"[MEMORY DEBUG] Dialog object: {dialog}")
    print(f"[MEMORY DEBUG] Messages count: {len(messages)}")
    print(f"{'='*60}\n")
    
    def truncate_memory(text, max_words=100):
        words = text.strip().split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])
        return text.strip()

    def _generate_memory():
        """Inner function that runs in background thread"""
        try:
            print(f"[MEMORY THREAD] Inside thread for: {conversation_id}")
            print(f"[MEMORY THREAD] About to call short_memory()...")
            
            # Nếu đã có old_memory, chỉ cần 2 messages gần nhất
            messages_to_use = messages[-2:] if old_memory else messages
            
            # Call LLM to generate memory summary
            memory_text = short_memory(dialog.tenant_id, dialog.llm_id, messages_to_use, short_memory=old_memory)
            memory_text = truncate_memory(memory_text, max_words=100)
            print(f"[MEMORY THREAD] short_memory() returned: {memory_text[:100] if memory_text else 'None'}...")
            
            if memory_text:
                print(f"[MEMORY THREAD] Calling save_memory_to_redis()...")
                result = save_memory_to_redis(conversation_id, memory_text)
                print(f"[MEMORY THREAD] Save result: {result}")
                if result:
                    print(f"[MEMORY THREAD] ✓ SUCCESS - Memory saved for: {conversation_id}")
                    logging.info(f"[MEMORY] Memory saved successfully for conversation: {conversation_id}")
                else:
                    print(f"[MEMORY THREAD] ✗ FAILED - Could not save to Redis")
                    logging.error(f"[MEMORY] Failed to save memory for conversation: {conversation_id}")
            else:
                print(f"[MEMORY THREAD] ✗ No memory generated from short_memory()")
                logging.warning(f"[MEMORY] No memory generated for conversation: {conversation_id}")
                
        except Exception as e:
            print(f"[MEMORY THREAD] ✗ EXCEPTION: {e}")
            logging.error(f"[MEMORY] Exception in memory generation for {conversation_id}: {e}")
            traceback.print_exc()
    
    try:
        print(f"[MEMORY DEBUG] Creating thread...")
        thread = threading.Thread(
            target=_generate_memory, 
            daemon=True, 
            name=f"MemoryGen-{conversation_id}"
        )
        print(f"[MEMORY DEBUG] Starting thread...")
        thread.start()
        print(f"[MEMORY DEBUG] ✓ Thread started successfully!")
        logging.info(f"[MEMORY] Started background thread for conversation: {conversation_id}")
    except Exception as e:
        print(f"[MEMORY DEBUG] ✗ Failed to start thread: {e}")
        logging.error(f"[MEMORY] Failed to start memory generation thread: {e}")
        traceback.print_exc()
