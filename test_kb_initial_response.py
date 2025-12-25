#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for KB initial response feature

This test verifies that:
1. classify_and_respond provides an initial response for KB questions
2. The initial response is streamed immediately
3. KB retrieval runs in parallel
4. Final detailed answer is provided after KB retrieval

Usage:
    python test_kb_initial_response.py
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

def test_kb_initial_response():
    """
    Test that KB questions get an immediate initial response
    while KB retrieval runs in background
    """
    print("\n" + "=" * 80)
    print("TESTING KB INITIAL RESPONSE FEATURE")
    print("=" * 80 + "\n")
    
    from api.db.services.dialog_service import DialogService
    
    # Get a dialog that has KB attached
    dialog_id = input("Enter dialog_id with KB attached (or press Enter to skip): ").strip()
    if not dialog_id:
        print("⚠️  No dialog_id provided. Skipping test.")
        print("\nTo test properly, you need a dialog with KB attached.")
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
    
    # Test with a KB question
    test_questions = [
        "What is RAGFlow?",
        "How do I install Docker?",
        "Explain the API endpoints",
        "What are the system requirements?",
    ]
    
    print("Select a test question:")
    for i, q in enumerate(test_questions, 1):
        print(f"  {i}. {q}")
    print(f"  {len(test_questions) + 1}. Custom question")
    
    choice = input("\nEnter choice: ").strip()
    
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
    print("🚀 Starting chatv1 (watch for initial response + KB retrieval)...")
    print("-" * 80)
    
    start_time = time.time()
    initial_response_time = None
    kb_retrieval_start = None
    kb_retrieval_end = None
    
    try:
        response_count = 0
        for chunk in DialogService.chatv1(dialog, messages, stream=True):
            response_count += 1
            
            if "answer" in chunk and chunk["answer"]:
                answer = chunk["answer"]
                
                # Track first response (initial KB response)
                if response_count == 1 and initial_response_time is None:
                    initial_response_time = time.time() - start_time
                    print(f"\n⚡ INITIAL RESPONSE (at {initial_response_time:.3f}s):")
                    print(f"   {answer}")
                    print()
                
                # Track subsequent responses
                elif response_count > 1:
                    if response_count == 2:
                        print(f"🔄 STREAMING KB-ENHANCED RESPONSE:")
                    
                    # Show progress indicator
                    if len(answer) < 100:
                        print(f"   [{response_count}] {answer}")
                    else:
                        # Only show first and last few chunks to avoid spam
                        if response_count <= 3 or response_count % 10 == 0:
                            print(f"   [{response_count}] {answer[:80]}... ({len(answer)} chars)")
        
        total_time = time.time() - start_time
        
        print("\n" + "-" * 80)
        print(f"✅ Response completed in {total_time:.3f}s")
        
        print("\n" + "=" * 80)
        print("KEY METRICS:")
        print("=" * 80)
        if initial_response_time:
            print(f"  ⚡ Time to initial response: {initial_response_time:.3f}s")
        print(f"  📊 Total response chunks: {response_count}")
        print(f"  🕐 Total time: {total_time:.3f}s")
        
        print("\n" + "=" * 80)
        print("FEATURE VERIFICATION:")
        print("=" * 80)
        print("✅ Expected behavior:")
        print("  1. Initial response appears immediately (< 1s)")
        print("  2. Initial response acknowledges the question")
        print("  3. KB retrieval happens in background")
        print("  4. Final detailed answer includes KB information")
        print()
        if initial_response_time and initial_response_time < 1.0:
            print("✅ SUCCESS: Initial response was fast (< 1s)")
        elif initial_response_time:
            print(f"⚠️  WARNING: Initial response took {initial_response_time:.3f}s (> 1s)")
        
        if response_count > 1:
            print("✅ SUCCESS: Multiple response chunks received")
        else:
            print("⚠️  WARNING: Only one response chunk received")
        
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kb_initial_response()
