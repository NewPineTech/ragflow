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

import re


def remove_redundant_spaces(txt: str):
    """
    Remove redundant spaces around punctuation marks while preserving meaningful spaces.

    This function performs two main operations:
    1. Remove spaces after left-boundary characters (opening brackets, etc.)
    2. Remove spaces before right-boundary characters (closing brackets, punctuation, etc.)

    Args:
        txt (str): Input text to process

    Returns:
        str: Text with redundant spaces removed
    """
    # First pass: Remove spaces after left-boundary characters
    # Matches: [non-alphanumeric-and-specific-right-punctuation] + [non-space]
    # Removes spaces after characters like '(', '<', and other non-alphanumeric chars
    # Examples:
    #   "( test" → "(test"
    txt = re.sub(r"([^a-z0-9.,\)>]) +([^ ])", r"\1\2", txt, flags=re.IGNORECASE)

    # Second pass: Remove spaces before right-boundary characters
    # Matches: [non-space] + [non-alphanumeric-and-specific-left-punctuation]
    # Removes spaces before characters like non-')', non-',', non-'.', and non-alphanumeric chars
    # Examples:
    #   "world !" → "world!"
    return re.sub(r"([^ ]) +([^a-z0-9.,\(<])", r"\1\2", txt, flags=re.IGNORECASE)


def clean_markdown_block(text):
    """
    Remove Markdown code block syntax from the beginning and end of text.

    This function cleans Markdown code blocks by removing:
    - Opening ```Markdown tags (with optional whitespace and newlines)
    - Closing ``` tags (with optional whitespace and newlines)

    Args:
        text (str): Input text that may be wrapped in Markdown code blocks

    Returns:
        str: Cleaned text with Markdown code block syntax removed, and stripped of surrounding whitespace

    """
    # Remove opening ```Markdown tag with optional whitespace and newlines
    # Matches: optional whitespace + ```markdown + optional whitespace + optional newline
    text = re.sub(r'^\s*```markdown\s*\n?', '', text)

    # Remove closing ``` tag with optional whitespace and newlines
    # Matches: optional newline + optional whitespace + ``` + optional whitespace at end
    
    # Return text with surrounding whitespace removed
    return text.strip()
    
def remove_markdown(text, bypass=True):
    if bypass:
        return text
    if not text:
        return ""
    # 1. Remove bold/italic: **text** -> text, *text* -> text
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    
    # 2. Remove headers: # Header -> Header
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # 3. Remove links: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # 4. Remove images: ![alt](url) -> ""
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)
    
    # 5. Remove code block syntax but keep content
    text = re.sub(r'```\w*\n?(.*?)\n?```', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 6. Remove blockquotes: > text -> text
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # 7. Remove horizontal rules
    text = re.sub(r'^\s*([-*_]){3,}\s*$', '', text, flags=re.MULTILINE)
    
    return text.strip()
