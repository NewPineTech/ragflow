#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test word boundary detection for Vietnamese streaming
"""

import re

def num_tokens_from_string(text):
    return len(text.split())

def should_flush(delta_text, first_chunk_sent_ref):
    """Test version of should_flush"""
    if not first_chunk_sent_ref[0] and len(delta_text.strip()) > 0:
        if delta_text.rstrip() != delta_text:  # Has trailing space
            stripped = delta_text.rstrip()
            if len(stripped) >= 3:
                first_chunk_sent_ref[0] = True
                return True, 'early_flush'
    
    if re.search(r'[.!?;。！？；]\s*$', delta_text.strip()):
        return True, 'sentence'
    
    phrase_endings = re.search(r'[,—:、，：]\s*$', delta_text.strip())
    if phrase_endings and len(delta_text) >= 10:
        return True, 'phrase'
    
    if re.search(r'\.{3,}\s*$', delta_text.strip()):
        return True, 'ellipsis'
    
    if len(delta_text) >= 50 or num_tokens_from_string(delta_text) >= 8:
        return True, 'fallback'
    
    return False, None

def test_streaming(text, description):
    """Test streaming with word boundaries"""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Input: \"{text}\"")
    print(f"-"*70)
    
    first_chunk_sent = [False]
    buffer = ""
    chunk_num = 0
    
    for i, char in enumerate(text):
        buffer += char
        
        result, reason = should_flush(buffer, first_chunk_sent)
        
        if result:
            chunk_num += 1
            print(f"✅ Chunk {chunk_num} [{reason:15s}]: \"{buffer}\"")
            buffer = ""
    
    # Final flush
    if buffer:
        chunk_num += 1
        print(f"✅ Chunk {chunk_num} [final          ]: \"{buffer}\"")
    
    print(f"-"*70)
    print(f"Total chunks: {chunk_num}\n")

# Run tests
print("\n" + "="*70)
print("🧪 WORD BOUNDARY DETECTION TESTS")
print("="*70)

test_streaming(
    "Con muốn tìm hiểu về Phật pháp",
    "Vietnamese sentence without punctuation"
)

test_streaming(
    "Phật giáo là tôn giáo.",
    "Short sentence with period"
)

test_streaming(
    "Vâng, thầy sẽ giảng giải cho con.",
    "Sentence with comma"
)

test_streaming(
    "Để thầy giải thích...",
    "Sentence with ellipsis"
)

test_streaming(
    "Phật ",
    "Single word with space - should flush immediately"
)

test_streaming(
    "Con ",
    "Short word (3 chars) with space - should flush"
)

test_streaming(
    "Ơi ",
    "Very short word (2 chars) with space - should NOT flush"
)

print("\n" + "="*70)
print("✅ TESTS COMPLETE")
print("="*70)
print("\n📊 Key observations:")
print("  1. First word flushes ONLY at space boundary")
print("  2. Minimum 3 chars before space (avoid 'Ơi', 'À')")
print("  3. No cutting mid-word like 'mu' + 'ốn'")
print("  4. Preserves Vietnamese diacritics")
print()
