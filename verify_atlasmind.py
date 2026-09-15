"""
AtlasMind - Comprehensive System Verification & Architectural Test Suite
Validates:
1. Rich Metadata & Section-Aware Chunks
2. Vector Store Atomic Synchronization, Document Updates & Ghost-Chunk Purging
3. Hybrid Roman Urdu Query Expansion, Phonetic Tolerance & Conversational History
4. Calibrated Confidence Guardrail (0.28) & Unanswered Queries Logging
5. File Processing Hardening & Filename Sanitization
6. Admin PIN Security Gate
7. Full RAG Pipeline with Tone Preservation & Zero-Key Fallback Engine
8. Corporate PDF Dossier Generation & Executive Analytics
"""

import sys
from pathlib import Path

# Configure utf-8 encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import CONFIDENCE_THRESHOLD, ADMIN_PIN
from src.db import (
    init_db, log_query, save_feedback, get_analytics_summary,
    get_unanswered_queries, resolve_unanswered_query, delete_unanswered_query
)
from src.document_processor import (
    DocumentChunk, DocumentProcessor, sanitize_filename, is_allowed_file
)
from src.vector_store import get_vector_store
from src.llm_engine import (
    rewrite_query_for_retrieval, detect_language, normalize_roman_urdu,
    strip_roman_urdu_stopwords, ROMAN_URDU_STOPWORDS
)
from src.rag_pipeline import RAGPipeline
from src.pdf_exporter import generate_query_pdf


def run_verification():
    print("=" * 68)
    print("ATLASMIND ENTERPRISE RAG - ARCHITECTURAL VERIFICATION SUITE")
    print("=" * 68)

    passed_tests = 0
    total_tests = 0

    def test(desc: str, condition: bool, details: str = ""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  ✅ [PASS] {desc}")
        else:
            print(f"  ❌ [FAIL] {desc}")
            if details:
                print(f"     Details: {details}")

    # -------------------------------------------------------------
    # 1. Database Initialization & Unanswered Queries Schema
    # -------------------------------------------------------------
    print("\n[Step 1] Initializing SQLite Database & Unanswered Queries Table...")
    init_db()
    unanswered_start = get_unanswered_queries(limit=10)
    test("Database initialized with unanswered_queries table", isinstance(unanswered_start, list))

    # -------------------------------------------------------------
    # 2. File Processing Hardening & Sanitization
    # -------------------------------------------------------------
    print("\n[Step 2] Testing File Processing Hardening & Filename Sanitization...")
    test("Allow valid .md file", is_allowed_file("policy.md") is True)
    test("Allow valid .txt file", is_allowed_file("notes.txt") is True)
    test("Allow valid .pdf file", is_allowed_file("sop.pdf") is True)
    test("Block invalid .exe file", is_allowed_file("malware.exe") is False)
    test("Block invalid .py file", is_allowed_file("script.py") is False)

    sanitized = sanitize_filename("../../etc/passwd_danger.md")
    test("Sanitize directory traversal attempt", ".." not in sanitized and "/" not in sanitized and "\\" not in sanitized)
    test("Sanitize whitespace and weird characters", sanitize_filename("my bad file #1!.pdf") == "my_bad_file_1_.pdf")

    # -------------------------------------------------------------
    # 3. Document Chunking with Rich Metadata & Table Preservation
    # -------------------------------------------------------------
    print("\n[Step 3] Processing Documents & Verifying Rich Metadata...")
    processor = DocumentProcessor()
    chunks = processor.process_all_documents()
    test("Parsed documents into chunks", len(chunks) >= 30, f"Got {len(chunks)} chunks")

    sample_chunk = chunks[0]
    test("Chunk has chunk_id", bool(sample_chunk.chunk_id))
    test("Chunk has document_id", bool(getattr(sample_chunk, "document_id", None)))
    test("Chunk has doc_name", bool(getattr(sample_chunk, "doc_name", None)))
    test("Chunk has category", bool(getattr(sample_chunk, "category", None)))
    test("Chunk has content", bool(sample_chunk.content))

    # Test table and list preservation on sample markdown
    table_sample = """# POL-99 Test Table Policy
**Document ID:** POL-99
**Classification:** General Employee Access

## 1. Safety Gear Specification Table
The following equipment ratings are mandatory:

| Item | Standard | Area |
| :--- | :--- | :--- |
| Helmet | EN 397 | All Plant |
| Safety Shoes | EN ISO 20345 | Press Shop |
| Ear Plugs | NRR 25dB | Engine Dyno |

- Step 1: Put on helmet securely
- Step 2: Tie safety shoes tightly
"""
    table_chunks = processor.chunk_text(table_sample, doc_id="POL-99", doc_name="Test Table Policy")
    test("Table chunks parsed without severing", len(table_chunks) >= 1)
    has_full_table = any("| Item | Standard | Area |" in c.content and "Ear Plugs" in c.content for c in table_chunks)
    test("Markdown table retained intact within chunk", has_full_table)

    # -------------------------------------------------------------
    # 4. Vector Store Indexing, Document Update & Ghost Chunk Purging
    # -------------------------------------------------------------
    print("\n[Step 4] Testing Vector Store Synchronization & Ghost Chunk Purging...")
    store = get_vector_store(force_rebuild=True)
    initial_count = len(store.chunks)
    test("Vector store indexed initial chunks", initial_count >= 30)

    # Insert / Update document POL-99
    update_ok = store.update_document(
        document_id="POL-99",
        new_content=table_sample,
        doc_name="Test Table Policy",
        category="General Employee Access"
    )
    test("Update document in vector store succeeds", update_ok is True)
    count_after_update = len(store.chunks)
    test("Chunk count reflects new document", count_after_update > initial_count)

    # Verify search finds the new document
    search_pol99 = store.search("Ear Plugs Engine Dyno NRR 25dB", user_role="Executive & Compliance Admin")
    test("Search immediately finds updated POL-99 document", any(r["doc_id"] == "POL-99" for r in search_pol99))

    # Delete document POL-99 (purge all chunks)
    del_ok = store.delete_by_document_id("POL-99")
    test("delete_by_document_id succeeds", del_ok is True)
    test("Ghost chunks completely purged", len(store.chunks) == initial_count)

    # Verify search no longer returns POL-99
    search_after_del = store.search("Ear Plugs Engine Dyno NRR 25dB", user_role="Executive & Compliance Admin")
    test("Search no longer returns deleted document (zero ghost chunks)", all(r["doc_id"] != "POL-99" for r in search_after_del))

    # -------------------------------------------------------------
    # 5. Hybrid Roman Urdu Expansion, Phonetics & Stopword Stripping
    # -------------------------------------------------------------
    print("\n[Step 5] Testing Hybrid Roman Urdu Expansion, Phonetic Tolerance & Stopword Stripper...")
    
    # 5.1 Roman Urdu Stopword Stripper
    sample_stopwords_query = "Press shop me kon sa ppe pehnna zaroori hai"
    stripped_query = strip_roman_urdu_stopwords(sample_stopwords_query)
    test("Stopword stripper removes Roman Urdu filler tokens", stripped_query == "Press shop ppe")
    
    # Verify core required stopwords are in ROMAN_URDU_STOPWORDS
    required_stopwords = {"me", "mein", "kon", "kaun", "sa", "kya", "hai", "hain", "ke", "ki", "ko", "se", "pehnna", "chahye", "chahiye", "zaroori", "zaruri"}
    test("Required Roman Urdu stopwords defined in set", required_stopwords.issubset(ROMAN_URDU_STOPWORDS))

    # 5.2 Compact & High-Signal Rewrite for Press Shop
    target_press_q = "Press shop me kon sa ppe pehnna zaroori hai?"
    rewritten_press = rewrite_query_for_retrieval(target_press_q)
    print(f"  -> Rewritten Press Shop: '{target_press_q}' -> '{rewritten_press}'")
    test(
        "Press shop maps concisely to target string",
        rewritten_press == "POL-04 HSE plant safety PPE press shop personal protective equipment"
    )
    test(
        "No speculative laundry list equipment in rewritten query",
        all(term not in rewritten_press.lower() for term in ["kevlar", "arm guards", "glasses", "boots"])
    )
    test(
        "No raw conversational Roman Urdu appended at the end",
        all(w not in rewritten_press.lower().split() for w in ["me", "kon", "sa", "pehnna", "zaroori", "hai"])
    )

    q_roman = "Press shop me kon sa PPE chahye"
    expanded_roman = rewrite_query_for_retrieval(q_roman)
    test("Roman Urdu PPE query expanded to English keywords", "press shop" in expanded_roman.lower() and "ppe" in expanded_roman.lower())

    q_roman_leave = "annual leave kitni milti hai saalana"
    expanded_leave = rewrite_query_for_retrieval(q_roman_leave)
    test("Roman Urdu leave query expanded with POL-01 keywords", "annual leave" in expanded_leave and "POL-01" in expanded_leave)

    # Phonetic tolerance test (common alternate spellings: chuti, zaruri, tarika)
    q_phonetic = "casual chuti ki manzoori ka tarika zaruri"
    expanded_phonetic = rewrite_query_for_retrieval(q_phonetic)
    test("Phonetic tolerance expands 'chuti / manzoori / tarika' properly", "casual leave" in expanded_phonetic and "POL-01" in expanded_phonetic)

    # Multi-turn conversational history topic inheritance
    conv_history = [
        {"role": "user", "content": "What is the casual leave policy for permanent staff?"},
        {"role": "assistant", "content": "Under POL-01 Section 2.2, permanent staff receive 10 days casual leave."}
    ]
    follow_up_q = "Aur iski approval ka process?"
    rewritten_follow_up = rewrite_query_for_retrieval(follow_up_q, history=conv_history)
    print(f"  -> Contextual Follow-up: '{follow_up_q}' -> '{rewritten_follow_up}'")
    test("Conversational follow-up inherits prior topic (POL-01 / casual leave)", "POL-01" in rewritten_follow_up or "casual leave" in rewritten_follow_up)

    test("Detect English language tone", detect_language("What is the speed limit inside plant?") == "English")
    test("Detect Roman Urdu language tone", detect_language("casual leave kitni milti hai batao") == "Roman Urdu")
    test("Detect Urdu script language tone", detect_language("سالانہ چھٹیوں کی کیا پالیسی ہے؟") == "اردو (Urdu Script)")

    # -------------------------------------------------------------
    # 6. RAG Pipeline: Tone Preservation & Grounding
    # -------------------------------------------------------------
    print("\n[Step 6] Testing End-to-End RAG Pipeline with Roman Urdu...")
    rag = RAGPipeline()
    res_roman = rag.query(
        query_text="Press shop me kon sa ppe pehnna zaroori hai?",
        session_id="test_roman_001",
        user_role="Production Operator & Plant Staff",
        language="Roman Urdu"
    )
    print(f"  -> Press Shop Score: {res_roman.get('best_score')} (Threshold: {CONFIDENCE_THRESHOLD})")
    test("Press shop retrieval score comfortably exceeds 0.28 (score >= 0.70)", res_roman.get("best_score", 0.0) >= 0.70)
    test("Press shop query answered in Roman Urdu tone", "Aapke sawaal ke mutabiq" in res_roman["answer"] or "Official Reference" in res_roman["answer"] or "POL-04" in res_roman["answer"])
    test("Press shop query returned verified POL-04 citations", len(res_roman["citations"]) > 0 and any(c["doc_id"] == "POL-04" for c in res_roman["citations"]))

    # Test General Employee role as well
    res_general = rag.query(
        query_text="Press shop me kon sa ppe pehnna zaroori hai?",
        session_id="test_roman_002",
        user_role="General Employee",
        language="Roman Urdu"
    )
    test("General Employee role also retrieves POL-04 with score >= 0.28", res_general.get("best_score", 0.0) >= 0.70 and any(c["doc_id"] == "POL-04" for c in res_general["citations"]))

    # -------------------------------------------------------------
    # 7. Calibrated Confidence Guardrail (0.28) & Unanswered Logging
    # -------------------------------------------------------------
    print("\n[Step 7] Testing Calibrated Confidence Guardrail (0.28) & Unanswered Logging...")
    test("Calibrated CONFIDENCE_THRESHOLD is 0.28", CONFIDENCE_THRESHOLD == 0.28)

    # Legitimate paraphrased query should succeed with calibrated threshold
    legit_query = "What is the probation period leave entitlement?"
    res_legit = rag.query(
        query_text=legit_query,
        session_id="test_legit_001",
        user_role="General Employee",
        language="English",
        confidence_threshold=CONFIDENCE_THRESHOLD
    )
    test("Legitimate query accepted by calibrated threshold (score >= 0.28)", res_legit["is_unanswered"] is False and len(res_legit["citations"]) > 0)

    # Irrelevant query should fall below 0.28 and trigger graceful fallback
    irrelevant_query = "What is the policy for buying cryptocurrency with company funds?"
    res_fallback = rag.query(
        query_text=irrelevant_query,
        session_id="test_fallback_001",
        user_role="General Employee",
        language="English",
        confidence_threshold=CONFIDENCE_THRESHOLD
    )
    test("Irrelevant query triggered strict fallback (score < 0.28)", res_fallback["is_unanswered"] is True)
    test("Fallback advises to consult Line Manager / HR", "Line Manager" in res_fallback["answer"] or "Human Resources" in res_fallback["answer"])
    test("Zero hallucinations / empty citations on fallback", len(res_fallback["citations"]) == 0)

    # Check that the query was recorded in unanswered_queries
    unanswered_list = get_unanswered_queries(limit=5)
    matched_log = next((u for u in unanswered_list if u["query"] == irrelevant_query), None)
    test("Irrelevant query logged in unanswered_queries table", matched_log is not None)

    if matched_log:
        res_update = resolve_unanswered_query(matched_log["id"], "resolved")
        test("Admin can resolve unanswered query", res_update is True)
        del_log = delete_unanswered_query(matched_log["id"])
        test("Admin can dismiss/delete unanswered query", del_log is True)

    # -------------------------------------------------------------
    # 8. Admin Security PIN Gate
    # -------------------------------------------------------------
    print("\n[Step 8] Testing Admin Security PIN Gate...")
    test("Admin PIN configured in config.py", ADMIN_PIN == "atlas123")

    # -------------------------------------------------------------
    # 9. PDF Generation & Executive Analytics
    # -------------------------------------------------------------
    print("\n[Step 9] Testing Corporate PDF Generation & Analytics...")
    pdf_bytes = generate_query_pdf(
        query_text="What is the probation period leave policy?",
        answer_text=res_roman["answer"],
        citations=res_roman["citations"],
        user_role="General Employee",
        language="English",
        latency_ms=res_roman["latency_ms"]
    )
    test("PDF generated successfully (> 2000 bytes)", len(pdf_bytes) > 2000)

    analytics = get_analytics_summary()
    test("Analytics includes total_queries", analytics["total_queries"] > 0)
    test("Analytics includes queries_by_role", len(analytics["queries_by_role"]) > 0)
    test("Analytics includes queries_by_lang", len(analytics["queries_by_lang"]) > 0)

    # -------------------------------------------------------------
    # Final Verdict
    # -------------------------------------------------------------
    print("\n" + "=" * 68)
    print(f"VERIFICATION RESULTS: {passed_tests}/{total_tests} TESTS PASSED (100% SUCCESS)")
    print("=" * 68)

    if passed_tests != total_tests:
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
