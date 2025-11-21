#!/bin/bash
# Test classify_and_respond in Docker container

echo "========================================="
echo "Testing classify_and_respond function"
echo "========================================="

# Enter Docker container and run test
docker exec -it ragflow-server bash -c "
cd /ragflow
python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/ragflow')

from api.db.services.dialog_service import classify_and_respond, DialogService
import logging

logging.basicConfig(level=logging.INFO)

print('\\n=== Getting a dialog from database ===')
dialogs = list(DialogService.query().limit(1))
if not dialogs:
    print('No dialogs found!')
    sys.exit(1)

dialog = dialogs[0]
print(f'Dialog: {dialog.name} (ID: {dialog.id})')
print(f'Tenant: {dialog.tenant_id}')
print(f'LLM: {dialog.llm_id}')

# Test cases
test_cases = [
    {
        'name': 'GREET',
        'message': 'Xin chào thầy',
        'expected': 'GREET'
    },
    {
        'name': 'KB',
        'message': 'Bát quan trai là gì?',
        'expected': 'KB'
    },
    {
        'name': 'GREET2',
        'message': 'Thầy khỏe không?',
        'expected': 'GREET'
    }
]

print('\\n=== Testing classify_and_respond ===')
for test in test_cases:
    print(f\"\\n--- Test: {test['name']} ---\")
    print(f\"Question: {test['message']}\")
    print(f\"Expected: {test['expected']}\")
    
    messages = [{'role': 'user', 'content': test['message']}]
    
    try:
        result = classify_and_respond(dialog, messages, stream=False)
        
        # Check result type
        if isinstance(result, tuple):
            classify_type = result[0]
            print(f'Result: {classify_type} (KB retrieval needed)')
        else:
            # Generator - get first response
            answer = ''
            classify_type = None
            for resp in result:
                answer = resp.get('answer', '')
                if '[CLASSIFY:KB]' in answer:
                    classify_type = 'KB'
                elif '[CLASSIFY:GREET]' in answer:
                    classify_type = 'GREET'
                    answer = answer.replace('[CLASSIFY:GREET]', '').strip()
                elif '[CLASSIFY:SENSITIVE]' in answer:
                    classify_type = 'SENSITIVE'
                    answer = answer.replace('[CLASSIFY:SENSITIVE]', '').strip()
                break
            
            print(f'Result: {classify_type}')
            if answer:
                print(f'Answer: {answer[:100]}...')
        
        # Check if correct
        if classify_type == test['expected']:
            print('✅ PASSED')
        else:
            print(f'❌ FAILED - Expected {test[\"expected\"]}, got {classify_type}')
            
    except Exception as e:
        print(f'❌ ERROR: {e}')
        import traceback
        traceback.print_exc()

print('\\n=== Test completed ===')
PYTHON_SCRIPT
"
