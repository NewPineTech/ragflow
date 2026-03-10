#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

import logging
import re
import json
import gc
from datetime import datetime
from io import BytesIO
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from common.constants import LLMType
from rag.nlp import rag_tokenizer
from deepdoc.parser.pdf_parser import RAGFlowPdfParser
from deepdoc.parser.docx_parser import RAGFlowDocxParser
from api.db.services.document_service import DocumentService


def clean_empty_values(data):
    """Recursively remove empty values."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if v is None or str(v).strip() == "" or str(v).lower() == "empty":
                continue
            val = clean_empty_values(v)
            if val is not None:
                cleaned[k] = val
        return cleaned if cleaned else None
    elif isinstance(data, list):
        cleaned = [
            clean_empty_values(item)
            for item in data
            if item is not None and str(item).strip() != "" and str(item).lower() != "empty"
        ]
        return [c for c in cleaned if c is not None]
    return data

def chunk(filename, binary=None, callback=None, **kwargs):
    """
    The supported file formats are pdf and docx.
    """
    if not re.search(r"\.(pdf|doc|docx)$", filename, flags=re.IGNORECASE):
        raise NotImplementedError("file type not supported yet (pdf, docx supported)")

    if not binary:
        with open(filename, "rb") as f:
            binary = f.read()

    callback(0.1, "Extracting text...")
    
    full_text = ""

    is_pdf = bool(re.search(r"\.pdf$", filename, flags=re.IGNORECASE))

    try:
        if is_pdf:
            parser = RAGFlowPdfParser()
            def ocr_callback(prog, msg=None):
                if callback:
                    scaled_prog = 0.1 + (max(0, min(prog, 1.0)) * 0.4)
                    callback(scaled_prog, msg)

            parser.parse_into_bboxes(binary, callback=ocr_callback, zoomin=3)
            all_boxes = parser.boxes
            sorted_boxes = sorted(all_boxes, key=lambda b: (
                b.get("page_number", 0),
                b.get("col_id", 0),
                b.get("top", 0)
            ))
            full_text = "\n".join([
                box.get("text", "").strip() 
                for box in sorted_boxes 
                if box.get("text", "").strip()
            ])
            parser.page_images = []
            parser.boxes = []
            gc.collect()
        else:
            parser = RAGFlowDocxParser()
            secs, tbls = parser(binary)
            text_parts = [text for text, _ in secs if text.strip()]
            for tb in tbls:
                if isinstance(tb, list):
                    text_parts.extend(tb)
                elif isinstance(tb, str):
                    text_parts.append(tb)
            full_text = "\n".join(text_parts)
            
    except Exception as e:
        callback(-1, f"Parsing failed: {str(e)}")
        raise e

    callback(0.4, "Using LLM to extract JD details...")
    structured_data = {}
    
    tenant_id = kwargs.get("tenant_id")
    if tenant_id:
        try:
            llm_bundle = LLMBundle(tenant_id, LLMType.CHAT)
            
            prompt = f"""Extract comprehensive information from the following Job Description (in Markdown or plain text format). 
Return ONLY a valid JSON object. Be as detailed as possible.

Required JSON Structure:
- job_title: (String)
- company: (String or Empty)
- location: (String or Empty)
- employment_type: (Full-time, Part-time, Contract, etc., or Empty)
- salary: (String or Empty)
- responsibilities: [ "responsibility 1", "responsibility 2", ... ]
- requirements: [ "requirement 1", "requirement 2", ... ]
- skills: [ "skill 1", "skill 2", ... ]
- benefits: [ "benefit 1", "benefit 2", ... ]

Job Description:
---
{full_text}
---"""
            
            response = llm_bundle._run_coroutine_sync(
                llm_bundle.async_chat(prompt, [{"role": "user", "content": "Extract all details and return as JSON, paying attention to specific job details."}], {"temperature": 0.1})
            )
            
            callback(0.65, "LLM extraction completed.")
            logging.info(f"LLM JD Response: {response[:100]}...")
            
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                structured_data = json.loads(json_match.group(0))
            else:
                logging.warning(f"No JSON found in LLM response: {response}")
        except Exception as e:
            logging.exception("LLM JD Extraction failed")
            callback(0.65, f"LLM extraction failed (falling back): {str(e)}")

    callback(0.7, "Processing extracted data...")

    structured_data = clean_empty_values(structured_data)

    field_map = {
        "job_title_tks": "Job Title",
        "company_name_tks": "Company",
        "location_kwd": "Location",
        "employment_type_kwd": "Employment Type",
        "salary_kwd": "Salary",
    }
    
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])

    if structured_data:
        doc["job_title_tks"] = structured_data.get("job_title", "")
        doc["company_name_tks"] = structured_data.get("company", "")
        doc["location_kwd"] = structured_data.get("location", "")
        doc["employment_type_kwd"] = structured_data.get("employment_type", "")
        doc["salary_kwd"] = structured_data.get("salary", "")
        
        doc_id = kwargs.get("doc_id")
        if doc_id:
            DocumentService.update_meta_fields(doc_id, structured_data)
        
        summary_parts = []
        if structured_data.get("job_title"):
            summary_parts.append(f"Job Title: {structured_data['job_title']}")
        if structured_data.get("company"):
            summary_parts.append(f"Company: {structured_data['company']}")
        if structured_data.get("location"):
            summary_parts.append(f"Location: {structured_data['location']}")
        if structured_data.get("employment_type"):
            summary_parts.append(f"Employment Type: {structured_data['employment_type']}")
        if structured_data.get("salary"):
            summary_parts.append(f"Salary: {structured_data['salary']}")

        if structured_data.get("responsibilities"):
            summary_parts.append("\nResponsibilities:")
            for r in structured_data["responsibilities"]:
                summary_parts.append(f"- {r}")
                
        if structured_data.get("requirements"):
            summary_parts.append("\nRequirements:")
            for r in structured_data["requirements"]:
                summary_parts.append(f"- {r}")

        if structured_data.get("skills"):
            summary_parts.append(f"\nSkills: {', '.join(structured_data['skills'])}")
            
        if structured_data.get("benefits"):
            summary_parts.append("\nBenefits:")
            for b in structured_data["benefits"]:
                summary_parts.append(f"- {b}")

        doc["content_with_weight"] = "\n".join(summary_parts) + "\n\nFull Text (extracted):\n" + full_text
    else:
        doc["content_with_weight"] = full_text

    doc["content_ltks"] = rag_tokenizer.tokenize(doc["content_with_weight"])
    doc["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(doc["content_ltks"])

    if structured_data:
        doc["jd_metadata_obj"] = structured_data

    KnowledgebaseService.update_parser_config(
        kwargs["kb_id"], {"field_map": field_map})
    
    return [doc]

if __name__ == "__main__":
    import sys
    def dummy(a, b):
        pass
    chunk(sys.argv[1], callback=dummy)
