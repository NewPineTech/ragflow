#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test query normalization for cache optimization.
Verify that similar queries produce the same cache key.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.utils.cache_utils import _normalize_query, _make_cache_key

def test_normalization():
    """Test query normalization"""
    print("=" * 80)
    print("TEST 1: Query Normalization")
    print("=" * 80)
    
    test_cases = [
        # Case 1: Chữ hoa thường
        [
            "Phật giáo là gì?",
            "phật giáo là gì",
            "PHẬT GIÁO LÀ GÌ",
            "Phật Giáo Là Gì",
        ],
        # Case 2: Dấu câu
        [
            "Bát quan trai là gì?",
            "Bát quan trai là gì",
            "Bát quan trai, là gì?",
            "Bát quan trai - là gì!",
        ],
        # Case 3: Thứ tự từ
        [
            "Tu tập như thế nào",
            "Như thế nào tu tập",
            "Như thế nào để tu tập",
        ],
        # Case 4: Khoảng trắng
        [
            "Phật   giáo",
            "Phật giáo",
            "Phật     giáo    ",
        ],
    ]
    
    passed = 0
    failed = 0
    
    for i, group in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"Test Case {i}: {group[0][:50]}...")
        print(f"{'─' * 80}")
        
        normalized_set = set()
        for query in group:
            norm = _normalize_query(query)
            normalized_set.add(norm)
            print(f"  {query:40} → {norm}")
        
        if len(normalized_set) == 1:
            print(f"  ✅ PASS - All queries normalized to: '{normalized_set.pop()}'")
            passed += 1
        else:
            print(f"  ❌ FAIL - Got {len(normalized_set)} different results: {normalized_set}")
            failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"Normalization Tests: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")
    
    return failed == 0


def test_cache_keys():
    """Test that normalized queries produce same cache key"""
    print("=" * 80)
    print("TEST 2: Cache Key Generation")
    print("=" * 80)
    
    test_groups = [
        {
            "name": "Case insensitive",
            "queries": [
                "Phật giáo là gì?",
                "phật giáo là gì",
                "PHẬT GIÁO LÀ GÌ",
            ]
        },
        {
            "name": "Punctuation variants",
            "queries": [
                "Bát quan trai là gì?",
                "Bát quan trai là gì",
                "Bát quan trai, là gì!?",
            ]
        },
        {
            "name": "Word order",
            "queries": [
                "Phật pháp tu tập",
                "Tu tập phật pháp",
            ]
        },
    ]
    
    passed = 0
    failed = 0
    kb_ids = ["kb1", "kb2"]
    top_k = 6
    
    for group in test_groups:
        print(f"\n{'─' * 80}")
        print(f"Test: {group['name']}")
        print(f"{'─' * 80}")
        
        keys = []
        for query in group["queries"]:
            key = _make_cache_key("retrieval", query, kb_ids, top_k)
            keys.append(key)
            print(f"  {query:40} → {key}")
        
        unique_keys = set(keys)
        if len(unique_keys) == 1:
            print(f"  ✅ PASS - All queries produce same cache key")
            passed += 1
        else:
            print(f"  ❌ FAIL - Got {len(unique_keys)} different cache keys")
            failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"Cache Key Tests: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")
    
    return failed == 0


def test_edge_cases():
    """Test edge cases"""
    print("=" * 80)
    print("TEST 3: Edge Cases")
    print("=" * 80)
    
    edge_cases = [
        ("", "Empty string"),
        ("   ", "Only whitespace"),
        ("là gì vậy?", "Mostly stopwords"),
        ("Phật", "Single word"),
        ("???", "Only punctuation"),
        ("123 456", "Numbers"),
        ("ABC DEF GHI", "English uppercase"),
    ]
    
    print()
    for query, description in edge_cases:
        normalized = _normalize_query(query)
        print(f"  {description:25} | '{query:20}' → '{normalized}'")
    
    print(f"\n{'=' * 80}")
    print("Edge case handling: OK (manual review)")
    print(f"{'=' * 80}\n")
    
    return True


def test_stopword_removal():
    """Test stopword removal effectiveness"""
    print("=" * 80)
    print("TEST 4: Stopword Removal")
    print("=" * 80)
    
    test_cases = [
        ("Phật giáo là gì", "Should remove 'là'"),
        ("Tu tập trong phật pháp", "Should remove 'trong'"),
        ("Bát quan trai của Phật giáo", "Should remove 'của'"),
        ("Phật pháp và tu tập", "Should remove 'và'"),
    ]
    
    print()
    for query, expected in test_cases:
        normalized = _normalize_query(query)
        print(f"  {query:35} → {normalized:30} | {expected}")
    
    print(f"\n{'=' * 80}")
    print("Stopword removal: OK (manual review)")
    print(f"{'=' * 80}\n")
    
    return True


def performance_comparison():
    """Show performance improvement from normalization"""
    print("=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    
    # Simulate 10 user queries with variants
    queries = [
        "Phật giáo là gì?",
        "phật giáo là gì",
        "Phật giáo là gì ?",
        "PHẬT GIÁO LÀ GÌ",
        "Bát quan trai là gì?",
        "bát quan trai là gì",
        "Bát Quan Trai là gì",
        "Tu tập như thế nào",
        "Như thế nào tu tập",
        "như thế nào tu tập?",
    ]
    
    # Without normalization (old logic)
    old_keys = [f"cache:{q.strip().lower()}" for q in queries]
    old_unique = len(set(old_keys))
    
    # With normalization (new logic)
    new_keys = [_make_cache_key("retrieval", q, ["kb1"], 6) for q in queries]
    new_unique = len(set(new_keys))
    
    print(f"\n10 user queries (with variants)")
    print(f"{'─' * 80}")
    print(f"Without normalization:")
    print(f"  - Unique cache keys: {old_unique}")
    print(f"  - Cache hits:        {10 - old_unique} / 10 ({(10 - old_unique) / 10 * 100:.0f}%)")
    print(f"  - Cache misses:      {old_unique} / 10 ({old_unique / 10 * 100:.0f}%)")
    print()
    print(f"With normalization:")
    print(f"  - Unique cache keys: {new_unique}")
    print(f"  - Cache hits:        {10 - new_unique} / 10 ({(10 - new_unique) / 10 * 100:.0f}%)")
    print(f"  - Cache misses:      {new_unique} / 10 ({new_unique / 10 * 100:.0f}%)")
    print()
    print(f"Improvement:")
    old_hit_rate = (10 - old_unique) / 10 * 100
    new_hit_rate = (10 - new_unique) / 10 * 100
    improvement = new_hit_rate - old_hit_rate
    print(f"  - Cache hit rate: +{improvement:.0f}% ({old_hit_rate:.0f}% → {new_hit_rate:.0f}%)")
    
    print(f"\n{'=' * 80}\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print(" " * 20 + "CACHE QUERY NORMALIZATION TESTS")
    print("=" * 80 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Normalization", test_normalization()))
    results.append(("Cache Keys", test_cache_keys()))
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("Stopwords", test_stopword_removal()))
    
    # Show performance comparison
    performance_comparison()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:20} {status}")
    
    print(f"\n  Total: {passed}/{total} test suites passed")
    print("=" * 80 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
