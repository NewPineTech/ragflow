import os
import re
import sys

def find_chinese(directory):
    # Pattern for Chinese characters
    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]')
    target_extensions = ('.py', '.md', '.js', '.ts', '.tsx', '.html', '.json')
    
    for root, dirs, files in os.walk(directory):
        # Skip common directories to ignore
        if any(ignored in root for ignored in ['.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build']):
            continue
            
        for file in files:
            if file.endswith(target_extensions):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if chinese_pattern.search(line):
                                # Clean up the output to be readable
                                clean_line = line.strip()
                                print(f"{filepath}:{i}:{clean_line}")
                except (UnicodeDecodeError, PermissionError):
                    continue
                except Exception as e:
                    print(f"Error reading {filepath}: {e}", file=sys.stderr)

if __name__ == "__main__":
    search_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    find_chinese(search_dir)
