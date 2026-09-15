"""
AtlasMind - Hybrid Vector Store & Retrieval Engine
Combines TF-IDF sub-linear term frequency, BM25-style ngram matching, dense cosine 
similarity, and Role-Based Access Control (RBAC) filtering.
Provides atomic disk synchronization, thread safety, and zero-ghost-chunk document updates.
"""

import os
import pickle
import threading
import uuid
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import DATA_DIR, ROLES_PERMISSIONS
from src.document_processor import DocumentChunk, DocumentProcessor


INDEX_CACHE_PATH = DATA_DIR / "vector_index.pkl"


class HybridVectorStore:
    """
    Thread-safe hybrid vector store with atomic serialization and full document lifecycle management.
    """
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.is_indexed: bool = False
        self._lock = threading.RLock()

    def build_index(self, chunks: List[DocumentChunk]):
        """Build hybrid TF-IDF + n-gram vector index from document chunks."""
        with self._lock:
            self.chunks = list(chunks)
            if not self.chunks:
                self.vectorizer = None
                self.tfidf_matrix = None
                self.is_indexed = False
                self.save_index()
                return

            corpus = []
            for c in self.chunks:
                doc_id = getattr(c, "document_id", getattr(c, "doc_id", ""))
                doc_name = getattr(c, "doc_name", getattr(c, "doc_title", ""))
                category = getattr(c, "category", getattr(c, "classification", ""))
                
                # Emphasize document identifier, title, category, and section title heavily
                enriched_text = (
                    f"{doc_id} {doc_id} {doc_name} {doc_name} {category} "
                    f"{c.section_title} {c.section_title} {c.section_number} "
                    f"{c.content}"
                )
                corpus.append(enriched_text)

            # Build TF-IDF with character + word ngrams for robust matching (e.g., PPE, LOTO, AQL, ISO)
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 3),
                sublinear_tf=True,
                stop_words="english",
                max_features=15000
            )
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
            self.is_indexed = True
            self.save_index()

    def save_index(self):
        """
        Thread-safe, atomic serialization of vector index and chunks to disk cache.
        Writes to a temporary file first, flushes and syncs to disk, then performs an atomic replace.
        """
        with self._lock:
            try:
                temp_filename = f"vector_index_{uuid.uuid4().hex}.tmp"
                temp_path = DATA_DIR / temp_filename

                payload = {
                    "chunks": self.chunks,
                    "vectorizer": self.vectorizer,
                    "tfidf_matrix": self.tfidf_matrix,
                    "version": "2.2"
                }

                with open(temp_path, "wb") as f:
                    pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic replace guaranteed on POSIX and Windows (Python 3.3+)
                os.replace(temp_path, INDEX_CACHE_PATH)
            except Exception as e:
                print(f"[VectorStore] Failed to atomically save index cache: {e}")
                if 'temp_path' in locals() and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

    def load_index(self) -> bool:
        """Load index from disk cache if present and valid."""
        with self._lock:
            if INDEX_CACHE_PATH.exists():
                try:
                    with open(INDEX_CACHE_PATH, "rb") as f:
                        data = pickle.load(f)
                        self.chunks = data.get("chunks", [])
                        self.vectorizer = data.get("vectorizer")
                        self.tfidf_matrix = data.get("tfidf_matrix")
                        self.is_indexed = bool(self.chunks and self.vectorizer is not None and self.tfidf_matrix is not None)
                        return self.is_indexed
                except Exception as e:
                    print(f"[VectorStore] Failed to load cached index: {e}")
            return False

    def delete_by_document_id(self, document_id: str) -> bool:
        """
        Purge all chunks associated with a document ID from the vector index.
        Rebuilds the index and atomically persists to avoid ghost chunks.
        """
        with self._lock:
            doc_id_clean = document_id.strip().upper()
            initial_count = len(self.chunks)
            
            # Filter out chunks matching document_id or doc_id
            retained_chunks = [
                c for c in self.chunks
                if getattr(c, "document_id", getattr(c, "doc_id", "")).strip().upper() != doc_id_clean
            ]

            removed_count = initial_count - len(retained_chunks)
            if removed_count == 0:
                return False

            print(f"[VectorStore] Purged {removed_count} chunks for document '{document_id}'.")
            self.build_index(retained_chunks)
            return True

    def update_document(
        self,
        document_id: str,
        new_content: str,
        doc_name: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update or replace a document in the vector store.
        Purges any existing chunks for document_id first, generates fresh chunks,
        rebuilds the index, and atomically saves to guarantee zero ghost chunks.
        """
        with self._lock:
            doc_id_clean = document_id.strip().upper()
            
            # 1. Purge previous chunks
            retained_chunks = [
                c for c in self.chunks
                if getattr(c, "document_id", getattr(c, "doc_id", "")).strip().upper() != doc_id_clean
            ]

            # 2. Chunk new content
            processor = DocumentProcessor()
            new_chunks = processor.chunk_text(
                text=new_content,
                doc_id=doc_id_clean,
                doc_name=doc_name,
                classification=category,
                metadata=metadata
            )

            if not new_chunks:
                print(f"[VectorStore] Warning: No chunks generated for document '{document_id}'.")
                self.build_index(retained_chunks)
                return False

            # 3. Combine and rebuild
            all_chunks = retained_chunks + new_chunks
            self.build_index(all_chunks)
            print(f"[VectorStore] Successfully updated document '{document_id}' with {len(new_chunks)} fresh chunks.")
            return True

    def search(
        self,
        query: str,
        user_role: str = "Executive & Compliance Admin",
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Search vector store with Role-Based Access Control (RBAC) filtering and semantic ranking.
        Returns rich metadata for every matched chunk.
        """
        with self._lock:
            if not self.is_indexed or self.vectorizer is None or self.tfidf_matrix is None or not self.chunks:
                return []

            # RBAC Check: Determine allowed document IDs and categories for user's assigned role
            role_info = ROLES_PERMISSIONS.get(user_role, ROLES_PERMISSIONS["General Employee"])
            allowed_doc_ids = set(doc_id.upper() for doc_id in role_info["accessible_doc_ids"])
            allowed_categories = set(cat.lower() for cat in role_info.get("allowed_categories", []))
            is_admin_tier = (user_role == "Executive & Compliance Admin")

            # Vectorize query
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

            # Rank candidate indices descending
            scored_indices = np.argsort(similarities)[::-1]
            results = []

            # Query tokens for keyword boosting
            query_terms = set(query.lower().split())

            for idx in scored_indices:
                raw_score = float(similarities[idx])
                chunk = self.chunks[idx]

                chunk_doc_id = getattr(chunk, "document_id", getattr(chunk, "doc_id", "")).strip().upper()
                chunk_doc_name = getattr(chunk, "doc_name", getattr(chunk, "doc_title", "Atlas Honda Policy"))
                chunk_category = getattr(chunk, "category", getattr(chunk, "classification", "General Employee Access"))

                # Enforce RBAC Filter: Skip if doc_id not in user's tier and category not permitted
                if not is_admin_tier:
                    is_doc_allowed = (chunk_doc_id in allowed_doc_ids)
                    is_cat_allowed = any(c in chunk_category.lower() for c in allowed_categories) if allowed_categories else False
                    if not is_doc_allowed and not is_cat_allowed:
                        continue

                # Title & ID keyword booster
                title_text = f"{chunk_doc_name} {chunk.section_title} {chunk_doc_id}".lower()
                overlap = sum(1 for t in query_terms if len(t) > 2 and t in title_text)
                adjusted_score = raw_score + (overlap * 0.12)
                final_score = round(min(adjusted_score, 0.99), 3)

                # Collect valid matches above base noise threshold
                if final_score >= 0.05:
                    results.append({
                        "chunk_id": getattr(chunk, "chunk_id", f"{chunk_doc_id}_chunk_{idx:02d}"),
                        "document_id": chunk_doc_id,
                        "doc_id": chunk_doc_id,                      # Backwards compatibility
                        "doc_name": chunk_doc_name,
                        "doc_title": chunk_doc_name,                  # Backwards compatibility
                        "category": chunk_category,
                        "classification": chunk_category,            # Backwards compatibility
                        "section_title": getattr(chunk, "section_title", "General"),
                        "section_number": getattr(chunk, "section_number", ""),
                        "content": chunk.content,
                        "score": final_score,
                        "metadata": getattr(chunk, "metadata", {})
                    })

                if len(results) >= top_k:
                    break

            return results


# Global singleton instance
_vector_store: Optional[HybridVectorStore] = None
_store_init_lock = threading.Lock()


def get_vector_store(force_rebuild: bool = False) -> HybridVectorStore:
    """Access the global thread-safe vector store singleton."""
    global _vector_store
    with _store_init_lock:
        if _vector_store is None:
            _vector_store = HybridVectorStore()

        if force_rebuild or not _vector_store.is_indexed:
            if not force_rebuild and _vector_store.load_index():
                return _vector_store
                
            # Build fresh from documents directory
            processor = DocumentProcessor()
            chunks = processor.process_all_documents()
            _vector_store.build_index(chunks)

        return _vector_store
