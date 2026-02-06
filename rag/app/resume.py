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
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from common.constants import LLMType
from rag.nlp import rag_tokenizer
from deepdoc.parser.docling_parser import DoclingParser


forbidden_select_fields4resume = [
    "name_pinyin_kwd", "edu_first_fea_kwd", "degree_kwd", "sch_rank_kwd", "edu_fea_kwd"
]

def chunk(filename, binary=None, callback=None, **kwargs):
    """
    The supported file formats are pdf, docx and txt.
    """
    if not re.search(r"\.(pdf|doc|docx|txt)$", filename, flags=re.IGNORECASE):
        raise NotImplementedError("file type not supported yet(pdf supported)")

    if not binary:
        with open(filename, "rb") as f:
            binary = f.read()

    callback(0.2, "Extracting text using Docling...")
    
    # 1. Use DoclingParser to get full text
    parser = DoclingParser()
    try:
        def docling_callback(prog, msg):
            if callback:
                # Scale Docling's 0.0-1.0 to 0.2-0.4 range in resume process
                scaled_prog = 0.2 + (max(0, min(prog, 1.0)) * 0.2)
                callback(scaled_prog, msg)

        sections, _, markdown_text = parser.parse_pdf(filepath=filename, binary=binary, callback=docling_callback)
    except Exception as e:
        callback(-1, f"Docling parsing failed: {str(e)}")
        raise e

    # Combine markdown if available with any unique text from sections to be safer
    full_text = markdown_text if markdown_text else ""
    sections_text = "\n".join([sec[0] for sec in sections if sec[0]])
    
    if not full_text:
        full_text = sections_text
    elif sections_text and len(sections_text) > len(full_text) * 1.5:
        # If sections text is significantly larger, combine them
        full_text = full_text + "\n\n--- Additional Sections ---\n" + sections_text

    # 2. Use LLM to extract structured data
    callback(0.4, "Using LLM to extract details...")
    structured_data = {}
    
    tenant_id = kwargs.get("tenant_id")
    if tenant_id:
        try:
            llm_bundle = LLMBundle(tenant_id, LLMType.CHAT)
            
            prompt = f"""Extract comprehensive professional details from the following resume (in Markdown or plain text format). 
The resume might have a complex multi-column layout; ensure you capture all sections including sidebars (Skills, Languages, Education often appear in sidebars).
Return ONLY a valid JSON object. Be as detailed as possible.

Required JSON Structure:
- name: (String)
- email: (String)
- phone: (String)
- gender: (M/F/Empty)
- birth: (YYYY-MM-DD or Empty)
- address: (String)
- position: (Current or latest professional title)
- summary: (A brief professional summary or profile statement)
- education: [ 
    {{"school": "...", "degree": "...", "major": "...", "gpa": "...", "start": "...", "end": "...", "description": "..."}}, ... 
  ]
- work: [ 
    {{"company": "...", "position": "...", "start": "...", "end": "...", "responsibilities": "Detailed list or paragraph of what they did", "achievements": ["...", "..."]}}, ... 
  ]
- projects: [
    {{"name": "...", "role": "...", "technologies": ["...", "..."], "description": "...", "start": "...", "end": "..."}}, ...
  ]
- skills: [ "Skill 1", "Skill 2", ... ]
- certifications: [ {{"name": "...", "date": "...", "issuer": "..."}}, ... ]
- languages: [ {{"language": "...", "proficiency": "..."}}, ... ]

Resume:
---
{full_text}
---"""
            
            # Use _run_coroutine_sync as chunk is called in a thread but LLMBundle uses async
            response = llm_bundle._run_coroutine_sync(
                llm_bundle.async_chat(prompt, [{"role": "user", "content": "Extract all details and return as JSON, paying attention to sidebar information."}], {"temperature": 0.1})
            )
            
            callback(0.65, "LLM extraction completed.")
            logging.info(f"LLM Resume Response: {response[:100]}...")
            
            # Extract JSON from response (handling potential markdown fences)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                structured_data = json.loads(json_match.group(0))
            else:
                logging.warning(f"No JSON found in LLM response: {response}")
        except Exception as e:
            logging.exception("LLM Resume Extraction failed")
            callback(0.65, f"LLM extraction failed (falling back): {str(e)}")

    callback(0.7, "Processing extracted data...")

    # 3. Construct the RAGFlow document
    # Map structured data to RAGFlow fields
    field_map = {
        "name_kwd": "Name",
        "email_tks": "Email",
        "phone_kwd": "Phone",
        "gender_kwd": "Gender",
        "birth_dt": "Birthday",
        "address_kwd": "Address",
        "position_name_tks": "Position",
    }
    
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])

    # Populate fields from LLM data
    if structured_data:
        doc["name_kwd"] = structured_data.get("name", "")
        if structured_data.get("education") and len(structured_data["education"]) > 0:
            doc["school_name_tks"] = structured_data["education"][0].get("school", "")
            doc["major_tks"] = structured_data["education"][0].get("major", "")
        else:
            doc["school_name_tks"] = ""
            doc["major_tks"] = ""
        
        doc["email_tks"] = structured_data.get("email", "")
        doc["phone_kwd"] = structured_data.get("phone", "")
        doc["gender_kwd"] = "男" if structured_data.get("gender") == "M" else ("女" if structured_data.get("gender") == "F" else "")
        if structured_data.get("birth"):
            doc["birth_dt"] = structured_data["birth"]
        doc["address_kwd"] = structured_data.get("address", "")
        doc["position_name_tks"] = structured_data.get("position", "")
        
        # Format a summary section from education, work, projects, etc.
        summary_parts = []
        if structured_data.get("summary"):
            summary_parts.append(f"Summary: {structured_data['summary']}")

        if structured_data.get("education"):
            summary_parts.append("\nEducation:")
            for edu in structured_data["education"]:
                summary_parts.append(f"- {edu.get('school')} ({edu.get('degree')} in {edu.get('major')}) {edu.get('start')}-{edu.get('end')} {edu.get('description', '')}")
        
        if structured_data.get("work"):
            summary_parts.append("\nWork Experience:")
            for w in structured_data["work"]:
                achievements = ""
                if w.get("achievements"):
                    achievements = "\n    Achievements: " + "; ".join(w["achievements"])
                summary_parts.append(f"- {w.get('company')} as {w.get('position')} ({w.get('start')}-{w.get('end')})\n    Responsibilities: {w.get('responsibilities', '')}{achievements}")

        if structured_data.get("projects"):
            summary_parts.append("\nProjects:")
            for p in structured_data["projects"]:
                tech = ", ".join(p.get("technologies", []))
                summary_parts.append(f"- {p.get('name')} (Role: {p.get('role')}) {p.get('start')}-{p.get('end')}\n    Tech: {tech}\n    Desc: {p.get('description')}")

        if structured_data.get("certifications"):
            summary_parts.append("\nCertifications:")
            for c in structured_data["certifications"]:
                summary_parts.append(f"- {c.get('name')} by {c.get('issuer')} ({c.get('date')})")

        if structured_data.get("languages"):
            summary_parts.append("\nLanguages: " + ", ".join([f"{l.get('language')} ({l.get('proficiency')})" for l in structured_data["languages"]]))
        
        if structured_data.get("skills"):
            summary_parts.append(f"\nSkills: {', '.join(structured_data['skills'])}")

        # Weight the structured summary higher or just prepend it
        doc["content_with_weight"] = "\n".join(summary_parts) + "\n\nFull Text (extracted):\n" + full_text
    else:
        doc["content_with_weight"] = full_text

    doc["content_ltks"] = rag_tokenizer.tokenize(doc["content_with_weight"])
    doc["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(doc["content_ltks"])

    KnowledgebaseService.update_parser_config(
        kwargs["kb_id"], {"field_map": field_map})
    
    return [doc]


if __name__ == "__main__":
    import sys

    def dummy(a, b):
        pass
    chunk(sys.argv[1], callback=dummy)
