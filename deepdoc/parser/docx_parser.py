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

import logging  # Fix #6: add missing logging import
import re
from collections import Counter
from io import BytesIO

import pandas as pd
from docx import Document

from rag.nlp import rag_tokenizer


class RAGFlowDocxParser:

    # Fix #1: replace magic 100000000 with a named sentinel
    _MAX_PAGE = 10_000_000

    def __extract_table_content(self, tb):
        df = []
        for row in tb.rows:
            # Fix #5: python-docx repeats the same cell object for merged cells;
            # deduplicate by object identity to avoid duplicate column values.
            seen = set()
            cells = []
            for c in row.cells:
                if id(c) not in seen:
                    seen.add(id(c))
                    cells.append(c.text)
            df.append(cells)
        return self.__compose_table_content(pd.DataFrame(df))

    def __compose_table_content(self, df):

        def blockType(b):
            pattern = [
                ("^(20|19)[0-9]{2}[年/-][0-9]{1,2}[月/-][0-9]{1,2}日*$", "Dt"),
                (r"^(20|19)[0-9]{2}年$", "Dt"),
                (r"^(20|19)[0-9]{2}[年/-][0-9]{1,2}月*$", "Dt"),
                ("^[0-9]{1,2}[月/-][0-9]{1,2}日*$", "Dt"),
                (r"^第*[一二三四1-4]季度$", "Dt"),
                (r"^(20|19)[0-9]{2}年*[一二三四1-4]季度$", "Dt"),
                (r"^(20|19)[0-9]{2}[ABCDE]$", "DT"),
                ("^[0-9.,+%/ -]+$", "Nu"),
                (r"^[0-9A-Z/\._~-]+$", "Ca"),
                (r"^[A-Z]*[a-z' -]+$", "En"),
                (r"^[0-9.,+-]+[0-9A-Za-z/$￥%<>（）()' -]+$", "NE"),
                (r"^.{1}$", "Sg")
            ]
            for p, n in pattern:
                if re.search(p, b):
                    return n
            tks = [t for t in rag_tokenizer.tokenize(b).split() if len(t) > 1]
            if len(tks) > 3:
                if len(tks) < 12:
                    return "Tx"
                else:
                    return "Lx"

            if len(tks) == 1 and rag_tokenizer.tag(tks[0]) == "nr":
                return "Nr"

            return "Ot"

        # Fix #4: log visibly instead of silently returning when table is too small
        if len(df) < 2:
            logging.debug("Table has fewer than 2 rows; skipping content composition.")
            return []

        max_type = Counter([blockType(str(df.iloc[i, j])) for i in range(
            1, len(df)) for j in range(len(df.iloc[i, :]))])
        max_type = max(max_type.items(), key=lambda x: x[1])[0]

        colnm = len(df.iloc[0, :])
        hdrows = [0]  # header is not necessarily appear in the first line
        if max_type == "Nu":
            for r in range(1, len(df)):
                tys = Counter([blockType(str(df.iloc[r, j]))
                              for j in range(len(df.iloc[r, :]))])
                tys = max(tys.items(), key=lambda x: x[1])[0]
                if tys != max_type:
                    hdrows.append(r)

        lines = []
        for i in range(1, len(df)):
            if i in hdrows:
                continue
            hr = [r - i for r in hdrows]
            hr = [r for r in hr if r < 0]
            t = len(hr) - 1
            while t > 0:
                if hr[t] - hr[t - 1] > 1:
                    hr = hr[t:]
                    break
                t -= 1
            headers = []
            for j in range(len(df.iloc[i, :])):
                t = []
                for h in hr:
                    x = str(df.iloc[i + h, j]).strip()
                    if x in t:
                        continue
                    t.append(x)
                t = ",".join(t)
                if t:
                    t += ": "
                headers.append(t)
            cells = []
            for j in range(len(df.iloc[i, :])):
                if not str(df.iloc[i, j]):
                    continue
                cells.append(headers[j] + str(df.iloc[i, j]))
            lines.append(";".join(cells))

        if colnm > 3:
            return lines
        return ["\n".join(lines)]

    def __call__(self, fnm, from_page=0, to_page=None):
        # Fix #1: use named sentinel instead of magic number
        to_page = self._MAX_PAGE if to_page is None else to_page

        self.doc = Document(fnm) if isinstance(fnm, str) else Document(BytesIO(fnm))
        pn = 0  # current page index (0-based)
        secs = []  # parsed (text, style) pairs

        for p in self.doc.paragraphs:
            if pn > to_page:
                break

            runs_within_single_paragraph = []
            for run in p.runs:
                # Fix #1 (Bug A): increment page counter BEFORE the range check
                # so pn reflects the correct page when we decide to include text.
                if 'lastRenderedPageBreak' in run._element.xml:
                    pn += 1

                if from_page <= pn <= to_page and p.text.strip():
                    runs_within_single_paragraph.append(run.text)

            # Fix #2: if runs produced no text but p.text has content
            # (e.g. field-only paragraphs, inline images with alt-text),
            # fall back to p.text so content is not silently lost.
            text = "".join(runs_within_single_paragraph)
            if not text and p.text.strip() and from_page <= pn <= to_page:
                text = p.text

            style = p.style.name if hasattr(p.style, 'name') else ''
            secs.append((text, style))

        # Fix #3: catch per-table errors so one bad table doesn't abort the parse
        tbls = []
        for tb in self.doc.tables:
            try:
                tbls.append(self.__extract_table_content(tb))
            except Exception as e:
                logging.warning(f"Skipping malformed table: {e}")
                tbls.append([])

        return secs, tbls
