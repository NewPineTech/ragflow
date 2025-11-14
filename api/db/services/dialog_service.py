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
import binascii
import logging
import re
import time
from copy import deepcopy
from datetime import datetime
from functools import partial
from timeit import default_timer as timer
import trio
from langfuse import Langfuse
from peewee import fn

try:
    from lunarcalendar import Converter, Solar
except ImportError:
    Converter = None
    Solar = None

from agentic_reasoning import DeepResearcher
from api import settings
from common.constants import LLMType, ParserType, StatusEnum
from api.db.db_models import DB, Dialog
from api.db.services.common_service import CommonService
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.langfuse_service import TenantLangfuseService
from api.db.services.llm_service import LLMBundle
from api.db.services.tenant_llm_service import TenantLLMService
from common.time_utils import current_timestamp, datetime_format
from graphrag.general.mind_map_extractor import MindMapExtractor
from rag.app.resume import forbidden_select_fields4resume
from rag.app.tag import label_question
from rag.nlp.search import index_name
from rag.prompts.generator import chunks_format, citation_prompt, cross_languages, full_question, kb_prompt, keyword_extraction, message_fit_in, \
    begin_chat, gen_meta_filter, PROMPT_JINJA_ENV, ASK_SUMMARY, question_classify_prompt, short_memory
from common.token_utils import num_tokens_from_string
from rag.utils.tavily_conn import Tavily
from common.string_utils import remove_redundant_spaces
from rag.utils.redis_conn import REDIS_CONN


class DialogService(CommonService):
    model = Dialog

    @classmethod
    def save(cls, **kwargs):
        """Save a new record to database.

        This method creates a new record in the database with the provided field values,
        forcing an insert operation rather than an update.

        Args:
            **kwargs: Record field values as keyword arguments.

        Returns:
            Model instance: The created record object.
        """
        sample_obj = cls.model(**kwargs).save(force_insert=True)
        return sample_obj

    @classmethod
    def update_many_by_id(cls, data_list):
        """Update multiple records by their IDs.

        This method updates multiple records in the database, identified by their IDs.
        It automatically updates the update_time and update_date fields for each record.

        Args:
            data_list (list): List of dictionaries containing record data to update.
                             Each dictionary must include an 'id' field.
        """
        with DB.atomic():
            for data in data_list:
                data["update_time"] = current_timestamp()
                data["update_date"] = datetime_format(datetime.now())
                cls.model.update(data).where(cls.model.id == data["id"]).execute()

    @classmethod
    @DB.connection_context()
    def get_list(cls, tenant_id, page_number, items_per_page, orderby, desc, id, name):
        chats = cls.model.select()
        if id:
            chats = chats.where(cls.model.id == id)
        if name:
            chats = chats.where(cls.model.name == name)
        chats = chats.where((cls.model.tenant_id == tenant_id) & (cls.model.status == StatusEnum.VALID.value))
        if desc:
            chats = chats.order_by(cls.model.getter_by(orderby).desc())
        else:
            chats = chats.order_by(cls.model.getter_by(orderby).asc())

        chats = chats.paginate(page_number, items_per_page)

        return list(chats.dicts())

    @classmethod
    @DB.connection_context()
    def get_by_tenant_ids(cls, joined_tenant_ids, user_id, page_number, items_per_page, orderby, desc, keywords, parser_id=None):
        from api.db.db_models import User

        fields = [
            cls.model.id,
            cls.model.tenant_id,
            cls.model.name,
            cls.model.description,
            cls.model.language,
            cls.model.llm_id,
            cls.model.llm_setting,
            cls.model.prompt_type,
            cls.model.prompt_config,
            cls.model.similarity_threshold,
            cls.model.vector_similarity_weight,
            cls.model.top_n,
            cls.model.top_k,
            cls.model.do_refer,
            cls.model.rerank_id,
            cls.model.kb_ids,
            cls.model.icon,
            cls.model.status,
            User.nickname,
            User.avatar.alias("tenant_avatar"),
            cls.model.update_time,
            cls.model.create_time,
        ]
        if keywords:
            dialogs = (
                cls.model.select(*fields)
                .join(User, on=(cls.model.tenant_id == User.id))
                .where(
                    (cls.model.tenant_id.in_(joined_tenant_ids) | (cls.model.tenant_id == user_id)) & (cls.model.status == StatusEnum.VALID.value),
                    (fn.LOWER(cls.model.name).contains(keywords.lower())),
                )
            )
        else:
            dialogs = (
                cls.model.select(*fields)
                .join(User, on=(cls.model.tenant_id == User.id))
                .where(
                    (cls.model.tenant_id.in_(joined_tenant_ids) | (cls.model.tenant_id == user_id)) & (cls.model.status == StatusEnum.VALID.value),
                )
            )
        if parser_id:
            dialogs = dialogs.where(cls.model.parser_id == parser_id)
        if desc:
            dialogs = dialogs.order_by(cls.model.getter_by(orderby).desc())
        else:
            dialogs = dialogs.order_by(cls.model.getter_by(orderby).asc())

        count = dialogs.count()

        if page_number and items_per_page:
            dialogs = dialogs.paginate(page_number, items_per_page)

        return list(dialogs.dicts()), count

    @classmethod
    @DB.connection_context()
    def get_all_dialogs_by_tenant_id(cls, tenant_id):
        fields = [cls.model.id]
        dialogs = cls.model.select(*fields).where(cls.model.tenant_id == tenant_id)
        dialogs.order_by(cls.model.create_time.asc())
        offset, limit = 0, 100
        res = []
        while True:
            d_batch = dialogs.offset(offset).limit(limit)
            _temp = list(d_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res

def get_current_datetime_info():
    """
    Lấy thông tin ngày giờ hiện tại bao gồm cả ngày âm lịch.
    Returns: String chứa thông tin ngày giờ
    """
    now = datetime.now()
    
    # Ngày dương lịch
    solar_date = now.strftime("%d/%m/%Y")
    current_time = now.strftime("%H:%M:%S")
    weekday = now.strftime("%A")
    weekday_vi = {
        "Monday": "Thứ Hai",
        "Tuesday": "Thứ Ba", 
        "Wednesday": "Thứ Tư",
        "Thursday": "Thứ Năm",
        "Friday": "Thứ Sáu",
        "Saturday": "Thứ Bảy",
        "Sunday": "Chủ Nhật"
    }

    solar_day = now.strftime("%d")
    datetime_info = f"Hôm nay là {weekday_vi.get(weekday, weekday)}, ngày {solar_day}, tháng {now.month}, năm {now.year}, lúc {current_time}."

    # Thêm ngày âm lịch nếu có thư viện
    if Converter and Solar:
        try:
            solar = Solar(now.year, now.month, now.day)
            lunar = Converter.Solar2Lunar(solar)
            lunar_date = f"{lunar.day}/{lunar.month}/{lunar.year}"
            datetime_info += f" (Âm lịch: {lunar_date})"
        except Exception as e:
            logging.debug(f"Could not convert to lunar calendar: {e}")
    
    return datetime_info


def classify_and_respond(dialog, messages, stream=True):
    """
    🚀 OPTIMIZED: Classify question + Generate response in ONE LLM call
    
    Returns: (classify_type, response_generator)
        - classify_type: "KB" | "GREET" | "SENSITIVE"
        - response_generator: Generator yielding response chunks if not KB
    """
    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    prompt_config = dialog.prompt_config
    datetime_info = get_current_datetime_info()
    
    # Combined system prompt: Classify + Respond
    system_content = f"""{datetime_info}

{prompt_config.get("system", "")}

## IMPORTANT INSTRUCTIONS:
1. First, classify the user's question into ONE category:
   - KB: Requires knowledge base lookup (questions about specific topics, facts, procedures)
   - GREET: Greeting, chitchat, or general conversation
   - SENSITIVE: Inappropriate, harmful, or off-topic content

2. Response format:
   - If KB: Start with "[CLASSIFY:KB]" then stop (no answer needed)
   - If GREET or SENSITIVE: Start with "[CLASSIFY:GREET]" or "[CLASSIFY:SENSITIVE]" then provide a friendly response

Example:
User: "Xin chào thầy"
Assistant: [CLASSIFY:GREET] Chào con, thầy rất vui được gặp con.

User: "Bát quan trai là gì?"
Assistant: [CLASSIFY:KB]

User: "Thầy khỏe không?"
Assistant: [CLASSIFY:GREET] Thầy khỏe, cảm ơn con đã hỏi."""

    tts_mdl = None
    if prompt_config.get("tts"):
        tts_mdl = LLMBundle(dialog.tenant_id, LLMType.TTS)
    
    msg = [{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} for m in messages if m["role"] != "system"]
    
    if stream:
        last_ans = ""
        answer = ""
        classify_type = None
        
        for ans in chat_mdl.chat_streamly(system_content, msg, dialog.llm_setting):
            answer = ans
            
            # Extract classification from first chunk
            if classify_type is None:
                if "[CLASSIFY:KB]" in answer:
                    classify_type = "KB"
                    logging.info(f"[CLASSIFY_AND_RESPOND] Detected KB classification")
                    return classify_type, None  # No response needed for KB
                elif "[CLASSIFY:GREET]" in answer:
                    classify_type = "GREET"
                    answer = answer.replace("[CLASSIFY:GREET]", "").strip()
                    logging.info(f"[CLASSIFY_AND_RESPOND] Detected GREET, answer after strip: {answer[:100]}")
                elif "[CLASSIFY:SENSITIVE]" in answer:
                    classify_type = "SENSITIVE"
                    answer = answer.replace("[CLASSIFY:SENSITIVE]", "").strip()
                    logging.info(f"[CLASSIFY_AND_RESPOND] Detected SENSITIVE, answer after strip: {answer[:100]}")
            
            # Stream response for GREET/SENSITIVE
            if classify_type in ["GREET", "SENSITIVE"]:
                delta_ans = answer[len(last_ans):]
                # Yield immediately if we have enough content (reduced threshold for faster response)
                if len(answer) >= 10:  # Changed from token count to char count for simplicity
                    if len(delta_ans) > 0:  # Yield any new content
                        last_ans = answer
                        logging.debug(f"[CLASSIFY_AND_RESPOND] Yielding delta: {delta_ans[:50]}...")
                        yield {"answer": answer, "reference": {}, "audio_binary": None, "prompt": "", "created_at": time.time()}
        
        # Final chunk - always yield to ensure response is sent
        if classify_type in ["GREET", "SENSITIVE"]:
            if len(answer) > len(last_ans):  # Only if there's new content
                delta_ans = answer[len(last_ans):]
                logging.info(f"[CLASSIFY_AND_RESPOND] Final yield, answer length: {len(answer)}, delta: {len(delta_ans)}")
                yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
            elif len(answer) > 0:  # Ensure we send at least the complete answer
                logging.info(f"[CLASSIFY_AND_RESPOND] Final yield (complete answer): {answer[:100]}...")
                yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, answer), "prompt": "", "created_at": time.time()}
    else:
        answer = chat_mdl.chat(system_content, msg, dialog.llm_setting)
        
        # Extract classification
        if "[CLASSIFY:KB]" in answer:
            return "KB", None
        elif "[CLASSIFY:GREET]" in answer:
            classify_type = "GREET"
            answer = answer.replace("[CLASSIFY:GREET]", "").strip()
        elif "[CLASSIFY:SENSITIVE]" in answer:
            classify_type = "SENSITIVE"
            answer = answer.replace("[CLASSIFY:SENSITIVE]", "").strip()
        else:
            classify_type = "GREET"  # Default fallback
        
        logging.debug(f"User: {msg[-1].get('content', '')}|Classify: {classify_type}|Assistant: {answer}")
        yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, answer), "prompt": "", "created_at": time.time()}


def chat_solo(dialog, messages, stream=True):
    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    prompt_config = dialog.prompt_config
    
    # Thêm thông tin ngày giờ hiện tại
    datetime_info = get_current_datetime_info()
    
    # Lấy system prompt và thêm thông tin ngày giờ
    system_prompt = prompt_config.get("system", "")
    system_content = f"{datetime_info}\n\n{system_prompt}"
    
    tts_mdl = None
    if prompt_config.get("tts"):
        tts_mdl = LLMBundle(dialog.tenant_id, LLMType.TTS)
    msg = [{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} for m in messages if m["role"] != "system"]
    if stream:
        last_ans = ""
        delta_ans = ""
        for ans in chat_mdl.chat_streamly(system_content, msg, dialog.llm_setting):
            answer = ans
            delta_ans = ans[len(last_ans):]
            if num_tokens_from_string(delta_ans) < 16:
                continue
            last_ans = answer
            yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
            delta_ans = ""
        if delta_ans:
            yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
    else:
        answer = chat_mdl.chat(system_content, msg, dialog.llm_setting)
        user_content = msg[-1].get("content", "[content not available]")
        logging.debug("User: {}|Assistant: {}".format(user_content, answer))
        yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, answer), "prompt": "", "created_at": time.time()}


def chat_solo_simple(dialog, last_message, stream=True):
    """
    Trả lời ngắn gọn để xác nhận/tóm tắt ý định của user trước khi retrieve.
    Chỉ nhận message cuối cùng từ user.
    Ví dụ: User hỏi "bát quan trai là gì" -> Trả lời: "Con muốn tìm hiểu về bát quan trai à."
    
    Args:
        dialog: Dialog object
        last_message: Dict containing the last user message, e.g. {"role": "user", "content": "..."}
        stream: Boolean for streaming response
    """
    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    tts_mdl = None
    prompt_config = dialog.prompt_config
    if prompt_config.get("tts"):
        tts_mdl = LLMBundle(dialog.tenant_id, LLMType.TTS)
    
    # Tạo system prompt cho việc xác nhận ý định ngắn gọn
    simple_system_prompt = """Bạn là một trợ lý thân thiện và ngắn gọn. 
                            Nhiệm vụ của bạn là xác nhận/tóm tắt lại ý định của người dùng một cách ngắn gọn, thân thiện.
                            Chỉ trả lời 1-2 câu ngắn để xác nhận bạn đã hiểu câu hỏi, sau đó sẽ tìm kiếm thông tin chi tiết.
                            liên quan đến phật pháp thì không được nói là tìm kiếm thông tin, mà là giảng giải.
                            Ví dụ:
                            - User: "bát quan trai là gì" -> Bot: "Con muốn tìm hiểu về bát quan trai à. Để thầy giảng giải cho con."
                            - User: "con muốn tìm hiểu về tu tập" -> Bot: "Thầy rất vui khi con quan tâm đến việc tu tập."
                            - User: "Thầy giảng cho con về phật pháp đi" -> Bot: "Thật là tốt khi con muốn tìm hiểu về phật pháp."
                            Hãy trả lời thật ngắn gọn, thân thiện."""

    # Chỉ lấy message cuối cùng
    msg = [{"role": last_message["role"], "content": re.sub(r"##\d+\$\$", "", last_message["content"])}]
    
    # Cấu hình để trả lời ngắn gọn
    simple_gen_conf = dialog.llm_setting.copy()
    simple_gen_conf["max_tokens"] = 100  # Giới hạn để trả lời ngắn
    simple_gen_conf["temperature"] = 0.7  # Tăng độ sáng tạo một chút
    
    if stream:
        last_ans = ""
        delta_ans = ""
        for ans in chat_mdl.chat_streamly(simple_system_prompt, msg, simple_gen_conf):
            answer = ans
            delta_ans = ans[len(last_ans):]
            if num_tokens_from_string(delta_ans) < 8:  # Ngưỡng thấp hơn để stream nhanh hơn
                continue
            last_ans = answer
            yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
            delta_ans = ""
        if delta_ans:
            yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, delta_ans), "prompt": "", "created_at": time.time()}
    else:
        answer = chat_mdl.chat(simple_system_prompt, msg, simple_gen_conf)
        user_content = msg[-1].get("content", "[content not available]")
        logging.debug("User: {}|Assistant (simple): {}".format(user_content, answer))
        yield {"answer": answer, "reference": {}, "audio_binary": tts(tts_mdl, answer), "prompt": "", "created_at": time.time()}


def get_models(dialog):
    embd_mdl, chat_mdl, rerank_mdl, tts_mdl = None, None, None, None
    kbs = KnowledgebaseService.get_by_ids(dialog.kb_ids)
    embedding_list = list(set([kb.embd_id for kb in kbs]))
    if len(embedding_list) > 1:
        raise Exception("**ERROR**: Knowledge bases use different embedding models.")

    if embedding_list:
        embd_mdl = LLMBundle(dialog.tenant_id, LLMType.EMBEDDING, embedding_list[0])
        if not embd_mdl:
            raise LookupError("Embedding model(%s) not found" % embedding_list[0])

    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        chat_mdl = LLMBundle(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    if dialog.rerank_id:
        rerank_mdl = LLMBundle(dialog.tenant_id, LLMType.RERANK, dialog.rerank_id)

    if dialog.prompt_config.get("tts"):
        tts_mdl = LLMBundle(dialog.tenant_id, LLMType.TTS)
    return kbs, embd_mdl, rerank_mdl, chat_mdl, tts_mdl


BAD_CITATION_PATTERNS = [
    re.compile(r"\(\s*ID\s*[: ]*\s*(\d+)\s*\)"),  # (ID: 12)
    re.compile(r"\[\s*ID\s*[: ]*\s*(\d+)\s*\]"),  # [ID: 12]
    re.compile(r"【\s*ID\s*[: ]*\s*(\d+)\s*】"),  # 【ID: 12】
    re.compile(r"ref\s*(\d+)", flags=re.IGNORECASE),  # ref12、REF 12
]


def repair_bad_citation_formats(answer: str, kbinfos: dict, idx: set):
    max_index = len(kbinfos["chunks"])

    def safe_add(i):
        if 0 <= i < max_index:
            idx.add(i)
            return True
        return False

    def find_and_replace(pattern, group_index=1, repl=lambda i: f"ID:{i}", flags=0):
        nonlocal answer

        def replacement(match):
            try:
                i = int(match.group(group_index))
                if safe_add(i):
                    return f"[{repl(i)}]"
            except Exception:
                pass
            return match.group(0)

        answer = re.sub(pattern, replacement, answer, flags=flags)

    for pattern in BAD_CITATION_PATTERNS:
        find_and_replace(pattern)

    return answer, idx


def convert_conditions(metadata_condition):
    if metadata_condition is None:
        metadata_condition = {}
    op_mapping = {
        "is": "=",
        "not is": "≠"
    }
    return [
        {
            "op": op_mapping.get(cond["comparison_operator"], cond["comparison_operator"]),
            "key": cond["name"],
            "value": cond["value"]
        }
        for cond in metadata_condition.get("conditions", [])
    ]


def meta_filter(metas: dict, filters: list[dict]):
    doc_ids = set([])

    def filter_out(v2docs, operator, value):
        ids = []
        for input, docids in v2docs.items():
            try:
                input = float(input)
                value = float(value)
            except Exception:
                input = str(input)
                value = str(value)

            for conds in [
                (operator == "contains", str(value).lower() in str(input).lower()),
                (operator == "not contains", str(value).lower() not in str(input).lower()),
                (operator == "start with", str(input).lower().startswith(str(value).lower())),
                (operator == "end with", str(input).lower().endswith(str(value).lower())),
                (operator == "empty", not input),
                (operator == "not empty", input),
                (operator == "=", input == value),
                (operator == "≠", input != value),
                (operator == ">", input > value),
                (operator == "<", input < value),
                (operator == "≥", input >= value),
                (operator == "≤", input <= value),
            ]:
                try:
                    if all(conds):
                        ids.extend(docids)
                        break
                except Exception:
                    pass
        return ids

    for k, v2docs in metas.items():
        for f in filters:
            if k != f["key"]:
                continue
            ids = filter_out(v2docs, f["op"], f["value"])
            if not doc_ids:
                doc_ids = set(ids)
            else:
                doc_ids = doc_ids & set(ids)
            if not doc_ids:
                return []
    return list(doc_ids)


def chat(dialog, messages, stream=True, **kwargs):
    assert messages[-1]["role"] == "user", "The last content of this conversation is not from user."

    current_message=messages[-1]["content"]
    classify =  [question_classify_prompt(dialog.tenant_id, dialog.llm_id, current_message)][0]
    print("Classify:", classify) #Classify: ['GREET']
    if (classify == "GREET" or classify=="SENSITIVE") or ( not dialog.kb_ids and not dialog.prompt_config.get("tavily_api_key")):
        print("Use solo chat for greeting or sensitive question or no knowledge base.")
        for ans in chat_solo(dialog, messages, stream):
            yield ans
        return

    chat_start_ts = timer()

    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        llm_model_config = TenantLLMService.get_model_config(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        llm_model_config = TenantLLMService.get_model_config(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    max_tokens = llm_model_config.get("max_tokens", 8192)

    check_llm_ts = timer()
   
    langfuse_tracer = None
    trace_context = {}
    langfuse_keys = TenantLangfuseService.filter_by_tenant(tenant_id=dialog.tenant_id)
    if langfuse_keys:
        langfuse = Langfuse(public_key=langfuse_keys.public_key, secret_key=langfuse_keys.secret_key, host=langfuse_keys.host)
        if langfuse.auth_check():
            langfuse_tracer = langfuse
            trace_id = langfuse_tracer.create_trace_id()
            trace_context = {"trace_id": trace_id}

    check_langfuse_tracer_ts = timer()
    kbs, embd_mdl, rerank_mdl, chat_mdl, tts_mdl = get_models(dialog)
    toolcall_session, tools = kwargs.get("toolcall_session"), kwargs.get("tools")
    if toolcall_session and tools:
        chat_mdl.bind_tools(toolcall_session, tools)
    bind_models_ts = timer()

    # Send initial simple response to acknowledge user's intent before retrieval
    #print("=== START: Sending initial simple response via chat_solo_simple before retrieval ===")
    initial_answer = ""
    # if stream:
    #     for ans in chat_solo_simple(dialog, messages[-1], stream):
    #         initial_answer = ans.get("answer", "")
    #         print(f"=== YIELDING simple answer: {initial_answer[:50]}... ===")
    #         yield ans
    #     print(f"=== DONE: Simple answer sent. Starting retrieval... ===")
    # if initial_answer:
    #     initial_answer += "\n"
    retriever = settings.retriever
    questions = [m["content"] for m in messages if m["role"] == "user"][-3:]
    attachments = kwargs["doc_ids"].split(",") if "doc_ids" in kwargs else []
    if "doc_ids" in messages[-1]:
        attachments = messages[-1]["doc_ids"]

    prompt_config = dialog.prompt_config
    field_map = KnowledgebaseService.get_field_map(dialog.kb_ids)
    # try to use sql if field mapping is good to go
    if field_map:
        logging.debug("Use SQL to retrieval:{}".format(questions[-1]))
        ans = use_sql(questions[-1], field_map, dialog.tenant_id, chat_mdl, prompt_config.get("quote", True), dialog.kb_ids)
        if ans:
            yield ans
            return

    for p in prompt_config["parameters"]:
        if p["key"] == "knowledge":
            continue
        if p["key"] not in kwargs and not p["optional"]:
            raise KeyError("Miss parameter: " + p["key"])
        if p["key"] not in kwargs:
            prompt_config["system"] = prompt_config["system"].replace("{%s}" % p["key"], " ")
    # Lấy short_memory từ kwargs nếu có (đã được load từ Redis)
    memory_text = kwargs.pop("short_memory", None)
  
    if len(questions) > 1 and prompt_config.get("refine_multiturn"):
        questions = [full_question(dialog.tenant_id, dialog.llm_id, messages)]
    else:
        questions = questions[-1:]

    logging.info("Final questions: {}, memory: {} ".format(" ".join(questions), memory_text))
   
    if prompt_config.get("cross_languages"):
        questions = [cross_languages(dialog.tenant_id, dialog.llm_id, questions[0], prompt_config["cross_languages"])]

    if dialog.meta_data_filter:
        metas = DocumentService.get_meta_by_kbs(dialog.kb_ids)
        if dialog.meta_data_filter.get("method") == "auto":
            filters = gen_meta_filter(chat_mdl, metas, questions[-1])
            attachments.extend(meta_filter(metas, filters))
            if not attachments:
                attachments = None
        elif dialog.meta_data_filter.get("method") == "manual":
            attachments.extend(meta_filter(metas, dialog.meta_data_filter["manual"]))
            if not attachments:
                attachments = None

    if prompt_config.get("keyword", False):
        questions[-1] += keyword_extraction(chat_mdl, questions[-1])

    refine_question_ts = timer()

    thought = ""
    kbinfos = {"total": 0, "chunks": [], "doc_aggs": []}
    knowledges = []

    if attachments is not None and "knowledge" in [p["key"] for p in prompt_config["parameters"]]:
        tenant_ids = list(set([kb.tenant_id for kb in kbs]))
        knowledges = []
        if prompt_config.get("reasoning", False):
            reasoner = DeepResearcher(
                chat_mdl,
                prompt_config,
                partial(
                    retriever.retrieval,
                    embd_mdl=embd_mdl,
                    tenant_ids=tenant_ids,
                    kb_ids=dialog.kb_ids,
                    page=1,
                    page_size=dialog.top_n,
                    similarity_threshold=0.2,
                    vector_similarity_weight=0.3,
                    doc_ids=attachments,
                ),
            )

            for think in reasoner.thinking(kbinfos, " ".join(questions)):
                if isinstance(think, str):
                    thought = think
                    knowledges = [t for t in think.split("\n") if t]
                elif stream:
                    yield think
        else:
            if embd_mdl:
                kbinfos = retriever.retrieval(
                    " ".join(questions),
                    embd_mdl,
                    tenant_ids,
                    dialog.kb_ids,
                    1,
                    dialog.top_n,
                    dialog.similarity_threshold,
                    dialog.vector_similarity_weight,
                    doc_ids=attachments,
                    top=dialog.top_k,
                    aggs=False,
                    rerank_mdl=rerank_mdl,
                    rank_feature=label_question(" ".join(questions), kbs),
                )
                if prompt_config.get("toc_enhance"):
                    cks = retriever.retrieval_by_toc(" ".join(questions), kbinfos["chunks"], tenant_ids, chat_mdl, dialog.top_n)
                    if cks:
                        kbinfos["chunks"] = cks
            if prompt_config.get("tavily_api_key"):
                tav = Tavily(prompt_config["tavily_api_key"])
                tav_res = tav.retrieve_chunks(" ".join(questions))
                kbinfos["chunks"].extend(tav_res["chunks"])
                kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])
            if prompt_config.get("use_kg"):
                ck = settings.kg_retriever.retrieval(" ".join(questions), tenant_ids, dialog.kb_ids, embd_mdl,
                                                       LLMBundle(dialog.tenant_id, LLMType.CHAT))
                if ck["content_with_weight"]:
                    kbinfos["chunks"].insert(0, ck)

            knowledges = kb_prompt(kbinfos, max_tokens)

    logging.debug("{}->{}".format(" ".join(questions), "\n->".join(knowledges)))

    retrieval_ts = timer()
    if not knowledges and prompt_config.get("empty_response"):
        empty_res = prompt_config["empty_response"]
        yield {"answer": empty_res, "reference": kbinfos, "prompt": "\n\n### Query:\n%s" % " ".join(questions),
               "audio_binary": tts(tts_mdl, empty_res)}
        return {"answer": prompt_config["empty_response"], "reference": kbinfos}

    kwargs["knowledge"] = ""
    # Thêm thông tin ngày giờ hiện tại
    datetime_info = get_current_datetime_info()
    
     
    gen_conf = dialog.llm_setting

    try:
        system_content = prompt_config["system"].format(**kwargs)
    except KeyError as e:
        # Nếu còn placeholder chưa được thay thế, dùng giá trị rỗng
        logging.warning(f"Missing parameter in system prompt: {e}")
        system_content = prompt_config["system"]
    
    # 🔧 Build single system prompt with all context (datetime, memory, knowledge)
    system_parts = [system_content, f"\n## Context:{datetime_info}"]
    
    if memory_text:
        system_parts.append(f"\n##Memory: {memory_text}")
        logging.info(f"Memory added to message: {memory_text[:100]}...")
   
    if knowledges:
        kwargs["knowledge"] = "\n\n------\n\n".join(knowledges)
        system_parts.append(f"\n## Knowledge Context: {kwargs['knowledge']}")
    
    # Single system message for better LLM compatibility
    msg = [{"role": "system", "content": "".join(system_parts)}]

    prompt4citation = ""
    if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
        prompt4citation = citation_prompt()
    
    # Nếu có memory, chỉ gửi câu hỏi cuối cùng (memory đã chứa context lịch sử)
    # Nếu không có memory, gửi toàn bộ lịch sử chat
    if memory_text:
        logging.info("[MEMORY] Using memory - only sending last user message to LLM")
        print("[MEMORY] Using memory context - sending only last message")
        # Chỉ lấy message cuối cùng từ user
        msg.extend([{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} for m in messages[-1:] if m["role"] != "system"])
    else:
        logging.info("[MEMORY] No memory - sending full conversation history to LLM")
        print("[MEMORY] No memory - sending full history")
        # Gửi toàn bộ lịch sử
        msg.extend([{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} for m in messages if m["role"] != "system"])
    
    used_token_count, msg = message_fit_in(msg, int(max_tokens * 0.95))
    assert len(msg) >= 2, f"message_fit_in has bug: {msg}"
    prompt = msg[0]["content"]

    if "max_tokens" in gen_conf:
        gen_conf["max_tokens"] = min(gen_conf["max_tokens"], max_tokens - used_token_count)

    def decorate_answer(answer):
        nonlocal embd_mdl, prompt_config, knowledges, kwargs, kbinfos, prompt, retrieval_ts, questions, langfuse_tracer, initial_answer

        refs = []
        ans = answer.split("</think>")
        think = ""
        if len(ans) == 2:
            think = ans[0] + "</think>"
            answer = ans[1]

        if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
            idx = set([])
            if embd_mdl and not re.search(r"\[ID:([0-9]+)\]", answer):
                answer, idx = retriever.insert_citations(
                    answer,
                    [ck["content_ltks"] for ck in kbinfos["chunks"]],
                    [ck["vector"] for ck in kbinfos["chunks"]],
                    embd_mdl,
                    tkweight=1 - dialog.vector_similarity_weight,
                    vtweight=dialog.vector_similarity_weight,
                )
            else:
                for match in re.finditer(r"\[ID:([0-9]+)\]", answer):
                    i = int(match.group(1))
                    if i < len(kbinfos["chunks"]):
                        idx.add(i)

            answer, idx = repair_bad_citation_formats(answer, kbinfos, idx)

            idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
            recall_docs = [d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
            if not recall_docs:
                recall_docs = kbinfos["doc_aggs"]
            kbinfos["doc_aggs"] = recall_docs

        refs = deepcopy(kbinfos)
        for c in refs["chunks"]:
            if c.get("vector"):
                del c["vector"]

        if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
            answer += " Please set LLM API-Key in 'User Setting -> Model providers -> API-Key'"
        
        # Append retrieval answer to initial answer
        if initial_answer:
            answer = initial_answer + answer
        
        finish_chat_ts = timer()

        total_time_cost = (finish_chat_ts - chat_start_ts) * 1000
        check_llm_time_cost = (check_llm_ts - chat_start_ts) * 1000
        check_langfuse_tracer_cost = (check_langfuse_tracer_ts - check_llm_ts) * 1000
        bind_embedding_time_cost = (bind_models_ts - check_langfuse_tracer_ts) * 1000
        refine_question_time_cost = (refine_question_ts - bind_models_ts) * 1000
        retrieval_time_cost = (retrieval_ts - refine_question_ts) * 1000
        generate_result_time_cost = (finish_chat_ts - retrieval_ts) * 1000

        tk_num = num_tokens_from_string(think + answer)
        prompt += "\n\n### Query:\n%s" % " ".join(questions)
        prompt = (
            f"{prompt}\n\n"
            "## Time elapsed:\n"
            f"  - Total: {total_time_cost:.1f}ms\n"
            f"  - Check LLM: {check_llm_time_cost:.1f}ms\n"
            f"  - Check Langfuse tracer: {check_langfuse_tracer_cost:.1f}ms\n"
            f"  - Bind models: {bind_embedding_time_cost:.1f}ms\n"
            f"  - Query refinement(LLM): {refine_question_time_cost:.1f}ms\n"
            f"  - Retrieval: {retrieval_time_cost:.1f}ms\n"
            f"  - Generate answer: {generate_result_time_cost:.1f}ms\n\n"
            "## Token usage:\n"
            f"  - Generated tokens(approximately): {tk_num}\n"
            f"  - Token speed: {int(tk_num / (generate_result_time_cost / 1000.0))}/s"
        )
        logging.info(prompt)
        # Add a condition check to call the end method only if langfuse_tracer exists
        if langfuse_tracer and "langfuse_generation" in locals():
            langfuse_output = "\n" + re.sub(r"^.*?(### Query:.*)", r"\1", prompt, flags=re.DOTALL)
            langfuse_output = {"time_elapsed:": re.sub(r"\n", "  \n", langfuse_output), "created_at": time.time()}
            langfuse_generation.update(output=langfuse_output)
            langfuse_generation.end()
            

        return {"answer": think + answer, "reference": refs, "prompt": re.sub(r"\n", "  \n", prompt), "created_at": time.time()}

    if langfuse_tracer:
        langfuse_generation = langfuse_tracer.start_generation(
            trace_context=trace_context, name="chat", model=llm_model_config["llm_name"],
            input={"prompt": prompt, "prompt4citation": prompt4citation, "messages": msg}
        )

    if stream:
        last_ans = ""
        answer = ""
        
        
        
        for ans in chat_mdl.chat_streamly(prompt + prompt4citation, msg[1:], gen_conf):
            if thought:
                ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
            answer = ans
            delta_ans = ans[len(last_ans):]
            
            if len(delta_ans) < 16:
                continue
            
            last_ans = answer
            # Append to initial answer for streaming
            combined_answer = initial_answer +  thought + answer if initial_answer else thought + answer
            # Skip TTS during streaming to avoid blocking
            yield {"answer": combined_answer, "reference": {}, "audio_binary": None}
        
        # Final chunk: Flush remaining text
        delta_ans = answer[len(last_ans) :]
        if delta_ans:
            combined_answer = initial_answer +  thought + answer if initial_answer else thought + answer
            yield {"answer": combined_answer, "reference": {}, "audio_binary": None}
        yield decorate_answer(thought + answer)
    else:
        answer = chat_mdl.chat(prompt + prompt4citation, msg[1:], gen_conf)
        user_content = msg[-1].get("content", "[content not available]")
        logging.debug("User: {}|Assistant: {}".format(user_content, answer))
        res = decorate_answer(answer)
        res["audio_binary"] = tts(tts_mdl, answer)
        yield res


def chatv1(dialog, messages, stream=True, **kwargs):
    """
    Optimized chat function with intelligent streaming (V1)
    
    Improvements over chat():
    1. ✅ Intelligent streaming with phrase/sentence boundaries
    2. ✅ Word boundary detection (no mid-word cuts for Vietnamese)
    3. ✅ Memory optimization (only last message when memory exists)
    4. ✅ No TTS blocking during streaming
    5. ✅ Early flush for instant feedback
    
    Args:
        dialog: Dialog object with config
        messages: List of conversation messages
        stream: Enable streaming (default: True)
        **kwargs: Additional parameters including:
            - short_memory: Memory text from Redis
            - doc_ids: Document filter
            - quote: Enable citations
            
    Yields:
        dict: Response chunks with answer, reference, audio_binary
    """
    assert messages[-1]["role"] == "user", "The last content of this conversation is not from user."

    # # 🚀 OPTIMIZATION: Classify + Respond in ONE LLM call (2x faster than separate calls)
    # # Returns immediately if KB not needed, otherwise proceeds with retrieval
    # result = classify_and_respond(dialog, messages, stream)
    
    # # Check if it's a simple classify result (KB needed)
    # if isinstance(result, tuple) and result[0] == "KB":
    #     logging.info(f"[CHATV1] Question requires KB - proceeding with retrieval")
    #     # Continue with normal KB flow below
    # else:
    #     # GREET or SENSITIVE - response already generated, yield and return
    #     logging.info(f"[CHATV1] Non-KB question - response generated in classify_and_respond")
    #     for ans in result:
    #         yield ans
    #     return
    current_message=messages[-1]["content"]
    classify =  [question_classify_prompt(dialog.tenant_id, dialog.llm_id, current_message)][0]
    print("Classify:", classify) #Classify: ['GREET']
    if (classify == "GREET" or classify=="SENSITIVE") or ( not dialog.kb_ids and not dialog.prompt_config.get("tavily_api_key")):
        print("Use solo chat for greeting or sensitive question or no knowledge base.")
        for ans in chat_solo(dialog, messages, stream):
            yield ans
        return
    
    # Additional check: No KB configured
    if not dialog.kb_ids and not dialog.prompt_config.get("tavily_api_key"):
        logging.info("[CHATV1] No KB configured, falling back to chat_solo")
        for ans in chat_solo(dialog, messages, stream):
            yield ans
        return

    chat_start_ts = timer()

    if TenantLLMService.llm_id2llm_type(dialog.llm_id) == "image2text":
        llm_model_config = TenantLLMService.get_model_config(dialog.tenant_id, LLMType.IMAGE2TEXT, dialog.llm_id)
    else:
        llm_model_config = TenantLLMService.get_model_config(dialog.tenant_id, LLMType.CHAT, dialog.llm_id)

    max_tokens = llm_model_config.get("max_tokens", 1024)
    check_llm_ts = timer()
   
    langfuse_tracer = None
    trace_context = {}
    langfuse_keys = TenantLangfuseService.filter_by_tenant(tenant_id=dialog.tenant_id)
    if langfuse_keys:
        langfuse = Langfuse(public_key=langfuse_keys.public_key, secret_key=langfuse_keys.secret_key, host=langfuse_keys.host)
        if langfuse.auth_check():
            langfuse_tracer = langfuse
            trace_id = langfuse_tracer.create_trace_id()
            trace_context = {"trace_id": trace_id}

    check_langfuse_tracer_ts = timer()
    kbs, embd_mdl, rerank_mdl, chat_mdl, tts_mdl = get_models(dialog)
    toolcall_session, tools = kwargs.get("toolcall_session"), kwargs.get("tools")
    if toolcall_session and tools:
        chat_mdl.bind_tools(toolcall_session, tools)
    bind_models_ts = timer()

    retriever = settings.retriever
    questions = [m["content"] for m in messages if m["role"] == "user"][-3:]
    attachments = kwargs["doc_ids"].split(",") if "doc_ids" in kwargs else []
    if "doc_ids" in messages[-1]:
        attachments = messages[-1]["doc_ids"]

    prompt_config = dialog.prompt_config
    field_map = KnowledgebaseService.get_field_map(dialog.kb_ids)
    
    # Try SQL retrieval if field mapping exists
    if field_map:
        logging.debug("[CHATV1] Attempting SQL retrieval: {}".format(questions[-1]))
        ans = use_sql(questions[-1], field_map, dialog.tenant_id, chat_mdl, prompt_config.get("quote", True), dialog.kb_ids)
        if ans:
            yield ans
            return

    for p in prompt_config["parameters"]:
        if p["key"] == "knowledge":
            continue
        if p["key"] not in kwargs and not p["optional"]:
            raise KeyError("Miss parameter: " + p["key"])
        if p["key"] not in kwargs:
            prompt_config["system"] = prompt_config["system"].replace("{%s}" % p["key"], " ")
    
    # Extract memory from kwargs (loaded from Redis)
    memory_text = kwargs.pop("short_memory", None)
  
    if len(questions) > 1 and prompt_config.get("refine_multiturn"):
        questions = [full_question(dialog.tenant_id, dialog.llm_id, messages)]
    else:
        questions = questions[-1:]

    logging.info("[CHATV1] Questions: {}, Memory: {}".format(" ".join(questions), "Yes" if memory_text else "No"))
   
    if prompt_config.get("cross_languages"):
        questions = [cross_languages(dialog.tenant_id, dialog.llm_id, questions[0], prompt_config["cross_languages"])]

    if dialog.meta_data_filter:
        metas = DocumentService.get_meta_by_kbs(dialog.kb_ids)
        if dialog.meta_data_filter.get("method") == "auto":
            filters = gen_meta_filter(chat_mdl, metas, questions[-1])
            attachments.extend(meta_filter(metas, filters))
            if not attachments:
                attachments = None
        elif dialog.meta_data_filter.get("method") == "manual":
            attachments.extend(meta_filter(metas, dialog.meta_data_filter["manual"]))
            if not attachments:
                attachments = None

    if prompt_config.get("keyword", False):
        questions[-1] += keyword_extraction(chat_mdl, questions[-1])

    refine_question_ts = timer()

    thought = ""
    kbinfos = {"total": 0, "chunks": [], "doc_aggs": []}
    knowledges = []

    if attachments is not None and "knowledge" in [p["key"] for p in prompt_config["parameters"]]:
        tenant_ids = list(set([kb.tenant_id for kb in kbs]))
        knowledges = []
        
        if prompt_config.get("reasoning", False):
            reasoner = DeepResearcher(
                chat_mdl,
                prompt_config,
                partial(
                    retriever.retrieval,
                    embd_mdl=embd_mdl,
                    tenant_ids=tenant_ids,
                    kb_ids=dialog.kb_ids,
                    page=1,
                    page_size=dialog.top_n,
                    similarity_threshold=0.2,
                    vector_similarity_weight=0.3,
                    doc_ids=attachments,
                ),
            )

            for think in reasoner.thinking(kbinfos, " ".join(questions)):
                if isinstance(think, str):
                    thought = think
                    knowledges = [t for t in think.split("\n") if t]
                elif stream:
                    yield think
        else:
            if embd_mdl:
                kbinfos = retriever.retrieval(
                    " ".join(questions),
                    embd_mdl,
                    tenant_ids,
                    dialog.kb_ids,
                    1,
                    dialog.top_n,
                    dialog.similarity_threshold,
                    dialog.vector_similarity_weight,
                    doc_ids=attachments,
                    top=dialog.top_k,
                    aggs=False,
                    rerank_mdl=rerank_mdl,
                    rank_feature=label_question(" ".join(questions), kbs),
                )
                if prompt_config.get("toc_enhance"):
                    cks = retriever.retrieval_by_toc(" ".join(questions), kbinfos["chunks"], tenant_ids, chat_mdl, dialog.top_n)
                    if cks:
                        kbinfos["chunks"] = cks
                        
            if prompt_config.get("tavily_api_key"):
                tav = Tavily(prompt_config["tavily_api_key"])
                tav_res = tav.retrieve_chunks(" ".join(questions))
                kbinfos["chunks"].extend(tav_res["chunks"])
                kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])
                
            if prompt_config.get("use_kg"):
                ck = settings.kg_retriever.retrieval(" ".join(questions), tenant_ids, dialog.kb_ids, embd_mdl,
                                                       LLMBundle(dialog.tenant_id, LLMType.CHAT))
                if ck["content_with_weight"]:
                    kbinfos["chunks"].insert(0, ck)

            knowledges = kb_prompt(kbinfos, max_tokens)

    logging.debug("[CHATV1] Retrieved {} knowledge chunks".format(len(knowledges)))

    retrieval_ts = timer()
    
    if not knowledges and prompt_config.get("empty_response"):
        empty_res = prompt_config["empty_response"]
        yield {"answer": empty_res, "reference": kbinfos, "prompt": "\n\n### Query:\n%s" % " ".join(questions),
               "audio_binary": tts(tts_mdl, empty_res)}
        return

    kwargs["knowledge"] = ""
    datetime_info = get_current_datetime_info()
    gen_conf = dialog.llm_setting

    try:
        system_content = prompt_config["system"].format(**kwargs)
    except KeyError as e:
        logging.warning(f"[CHATV1] Missing parameter in system prompt: {e}")
        system_content = prompt_config["system"]
    
    # 🔧 Build single system prompt with all context (datetime, memory, knowledge)
    system_parts = [system_content, f"\n## Context:{datetime_info}"]
    
    if memory_text:
        system_parts.append(f"\n##Memory: {memory_text}")
        logging.info(f"[CHATV1] Memory added: {memory_text[:100]}...")
   
    if knowledges:
        kwargs["knowledge"] = "\n\n------\n\n".join(knowledges)
        system_parts.append(f"\n## Knowledge Context: {kwargs['knowledge']}")
    
    # Single system message for better LLM compatibility
    msg = [{"role": "system", "content": "".join(system_parts)}]

    def strip_markdown(text):
        """
        Remove markdown formatting while preserving citations [ID:n].
        Strips: **bold**, *italic*, __underline__, ~~strikethrough~~, #headers, etc.
        """
        # Preserve citations by replacing temporarily
        citation_placeholder = {}
        citation_pattern = r'\[ID:\d+\]'
        for i, match in enumerate(re.finditer(citation_pattern, text)):
            placeholder = f"__CITATION_{i}__"
            citation_placeholder[placeholder] = match.group(0)
            text = text.replace(match.group(0), placeholder, 1)
        
        # Remove markdown formatting
        # Headers (##, ###, etc.)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Bold (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        # Italic (*text* or _text_)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
        # Strikethrough (~~text~~)
        text = re.sub(r'~~(.+?)~~', r'\1', text)
        # Code blocks (```code```)
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Inline code (`code`)
        text = re.sub(r'`(.+?)`', r'\1', text)
        # Links ([text](url))
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Images (![alt](url))
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
        # Blockquotes (> text)
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        # Horizontal rules (---, ***, ___)
        text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
        # Lists (- item, * item, 1. item)
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Restore citations
        for placeholder, citation in citation_placeholder.items():
            text = text.replace(placeholder, citation)
        
        return text

    prompt4citation = ""
    if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
        prompt4citation = citation_prompt()
    
    # 🎯 MEMORY OPTIMIZATION: Only send last message if memory exists
    if memory_text:
        logging.info("[CHATV1] Using memory - sending only last user message")
        msg.extend([{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} 
                    for m in messages[-1:] if m["role"] != "system"])
    else:
        logging.info("[CHATV1] No memory - sending full conversation history")
        msg.extend([{"role": m["role"], "content": re.sub(r"##\d+\$\$", "", m["content"])} 
                    for m in messages if m["role"] != "system"])
    
    used_token_count, msg = message_fit_in(msg, int(max_tokens * 0.95))
    assert len(msg) >= 2, f"message_fit_in has bug: {msg}"
    prompt = msg[0]["content"]

    if "max_tokens" in gen_conf:
        gen_conf["max_tokens"] = min(gen_conf["max_tokens"], max_tokens - used_token_count)

    def decorate_answer(answer):
        nonlocal embd_mdl, prompt_config, knowledges, kwargs, kbinfos, prompt, retrieval_ts, questions, langfuse_tracer

        refs = []
        ans = answer.split("</think>")
        think = ""
        if len(ans) == 2:
            think = ans[0] + "</think>"
            answer = ans[1]

        if knowledges and (prompt_config.get("quote", True) and kwargs.get("quote", True)):
            idx = set([])
            if embd_mdl and not re.search(r"\[ID:([0-9]+)\]", answer):
                answer, idx = retriever.insert_citations(
                    answer,
                    [ck["content_ltks"] for ck in kbinfos["chunks"]],
                    [ck["vector"] for ck in kbinfos["chunks"]],
                    embd_mdl,
                    tkweight=1 - dialog.vector_similarity_weight,
                    vtweight=dialog.vector_similarity_weight,
                )
            else:
                for match in re.finditer(r"\[ID:([0-9]+)\]", answer):
                    i = int(match.group(1))
                    if i < len(kbinfos["chunks"]):
                        idx.add(i)

            answer, idx = repair_bad_citation_formats(answer, kbinfos, idx)

            idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
            recall_docs = [d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
            if not recall_docs:
                recall_docs = kbinfos["doc_aggs"]
            kbinfos["doc_aggs"] = recall_docs

        # 🧹 Strip markdown AFTER citations are added (preserves [ID:n] format)
        answer = strip_markdown(answer)

        refs = deepcopy(kbinfos)
        for c in refs["chunks"]:
            if c.get("vector"):
                del c["vector"]

        if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
            answer += " Please set LLM API-Key in 'User Setting -> Model providers -> API-Key'"
        
        finish_chat_ts = timer()

        total_time_cost = (finish_chat_ts - chat_start_ts) * 1000
        check_llm_time_cost = (check_llm_ts - chat_start_ts) * 1000
        check_langfuse_tracer_cost = (check_langfuse_tracer_ts - check_llm_ts) * 1000
        bind_embedding_time_cost = (bind_models_ts - check_langfuse_tracer_ts) * 1000
        refine_question_time_cost = (refine_question_ts - bind_models_ts) * 1000
        retrieval_time_cost = (retrieval_ts - refine_question_ts) * 1000
        generate_result_time_cost = (finish_chat_ts - retrieval_ts) * 1000

        tk_num = num_tokens_from_string(think + answer)
        prompt += "\n\n### Query:\n%s" % " ".join(questions)
        prompt = (
            f"{prompt}\n\n"
            "## Time elapsed:\n"
            f"  - Total: {total_time_cost:.1f}ms\n"
            f"  - Check LLM: {check_llm_time_cost:.1f}ms\n"
            f"  - Check Langfuse tracer: {check_langfuse_tracer_cost:.1f}ms\n"
            f"  - Bind models: {bind_embedding_time_cost:.1f}ms\n"
            f"  - Query refinement(LLM): {refine_question_time_cost:.1f}ms\n"
            f"  - Retrieval: {retrieval_time_cost:.1f}ms\n"
            f"  - Generate answer: {generate_result_time_cost:.1f}ms\n\n"
            "## Token usage:\n"
            f"  - Generated tokens(approximately): {tk_num}\n"
            f"  - Token speed: {int(tk_num / (generate_result_time_cost / 1000.0))}/s"
        )
        logging.info(f"[CHATV1] {prompt}")
        
        if langfuse_tracer and "langfuse_generation" in locals():
            langfuse_output = "\n" + re.sub(r"^.*?(### Query:.*)", r"\1", prompt, flags=re.DOTALL)
            langfuse_output = {"time_elapsed:": re.sub(r"\n", "  \n", langfuse_output), "created_at": time.time()}
            langfuse_generation.update(output=langfuse_output)
            langfuse_generation.end()

        return {"answer": think + answer, "reference": refs, "prompt": re.sub(r"\n", "  \n", prompt), "created_at": time.time()}

    if langfuse_tracer:
        langfuse_generation = langfuse_tracer.start_generation(
            trace_context=trace_context, name="chatv1", model=llm_model_config["llm_name"],
            input={"prompt": prompt, "prompt4citation": prompt4citation, "messages": msg}
        )

    if stream:
        last_ans = ""
        answer = ""
        first_chunk_sent = False
        
        def should_flush(delta_text):
            """
            🚀 INTELLIGENT STREAMING: Flush detection based on natural language boundaries
            
            Priority:
            1. First chunk: Complete word (3+ chars + space) - NO MID-WORD CUTS
            2. Sentence boundaries: . ! ? ; (Vietnamese + English)
            3. Phrase boundaries: , — : (natural pauses, min 10 chars)
            4. Ellipsis patterns: ... (3+ dots)
            5. Fallback: 50+ chars or 8+ tokens (safety net)
            
            Returns True if we should yield the current chunk.
            """
            nonlocal first_chunk_sent
            
            # 1. Early flush: Send first COMPLETE word immediately
            # For first chunk: Flush when we have 3+ chars (even without trailing space)
            # This gives faster first token experience
            # Example: "Thầy" (3 chars, OK), "Th" (2 chars, wait), "Phật giáo" (OK)
            if not first_chunk_sent and len(delta_text.strip()) >= 3:
                first_chunk_sent = True
                return True
            
            # 2. Sentence boundaries (strongest signal)
            # Vietnamese: . ! ? ; 。！？；
            sentence_endings = re.search(r'[.!?;。！？；]\s*$', delta_text.strip())
            if sentence_endings:
                return True
            
            # 3. Phrase boundaries (medium signal)
            # Vietnamese/English: , — : 、，：
            phrase_endings = re.search(r'[,—:、，：]\s*$', delta_text.strip())
            if phrase_endings and len(delta_text) >= 10:
                return True
            
            # 4. Ellipsis patterns: ... (3+ dots)
            if re.search(r'\.{3,}\s*$', delta_text.strip()):
                return True
            
            # 5. Fallback: Length-based (avoid chunks too large)
            if len(delta_text) >= 50:
                return True
            if num_tokens_from_string(delta_text) >= 8:
                return True
            
            return False
        
        for ans in chat_mdl.chat_streamly(prompt + prompt4citation, msg[1:], gen_conf):
            if thought:
                ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
            answer = ans
            delta_ans = answer[len(last_ans):]
            
            # 🚀 INTELLIGENT STREAMING: Check full answer for boundaries (not just delta)
            if not should_flush(answer):
                continue
            
            last_ans = answer
            # No TTS during streaming to avoid blocking
            yield {"answer": thought + answer, "reference": {}, "audio_binary": None}
        
        # Final chunk: Flush remaining text
        delta_ans = answer[len(last_ans):]
        if delta_ans:
            yield {"answer": thought + answer, "reference": {}, "audio_binary": None}
        
        yield decorate_answer(thought + answer)
    else:
        answer = chat_mdl.chat(prompt + prompt4citation, msg[1:], gen_conf)
        user_content = msg[-1].get("content", "[content not available]")
        logging.debug("[CHATV1] User: {}|Assistant: {}".format(user_content, answer))
        res = decorate_answer(answer)
        res["audio_binary"] = tts(tts_mdl, answer)
        yield res


def use_sql(question, field_map, tenant_id, chat_mdl, quota=True, kb_ids=None):
    sys_prompt = "You are a Database Administrator. You need to check the fields of the following tables based on the user's list of questions and write the SQL corresponding to the last question."
    user_prompt = """
Table name: {};
Table of database fields are as follows:
{}

Question are as follows:
{}
Please write the SQL, only SQL, without any other explanations or text.
""".format(index_name(tenant_id), "\n".join([f"{k}: {v}" for k, v in field_map.items()]), question)
    tried_times = 0

    def get_table():
        nonlocal sys_prompt, user_prompt, question, tried_times
        sql = chat_mdl.chat(sys_prompt, [{"role": "user", "content": user_prompt}], {"temperature": 0.06})
        sql = re.sub(r"^.*</think>", "", sql, flags=re.DOTALL)
        logging.debug(f"{question} ==> {user_prompt} get SQL: {sql}")
        sql = re.sub(r"[\r\n]+", " ", sql.lower())
        sql = re.sub(r".*select ", "select ", sql.lower())
        sql = re.sub(r" +", " ", sql)
        sql = re.sub(r"([;；]|```).*", "", sql)
        if sql[: len("select ")] != "select ":
            return None, None
        if not re.search(r"((sum|avg|max|min)\(|group by )", sql.lower()):
            if sql[: len("select *")] != "select *":
                sql = "select doc_id,docnm_kwd," + sql[6:]
            else:
                flds = []
                for k in field_map.keys():
                    if k in forbidden_select_fields4resume:
                        continue
                    if len(flds) > 11:
                        break
                    flds.append(k)
                sql = "select doc_id,docnm_kwd," + ",".join(flds) + sql[8:]

        if kb_ids:
            kb_filter = "(" + " OR ".join([f"kb_id = '{kb_id}'" for kb_id in kb_ids]) + ")"
            if "where" not in sql.lower():
                sql += f" WHERE {kb_filter}"
            else:
                sql += f" AND {kb_filter}"

        logging.debug(f"{question} get SQL(refined): {sql}")
        tried_times += 1
        return settings.retriever.sql_retrieval(sql, format="json"), sql

    tbl, sql = get_table()
    if tbl is None:
        return None
    if tbl.get("error") and tried_times <= 2:
        user_prompt = """
        Table name: {};
        Table of database fields are as follows:
        {}

        Question are as follows:
        {}
        Please write the SQL, only SQL, without any other explanations or text.


        The SQL error you provided last time is as follows:
        {}

        Error issued by database as follows:
        {}

        Please correct the error and write SQL again, only SQL, without any other explanations or text.
        """.format(index_name(tenant_id), "\n".join([f"{k}: {v}" for k, v in field_map.items()]), question, sql, tbl["error"])
        tbl, sql = get_table()
        logging.debug("TRY it again: {}".format(sql))

    logging.debug("GET table: {}".format(tbl))
    if tbl.get("error") or len(tbl["rows"]) == 0:
        return None

    docid_idx = set([ii for ii, c in enumerate(tbl["columns"]) if c["name"] == "doc_id"])
    doc_name_idx = set([ii for ii, c in enumerate(tbl["columns"]) if c["name"] == "docnm_kwd"])
    column_idx = [ii for ii in range(len(tbl["columns"])) if ii not in (docid_idx | doc_name_idx)]

    # compose Markdown table
    columns = (
            "|" + "|".join(
        [re.sub(r"(/.*|（[^（）]+）)", "", field_map.get(tbl["columns"][i]["name"], tbl["columns"][i]["name"])) for i in column_idx]) + (
                "|Source|" if docid_idx and docid_idx else "|")
    )

    line = "|" + "|".join(["------" for _ in range(len(column_idx))]) + ("|------|" if docid_idx and docid_idx else "")

    rows = ["|" + "|".join([remove_redundant_spaces(str(r[i])) for i in column_idx]).replace("None", " ") + "|" for r in tbl["rows"]]
    rows = [r for r in rows if re.sub(r"[ |]+", "", r)]
    if quota:
        rows = "\n".join([r + f" ##{ii}$$ |" for ii, r in enumerate(rows)])
    else:
        rows = "\n".join([r + f" ##{ii}$$ |" for ii, r in enumerate(rows)])
    rows = re.sub(r"T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+Z)?\|", "|", rows)

    if not docid_idx or not doc_name_idx:
        logging.warning("SQL missing field: " + sql)
        return {"answer": "\n".join([columns, line, rows]), "reference": {"chunks": [], "doc_aggs": []}, "prompt": sys_prompt}

    docid_idx = list(docid_idx)[0]
    doc_name_idx = list(doc_name_idx)[0]
    doc_aggs = {}
    for r in tbl["rows"]:
        if r[docid_idx] not in doc_aggs:
            doc_aggs[r[docid_idx]] = {"doc_name": r[doc_name_idx], "count": 0}
        doc_aggs[r[docid_idx]]["count"] += 1
    return {
        "answer": "\n".join([columns, line, rows]),
        "reference": {
            "chunks": [{"doc_id": r[docid_idx], "docnm_kwd": r[doc_name_idx]} for r in tbl["rows"]],
            "doc_aggs": [{"doc_id": did, "doc_name": d["doc_name"], "count": d["count"]} for did, d in doc_aggs.items()],
        },
        "prompt": sys_prompt,
    }


def tts(tts_mdl, text):
    if not tts_mdl or not text:
        return
    bin = b""
    for chunk in tts_mdl.tts(text):
        bin += chunk
    return binascii.hexlify(bin).decode("utf-8")


def ask(question, kb_ids, tenant_id, chat_llm_name=None, search_config={}):
    doc_ids = search_config.get("doc_ids", [])
    rerank_mdl = None
    kb_ids = search_config.get("kb_ids", kb_ids)
    chat_llm_name = search_config.get("chat_id", chat_llm_name)
    rerank_id = search_config.get("rerank_id", "")
    meta_data_filter = search_config.get("meta_data_filter")

    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    embedding_list = list(set([kb.embd_id for kb in kbs]))

    is_knowledge_graph = all([kb.parser_id == ParserType.KG for kb in kbs])
    retriever = settings.retriever if not is_knowledge_graph else settings.kg_retriever

    embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embedding_list[0])
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, chat_llm_name)
    if rerank_id:
        rerank_mdl = LLMBundle(tenant_id, LLMType.RERANK, rerank_id)
    max_tokens = chat_mdl.max_length
    tenant_ids = list(set([kb.tenant_id for kb in kbs]))

    if meta_data_filter:
        metas = DocumentService.get_meta_by_kbs(kb_ids)
        if meta_data_filter.get("method") == "auto":
            filters = gen_meta_filter(chat_mdl, metas, question)
            doc_ids.extend(meta_filter(metas, filters))
            if not doc_ids:
                doc_ids = None
        elif meta_data_filter.get("method") == "manual":
            doc_ids.extend(meta_filter(metas, meta_data_filter["manual"]))
            if not doc_ids:
                doc_ids = None

    kbinfos = retriever.retrieval(
        question=question,
        embd_mdl=embd_mdl,
        tenant_ids=tenant_ids,
        kb_ids=kb_ids,
        page=1,
        page_size=12,
        similarity_threshold=search_config.get("similarity_threshold", 0.1),
        vector_similarity_weight=search_config.get("vector_similarity_weight", 0.3),
        top=search_config.get("top_k", 1024),
        doc_ids=doc_ids,
        aggs=False,
        rerank_mdl=rerank_mdl,
        rank_feature=label_question(question, kbs)
    )

    knowledges = kb_prompt(kbinfos, max_tokens)
    sys_prompt = PROMPT_JINJA_ENV.from_string(ASK_SUMMARY).render(knowledge="\n".join(knowledges))

    msg = [{"role": "user", "content": question}]

    def decorate_answer(answer):
        nonlocal knowledges, kbinfos, sys_prompt
        answer, idx = retriever.insert_citations(answer, [ck["content_ltks"] for ck in kbinfos["chunks"]], [ck["vector"] for ck in kbinfos["chunks"]],
                                                 embd_mdl, tkweight=0.7, vtweight=0.3)
        idx = set([kbinfos["chunks"][int(i)]["doc_id"] for i in idx])
        recall_docs = [d for d in kbinfos["doc_aggs"] if d["doc_id"] in idx]
        if not recall_docs:
            recall_docs = kbinfos["doc_aggs"]
        kbinfos["doc_aggs"] = recall_docs
        refs = deepcopy(kbinfos)
        for c in refs["chunks"]:
            if c.get("vector"):
                del c["vector"]

        if answer.lower().find("invalid key") >= 0 or answer.lower().find("invalid api") >= 0:
            answer += " Please set LLM API-Key in 'User Setting -> Model Providers -> API-Key'"
        refs["chunks"] = chunks_format(refs)
        return {"answer": answer, "reference": refs}

    answer = ""
    for ans in chat_mdl.chat_streamly(sys_prompt, msg, {"temperature": 0.1}):
        answer = ans
        yield {"answer": answer, "reference": {}}
    yield decorate_answer(answer)


def gen_mindmap(question, kb_ids, tenant_id, search_config={}):
    meta_data_filter = search_config.get("meta_data_filter", {})
    doc_ids = search_config.get("doc_ids", [])
    rerank_id = search_config.get("rerank_id", "")
    rerank_mdl = None
    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    if not kbs:
        return {"error": "No KB selected"}
    embedding_list = list(set([kb.embd_id for kb in kbs]))
    tenant_ids = list(set([kb.tenant_id for kb in kbs]))

    embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, llm_name=embedding_list[0])
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, llm_name=search_config.get("chat_id", ""))
    if rerank_id:
        rerank_mdl = LLMBundle(tenant_id, LLMType.RERANK, rerank_id)

    if meta_data_filter:
        metas = DocumentService.get_meta_by_kbs(kb_ids)
        if meta_data_filter.get("method") == "auto":
            filters = gen_meta_filter(chat_mdl, metas, question)
            doc_ids.extend(meta_filter(metas, filters))
            if not doc_ids:
                doc_ids = None
        elif meta_data_filter.get("method") == "manual":
            doc_ids.extend(meta_filter(metas, meta_data_filter["manual"]))
            if not doc_ids:
                doc_ids = None

    ranks = settings.retriever.retrieval(
        question=question,
        embd_mdl=embd_mdl,
        tenant_ids=tenant_ids,
        kb_ids=kb_ids,
        page=1,
        page_size=12,
        similarity_threshold=search_config.get("similarity_threshold", 0.2),
        vector_similarity_weight=search_config.get("vector_similarity_weight", 0.3),
        top=search_config.get("top_k", 1024),
        doc_ids=doc_ids,
        aggs=False,
        rerank_mdl=rerank_mdl,
        rank_feature=label_question(question, kbs),
    )
    mindmap = MindMapExtractor(chat_mdl)
    mind_map = trio.run(mindmap, [c["content_with_weight"] for c in ranks["chunks"]])
    return mind_map.output
