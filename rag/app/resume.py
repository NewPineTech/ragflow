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
from io import BytesIO
from PIL import Image
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from common.constants import LLMType
from rag.nlp import rag_tokenizer
from deepdoc.parser.pdf_parser import RAGFlowPdfParser
from api.db.services.document_service import DocumentService


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

    callback(0.1, "Extracting text using OCR...")
    
    # 1. Use RAGFlowPdfParser to get full text with OCR
    parser = RAGFlowPdfParser()
    try:
        def ocr_callback(prog, msg):
            if callback:
                # Scale OCR's 0.0-1.0 to 0.1-0.5 range in resume process
                scaled_prog = 0.1 + (max(0, min(prog, 1.0)) * 0.4)
                callback(scaled_prog, msg)

        # Parse into bboxes which contain all the extracted text
        # Pass raw bytes directly, not BytesIO
        parser.parse_into_bboxes(binary, callback=ocr_callback, zoomin=3)
        
        # Extract all text from the boxes
        all_boxes = parser.boxes
        
        # Sort boxes by reading order (page, column, vertical position)
        sorted_boxes = sorted(all_boxes, key=lambda b: (
            b.get("page_number", 0),
            b.get("col_id", 0),
            b.get("top", 0)
        ))
        
        # Build full text from all boxes
        full_text = "\n".join([
            box.get("text", "").strip() 
            for box in sorted_boxes 
            if box.get("text", "").strip()
        ])
        
    except Exception as e:
        callback(-1, f"OCR parsing failed: {str(e)}")
        raise e

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
        doc["gender_kwd"] = "Male" if structured_data.get("gender") == "M" else ("Female" if structured_data.get("gender") == "F" else "")
        
        # Omit birth_dt if it's empty or the string "Empty" to avoid Elasticsearch parsing errors
        birth_val = structured_data.get("birth")
        if birth_val and str(birth_val).strip() and str(birth_val).lower() != "empty":
            doc["birth_dt"] = birth_val
            
        doc["address_kwd"] = structured_data.get("address", "")
        doc["position_name_tks"] = structured_data.get("position", "")
        
        
        # Save structured data to Document meta_fields in DB
        doc_id = kwargs.get("doc_id")
        if doc_id:
            DocumentService.update_meta_fields(doc_id, structured_data)
        
        # Candidate Avatar Extraction: collect all candidates and pick the best one
        avatar_candidates = []  # list of (pixel_area, image)

        # Method 1: Look for figure-type boxes across all pages
        figure_boxes = [b for b in all_boxes if b.get("layout_type") == "figure"]
        for fig in figure_boxes:
            w = fig.get("x1", 0) - fig.get("x0", 0)
            h = fig.get("bottom", 0) - fig.get("top", 0)
            img = fig.get("image")
            # Filter: skip full-page backgrounds and tiny icons
            if img and 50 < w < 400 and 50 < h < 400:
                # Use actual pixel dimensions if it's a PIL Image, else use box coords
                if hasattr(img, 'size'):
                    px_area = img.size[0] * img.size[1]
                else:
                    px_area = w * h
                avatar_candidates.append((px_area, img))

        # Method 2: Fallback — extract embedded images directly from the PDF
        if not avatar_candidates:
            try:
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(binary))
                for page_idx in range(min(3, len(reader.pages))):
                    page = reader.pages[page_idx]
                    for image_obj in page.images:
                        try:
                            img = Image.open(BytesIO(image_obj.data))
                            w, h = img.size
                            # Avatar: small-to-medium, roughly proportional
                            if 80 < w < 1000 and 80 < h < 1000 and 0.3 < w / h < 3.0:
                                avatar_candidates.append((w * h, img))
                        except Exception:
                            continue
            except Exception as e:
                logging.warning(f"PyPDF image extraction fallback failed: {e}")

        # Pick the largest candidate — a real photo is always bigger than icon sprites
        if avatar_candidates:
            avatar_candidates.sort(key=lambda x: x[0], reverse=True)
            doc["image"] = avatar_candidates[0][1]

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

    # Add all extracted structured data to metadata
    if structured_data:
        doc["cv_metadata_obj"] = structured_data

    KnowledgebaseService.update_parser_config(
        kwargs["kb_id"], {"field_map": field_map})
    
    return [doc]


if __name__ == "__main__":
    import sys

    def dummy(a, b):
        pass
    chunk(sys.argv[1], callback=dummy)
