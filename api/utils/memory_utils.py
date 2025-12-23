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
        expire_hours: TTL in hours (default: 720 hours = 30 days)
        
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
   
    
    def truncate_memory(text, max_words=100):
        words = text.strip().split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])
        return text.strip()

    def _generate_memory():
        """Inner function that runs in background thread"""
        try:
            
            # Nếu đã có old_memory, chỉ cần 2 messages gần nhất
            messages_to_use = messages[-2:] if old_memory else messages
            
            # Call LLM to generate memory summary
            memory_text = short_memory(dialog.tenant_id, dialog.llm_id, messages_to_use, short_memory=old_memory)
            memory_text = truncate_memory(memory_text, max_words=200)
            
            if memory_text:
                result = save_memory_to_redis(conversation_id, memory_text)
                print(f"\n[MEMORY]:\n  {memory_text}")
                #if result:
                #    logging.info(f"[MEMORY] Memory saved successfully for conversation: {conversation_id}")
                #else:
                #    logging.error(f"[MEMORY] Failed to save memory for conversation: {conversation_id}")
            else:
                logging.warning(f"[MEMORY] No memory generated for conversation: {conversation_id}")
                
        except Exception as e:
            print(f"[MEMORY THREAD] ✗ EXCEPTION: {e}")
            logging.error(f"[MEMORY] Exception in memory generation for {conversation_id}: {e}")
            traceback.print_exc()
    
    try:
        thread = threading.Thread(
            target=_generate_memory, 
            daemon=True, 
            name=f"MemoryGen-{conversation_id}"
        )
        thread.start()
        logging.info(f"[MEMORY] Started background thread for conversation: {conversation_id}")
    except Exception as e:
        logging.error(f"[MEMORY] Failed to start memory generation thread: {e}")
        traceback.print_exc()


from typing import List
from common.constants import MemoryType

def format_ret_data_from_memory(memory):
    return {
        "id": memory.id,
        "name": memory.name,
        "avatar": memory.avatar,
        "tenant_id": memory.tenant_id,
        "owner_name": memory.owner_name if hasattr(memory, "owner_name") else None,
        "memory_type": get_memory_type_human(memory.memory_type),
        "storage_type": memory.storage_type,
        "embd_id": memory.embd_id,
        "llm_id": memory.llm_id,
        "permissions": memory.permissions,
        "description": memory.description,
        "memory_size": memory.memory_size,
        "forgetting_policy": memory.forgetting_policy,
        "temperature": memory.temperature,
        "system_prompt": memory.system_prompt,
        "user_prompt": memory.user_prompt,
        "create_time": memory.create_time,
        "create_date": memory.create_date,
        "update_time": memory.update_time,
        "update_date": memory.update_date
    }


def get_memory_type_human(memory_type: int) -> List[str]:
    return [mem_type.name.lower() for mem_type in MemoryType if memory_type & mem_type.value]


def calculate_memory_type(memory_type_name_list: List[str]) -> int:
    memory_type = 0
    type_value_map = {mem_type.name.lower(): mem_type.value for mem_type in MemoryType}
    for mem_type in memory_type_name_list:
        if mem_type in type_value_map:
            memory_type |= type_value_map[mem_type]
    return memory_type
