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

def normalize_date(date_str):
    """Normalize various date formats to YYYY-MM-DD."""
    if not date_str or not isinstance(date_str, str):
        return date_str
    
    date_str = date_str.strip()
    # Already normalized?
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    
    # YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", date_str):
        return f"{date_str}-01"
    
    # YYYY
    if re.match(r"^\d{4}$", date_str):
        return f"{date_str}-01-01"

    # Human readable formats like "Dec 2023", "2023.12", "12/2023"
    try:
        from dateutil import parser
        # Set default to Jan 1st of current year if missing
        dt = parser.parse(date_str, default=datetime(datetime.now().year, 1, 1))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # If any parsing fails, check if it's just a year
        year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if year_match:
            return f"{year_match.group(0)}-01-01"
    
    return date_str

def clean_empty_values(data, normalize_dates=True):
    """Recursively remove empty values and optionally normalize dates."""
    date_fields = {"start", "end", "birth", "date"}
    
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if v is None or str(v).strip() == "" or str(v).lower() == "empty":
                continue
            
            val = clean_empty_values(v, normalize_dates)
            if val is not None:
                if normalize_dates and k in date_fields and isinstance(val, str):
                    val = normalize_date(val)
                cleaned[k] = val
        return cleaned if cleaned else None
    elif isinstance(data, list):
        cleaned = [
            clean_empty_values(item, normalize_dates)
            for item in data
            if item is not None and str(item).strip() != "" and str(item).lower() != "empty"
        ]
        return [c for c in cleaned if c is not None]
    return data

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
    full_text = ""
    avatar_image = None
    all_boxes = []

    try:
        def ocr_callback(prog, msg=None):
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

        # Candidate Avatar Extraction: collect all candidates and pick the best one
        # Moved up here so we can clear the heavy parser objects immediately after.
        avatar_candidates = []  # list of (score, image)

        def portrait_score(w, h, page=1):
            """Score an image on how likely it is to be a portrait/headshot.
            Returns a positive score (higher = more likely), or None to reject."""
            if w == 0 or h == 0:
                return None
            aspect = w / h  # < 1 means taller than wide
            # Must be roughly portrait-shaped — not a banner or wide chart
            if aspect > 1.5 or aspect < 0.4:
                return None
            # Must be a reasonable size for a headshot (not a tiny icon)
            if w < 60 or h < 60:
                return None
            # Reject very large images that are wider than they are tall  
            # (catches landscape panoramas), but allow tall high-res portraits
            if w > 4000 or h > 6000:
                return None
            # Score: prefer pages close to page 1, prefer portrait orientation (aspect<1)
            page_penalty = (page - 1) * 500
            # Portrait-ness bonus: images taller than wide score higher
            portrait_bonus = max(0, (1.0 - aspect)) * 1000
            # Use sqrt of area to reduce bias toward huge images vs. correct-size ones
            import math
            area_score = math.sqrt(w * h) * 10
            return area_score + portrait_bonus - page_penalty

        # Method 1: Look for figure-type boxes from page 1 only
        figure_boxes = [b for b in all_boxes if b.get("layout_type") == "figure"]
        for fig in figure_boxes:
            page = fig.get("page_number", 1)
            # Only consider the first 2 pages for avatars
            if page > 2:
                continue
            w = fig.get("x1", 0) - fig.get("x0", 0)
            h = fig.get("bottom", 0) - fig.get("top", 0)
            img = fig.get("image")
            if img is None:
                continue
            # Use actual pixel dimensions if available
            if hasattr(img, 'size'):
                pw, ph = img.size
            else:
                pw, ph = w, h
            score = portrait_score(pw, ph, page)
            if score is not None:
                avatar_candidates.append((score, img))

        # Method 2: Fallback — extract embedded images directly from the PDF
        if not avatar_candidates:
            try:
                import cv2
                import numpy as np
                from pypdf import PdfReader
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                reader = PdfReader(BytesIO(binary))
                for page_idx in range(min(3, len(reader.pages))):
                    page_obj = reader.pages[page_idx]
                    page_w_px = float(page_obj.mediabox.width) * 150 / 72
                    page_h_px = float(page_obj.mediabox.height) * 150 / 72
                    for image_obj in page_obj.images:
                        try:
                            img = Image.open(BytesIO(image_obj.data))
                            pw, ph = img.size
                            # Skip large background panels (sidebars, headers, etc.)
                            if pw / page_w_px >= 0.6 and ph / page_h_px >= 0.6:
                                continue
                            # Skip mostly-transparent RGBA overlays (decorative shapes)
                            if img.mode == 'RGBA':
                                alpha = np.array(img)[:, :, 3]
                                if (alpha < 128).sum() / alpha.size > 0.5:
                                    continue
                            # Skip solid color blocks (very low color diversity)
                            rgb = np.array(img.convert('RGB'))
                            flat = rgb.reshape(-1, 3)
                            sample = flat[::max(1, len(flat) // 500)]
                            unique_colors = len(set(map(tuple, sample)))
                            if unique_colors <= 5:
                                logging.debug(f"Skipping solid block {pw}x{ph} ({unique_colors} colors)")
                                continue
                            # Base portrait score (aspect ratio, size, page)
                            score = portrait_score(pw, ph, page_idx + 1)
                            if score is None:
                                continue
                            # Face detection bonus: images with a face score MUCH higher
                            # Require face to be ≥3% of image area to avoid false positives
                            try:
                                gray = cv2.cvtColor(
                                    cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                                    cv2.COLOR_BGR2GRAY
                                )
                                faces = face_cascade.detectMultiScale(
                                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                                )
                                img_area = pw * ph
                                for (fx, fy, fw, fh) in faces:
                                    face_pct = (fw * fh) / img_area
                                    if face_pct >= 0.03:  # Face is ≥3% of image
                                        score += 50000
                                        break
                            except Exception:
                                pass
                            avatar_candidates.append((score, img))
                        except Exception:
                            continue
            except Exception as e:
                logging.warning(f"PyPDF image extraction fallback failed: {e}")

            # If some candidates have faces, only keep those
            # If no candidate has a face, discard all — let Method 3 try instead
            face_candidates = [(s, im) for s, im in avatar_candidates if s >= 50000]
            if face_candidates:
                avatar_candidates = face_candidates
            else:
                avatar_candidates = []

        # Method 3: Face detection on rendered page (for scanned/rasterized CVs)
        if not avatar_candidates and hasattr(parser, 'page_images') and parser.page_images:
            try:
                import cv2
                import numpy as np
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                # Only check the first page
                page_img = parser.page_images[0]
                if isinstance(page_img, Image.Image):
                    cv_img = cv2.cvtColor(np.array(page_img), cv2.COLOR_RGB2BGR)
                elif isinstance(page_img, np.ndarray):
                    cv_img = page_img
                else:
                    cv_img = None

                if cv_img is not None:
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
                    )
                    if len(faces) > 0:
                        # Pick the largest detected face
                        faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                        x, y, w, h = faces_sorted[0]
                        # Add generous padding around the face for a natural portrait crop
                        pad_x = int(w * 0.4)
                        pad_y_top = int(h * 0.5)
                        pad_y_bottom = int(h * 0.3)
                        img_h, img_w = cv_img.shape[:2]
                        x1 = max(0, x - pad_x)
                        y1 = max(0, y - pad_y_top)
                        x2 = min(img_w, x + w + pad_x)
                        y2 = min(img_h, y + h + pad_y_bottom)
                        cropped = cv_img[y1:y2, x1:x2]
                        avatar_pil = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
                        avatar_candidates.append((10000, avatar_pil))
                        logging.info(f"Face detected at ({x},{y},{w},{h}), cropped portrait {x2-x1}x{y2-y1}")
            except Exception as e:
                logging.warning(f"Face detection fallback failed: {e}")

        # Pick the highest-scoring candidate (portrait-like, first page, right size)
        if avatar_candidates:
            avatar_candidates.sort(key=lambda x: x[0], reverse=True)
            avatar_image = avatar_candidates[0][1]

        # CLEAR HEAVY MEMORY
        parser.page_images = []
        parser.boxes = []
        all_boxes = []
        gc.collect()
        
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
    {{"school": "...", "degree": "...", "major": "...", "gpa": "...", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "description": "..."}}, ... 
  ]
- work: [ 
    {{"company": "...", "position": "...", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "responsibilities": "Detailed list or paragraph of what they did", "achievements": ["...", "..."]}}, ... 
  ]
- projects: [
    {{"name": "...", "role": "...", "technologies": ["...", "..."], "description": "...", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}}, ...
  ]
- skills: [ "Skill 1", "Skill 2", ... ]
- certifications: [ {{"name": "...", "date": "YYYY-MM-DD", "issuer": "..."}}, ... ]
- languages: [ {{"language": "...", "proficiency": "..."}}, ... ]

IMPORTANT: All dates MUST be in YYYY-MM-DD format. If only month and year are available, use the first day of the month (e.g., 2023-12-01).

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

    # Sanitize structured data to remove empty strings that break Elasticsearch date fields
    structured_data = clean_empty_values(structured_data)

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
        
        if avatar_image:
            doc["image"] = avatar_image

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
