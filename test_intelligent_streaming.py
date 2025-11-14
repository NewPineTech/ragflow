#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for intelligent streaming optimization.
Demonstrates phrase/sentence boundary detection.
"""

import re

def num_tokens_from_string(text):
    """Simple token counter (approximate: split by whitespace)"""
    return len(text.split())

def should_flush(delta_text, first_chunk_sent_ref):
    """
    Intelligent flush detection based on natural language boundaries.
    Returns True if we should yield the current chunk.
    
    Priority:
    1. First chunk: Send immediately (1-2 words) for responsiveness
    2. Sentence boundaries: . ! ? ; (Vietnamese + English)
    3. Phrase boundaries: , — ... (natural pauses)
    4. Fallback: 50+ chars or 8+ tokens if no boundary found
    """
    
    # 1. Early flush: Send first 1-2 complete words immediately
    if not first_chunk_sent_ref[0] and len(delta_text.strip()) > 0:
        # MUST end with space to avoid cutting Vietnamese words
        # Vietnamese words can be 2-10+ chars with diacritics
        # Example: "Phật " (OK), "Phật g" (BAD - cuts "giáo")
        #          "Con mu" (BAD), "Con muốn " (OK)
        if delta_text.rstrip() != delta_text:  # Has trailing space
            # Check if we have at least 1 complete word (3+ chars before space)
            stripped = delta_text.rstrip()
            if len(stripped) >= 3:  # At least 1 meaningful word
                first_chunk_sent_ref[0] = True
                return True, "early_flush"
    
    # 2. Sentence boundaries (strongest signal)
    sentence_endings = re.search(r'[.!?;。！？；]\s*$', delta_text.strip())
    if sentence_endings:
        return True, "sentence_boundary"
    
    # 3. Phrase boundaries (medium signal)
    phrase_endings = re.search(r'[,—:、，：]\s*$', delta_text.strip())
    if phrase_endings and len(delta_text) >= 10:
        return True, "phrase_boundary"
    
    # 4. Ellipsis patterns: ... (3+ dots)
    if re.search(r'\.{3,}\s*$', delta_text.strip()):
        return True, "ellipsis"
    
    # 5. Fallback: Length-based
    if len(delta_text) >= 50:
        return True, "fallback_chars"
    if num_tokens_from_string(delta_text) >= 8:
        return True, "fallback_tokens"
    
    return False, None


def simulate_streaming(text, chunk_size=3):
    """
    Simulate LLM streaming by breaking text into small chunks.
    Then apply intelligent flush detection.
    """
    print("=" * 80)
    print("🚀 INTELLIGENT STREAMING SIMULATION")
    print("=" * 80)
    print(f"\nOriginal text:\n{text}\n")
    print("-" * 80)
    print("Streaming chunks:\n")
    
    last_ans = ""
    first_chunk_sent = [False]  # Use list for mutability in nested function
    chunk_num = 0
    total_chunks = 0
    
    # Simulate character-by-character generation
    for i in range(0, len(text), chunk_size):
        answer = text[:i + chunk_size]
        delta_ans = answer[len(last_ans):]
        
        should_send, reason = should_flush(delta_ans, first_chunk_sent)
        
        if should_send:
            chunk_num += 1
            total_chunks += 1
            
            print(f"✅ Chunk {chunk_num} [{reason:20s}] ({len(delta_ans):3d} chars, {num_tokens_from_string(delta_ans):2d} tokens)")
            print(f"   └─> \"{delta_ans}\"")
            print()
            
            last_ans = answer
    
    # Final flush
    if answer != last_ans:
        chunk_num += 1
        total_chunks += 1
        delta_ans = answer[len(last_ans):]
        print(f"✅ Chunk {chunk_num} [final_flush          ] ({len(delta_ans):3d} chars, {num_tokens_from_string(delta_ans):2d} tokens)")
        print(f"   └─> \"{delta_ans}\"")
        print()
    
    print("-" * 80)
    print(f"Total chunks sent: {total_chunks}")
    print(f"Average chunk size: {len(text) / total_chunks:.1f} chars")
    print("=" * 80)


def main():
    """Run test cases"""
    
    # Test 1: Vietnamese Buddhist text (natural punctuation)
    print("\n\n📝 TEST 1: Vietnamese Buddhist Text (Natural Punctuation)\n")
    text1 = "Phật giáo là tôn giáo dạy về giác ngộ. Được thành lập bởi Đức Phật Thích Ca Mâu Ni, Phật pháp tập trung vào việc tu tập để đạt được giải thoát khỏi khổ đau và luân hồi. Bát quan trai là một trong những pháp môn tu tập quan trọng..."
    simulate_streaming(text1)
    
    # Test 2: Short response
    print("\n\n📝 TEST 2: Short Response (Early Flush)\n")
    text2 = "Vâng, thầy sẽ giảng giải cho con."
    simulate_streaming(text2, chunk_size=2)
    
    # Test 3: No punctuation (fallback test)
    print("\n\n📝 TEST 3: Long Text Without Punctuation (Fallback)\n")
    text3 = "Phật giáo dạy về giác ngộ và giải thoát khỏi khổ đau thông qua việc tu tập thiền định và trí tuệ để đạt được niết bàn"
    simulate_streaming(text3)
    
    # Test 4: Ellipsis pattern
    print("\n\n📝 TEST 4: Ellipsis Pattern\n")
    text4 = "Con muốn tìm hiểu về Phật pháp à... Thật tốt khi con quan tâm đến việc tu tập... Để thầy giảng giải cho con."
    simulate_streaming(text4)
    
    # Test 5: Mixed Vietnamese + English
    print("\n\n📝 TEST 5: Mixed Vietnamese + English\n")
    text5 = "Buddhism is a religion focused on enlightenment. Phật giáo dạy về giác ngộ. The Four Noble Truths guide practitioners..."
    simulate_streaming(text5)
    
    print("\n\n✅ All tests completed!")
    print("\n📊 Key observations:")
    print("  1. Early flush sends first word/phrase immediately")
    print("  2. Natural sentence boundaries create smooth reading flow")
    print("  3. Phrase boundaries (commas) provide natural pauses")
    print("  4. Fallback prevents chunks from becoming too large")
    print("  5. Works with Vietnamese, English, and mixed content")


if __name__ == "__main__":
    main()
