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

from flask import request
from api.db.services.tenant_llm_service import TenantLLMService
from api.utils.api_utils import get_error_data_result, construct_json_result, token_required
from common.constants import LLMType, StatusEnum


@manager.route("/chat_models", methods=["GET"])  # noqa: F821
@token_required
def get_chat_models(tenant_id):
    """
    Get list of available chat models for dialog configuration.
    ---
    tags:
      - LLM
    security:
      - ApiKeyAuth: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: List of chat models.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  llm_id:
                    type: string
                    description: LLM identifier (factory@name).
                  llm_factory:
                    type: string
                    description: LLM factory/provider.
                  llm_name:
                    type: string
                    description: LLM model name.
                  model_type:
                    type: string
                    description: Model type.
                  max_tokens:
                    type: integer
                    description: Maximum tokens.
                  api_base:
                    type: string
                    description: API base URL.
    """
    try:
        objs = TenantLLMService.query(
            tenant_id=tenant_id,
            model_type=LLMType.CHAT.value
        )

        result = []
        for o in objs:
            if o.status == StatusEnum.VALID.value and o.api_key:
                result.append({
                    "llm_id": f"{o.llm_factory}@{o.llm_name}",
                    "llm_factory": o.llm_factory,
                    "llm_name": o.llm_name,
                    "model_type": o.model_type,
                    "max_tokens": o.max_tokens or 8192,
                    "api_base": o.api_base or ""
                })

        return construct_json_result(data=result)
    except Exception as e:
        return get_error_data_result(message=str(e))


@manager.route("/rerank_models", methods=["GET"])  # noqa: F821
@token_required
def get_rerank_models(tenant_id):
    """
    Get list of available rerank models for dialog configuration.
    ---
    tags:
      - LLM
    security:
      - ApiKeyAuth: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: List of rerank models.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  llm_id:
                    type: string
                    description: LLM identifier (factory@name).
                  llm_factory:
                    type: string
                    description: LLM factory/provider.
                  llm_name:
                    type: string
                    description: LLM model name.
                  model_type:
                    type: string
                    description: Model type.
                  api_base:
                    type: string
                    description: API base URL.
    """
    try:
        objs = TenantLLMService.query(
            tenant_id=tenant_id,
            model_type=LLMType.RERANK.value
        )

        result = []
        for o in objs:
            if o.status == StatusEnum.VALID.value and o.api_key:
                result.append({
                    "llm_id": f"{o.llm_factory}@{o.llm_name}",
                    "llm_factory": o.llm_factory,
                    "llm_name": o.llm_name,
                    "model_type": o.model_type,
                    "api_base": o.api_base or ""
                })

        return construct_json_result(data=result)
    except Exception as e:
        return get_error_data_result(message=str(e))


@manager.route("/languages", methods=["GET"])  # noqa: F821
@token_required
def get_languages(tenant_id):
    """
    Get list of supported languages for dialog configuration.
    ---
    tags:
      - LLM
    security:
      - ApiKeyAuth: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: List of supported languages.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  language:
                    type: string
                    description: Language name.
    """
    try:
        languages = [
            {"language": "English"},
            {"language": "Chinese"},
            {"language": "Spanish"},
            {"language": "French"},
            {"language": "German"},
            {"language": "Japanese"},
            {"language": "Korean"},
            {"language": "Portuguese"},
            {"language": "Russian"},
            {"language": "Italian"},
            {"language": "Dutch"},
            {"language": "Polish"},
            {"language": "Swedish"},
            {"language": "Turkish"},
            {"language": "Arabic"},
            {"language": "Hindi"},
            {"language": "Vietnamese"},
            {"language": "Thai"},
            {"language": "Indonesian"}
        ]

        return construct_json_result(data=languages)
    except Exception as e:
        return get_error_data_result(message=str(e))
