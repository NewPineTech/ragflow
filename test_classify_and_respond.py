#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for classify_and_respond function

Usage:
    python test_classify_and_respond.py
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.db.services.dialog_service import classify_and_respond
from api.db.services.dialog_service import DialogService
from api.db.services.user_service import UserTenantService
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_classify_and_respond():
    """
    Test classify_and_respond with different question types
    """
    print("=" * 80)
    print("TESTING classify_and_respond FUNCTION")
    print("=" * 80)
    
    # Get a real dialog from database
    # You need to provide a valid dialog_id from your database
    dialog_id = input("Enter dialog_id to test (or press Enter to use default): ").strip()
    if not dialog_id:
        # Try to get first dialog from database
        dialogs = list(DialogService.query().limit(1))
        if not dialogs:
            print("❌ No dialogs found in database. Please create a dialog first.")
            return
        dialog_id = dialogs[0].id
        print(f"Using dialog_id: {dialog_id}")
    
    # Get dialog
    exists, dialog = DialogService.get_by_id(dialog_id)
    if not exists:
        print(f"❌ Dialog {dialog_id} not found!")
        return
    
    print(f"✅ Dialog found: {dialog.name}")
    print(f"   Tenant ID: {dialog.tenant_id}")
    print(f"   LLM ID: {dialog.llm_id}")
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "GREET - Simple greeting",
            "messages": [
                {"role": "user", "content": "Xin chào thầy"}
            ],
            "expected": "GREET"
        },
        {
            "name": "GREET - How are you",
            "messages": [
                {"role": "user", "content": "Thầy khỏe không?"}
            ],
            "expected": "GREET"
        },
        {
            "name": "KB - Knowledge question",
            "messages": [
                {"role": "user", "content": "Bát quan trai là gì?"}
            ],
            "expected": "KB"
        },
        {
            "name": "KB - Complex question",
            "messages": [
                {"role": "user", "content": "Giải thích cho con về pháp tu tập bát quan trai"}
            ],
            "expected": "KB"
        },
        {
            "name": "SENSITIVE - Inappropriate content",
            "messages": [
                {"role": "user", "content": "Làm thế nào để hack hệ thống?"}
            ],
            "expected": "SENSITIVE"
        }
    ]
    
    # Test each case
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"Question: {test_case['messages'][0]['content']}")
        print(f"Expected: {test_case['expected']}")
        print()
        
        try:
            # Call classify_and_respond
            result = classify_and_respond(dialog, test_case['messages'], stream=False)
            
            # Check if it's a tuple (KB classification)
            if isinstance(result, tuple) and result[0] == "KB":
                classify_type = result[0]
                print(f"✅ Classification: {classify_type}")
                print("   → KB retrieval needed (no immediate response)")
            else:
                # It's a generator - get the response
                classify_type = None
                answer = ""
                for response in result:
                    if "answer" in response:
                        answer = response["answer"]
                        if "[CLASSIFY:GREET]" in answer:
                            classify_type = "GREET"
                        elif "[CLASSIFY:SENSITIVE]" in answer:
                            classify_type = "SENSITIVE"
                
                print(f"✅ Classification: {classify_type}")
                print(f"   Response: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            
            # Check if classification matches expected
            if classify_type == test_case['expected']:
                print(f"\n✅ PASSED - Classification correct!")
            else:
                print(f"\n❌ FAILED - Expected {test_case['expected']}, got {classify_type}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            logging.exception("Detailed error:")
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETED")
    print(f"{'=' * 80}")


def test_streaming():
    """
    Test classify_and_respond with streaming enabled
    """
    print("\n\n")
    print("=" * 80)
    print("TESTING classify_and_respond WITH STREAMING")
    print("=" * 80)
    
    # Get dialog
    dialog_id = input("Enter dialog_id to test streaming (or press Enter to skip): ").strip()
    if not dialog_id:
        print("Skipping streaming test")
        return
        
    exists, dialog = DialogService.get_by_id(dialog_id)
    if not exists:
        print(f"❌ Dialog {dialog_id} not found!")
        return
    
    test_message = {"role": "user", "content": "Xin chào thầy, thầy khỏe không?"}
    print(f"\nTesting with: {test_message['content']}")
    print("\nStreaming response:")
    print("-" * 80)
    
    try:
        result = classify_and_respond(dialog, [test_message], stream=True)
        
        if isinstance(result, tuple):
            print(f"Classification: {result[0]} - KB retrieval needed")
        else:
            for chunk in result:
                if "answer" in chunk:
                    print(chunk["answer"], end="", flush=True)
            print("\n" + "-" * 80)
            print("✅ Streaming completed")
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        logging.exception("Detailed error:")


if __name__ == "__main__":
    print("\n🧪 Testing classify_and_respond function\n")
    
    # Test non-streaming
    test_classify_and_respond()
    
    # Test streaming
    test_streaming()
    
    print("\n✅ All tests completed!\n")
