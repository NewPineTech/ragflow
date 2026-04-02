
import sys
import os

# Add project root to path
sys.path.append('/Users/khoiphan/projects/ragflow')

from deepdoc.parser.docling_parser import DoclingParser

def test_extract(filepath):
    parser = DoclingParser()
    sections, tables = parser.parse_pdf(filepath=filepath)
    
    print(f"--- SECTIONS ({len(sections)}) ---")
    for sec in sections:
        print(sec[0])
    
    print(f"--- TABLES ({len(tables)}) ---")
    for tab in tables:
        print(tab[0][1]) # HTML of the table

if __name__ == "__main__":
    test_extract("/Users/khoiphan/projects/CV/ITviecCV_An Nguyen.pdf")
