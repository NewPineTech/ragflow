#!/usr/bin/env python3
"""
Debug script to see what Docling is actually extracting from the CV
"""
import sys
sys.path.insert(0, '/Users/khoiphan/projects/ragflow')

from deepdoc.parser.docling_parser import DoclingParser

def debug_extraction(pdf_path):
    parser = DoclingParser()
    
    print("=" * 80)
    print("EXTRACTING WITH DOCLING...")
    print("=" * 80)
    
    try:
        sections, tables, markdown = parser.parse_pdf(filepath=pdf_path)
        
        print(f"\n✓ Extracted {len(sections)} sections")
        print(f"✓ Extracted {len(tables)} tables")
        print(f"✓ Markdown length: {len(markdown)} chars\n")
        
        print("=" * 80)
        print("SECTIONS (first 10):")
        print("=" * 80)
        for i, sec in enumerate(sections[:10]):
            print(f"\n[Section {i+1}]")
            print(f"Text: {sec[0][:200]}...")
            if len(sec) > 1:
                print(f"Tag: {sec[1]}")
        
        print("\n" + "=" * 80)
        print("MARKDOWN CONTENT (first 2000 chars):")
        print("=" * 80)
        print(markdown[:2000])
        
        print("\n" + "=" * 80)
        print("FULL SECTIONS TEXT:")
        print("=" * 80)
        full_text = "\n".join([s[0] for s in sections])
        print(full_text[:3000])
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_cv_extraction.py <path_to_cv.pdf>")
        sys.exit(1)
    
    debug_extraction(sys.argv[1])
