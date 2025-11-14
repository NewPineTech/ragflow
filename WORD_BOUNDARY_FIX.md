# Word Boundary Fix for Vietnamese Streaming

**Issue:** User reported "con muốn" bị cắt thành "con mu" + "ốn" (sai tiếng Việt)

**Date:** November 14, 2025

---

## 🐛 Problem

### Original Early Flush Logic:
```python
# BAD: Flush at 5 chars OR any space
if len(delta_text) >= 5 or ' ' in delta_text:
    first_chunk_sent = True
    return True
```

### Result:
```
❌ "Con muốn tìm hiểu"
   └─> Chunk 1: "Con mu"     (5 chars, cuts mid-word!)
   └─> Chunk 2: "ốn tìm hiểu" (broken word)
```

**Why bad:**
- ❌ Cuts Vietnamese words with diacritics ("muốn" → "mu" + "ốn")
- ❌ Arbitrary 5-char limit doesn't respect word boundaries
- ❌ Poor UX: users see broken words

---

## ✅ Solution

### New Early Flush Logic (Word-Aware):
```python
# GOOD: Flush at word boundary (space) only
if delta_text.rstrip() != delta_text:  # Has trailing space
    words = delta_text.strip().split()
    if len(words) >= 1 and len(words[0]) >= 3:  # At least 1 meaningful word
        first_chunk_sent = True
        return True
```

### Result:
```
✅ "Con muốn tìm hiểu"
   └─> Chunk 1: "Con "          (complete word!)
   └─> Chunk 2: "muốn tìm hiểu" (no breaking)
```

**Why good:**
- ✅ Respects word boundaries (wait for space)
- ✅ No mid-word cutting
- ✅ Preserves Vietnamese diacritics
- ✅ Minimum 3 chars (avoid "Ơi ", "À ")

---

## 🧪 Test Results

### Test 1: "Con muốn tìm hiểu"
```
✅ Chunk 1: "Con "          [early_flush]
✅ Chunk 2: "muốn tìm hiểu" [final]

NO MORE: "Con mu" + "ốn"  ← Fixed!
```

### Test 2: "Phật giáo là tôn giáo."
```
✅ Chunk 1: "Phật "              [early_flush]
✅ Chunk 2: "giáo là tôn giáo."  [sentence]

Clean word boundaries throughout
```

### Test 3: "Vâng, thầy sẽ giảng giải"
```
✅ Chunk 1: "Vâng, "              [early_flush]
✅ Chunk 2: "thầy sẽ giảng giải" [final]

Comma preserved with word
```

### Test 4: Edge case "Ơi "
```
✅ Chunk 1: "Ơi " [final]

Correctly skipped early flush (only 2 chars)
Minimum 3 chars required
```

---

## 📊 Comparison

| Aspect | Before | After |
|--------|--------|-------|
| **Detection** | 5 chars OR space | Space only |
| **Word cutting** | ❌ Yes ("mu"+"ốn") | ✅ No |
| **Minimum length** | 5 chars fixed | 3 chars + space |
| **Diacritics** | ⚠️ Sometimes broken | ✅ Preserved |
| **UX** | Choppy | Smooth |

---

## 🎯 Key Principles

### 1. **Wait for Space**
```python
if delta_text.rstrip() != delta_text:  # Must end with space
```
- Only flush at word boundaries
- Prevents mid-word cuts

### 2. **Minimum Word Length**
```python
if len(words[0]) >= 3:  # At least 3 chars
```
- Avoid flushing "À ", "Ơi " (interjections)
- Most Vietnamese words: 3-10+ chars

### 3. **Preserve Diacritics**
```python
words = delta_text.strip().split()  # UTF-8 aware
```
- Works with á, ă, â, é, ê, í, ó, ô, ơ, ú, ư, ý
- Unicode-safe string operations

### 4. **First Complete Word**
```python
if len(words) >= 1:  # At least 1 complete word
```
- Flush as soon as first word completes
- Balance speed vs correctness

---

## 🔧 Code Changes

**File:** `api/db/services/dialog_service.py`

**Lines:** ~787-798

**Before:**
```python
if not first_chunk_sent and len(delta_text.strip()) > 0:
    if len(delta_text) >= 5 or ' ' in delta_text:
        first_chunk_sent = True
        return True
```

**After:**
```python
if not first_chunk_sent and len(delta_text.strip()) > 0:
    if delta_text.rstrip() != delta_text:  # Has trailing space
        words = delta_text.strip().split()
        if len(words) >= 1 and len(words[0]) >= 3:
            first_chunk_sent = True
            return True
```

**Impact:**
- ✅ No more mid-word cuts
- ✅ Better Vietnamese support
- ✅ Cleaner streaming UX

---

## 📝 Examples

### Vietnamese Words Preserved:
```
✅ "Phật" (4 chars)    → Wait for space
✅ "Phật " (5 chars)   → FLUSH (complete)
✅ "muốn" (4 chars)    → Wait for space  
✅ "muốn " (5 chars)   → FLUSH (complete)
✅ "giác" (4 chars)    → Wait for space
✅ "giác " (5 chars)   → FLUSH (complete)
```

### Edge Cases Handled:
```
✅ "Con" (3 chars)     → Wait for space
✅ "Con " (4 chars)    → FLUSH ✓
❌ "Ơi" (2 chars)      → Too short
❌ "Ơi " (3 chars)     → Skip (< 3 chars before space)
✅ "Vâng" (4 chars)    → Wait for space
✅ "Vâng " (5 chars)   → FLUSH ✓
```

---

## ✅ Verification

**Test file:** `test_word_boundary.py`

**Run:**
```bash
python3 test_word_boundary.py
```

**Expected:**
- ✅ No mid-word cuts
- ✅ All words complete
- ✅ Diacritics preserved
- ✅ Minimum 3-char words

---

## 🎓 Lessons Learned

1. **Never cut mid-word** - Wait for natural boundaries
2. **Language-aware** - Vietnamese words need diacritics
3. **Minimum length** - Filter out single-letter interjections
4. **UTF-8 safety** - Use proper string operations
5. **Test edge cases** - Short words, long words, special chars

---

## 🚀 Status

**Issue:** ✅ Fixed  
**Testing:** ✅ Verified  
**Documentation:** ✅ Complete  
**Production:** ✅ Ready

**No more broken Vietnamese words in streaming!** 🎉
