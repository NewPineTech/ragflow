#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for async KB retrieval in chatv1

This test verifies that KB retrieval runs in parallel with message preparation
to improve overall response time.

Usage:
    python test_async_kb_retrieval.py
"""

import sys
import os
import time
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_async_kb_retrieval():
    """
    Test that KB retrieval happens in parallel with message preparation
    """
    print("\n" + "=" * 80)
    print("TESTING ASYNC KB RETRIEVAL IN CHATV1")
    print("=" * 80 + "\n")
    
    from api.db.services.dialog_service import DialogService
    
    # Get a dialog that has KB attached
    dialog_id = input("Enter dialog_id with KB attached (or press Enter to skip): ").strip()
    if not dialog_id:
        print("⚠️  No dialog_id provided. Skipping test.")
        print("\nTo test properly, you need a dialog with:")
        print("  - KB attached (dialog.kb_ids)")
        print("  - Some documents in the KB")
        return
    
    # Get dialog
    exists, dialog = DialogService.get_by_id(dialog_id)
    if not exists:
        print(f"❌ Dialog {dialog_id} not found!")
        return
    
    if not dialog.kb_ids:
        print(f"❌ Dialog {dialog_id} has no KB attached!")
        return
    
    print(f"✅ Using dialog: {dialog.name} (ID: {dialog_id})")
    print(f"   KB IDs: {dialog.kb_ids}")
    print()
    
    # Test with a sample question
    test_questions = [
        "What is RAGFlow?",
        "How do I install it?",
        "What are the system requirements?",
    ]
    
    print("Select a test question:")
    for i, q in enumerate(test_questions, 1):
        print(f"  {i}. {q}")
    print(f"  {len(test_questions) + 1}. Custom question")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == str(len(test_questions) + 1):
        question = input("Enter your question: ").strip()
    elif choice.isdigit() and 1 <= int(choice) <= len(test_questions):
        question = test_questions[int(choice) - 1]
    else:
        question = test_questions[0]
    
    print(f"\n📝 Testing with question: '{question}'")
    print()
    
    # Prepare messages
    messages = [
        {"role": "user", "content": question}
    ]
    
    # Test chatv1 with streaming
    print("🚀 Starting chatv1 (watch for parallel KB retrieval logs)...")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        answer_chunks = []
        for chunk in DialogService.chatv1(dialog, messages, stream=True):
            if "answer" in chunk and chunk["answer"]:
                answer_chunks.append(chunk["answer"])
                # Print first chunk immediately
                if len(answer_chunks) == 1:
                    first_chunk_time = time.time() - start_time
                    print(f"\n⚡ First chunk received in {first_chunk_time:.2f}s")
                    print(f"   Content: {chunk['answer'][:100]}...")
        
        total_time = time.time() - start_time
        
        print("\n" + "-" * 80)
        print(f"✅ Response completed in {total_time:.2f}s")
        
        if answer_chunks:
            final_answer = answer_chunks[-1]
            print(f"\n📄 Final answer ({len(final_answer)} chars):")
            print("-" * 80)
            print(final_answer[:500])
            if len(final_answer) > 500:
                print(f"... ({len(final_answer) - 500} more chars)")
        
        print("\n" + "=" * 80)
        print("KEY PERFORMANCE INDICATORS:")
        print("=" * 80)
        print(f"  - Total time: {total_time:.2f}s")
        if answer_chunks:
            print(f"  - Time to first chunk: {first_chunk_time:.2f}s")
        print("\nLook for these log messages in the output above:")
        print("  🚀 'Starting KB retrieval in background thread...'")
        print("  ⏳ 'Waiting for KB retrieval thread to complete...'")
        print("  ✅ 'KB retrieval completed!'")
        print("\nIf KB retrieval happens in parallel, you should see other")
        print("operations happening between the 'Starting' and 'Waiting' messages.")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_async_kb_retrieval()
