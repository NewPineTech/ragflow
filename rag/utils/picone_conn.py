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

import logging
import re
import json
import time
import os

import copy
from pinecone import Pinecone, ServerlessSpec
from rag import settings
from rag.settings import TAG_FLD, PAGERANK_FLD
from common.decorator import singleton
from common.file_utils import get_project_base_directory
from rag.utils.doc_store_conn import DocStoreConnection, MatchExpr, OrderByExpr, MatchTextExpr, MatchDenseExpr, \
    FusionExpr
from rag.nlp import is_english, rag_tokenizer

ATTEMPT_TIME = 2

logger = logging.getLogger('ragflow.picone_conn')


@singleton
class PICOneConnection(DocStoreConnection):
    def __init__(self):
        self.info = {}
        api_key = settings.PINECONE.get("api_key") if hasattr(settings, "PINECONE") else os.getenv("PINECONE_API_KEY")
        
        if not api_key:
            msg = "Pinecone API key not found in settings.PINECONE['api_key'] or PINECONE_API_KEY env variable"
            logger.error(msg)
            raise Exception(msg)
        
        logger.info(f"Connecting to Pinecone...")
        for _ in range(ATTEMPT_TIME):
            try:
                self.pc = Pinecone(api_key=api_key)
                self.info = {"version": {"number": "1.0.0"}, "type": "pinecone"}
                logger.info(f"Pinecone connection established successfully.")
                break
            except Exception as e:
                logger.warning(f"{str(e)}. Retrying Pinecone connection...")
                time.sleep(5)
        
        if not hasattr(self, 'pc') or self.pc is None:
            msg = f"Pinecone connection failed after {ATTEMPT_TIME} attempts."
            logger.error(msg)
            raise Exception(msg)
        
        # Store metadata mapping configuration
        self.metadata_config = {
            "indexed": ["kb_id", "doc_id", "available_int"]  # Filterable fields
        }
        logger.info(f"Pinecone is ready.")

    """
    Database operations
    """

    def dbType(self) -> str:
        return "pinecone"

    def health(self) -> dict:
        try:
            indexes = self.pc.list_indexes()
            return {
                "status": "healthy",
                "type": "pinecone",
                "indexes": [idx.name for idx in indexes]
            }
        except Exception as e:
            logger.error(f"Pinecone health check failed: {str(e)}")
            return {"status": "unhealthy", "type": "pinecone", "error": str(e)}

    """
    Table operations
    """

    def createIdx(self, indexName: str, knowledgebaseId: str, vectorSize: int):
        if self.indexExist(indexName, knowledgebaseId):
            logger.info(f"Pinecone index {indexName} already exists.")
            return True
        try:
            # Create serverless index with specified dimension
            self.pc.create_index(
                name=indexName,
                dimension=vectorSize,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=settings.PINECONE.get("cloud", "aws") if hasattr(settings, "PINECONE") else "aws",
                    region=settings.PINECONE.get("region", "us-east-1") if hasattr(settings, "PINECONE") else "us-east-1"
                )
            )
            logger.info(f"Created Pinecone index {indexName} with dimension {vectorSize}")
            return True
        except Exception as e:
            logger.exception(f"PineconeConnection.createIndex error {indexName}: {str(e)}")
            return False

    def deleteIdx(self, indexName: str, knowledgebaseId: str):
        if len(knowledgebaseId) > 0:
            # The index needs to be alive after any kb deletion since all kb under this tenant are in one index.
            logger.info(f"Skipping index deletion for {indexName} as knowledgebaseId is provided")
            return
        try:
            self.pc.delete_index(indexName)
            logger.info(f"Deleted Pinecone index {indexName}")
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(f"Index {indexName} not found, nothing to delete")
            else:
                logger.exception(f"PineconeConnection.deleteIdx error {indexName}")

    def indexExist(self, indexName: str, knowledgebaseId: str = None) -> bool:
        for i in range(ATTEMPT_TIME):
            try:
                indexes = self.pc.list_indexes()
                return any(idx.name == indexName for idx in indexes)
            except Exception as e:
                logger.exception("PineconeConnection.indexExist got exception")
                if "timeout" in str(e).lower():
                    continue
                break
        return False

    """
    CRUD operations
    """
    
    def _build_filter(self, condition: dict, knowledgebaseIds: list[str]) -> dict:
        """Build Pinecone filter from condition dict"""
        filter_dict = {}
        
        # Add knowledge base filter
        if knowledgebaseIds:
            filter_dict["kb_id"] = {"$in": knowledgebaseIds}
        
        for k, v in condition.items():
            if k == "kb_id":
                continue  # Already handled
            if k == "available_int":
                if v == 0:
                    filter_dict[k] = {"$lt": 1}
                else:
                    filter_dict[k] = {"$gte": 1}
            elif not v:
                continue
            elif isinstance(v, list):
                filter_dict[k] = {"$in": v}
            elif isinstance(v, (str, int)):
                filter_dict[k] = {"$eq": v}
        
        return filter_dict if filter_dict else None

    def search(
            self, selectFields: list[str],
            highlightFields: list[str],
            condition: dict,
            matchExprs: list[MatchExpr],
            orderBy: OrderByExpr,
            offset: int,
            limit: int,
            indexNames: str | list[str],
            knowledgebaseIds: list[str],
            aggFields: list[str] = [],
            rank_feature: dict | None = None
    ):
        """
        Pinecone vector search with metadata filtering
        """
        if isinstance(indexNames, str):
            indexNames = indexNames.split(",")
        assert isinstance(indexNames, list) and len(indexNames) > 0
        assert "_id" not in condition
        
        # Use first index (Pinecone doesn't support multi-index queries)
        indexName = indexNames[0]
        index = self.pc.Index(indexName)
        
        # Build filter
        filter_dict = self._build_filter(condition, knowledgebaseIds)
        
        # Extract vector search from matchExprs
        query_vector = None
        top_k = limit if limit > 0 else 10
        
        for m in matchExprs:
            if isinstance(m, MatchDenseExpr):
                query_vector = list(m.embedding_data)
                if m.topn:
                    top_k = m.topn
                break
        
        # Pinecone requires vector for search
        if query_vector is None:
            logger.warning("No vector provided for Pinecone search, returning empty results")
            return {
                "hits": {"total": {"value": 0}, "hits": []},
                "timed_out": False
            }
        
        logger.debug(f"PineconeConnection.search {indexName} filter: {json.dumps(filter_dict) if filter_dict else 'None'}")
        
        for i in range(ATTEMPT_TIME):
            try:
                # Perform Pinecone query
                results = index.query(
                    vector=query_vector,
                    top_k=top_k,
                    filter=filter_dict,
                    include_metadata=True
                )
                
                # Convert Pinecone response to OpenSearch-like format
                hits = []
                for match in results.get('matches', []):
                    hit = {
                        "_id": match['id'],
                        "_score": match.get('score', 0.0),
                        "_source": match.get('metadata', {})
                    }
                    hit["_source"]["id"] = match['id']
                    hits.append(hit)
                
                # Handle pagination with offset
                if offset > 0 and offset < len(hits):
                    hits = hits[offset:]
                elif offset >= len(hits):
                    hits = []
                
                res = {
                    "hits": {
                        "total": {"value": len(hits)},
                        "hits": hits
                    },
                    "timed_out": False
                }
                
                logger.debug(f"PineconeConnection.search {indexName} returned {len(hits)} results")
                return res
                
            except Exception as e:
                logger.exception(f"PineconeConnection.search {indexName} got exception")
                if "timeout" in str(e).lower():
                    continue
                raise e
        
        logger.error(f"PineconeConnection.search timeout for {ATTEMPT_TIME} times!")
        raise Exception("PineconeConnection.search timeout.")

    def get(self, chunkId: str, indexName: str, knowledgebaseIds: list[str]) -> dict | None:
        for i in range(ATTEMPT_TIME):
            try:
                index = self.pc.Index(indexName)
                res = index.fetch(ids=[chunkId])
                
                if not res or 'vectors' not in res or chunkId not in res['vectors']:
                    return None
                
                vector_data = res['vectors'][chunkId]
                chunk = vector_data.get('metadata', {})
                chunk["id"] = chunkId
                return chunk
                
            except Exception as e:
                if "not found" in str(e).lower():
                    return None
                logger.exception(f"PineconeConnection.get({chunkId}) got exception")
                if "timeout" in str(e).lower():
                    continue
                raise e
        logger.error(f"PineconeConnection.get timeout for {ATTEMPT_TIME} times!")
        raise Exception("PineconeConnection.get timeout.")

    def insert(self, documents: list[dict], indexName: str, knowledgebaseId: str = None) -> list[str]:
        """
        Insert documents into Pinecone index
        Documents must have 'id' field and vector embedding field (e.g., 'q_vec' or 'a_vec')
        """
        index = self.pc.Index(indexName)
        
        vectors_to_upsert = []
        errors = []
        
        for d in documents:
            assert "_id" not in d
            assert "id" in d
            d_copy = copy.deepcopy(d)
            doc_id = d_copy.pop("id")
            
            # Extract vector - look for common vector field names
            vector = None
            vector_field = None
            for field in ['q_vec', 'a_vec', 'vector', 'embedding']:
                if field in d_copy:
                    vector = d_copy.pop(field)
                    vector_field = field
                    break
            
            if vector is None:
                errors.append(f"{doc_id}: No vector field found")
                continue
            
            # All remaining fields become metadata
            metadata = d_copy
            
            vectors_to_upsert.append({
                "id": doc_id,
                "values": vector,
                "metadata": metadata
            })
        
        # Batch upsert (Pinecone handles this efficiently)
        for _ in range(ATTEMPT_TIME):
            try:
                if vectors_to_upsert:
                    index.upsert(vectors=vectors_to_upsert, namespace="")
                return errors
            except Exception as e:
                logger.warning(f"PineconeConnection.insert got exception: {str(e)}")
                errors.append(str(e))
                if "timeout" in str(e).lower():
                    time.sleep(3)
                    continue
                break
        return errors

    def update(self, condition: dict, newValue: dict, indexName: str, knowledgebaseId: str) -> bool:
        doc = copy.deepcopy(newValue)
        doc.pop("id", None)
        if "id" in condition and isinstance(condition["id"], str):
            # update specific single document
            chunkId = condition["id"]
            for i in range(ATTEMPT_TIME):
                try:
                    self.os.update(index=indexName, id=chunkId, body={"doc":doc})
                    return True
                except Exception as e:
                    logger.exception(
                        f"OSConnection.update(index={indexName}, id={id}, doc={json.dumps(condition, ensure_ascii=False)}) got exception")
                    if re.search(r"(timeout|connection)", str(e).lower()):
                        continue
                    break
            return False

        # update unspecific maybe-multiple documents
        bqry = Q("bool")
        for k, v in condition.items():
            if not isinstance(k, str) or not v:
                continue
            if k == "exists":
                bqry.filter.append(Q("exists", field=v))
                continue
            if isinstance(v, list):
                bqry.filter.append(Q("terms", **{k: v}))
            elif isinstance(v, str) or isinstance(v, int):
                bqry.filter.append(Q("term", **{k: v}))
            else:
                raise Exception(
                    f"Condition `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str or list.")
        scripts = []
        params = {}
        for k, v in newValue.items():
            if k == "remove":
                if isinstance(v, str):
                    scripts.append(f"ctx._source.remove('{v}');")
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        scripts.append(f"int i=ctx._source.{kk}.indexOf(params.p_{kk});ctx._source.{kk}.remove(i);")
                        params[f"p_{kk}"] = vv
                continue
            if k == "add":
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        scripts.append(f"ctx._source.{kk}.add(params.pp_{kk});")
                        params[f"pp_{kk}"] = vv.strip()
                continue
            if (not isinstance(k, str) or not v) and k != "available_int":
                continue
            if isinstance(v, str):
                v = re.sub(r"(['\n\r]|\\.)", " ", v)
                params[f"pp_{k}"] = v
                scripts.append(f"ctx._source.{k}=params.pp_{k};")
            elif isinstance(v, int) or isinstance(v, float):
                scripts.append(f"ctx._source.{k}={v};")
            elif isinstance(v, list):
                scripts.append(f"ctx._source.{k}=params.pp_{k};")
                params[f"pp_{k}"] = json.dumps(v, ensure_ascii=False)
            else:
                raise Exception(
                    f"newValue `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str.")
        ubq = UpdateByQuery(
            index=indexName).using(
            self.os).query(bqry)
        ubq = ubq.script(source="".join(scripts), params=params)
        ubq = ubq.params(refresh=True)
        ubq = ubq.params(slices=5)
        ubq = ubq.params(conflicts="proceed")

        for _ in range(ATTEMPT_TIME):
            try:
                _ = ubq.execute()
                return True
            except Exception as e:
                logger.error("OSConnection.update got exception: " + str(e) + "\n".join(scripts))
                if re.search(r"(timeout|connection|conflict)", str(e).lower()):
                    continue
                break
        return False

    def delete(self, condition: dict, indexName: str, knowledgebaseId: str) -> int:
        """Delete documents from Pinecone by ID list or by metadata filter."""
        index = self.pc.Index(indexName)
        
        for _ in range(ATTEMPT_TIME):
            try:
                if "id" in condition:
                    chunk_ids = condition["id"]
                    if not isinstance(chunk_ids, list):
                        chunk_ids = [chunk_ids]
                    
                    if not chunk_ids:
                        # Delete all - use delete with filter
                        index.delete(delete_all=True, namespace="")
                        logger.info(f"PICOneConnection.delete: Deleted all from {indexName}")
                        return -1  # Can't get exact count
                    else:
                        # Delete by IDs
                        index.delete(ids=chunk_ids)
                        return len(chunk_ids)
                else:
                    # Delete by metadata filter
                    filter_dict = self._build_filter(condition, [knowledgebaseId] if knowledgebaseId else [])
                    if filter_dict:
                        index.delete(filter=filter_dict)
                        logger.info(f"PICOneConnection.delete: Deleted with filter {filter_dict}")
                        return -1  # Pinecone doesn't return count for filter deletes
                    else:
                        logger.warning("PICOneConnection.delete: Empty filter, refusing to delete all")
                        return 0
            except Exception as e:
                logger.warning("PICOneConnection.delete got exception: " + str(e))
                if re.search(r"(timeout|connection)", str(e).lower()):
                    time.sleep(3)
                    continue
                if re.search(r"(not_found)", str(e), re.IGNORECASE):
                    return 0
        return 0

    """
    Helper functions for search result
    """

    def getTotal(self, res):
        """Get total count from search result."""
        if isinstance(res["hits"]["total"], type({})):
            return res["hits"]["total"]["value"]
        return res["hits"]["total"]

    def getChunkIds(self, res):
        """Extract document IDs from search result."""
        return [d["_id"] for d in res["hits"]["hits"]]

    def __getSource(self, res):
        """Extract _source with id and _score fields."""
        rr = []
        for d in res["hits"]["hits"]:
            d["_source"]["id"] = d["_id"]
            d["_source"]["_score"] = d["_score"]
            rr.append(d["_source"])
        return rr

    def getFields(self, res, fields: list[str]) -> dict[str, dict]:
        """Extract specific fields from search result."""
        res_fields = {}
        if not fields:
            return {}
        for d in self.__getSource(res):
            m = {n: d.get(n) for n in fields if d.get(n) is not None}
            for n, v in m.items():
                if isinstance(v, list):
                    m[n] = v
                    continue
                if not isinstance(v, str):
                    m[n] = str(m[n])

            if m:
                res_fields[d["id"]] = m
        return res_fields

    def getHighlight(self, res, keywords: list[str], fieldnm: str):
        """Get highlights for keywords. Not supported in Pinecone - returns empty dict."""
        logger.warning("PICOneConnection.getHighlight: Highlighting not supported in Pinecone")
        return {}

    def getAggregation(self, res, fieldnm: str):
        """Get aggregation results. Not supported in Pinecone - returns empty list."""
        logger.warning("PICOneConnection.getAggregation: Aggregations not supported in Pinecone")
        return list()

    """
    SQL
    """

    def sql(self, sql: str, fetch_size: int, format: str):
        """Execute SQL query. Not supported in Pinecone - returns None."""
        logger.warning("PICOneConnection.sql: SQL queries not supported in Pinecone")
        return None
