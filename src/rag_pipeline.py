"""
AtlasMind - RAG Pipeline & Conversational Coordinator
Integrates Multilingual Query Expansion, Hybrid Vector Retrieval, Role-Based Access Control,
Confidence Guardrails, Strict Fallback Handling, and Audit Logging.
"""

import time
import uuid
from typing import List, Dict, Any, Optional

from src.config import CONFIDENCE_THRESHOLD, DEBUG_RETRIEVAL
from src.vector_store import get_vector_store
from src.llm_engine import UnifiedLLMEngine, rewrite_query_for_retrieval, detect_language, strip_roman_urdu_stopwords
from src.db import log_query, log_unanswered_query


# Graceful rejection messages when best similarity score falls below threshold
FALLBACK_MESSAGES = {
    "English": (
        "I could not locate official policy guidance addressing this specific inquiry within approved Atlas Honda documents "
        "(Match confidence score fell below threshold). To avoid inaccurate guidance, please consult your **Line Manager**, "
        "**Human Resources Department**, or the **HSE Safety Officer** for official clarification."
    ),
    "Roman Urdu": (
        "Atlas Honda ki official policy documents mein is specific sawaal ke mutabiq koi official guidance nahi mili "
        "(Match confidence threshold se kam hai). Ghair-tasdeeq shuda maloomat se bachne ke liye, barah-e-karam apne **Line Manager**, "
        "**HR Department**, ya **HSE Officer** se rabta karein."
    ),
    "اردو (Urdu Script)": (
        "اٹلس ہونڈا لمیٹڈ کی باضابطہ دستاویزات میں اس مخصوص سوال سے متعلق کوئی مصدقہ پالیسی رہنمائی نہیں ملی "
        "(میچ اسکور حد سے کم ہے)۔ غیر مصدقہ معلومات سے بچنے کے لیے براہ کرم اپنے **لائن منیجر**، **ہیومن ریسورسز ڈیپارٹمنٹ**، "
        "یا **ایچ ایس ای آفیسر** سے باضابطہ رہنمائی حاصل فرمائیں۔"
    )
}


class RAGPipeline:
    """
    Enterprise RAG pipeline enforcing strict grounding, pre-retrieval rewriting,
    confidence thresholding, and unanswered query tracking.
    """
    def __init__(self):
        self.vector_store = get_vector_store()
        self.llm_engine = UnifiedLLMEngine()

    def query(
        self, 
        query_text: str, 
        session_id: str, 
        user_role: str = "General Employee",
        language: str = "English",
        llm_provider: str = "Local Fallback Engine (Zero API Keys)",
        history: Optional[List[Dict[str, str]]] = None,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        confidence_threshold: float = CONFIDENCE_THRESHOLD
    ) -> Dict[str, Any]:
        """
        Execute complete RAG flow:
        1. Multilingual / Roman Urdu Query Expansion & Context Resolution
        2. RBAC Vector Retrieval
        3. Confidence Score Threshold Guardrail
        4. Tone-Preserving LLM Generation or Strict Fallback
        5. Audit Logging (to query_logs and unanswered_queries if low confidence)
        """
        start_time = time.time()
        
        # Determine actual user language tone (if user left it as default or user query strongly signals Roman Urdu/Urdu)
        actual_tone = language
        detected = detect_language(query_text)
        if language == "English" and detected in ["Roman Urdu", "اردو (Urdu Script)"]:
            actual_tone = detected
        elif "Roman" in language:
            actual_tone = "Roman Urdu"
        elif "Urdu" in language and "Roman" not in language:
            actual_tone = "اردو (Urdu Script)"

        # 1. Pre-retrieval Query Expansion: Convert Roman Urdu / conversational slang to crisp English keywords
        search_query = rewrite_query_for_retrieval(
            user_query=query_text,
            history=history or [],
            llm_engine=self.llm_engine,
            provider=llm_provider,
            gemini_api_key=gemini_api_key,
            groq_api_key=groq_api_key
        )
        # Strip any lingering Roman Urdu non-content stopwords to guarantee zero vector dilution
        search_query = strip_roman_urdu_stopwords(search_query) or search_query
        
        # 2. Vector Retrieval with RBAC Filter
        retrieved_chunks = self.vector_store.search(
            query=search_query,
            user_role=user_role,
            top_k=4
        )
        
        # 3. Inspect Top Similarity Score & Enforce Strict Confidence Guardrail
        best_score = float(retrieved_chunks[0]["score"]) if retrieved_chunks else 0.0
        is_below_confidence = (best_score < confidence_threshold)
        
        # Terminal score debug output for tuning
        if DEBUG_RETRIEVAL:
            status_str = "CONFIDENT" if not is_below_confidence else "LOW_CONFIDENCE_FALLBACK"
            print(f"[RAG Retrieval Debug] Query: '{query_text}' | Rewritten: '{search_query}' | Best Score: {best_score:.3f} | Threshold: {confidence_threshold:.2f} | Status: {status_str}")
        
        if is_below_confidence:
            # DO NOT hallucinate an answer. Log to unanswered_queries and return graceful fallback
            answer_text = FALLBACK_MESSAGES.get(actual_tone, FALLBACK_MESSAGES["English"])
            
            # Record in unanswered_queries table for executive governance and HR gap analysis
            log_unanswered_query(
                query=query_text,
                user_role=user_role,
                language=actual_tone,
                best_score=best_score
            )
            citations = []
        else:
            # 4. Confident Retrieval: Generate grounded response preserving user's language tone
            answer_text = self.llm_engine.generate(
                query=query_text,
                context_chunks=retrieved_chunks,
                provider=llm_provider,
                language=actual_tone,
                gemini_api_key=gemini_api_key,
                groq_api_key=groq_api_key
            )
            
            # Format clean citation cards
            citations = []
            for c in retrieved_chunks:
                doc_id = c.get("document_id", c.get("doc_id", "DOC"))
                doc_name = c.get("doc_name", c.get("doc_title", "Atlas Honda Policy"))
                citations.append({
                    "chunk_id": c.get("chunk_id", ""),
                    "document_id": doc_id,
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "doc_title": doc_name,
                    "section_title": c.get("section_title", "General"),
                    "section_number": c.get("section_number", ""),
                    "classification": c.get("category", c.get("classification", "General Employee Access")),
                    "score": round(float(c.get("score", 0.0)), 2),
                    "content_snippet": c["content"][:400] + "..." if len(c["content"]) > 400 else c["content"]
                })
        
        latency_ms = max(int((time.time() - start_time) * 1000), 2)
        
        # 5. Database Audit Logging
        log_id = log_query(
            session_id=session_id,
            user_role=user_role,
            language=actual_tone,
            query_text=query_text,
            response_text=answer_text,
            sources=citations,
            latency_ms=latency_ms,
            llm_provider=llm_provider
        )
        
        return {
            "query_log_id": log_id,
            "answer": answer_text,
            "citations": citations,
            "latency_ms": latency_ms,
            "resolved_query": search_query,
            "session_id": session_id,
            "best_score": best_score,
            "is_unanswered": is_below_confidence,
            "language_used": actual_tone
        }
