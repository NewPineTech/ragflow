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
import time
import logging
from uuid import uuid4
from common.constants import StatusEnum
from api.db.db_models import Conversation, DB
from api.db.services.api_service import API4ConversationService
from api.db.services.common_service import CommonService
from api.db.services.dialog_service import DialogService, chat, chatv1
from common.misc_utils import get_uuid
from api.utils.memory_utils import generate_and_save_memory_async, get_memory_from_redis
from api.utils.cache_utils import (
    get_cached_dialog, cache_dialog,
    get_cached_conversation, cache_conversation,
    invalidate_conversation_cache
)
import json

from rag.prompts.generator import chunks_format


use_v1 = True
chat_func = chatv1 if use_v1 else chat
class ConversationService(CommonService):
    model = Conversation

    @classmethod
    @DB.connection_context()
    def get_list(cls, dialog_id, page_number, items_per_page, orderby, desc, id, name, user_id=None):
        sessions = cls.model.select().where(cls.model.dialog_id == dialog_id)
        if id:
            sessions = sessions.where(cls.model.id == id)
        if name:
            sessions = sessions.where(cls.model.name == name)
        if user_id:
            sessions = sessions.where(cls.model.user_id == user_id)
        if desc:
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())

        sessions = sessions.paginate(page_number, items_per_page)

        return list(sessions.dicts())

    @classmethod
    @DB.connection_context()
    def get_all_conversation_by_dialog_ids(cls, dialog_ids):
        sessions = cls.model.select().where(cls.model.dialog_id.in_(dialog_ids))
        sessions.order_by(cls.model.create_time.asc())
        offset, limit = 0, 100
        res = []
        while True:
            s_batch = sessions.offset(offset).limit(limit)
            _temp = list(s_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res

def structure_answer(conv, ans, message_id, session_id):
    reference = ans["reference"]
    if not isinstance(reference, dict):
        reference = {}
        ans["reference"] = {}

    chunk_list = chunks_format(reference)

    reference["chunks"] = chunk_list
    ans["id"] = message_id
    ans["session_id"] = session_id

    if not conv:
        return ans

    if not conv.message:
        conv.message = []
    if not conv.message or conv.message[-1].get("role", "") != "assistant":
        conv.message.append({"role": "assistant", "content": ans["answer"], "created_at": time.time(), "id": message_id})
    else:
        conv.message[-1] = {"role": "assistant", "content": ans["answer"], "created_at": time.time(), "id": message_id}
    if conv.reference:
        conv.reference[-1] = reference
    return ans


def completion(tenant_id, chat_id, question, name="New session", session_id=None, stream=True, **kwargs):
    start_time = time.time()
    print(f"[TIMING] completion() started at {start_time}")
    
    assert name, "`name` can not be empty."
    
    t1 = time.time()
    # Try to get from cache first
    cached_dialog = get_cached_dialog(chat_id, tenant_id)
    if cached_dialog:
        print(f"[CACHE] Dialog HIT: {chat_id}")
        # Convert dict back to query result format
        from api.db.db_models import Dialog
        dia_obj = Dialog(**cached_dialog)
        dia = [dia_obj]
    else:
        print(f"[CACHE] Dialog MISS: {chat_id}")
        dia = DialogService.query(id=chat_id, tenant_id=tenant_id, status=StatusEnum.VALID.value)
        if dia:
            # Cache the dialog for future requests
            cache_dialog(chat_id, tenant_id, dia[0].__dict__['__data__'])
    print(f"[TIMING] DialogService.query took {time.time() - t1:.3f}s")
    
    assert dia, "You do not own the chat."

    if not session_id:
        session_id = get_uuid()
        conv = {
            "id": session_id,
            "dialog_id": chat_id,
            "name": name,
            "message": [{"role": "assistant", "content": dia[0].prompt_config.get("prologue"), "created_at": time.time()}],
            "user_id": kwargs.get("user_id", "")
        }
        ConversationService.save(**conv)
        if stream:
            yield "data:" + json.dumps({"code": 0, "message": "",
                                        "data": {
                                            "answer": conv["message"][0]["content"],
                                            "reference": {},
                                            "audio_binary": None,
                                            "id": None,
                                            "session_id": session_id
                                        }},
                                    ensure_ascii=False) + "\n\n"
            yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"
            return

    t2 = time.time()
    # Try to get from cache first
    cached_conv = get_cached_conversation(session_id, chat_id)
    if cached_conv:
        print(f"[CACHE] Conversation HIT: {session_id}")
        # Convert dict back to query result format
        conv_obj = Conversation(**cached_conv)
        conv = [conv_obj]
    else:
        print(f"[CACHE] Conversation MISS: {session_id}")
        conv = ConversationService.query(id=session_id, dialog_id=chat_id)
        if conv:
            # Cache the conversation for future requests
            cache_conversation(session_id, chat_id, conv[0].__dict__['__data__'])
    print(f"[TIMING] ConversationService.query took {time.time() - t2:.3f}s")
    
    if not conv:
        raise LookupError("Session does not exist")

    conv = conv[0]
    msg = []
    question = {
        "content": question,
        "role": "user",
        "id": str(uuid4())
    }
    conv.message.append(question)
    
    t3 = time.time()
    for m in conv.message:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant" and not msg:
            continue
        msg.append(m)
    print(f"[TIMING] Message processing took {time.time() - t3:.3f}s")
    
    message_id = msg[-1].get("id")
    
    t4 = time.time()
    e, dia = DialogService.get_by_id(conv.dialog_id)
    print(f"[TIMING] DialogService.get_by_id took {time.time() - t4:.3f}s")
    print(f"[TIMING] Total before memory load: {time.time() - start_time:.3f}s")

    # Load memory from Redis
    logging.info(f"[MEMORY] Loading memory for session: {session_id}")
    print(f"[MEMORY] Loading memory for session: {session_id}")
    memory = get_memory_from_redis(session_id)
    if memory:
        kwargs["short_memory"] = memory
        logging.info(f"[MEMORY] Using memory for session: {session_id}")
        print(f"[MEMORY] Memory loaded: {memory[:100]}...")
    else:
        logging.info(f"[MEMORY] No memory found for session: {session_id}")
        print(f"[MEMORY] No existing memory")

    kb_ids = kwargs.get("kb_ids",[])
    dia.kb_ids = list(set(dia.kb_ids + kb_ids))
    if not conv.reference:
        conv.reference = []
    conv.message.append({"role": "assistant", "content": "", "id": message_id})
    conv.reference.append({"chunks": [], "doc_aggs": []})

    if stream:
        try:
            for ans in chat_func(dia, msg, True, **kwargs):
                ans = structure_answer(conv, ans, message_id, session_id)
                yield "data:" + json.dumps({"code": 0, "data": ans}, ensure_ascii=False) + "\n\n"
            ConversationService.update_by_id(conv.id, conv.to_dict())
            
            # Invalidate cache after update
            invalidate_conversation_cache(session_id, chat_id)
            
            # Generate memory after stream completes
            print(f"[STREAM] Generating memory for session: {session_id}")
            generate_and_save_memory_async(session_id, dia, conv.message, old_memory=memory)
            print(f"[STREAM] Memory generation triggered")
            
        except Exception as e:
            yield "data:" + json.dumps({"code": 500, "message": str(e),
                                        "data": {"answer": "**ERROR**: " + str(e), "reference": []}},
                                       ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "data": True}, ensure_ascii=False) + "\n\n"

    else:
        answer = None
        for ans in chat_func(dia, msg, False, **kwargs):
            answer = structure_answer(conv, ans, message_id, session_id)
            ConversationService.update_by_id(conv.id, conv.to_dict())
            
            # Invalidate cache after update
            invalidate_conversation_cache(session_id, chat_id)
            break
        
        # Generate memory after non-stream completes
        print(f"[NON-STREAM] Generating memory for session: {session_id}")
        generate_and_save_memory_async(session_id, dia, conv.message,old_memory=memory)
        print(f"[NON-STREAM] Memory generation triggered")
        
        yield answer


def iframe_completion(dialog_id, question, session_id=None, stream=True, **kwargs):
    e, dia = DialogService.get_by_id(dialog_id)
    assert e, "Dialog not found"
    if not session_id:
        session_id = get_uuid()
        conv = {
            "id": session_id,
            "dialog_id": dialog_id,
            "user_id": kwargs.get("user_id", ""),
            "message": [{"role": "assistant", "content": dia.prompt_config["prologue"], "created_at": time.time()}]
        }
        API4ConversationService.save(**conv)
        yield "data:" + json.dumps({"code": 0, "message": "",
                                    "data": {
                                        "answer": conv["message"][0]["content"],
                                        "reference": {},
                                        "audio_binary": None,
                                        "id": None,
                                        "session_id": session_id
                                    }},
                                   ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"
        return
    else:
        session_id = session_id
        e, conv = API4ConversationService.get_by_id(session_id)
        assert e, "Session not found!"

    if not conv.message:
        conv.message = []
    messages = conv.message
    question = {
        "role": "user",
        "content": question,
        "id": str(uuid4())
    }
    messages.append(question)

    msg = []
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant" and not msg:
            continue
        msg.append(m)
    if not msg[-1].get("id"):
        msg[-1]["id"] = get_uuid()
    message_id = msg[-1]["id"]

    if not conv.reference:
        conv.reference = []
    conv.reference.append({"chunks": [], "doc_aggs": []})

    if stream:
        try:
            for ans in  chat_func(dia, msg, True, **kwargs):
                ans = structure_answer(conv, ans, message_id, session_id)
                yield "data:" + json.dumps({"code": 0, "message": "", "data": ans},
                                           ensure_ascii=False) + "\n\n"
            API4ConversationService.append_message(conv.id, conv.to_dict())
        except Exception as e:
            yield "data:" + json.dumps({"code": 500, "message": str(e),
                                        "data": {"answer": "**ERROR**: " + str(e), "reference": []}},
                                       ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"

    else:
        answer = None
        for ans in chat_func(dia, msg, False, **kwargs):
            answer = structure_answer(conv, ans, message_id, session_id)
            API4ConversationService.append_message(conv.id, conv.to_dict())
            break
        yield answer
