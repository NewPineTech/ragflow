Based on the provided document or chat history, identify which sentences in the generated answer require citations according to the rules below.

# Citation Rules:

## General Principle:
- **Do NOT insert or display any citation markers (like [ID:x]) inside the answer text.**
- Instead, generate a clean, natural-language answer, and internally associate the relevant IDs for each factual statement in the reference output (not in the answer itself).

## Technical Rules:
- Never place citations inside or after the answer text.
- Keep the answer clean and natural.
- Record citation mappings separately in the reference data.
- Maximum 4 citations per sentence.
- DO NOT cite content not from <context></context>.
- DO NOT modify or rewrite the user’s input text.
- STRICTLY prohibit non-standard formatting (~~, [], (), {}, etc.) in the answer.
- The answer must not include any tokens like [ID:x], [ID:x][ID:y], or numeric footnotes.
- You may still record which sources support which statements, but only in the "reference" metadata.

## What MUST Be Cited:
1. **Quantitative data** – numbers, percentages, statistics, measurements.
2. **Temporal claims** – dates, timeframes, or sequences of events.
3. **Causal relationships** – cause–effect statements.
4. **Comparative statements** – rankings, comparisons, superlatives.
5. **Technical definitions** – specialized terms or methodologies.
6. **Direct attributions** – what someone said, did, or believes.
7. **Predictions or forecasts** – future projections or trends.
8. **Controversial or disputed facts**.

## What Should NOT Be Cited:
- Common knowledge (e.g., "The sun rises in the east").
- Transitional or stylistic phrases.
- General introductions.
- Your own synthesis or reasoning not directly from the context.

## Output Guideline:
- Produce a fluent, natural-language answer with no visible citation markers.
- Ensure that citation information is available only in the backend reference field.
- Each sentence in the answer that meets the citation requirements must be mapped to its source IDs internally, **not inline**.
