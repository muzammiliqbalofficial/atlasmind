"""
AtlasMind - Unified LLM Generation & Multilingual Query Expansion Engine
Supports Local Fallback (0-API-Key Zero Hallucination), Ollama (Local LLM),
Google Gemini Free API, and Groq API.
Features hybrid Roman Urdu & conversational query rewriting with phonetic tolerance,
multi-turn context stitching, and tone-preserved response generation.
"""

import os
import json
import re
import requests
from typing import List, Dict, Any, Optional

from src.config import THEME


SYSTEM_PROMPT_EN = """You are AtlasMind, the internal AI Knowledge Assistant for Atlas Honda Limited (Pakistan).
Your task is to provide accurate, professional, and strictly grounded answers to employee inquiries regarding company policies, plant safety guidelines, quality SOPs, and governance standards at the Karachi Mother Plant (F-36, Estate Avenue, S.I.T.E.) and across the company.

GROUNDING & FORMAT RULES:
1. Ground your response ONLY in the provided Document Excerpts below.
2. If the context does not contain the answer, state clearly: "I could not find specific guidance on this in the official Atlas Honda policies provided. Please consult your Line Manager or Human Resources." Do NOT guess or extrapolate.
3. MANDATORY CONCISE STRUCTURE (Under 90 words):
   - Line 1: Exactly ONE clear opening sentence answering the question with the policy name.
   - Lines 2-4: Exactly 2 to 3 concise bullet points with key numbers, entitlements, or rules.
   - Final line: Exact citation, e.g. **Official Citation:** [POL-01 | Section 2.1 – Annual Leave].
4. Do NOT dump unrelated sections, secondary chunks, or lengthy boilerplate disclaimers.
"""

SYSTEM_PROMPT_UR = """آپ اٹلس مائنڈ (AtlasMind) ہیں، اٹلس ہونڈا لمیٹڈ (پاکستان) کے باضابطہ اندرونی معلوماتی معاون۔
آپ کا کام ملازمین کے سوالات کا مصدقہ اور شائستہ جواب دینا ہے۔

قواعد:
1. جواب صرف نیچے دیے گئے سرکاری دستاویزات کے اقتباسات کی بنیاد پر دیں۔
2. جواب کی لازمی ساخت (90 الفاظ سے کم):
   - پہلی لائن: ایک واضح جملہ جو پالیسی کا نام لے کر بنیادی جواب فراہم کرے۔
   - 2 سے 3 بلٹ پوائنٹس: اہم شرائط، اعداد و شمار یا قواعد۔
   - آخری لائن: باضابطہ حوالہ (جیسے: **باضابطہ حوالہ:** [POL-01 | Section 2.1])۔
3. غیر ضروری لمبی وضاحتوں سے مکمل گریز کریں۔
"""

SYSTEM_PROMPT_ROMAN_UR = """Aap AtlasMind hain, Atlas Honda Limited (Pakistan) ke official internal AI assistant.
Aapka maqsad employees ko company policies, Karachi plant safety rules (ISO 14001/45001), aur quality SOPs ke mutabiq strictly grounded aur accurate jawab dena hai.

RULES & MANDATORY STRUCTURE:
1. Sirf provide kiye gaye Document Excerpts ki roshni mein jawab dein.
2. Response ko nihayat concise aur focused rakhein (under 90 words):
   - Pehli line: Aik clear opening sentence jo policy reference ke sath direct jawab de.
   - 2 se 3 bullet points: Sirf relevant rules, numbers, aur entitlements.
   - Aakhri line: Official reference (jaise **Official Reference:** [POL-01 | Section 2.1]).
3. Fuzool lambi baatein ya doosri sections ki ghair-mutalliq maloomat bilkul shamil na karein.
"""

# Regex for detecting Arabic/Urdu script
URDU_SCRIPT_REGEX = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

# Roman Urdu Stopwords & Grammatical Non-Content Particles
# Stripping these prevents TF-IDF vector dilution and prevents query norm ||Q|| inflation
ROMAN_URDU_STOPWORDS = {
    "me", "mein", "mai", "kon", "kaun", "sa", "kya", "hai", "hain",
    "ke", "ki", "ko", "se", "pehnna", "chahye", "chahiye", "chahiyen",
    "zaroori", "zaruri", "karo", "karna", "kaise", "kese", "batao",
    "bataein", "batayein", "bataiye", "aur", "bhi", "to", "toh", "ye",
    "yeh", "wo", "woh", "par", "pe", "ka", "kitni", "kitna", "kitne",
    "kahan", "kyun", "hoga", "hogi", "honge", "sakte", "sakti", "sakta",
    "mujhe", "mera", "meri", "mere", "aap", "apka", "apki", "apke",
    "hum", "hamara", "nahi", "nahin"
}


def strip_roman_urdu_stopwords(text: str) -> str:
    """
    Remove Roman Urdu non-content / stop words to prevent TF-IDF vector dilution
    and protect cosine similarity against query norm ||Q|| explosion.
    """
    if not text:
        return ""
    words = text.split()
    filtered = [w for w in words if w.lower().strip("?,.!;:\"'()[]{}") not in ROMAN_URDU_STOPWORDS]
    cleaned = " ".join(filtered).strip()
    return re.sub(r"\s+", " ", cleaned).strip()


# Roman Urdu Vocabulary Signatures (Includes Phonetic Variants)
ROMAN_URDU_KEYWORDS = {
    "chutti", "chuti", "chuttiyan", "chutiyan", "chutyan", "chuttiyon", "kitni", "kitna", "kitne",
    "batao", "bataein", "batayein", "bataiye", "batana", "milegi", "milta", "milte", "milti",
    "milega", "karein", "karna", "karo", "kaise", "kese", "kahan", "kyun", "hoga", "hogi",
    "honge", "sakte", "sakti", "sakta", "chahye", "chahiye", "chahiyen", "zaroori", "zaruri",
    "wapas", "beemari", "bimari", "saalana", "salana", "tohfay", "tohfa", "rishwat", "hazri",
    "kya", "hai", "hain", "mein", "mai", "ka", "ke", "ki", "ko", "se", "par", "pe", "aur",
    "bhi", "toh", "to", "yeh", "ye", "woh", "wo", "mujhe", "mera", "meri", "mere", "aap",
    "apka", "apki", "apke", "hum", "hamara", "nahi", "nahin", "rabta", "ijazat", "manzoori",
    "tareeqa", "tarika", "tareeka", "amal", "hifazat", "hifazati", "auqat", "waqt", "shikayat"
}


def detect_language(text: str) -> str:
    """
    Detect language tone of query: 'Urdu', 'Roman Urdu', or 'English'.
    """
    if not text or not text.strip():
        return "English"

    if URDU_SCRIPT_REGEX.search(text):
        return "اردو (Urdu Script)"

    # Clean words
    words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
    roman_matches = sum(1 for w in words if w in ROMAN_URDU_KEYWORDS)
    
    if roman_matches >= 2 or (roman_matches >= 1 and len(words) <= 5):
        return "Roman Urdu"

    return "English"


# Phonetic / Orthographic Normalization Map for Roman Urdu
PHONETIC_REPLACEMENTS = [
    (r"\bchut+y?a+n?\b", "chutti"),
    (r"\bchut+i\b", "chutti"),
    (r"\bchut+y\b", "chutti"),
    (r"\bzar+u+r+i\b", "zaroori"),
    (r"\bzar+u+r+a+t\b", "zaroori"),
    (r"\bija+z+a+t\b", "approval"),
    (r"\bmanzo+r+i\b", "approval"),
    (r"\bmanzu+r+i\b", "approval"),
    (r"\btar+e+q+a\b", "procedure"),
    (r"\btar+i+k+a\b", "procedure"),
    (r"\btar+e+k+a\b", "procedure"),
    (r"\bke+s+e\b", "kaise"),
    (r"\bkis\s+tarah\b", "kaise"),
    (r"\braf+t+a+r\b", "speed limit"),
    (r"\bga+r+i\b", "vehicle"),
    (r"\bga+d+i\b", "vehicle"),
    (r"\bwaq+t\b", "timing"),
    (r"\bauqa+t\b", "timing"),
    (r"\btanha\b", "salary"),
    (r"\btankhwah\b", "salary"),
    (r"\bbema+r+i\b", "sick leave"),
    (r"\bbima+r+i\b", "sick leave"),
]


def normalize_roman_urdu(text: str) -> str:
    """Normalize common phonetic variations of Roman Urdu words."""
    res = text.lower()
    for pattern, replacement in PHONETIC_REPLACEMENTS:
        res = re.sub(pattern, replacement, res)
    return res


# Curated dictionary for fast Roman Urdu / conversational expansion to crisp English keywords.
# Limited to 4-8 high-signal tokens matching actual document titles and section text.
# NO speculative laundry lists of equipment (e.g., Kevlar, arm guards, glasses, boots).
ROMAN_URDU_EXPANSIONS = [
    (r"\b(annual|saalana|salana)\s*(chutti|leave|holiday|chuttiyan)?\b", "annual leave entitlement 14 days privilege leave POL-01"),
    (r"\b(casual|itafaqi|emergency)\s*(chutti|leave)?\b", "casual leave entitlement emergency personal 10 days POL-01"),
    (r"\b(sick|bimari|beemari|medical|hospital)\s*(chutti|leave)?\b", "sick medical leave hospitalization POL-01"),
    (r"\b(maternity|pregnancy|delivery|hamal)\s*(chutti|leave)?\b", "maternity leave female employee 12 weeks POL-01"),
    (r"\b(probation|azmaishi)\b", "probation period 6 months leave confirmation evaluation SOP-06"),
    (r"\b(press\s*shop|stamping)\b", "POL-04 HSE plant safety PPE press shop personal protective equipment"),
    (r"\b(loto|lock\s*out|lockout|tagout)\b", "POL-04 LOTO lockout tagout zero energy safety procedure"),
    (r"\b(ppe|hifazati\s*saman|safety\s*gear|protective\s*equipment)\b", "POL-04 HSE plant safety PPE personal protective equipment"),
    (r"\b(speed\s*limit|gari|traffic|parking|reverse\s*parking)\b", "POL-04 plant traffic vehicle speed limit 15 kmh reverse parking"),
    (r"\b(dyno|roller|dynamometer|cd\s*70|inspection|qc|break)\b", "SOP-07 CD70 roller dynamometer brake emission speed test"),
    (r"\b(shift|timing|auqat|shabana|subah|morning|evening|night)\b", "POL-02 Karachi plant shift timings working hours"),
    (r"\b(late|der|attendance|hazri|absent|ghair\s*hazir|punching)\b", "POL-02 attendance punctuality grace period 15 minutes deduction"),
    (r"\b(tohfay|tohfa|gift|rishwat|bribe|conflict|ikhtilaf)\b", "POL-03 code of conduct gift acceptance anti bribery"),
    (r"\b(complaint|shikayat|whistleblower|speak\s*up|hotline)\b", "POL-09 whistleblower speak up integrity hotline reporting"),
    (r"\b(visitor|mehmaan|contractor|vendor|gate\s*pass)\b", "SOP-10 visitor contractor safety gate pass PPE induction"),
    (r"\b(misconduct|badtameezi|discipline|inquiry|punishment|suspension)\b", "POL-08 disciplinary domestic inquiry misconduct suspension"),
    (r"\b(it|computer|laptop|password|usb|internet|helpdesk|sla)\b", "POL-05 IT acceptable use password prohibited helpdesk SLA"),
    (r"\b(approval|manzoori|ijazat|line\s*manager|apply)\b", "approval process line manager procedure requirements"),
]

# Pure Urdu script token mappings - concise high-signal tokens
URDU_SCRIPT_MAPPINGS = [
    ("سالانہ چھٹی", "annual leave privilege leave POL-01"),
    ("کیژول لیو", "casual leave entitlement POL-01"),
    ("اتفاقی چھٹی", "casual leave entitlement POL-01"),
    ("بیماری کی رخصت", "sick leave medical POL-01"),
    ("پریس شاپ", "POL-04 HSE plant safety PPE press shop personal protective equipment"),
    ("پی پی ای", "POL-04 HSE plant safety PPE personal protective equipment"),
    ("حفاظتی سامان", "POL-04 HSE plant safety PPE personal protective equipment"),
    ("لوٹو طریقہ کار", "POL-04 LOTO lockout tagout six step procedure"),
    ("رفتار کی حد", "POL-04 plant vehicle speed limit 15 kmh reverse parking"),
    ("شفٹ کے اوقات", "POL-02 plant shift timings morning evening night"),
    ("حاضری", "POL-02 attendance punctuality grace period"),
    ("رشوت اور تحائف", "POL-03 code of conduct gift acceptance bribery"),
    ("وسل بلور", "POL-09 whistleblower speak up policy"),
    ("مہمان", "SOP-10 visitor contractor safety gate pass"),
    ("منظوری", "approval process procedure line manager"),
]


def extract_context_topic(history: List[Dict[str, Any]]) -> str:
    """
    Inspect the last 1-2 completed conversation turns to identify the active policy subject.
    Extracts policy IDs (POL-01, POL-04, etc.) and core thematic nouns.
    """
    if not history:
        return ""

    # Check recent turns in reverse (excluding the current turn which is at the end)
    candidates = []
    # Look back up to 4 items in history
    scan_slice = history[-4:] if len(history) >= 4 else history
    for msg in reversed(scan_slice):
        content = msg.get("content", "")
        # Find explicit policy references like POL-01, SOP-07, etc.
        doc_matches = re.findall(r"\b(POL-\d{2}|SOP-\d{2})\b", content, re.IGNORECASE)
        if doc_matches:
            candidates.extend([m.upper() for m in doc_matches])
        
        # Check for prominent topic phrases
        low = content.lower()
        if "casual leave" in low or "casual" in low:
            candidates.append("casual leave POL-01")
        elif "annual leave" in low or "saalana" in low or "privilege leave" in low:
            candidates.append("annual leave POL-01")
        elif "press shop" in low:
            candidates.append("press shop PPE POL-04")
        elif "loto" in low:
            candidates.append("LOTO lockout POL-04")
        elif "speed limit" in low or "parking" in low:
            candidates.append("speed limit traffic rules POL-04")
        elif "attendance" in low or "punctuality" in low or "grace period" in low:
            candidates.append("attendance punctuality POL-02")
        elif "disciplinary" in low or "inquiry" in low:
            candidates.append("disciplinary inquiry POL-08")
        elif "probation" in low:
            candidates.append("probation period SOP-06")

        if candidates:
            break

    return " ".join(list(dict.fromkeys(candidates))[:2])


def rewrite_query_for_retrieval(
    user_query: str,
    history: Optional[List[Dict[str, Any]]] = None,
    llm_engine: Optional['UnifiedLLMEngine'] = None,
    provider: str = "Local Fallback Engine (Zero API Keys)",
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None
) -> str:
    """
    Hybrid pre-retrieval query rewriting:
    1. Multi-turn context resolution: Blends prior turn's policy subject into anaphoric follow-ups.
    2. Phonetic normalization of Roman Urdu words.
    3. Rule-based lookup across core operational terms (PPE, LOTO, Leave, Shift, etc.).
    4. Zero-shot LLM fallback for conversational/complex Roman Urdu when API key is provided.
    """
    query_clean = user_query.strip()
    if not query_clean:
        return ""

    low_query = query_clean.lower()

    # 1. Multi-turn conversational context resolution (Handles: "Aur iski approval ka process?", "Can I take that?", etc.)
    follow_up_cues = [
        "aur iski", "aur iska", "aur iske", "iski", "iska", "iske", "iski limit",
        "approval", "process", "kese hoti", "kaise hoti", "kaun approve", "who approves",
        "what about", "how about", "can i", "is it allowed", "and for", "what if",
        "rules for that", "aur agar", "us ke baad", "procedure kya hai", "apply kaise"
    ]
    is_contextual_follow_up = any(cue in low_query for cue in follow_up_cues) or len(query_clean.split()) <= 4
    
    context_topic = ""
    if history and len(history) >= 2 and is_contextual_follow_up:
        # Pass history excluding the last message if the last message is the current query itself
        past_turns = history[:-1] if history[-1].get("content") == user_query else history
        context_topic = extract_context_topic(past_turns)
        if context_topic:
            query_clean = f"{context_topic} {query_clean}"
            low_query = query_clean.lower()

    # 2. Check Pure Urdu script phrases first
    for urdu_phrase, eng_expansion in URDU_SCRIPT_MAPPINGS:
        if urdu_phrase in query_clean:
            return strip_roman_urdu_stopwords(eng_expansion)

    # 3. Phonetic normalization of Roman Urdu terms
    normalized_query = normalize_roman_urdu(low_query)

    # Specific Press shop / Stamping mapping (Concise 4-8 high-signal tokens matching POL-04)
    if re.search(r"\b(press\s*shop|stamping)\b", normalized_query):
        return "POL-04 HSE plant safety PPE press shop personal protective equipment"

    # 4. Rule-based Roman Urdu & Slang expansion (Fast, zero-latency, 100% offline)
    expanded_terms = []
    for pattern, expansion in ROMAN_URDU_EXPANSIONS:
        if re.search(pattern, normalized_query):
            expanded_terms.append(expansion)

    if expanded_terms:
        # Collect unique high-signal tokens preserving order
        seen = set()
        unique_tokens = []
        for term_str in expanded_terms:
            for token in term_str.split():
                token_lower = token.lower()
                if token_lower not in seen and token_lower not in ROMAN_URDU_STOPWORDS:
                    seen.add(token_lower)
                    unique_tokens.append(token)
        # Return ONLY the clean English expanded string without appending raw Roman Urdu words
        clean_expansion = " ".join(unique_tokens).strip()
        return clean_expansion

    # 5. Zero-shot LLM Fallback (Gemini / Groq) if available and query is complex Roman Urdu
    detected_lang = detect_language(user_query)
    if detected_lang == "Roman Urdu" and llm_engine and provider != "Local Fallback Engine (Zero API Keys)":
        try:
            rewrite_prompt = (
                f"Rewrite this Roman Urdu employee query into a crisp, concise English technical keyword phrase "
                f"for searching corporate motorcycle manufacturing policies (Leave, HSE, Quality, HR, Safety):\n"
                f"User Query: \"{user_query}\"\n"
                f"Output ONLY the English search phrase (no extra commentary):"
            )
            if "Gemini" in provider and gemini_api_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
                payload = {
                    "contents": [{"parts": [{"text": rewrite_prompt}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 40}
                }
                res = requests.post(url, json=payload, timeout=4)
                if res.status_code == 200:
                    cand = res.json().get("candidates", [])
                    if cand:
                        rewritten = cand[0]["content"]["parts"][0]["text"].strip().strip('"')
                        if rewritten:
                            return strip_roman_urdu_stopwords(rewritten)
            elif "Groq" in provider and groq_api_key:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": rewrite_prompt}],
                    "temperature": 0.0,
                    "max_tokens": 40
                }
                res = requests.post(url, headers=headers, json=payload, timeout=4)
                if res.status_code == 200:
                    rewritten = res.json()["choices"][0]["message"]["content"].strip().strip('"')
                    if rewritten:
                        return strip_roman_urdu_stopwords(rewritten)
        except Exception:
            pass

    # If no expansion matched, filter out Roman Urdu non-content stopwords before vector calculation
    cleaned_query = strip_roman_urdu_stopwords(query_clean)
    return cleaned_query or query_clean


class LocalFallbackEngine:
    """Zero-dependency, offline extractive synthesizer that guarantees zero hallucinations and concise answers."""
    
    def generate(self, query: str, context_chunks: List[Dict[str, Any]], language: str = "English") -> str:
        if not context_chunks:
            if "Urdu" in language and "Roman" not in language:
                return "معذرت، آپ کے کردار (Role) کے مطابق اس موضوع پر کوئی متعلقہ باضابطہ پالیسی دستاویز نہیں ملی۔ براہ کرم اپنے لائن منیجر یا ایچ آر سے رابطہ فرمائیں۔"
            elif "Roman" in language:
                return "Maazrat, aapke current access level ke mutabiq koi related official policy document nahi mila. Barah-e-karam apne Line Manager ya HR se rabta karein."
            return "I could not locate any authorized policy documents matching your query under your current access level. Please contact your Department Head or Human Resources."

        # Filter out trivial divider chunks
        valid_chunks = [c for c in context_chunks if len(c.get("content", "").strip(" -\n\r\t*#")) >= 25]
        if not valid_chunks:
            valid_chunks = context_chunks

        top_chunk = valid_chunks[0]
        content = top_chunk.get("content", "").strip()
        doc_id = top_chunk.get("doc_id", top_chunk.get("document_id", "DOC"))
        doc_title = top_chunk.get("doc_title", top_chunk.get("doc_name", "Atlas Honda Policy"))
        sec_title = top_chunk.get("section_title", "General Regulations")
        doc_ref = f"[{doc_id} | {sec_title}]"

        q_low = query.lower()

        # 1. Check if chunk contains a Markdown Table (e.g., POL-04 Section 2 PPE Matrix)
        table_points = []
        if "|" in content:
            shop_map = {
                "press": ["press & stamping", "press shop", "stamping shop"],
                "welding": ["welding & frame", "welding shop"],
                "paint": ["paint & pre-treatment", "paint shop"],
                "engine": ["engine assembly", "engine line"],
                "final": ["final assembly & test", "test roller", "dynamometer"],
                "warehouse": ["warehouse & logistics", "logistics bay"]
            }
            target_synonyms = None
            for key, syns in shop_map.items():
                if any(s in q_low for s in [key, *syns]):
                    target_synonyms = syns
                    break

            for line in content.split("\n"):
                line_s = line.strip()
                if line_s.startswith("|") and not re.match(r"^\|\s*:?---", line_s):
                    cols = [c.strip() for c in line_s.split("|")[1:-1]]
                    if len(cols) >= 2:
                        area, reqs = cols[0], cols[1]
                        if "Shop / Production Area" in area or "Hazard" in area or "Standard" in area:
                            continue
                        area_clean = area.replace("*", "")
                        if target_synonyms:
                            if any(s in area.lower() for s in target_synonyms):
                                items = [it.strip() for it in reqs.split(",") if len(it.strip()) > 5]
                                for item in items:
                                    table_points.append(item)
                                break
                        elif len(table_points) < 3:
                            table_points.append(f"{area_clean}: {reqs}")

        # 2. Text Extraction (Scored by sub-topic relevance to prevent section cross-contamination)
        key_points = []
        if table_points:
            key_points = table_points[:3]
        else:
            content_lines = content.split("\n")
            candidate_lines = []
            
            is_annual_q = bool(re.search(r"\b(al|annual|privilege|saalana|salana)\b", q_low))
            is_casual_q = bool(re.search(r"\b(cl|casual|itafaqi)\b", q_low))
            is_sick_q = bool(re.search(r"\b(sl|sick|medical|hospital|bimari|beemari)\b", q_low))
            
            for line in content_lines:
                line_str = line.strip()
                if not line_str or line_str.startswith("#") or line_str.startswith("---") or line_str.startswith("|"):
                    continue
                
                if line_str.startswith("- ") or line_str.startswith("* ") or re.match(r"^\d+\.\s+", line_str):
                    clean_pt = re.sub(r"^[-*]\s+|\*\*", "", line_str)
                    clean_pt = re.sub(r"^\d+\.\s+", "", clean_pt)
                    if len(clean_pt) > 15:
                        pt_low = clean_pt.lower()
                        # Strictly prevent sub-section leakage when chunks contain multiple leave types
                        if is_annual_q and (pt_low.startswith("casual leave") or pt_low.startswith("sick leave") or "maternity leave" in pt_low):
                            continue
                        if is_casual_q and (pt_low.startswith("annual leave") or pt_low.startswith("privilege leave") or pt_low.startswith("sick leave")):
                            continue
                        if is_sick_q and (pt_low.startswith("annual leave") or pt_low.startswith("casual leave") or "maternity leave" in pt_low):
                            continue
                        candidate_lines.append(clean_pt)
                elif len(line_str) > 30 and not line_str.startswith(">"):
                    candidate_lines.append(line_str)

            key_points = candidate_lines[:3]
            if not key_points:
                first_para = [l.strip() for l in content_lines if len(l.strip()) > 30 and not l.startswith("#")]
                key_points = [first_para[0]] if first_para else [content[:250] + "..."]

        selected_points = key_points[:3]

        # 3. Assemble Crisp Response: 1 Opening Line + 2-3 Bullets + Citation
        if "Urdu" in language and "Roman" not in language:
            opening = f"**{doc_title}** ({doc_id}) کے مطابق بنیادی قواعد درج ذیل ہیں:"
            bullets_text = "\n".join([f"- {pt}" for pt in selected_points])
            citation = f"**باضابطہ حوالہ:** `{doc_ref}`"
            return f"{opening}\n\n{bullets_text}\n\n{citation}"
            
        elif "Roman" in language:
            if "annual" in q_low or "saalana" in q_low or "salana" in q_low:
                opening = f"**{doc_title}** ke mutabiq, annual leave entitlement ke ahem points yeh hain:"
            elif "casual" in q_low or "itafaqi" in q_low:
                opening = f"**{doc_title}** ke mutabiq, casual leave ke official rules yeh hain:"
            elif "sick" in q_low or "bimari" in q_low or "medical" in q_low:
                opening = f"**{doc_title}** ke mutabiq, sick leave ke official rules yeh hain:"
            elif "press shop" in q_low or "ppe" in q_low:
                opening = f"**{doc_title}** ke mutabiq, Press & Stamping Shop mein mandatory PPE yeh hai:"
            elif "loto" in q_low:
                opening = f"**{doc_title}** ke mutabiq, Lockout/Tagout (LOTO) procedure ke ahem steps yeh hain:"
            elif "speed" in q_low or "traffic" in q_low:
                opening = f"**{doc_title}** ke mutabiq, factory perimeter ke andar traffic rules yeh hain:"
            else:
                opening = f"**{doc_title}** ke mutabiq, aapke sawaal ke ahem policy points darj zail hain:"
            
            bullets_text = "\n".join([f"- {pt}" for pt in selected_points])
            citation = f"**Official Reference:** `{doc_ref}`"
            return f"{opening}\n\n{bullets_text}\n\n{citation}"

        # Default English
        if "annual" in q_low:
            opening = f"Under the **{doc_title}**, permanent employees are entitled to paid annual leave under the following guidelines:"
        elif "casual" in q_low:
            opening = f"Under the **{doc_title}**, permanent employees are entitled to casual leave under the following provisions:"
        elif "sick" in q_low:
            opening = f"Under the **{doc_title}**, permanent employees are granted sick leave under the following regulations:"
        elif "press shop" in q_low or "ppe" in q_low:
            opening = f"Under the **{doc_title}**, mandatory PPE requirements for the Press & Stamping Shop are:"
        elif "loto" in q_low:
            opening = f"Under the **{doc_title}**, the 6-step Lockout/Tagout (LOTO) protocol ensures a verified zero energy state:"
        elif "speed" in q_low or "traffic" in q_low or "parking" in q_low:
            opening = f"Under the **{doc_title}**, vehicular traffic regulations inside the plant perimeter state:"
        elif "probation" in q_low:
            opening = f"Under the **{doc_title}**, employee onboarding and probation regulations state:"
        else:
            opening = f"Under the **{doc_title}** (`{doc_ref}`), the key policy provisions state:"

        bullets_text = "\n".join([f"- {pt}" for pt in selected_points])
        citation = f"**Official Citation:** `{doc_ref}`"
        return f"{opening}\n\n{bullets_text}\n\n{citation}"


class UnifiedLLMEngine:
    """Coordinates generation across Local Fallback, Gemini, Groq, and Ollama."""
    def __init__(self):
        self.fallback = LocalFallbackEngine()

    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]], 
        provider: str = "Local Fallback Engine (Zero API Keys)", 
        language: str = "English",
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None
    ) -> str:
        
        # 1. Local Fallback Mode
        if provider == "Local Fallback Engine (Zero API Keys)":
            return self.fallback.generate(query, context_chunks, language)
            
        # Context block builder
        context_str = "\n\n".join([
            f"--- START EXCERPT: [{c.get('doc_id', c.get('document_id', 'DOC'))} | {c.get('section_title', '')}] ---\n{c['content']}\n--- END EXCERPT ---"
            for c in context_chunks
        ])
        
        # Choose system prompt based on language
        if "Urdu" in language and "Roman" not in language:
            sys_prompt = SYSTEM_PROMPT_UR
        elif "Roman" in language:
            sys_prompt = SYSTEM_PROMPT_ROMAN_UR
        else:
            sys_prompt = SYSTEM_PROMPT_EN
            
        user_prompt = (
            f"User Question: {query}\n\n"
            f"Relevant Document Excerpts:\n{context_str}\n\n"
            f"Please provide a clear, grounded answer in the specified language tone ({language}), citing document IDs and sections."
        )

        # 2. Google Gemini
        if "Gemini" in provider:
            api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                return "⚠️ **Gemini API Key Missing**: Please provide your Gemini API key in the sidebar or switch to the **Local Fallback Engine**.\n\n" + self.fallback.generate(query, context_chunks, language)
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{sys_prompt}\n\n{user_prompt}"}]
                    }],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}
                }
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"]
                return f"⚠️ Gemini API returned status {res.status_code}. Falling back to local engine:\n\n" + self.fallback.generate(query, context_chunks, language)
            except Exception as e:
                return f"⚠️ Gemini API connection issue ({str(e)}). Falling back:\n\n" + self.fallback.generate(query, context_chunks, language)

        # 3. Groq API
        elif "Groq" in provider:
            api_key = groq_api_key or os.getenv("GROQ_API_KEY")
            if not api_key:
                return "⚠️ **Groq API Key Missing**: Please provide your Groq API key in the sidebar or switch to the **Local Fallback Engine**.\n\n" + self.fallback.generate(query, context_chunks, language)
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 800
                }
                res = requests.post(url, headers=headers, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                return f"⚠️ Groq API error ({res.status_code}). Falling back:\n\n" + self.fallback.generate(query, context_chunks, language)
            except Exception as e:
                return f"⚠️ Groq connection issue ({str(e)}). Falling back:\n\n" + self.fallback.generate(query, context_chunks, language)

        # 4. Ollama Local Model
        elif "Ollama" in provider:
            try:
                url = "http://localhost:11434/api/generate"
                payload = {
                    "model": "llama3",
                    "prompt": f"{sys_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "options": {"temperature": 0.2}
                }
                res = requests.post(url, json=payload, timeout=15)
                if res.status_code == 200:
                    return res.json().get("response", "")
                return "⚠️ Ollama local server returned non-200. Is the model installed? Falling back:\n\n" + self.fallback.generate(query, context_chunks, language)
            except Exception as e:
                return "⚠️ Could not connect to local Ollama on `localhost:11434`. Please ensure Ollama is running (`ollama serve`) or switch to **Local Fallback Engine**.\n\n" + self.fallback.generate(query, context_chunks, language)

        return self.fallback.generate(query, context_chunks, language)
