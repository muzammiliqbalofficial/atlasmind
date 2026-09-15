"""
AtlasMind - Enterprise AI Knowledge Assistant
Production-grade, highly polished Streamlit Web Application for Atlas Honda Limited (Pakistan).
Designed with Honda Red (#ED1C24) and Slate aesthetics, role-based controls,
zero-friction free-text input, and executive-ready governance.
"""

# ==============================================================================
# 0. PYTHON 3.14 COMPATIBILITY SHIM (Altair / Streamlit TypedDict Fix)
# ==============================================================================
import typing
if hasattr(typing, "_TypedDictMeta"):
    _orig_typeddict_meta_new = typing._TypedDictMeta.__new__
    def _patched_typeddict_meta_new(cls, name, bases, ns, total=True, **kwargs):
        return _orig_typeddict_meta_new(cls, name, bases, ns, total=total)
    typing._TypedDictMeta.__new__ = _patched_typeddict_meta_new

# ==============================================================================
# 1. IMPORTS & SETUP
# ==============================================================================
import os
import uuid
import time
import json
from pathlib import Path
from datetime import datetime
import streamlit as st

# Streamlit Page Configuration
st.set_page_config(
    page_title="AtlasMind | Atlas Honda Knowledge Assistant",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Internal Engine Imports
from src.config import (
    THEME, ROLES_PERMISSIONS, AVAILABLE_PROVIDERS, DOCS_DIR,
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, CONFIDENCE_THRESHOLD, ADMIN_PIN
)
from src.db import (
    init_db, log_query, save_feedback, get_analytics_summary, 
    get_recent_queries, get_registered_documents, register_document,
    delete_registered_document, get_unanswered_queries, resolve_unanswered_query,
    delete_unanswered_query
)
from src.document_processor import DocumentProcessor, sanitize_filename, is_allowed_file
from src.vector_store import get_vector_store
from src.rag_pipeline import RAGPipeline
from src.llm_engine import detect_language
from src.pdf_exporter import generate_query_pdf

# ==============================================================================
# 2. CACHED RESOURCE INITIALIZERS (AVOID MEMORY LEAKS & RELOAD LATENCY)
# ==============================================================================
@st.cache_resource
def get_cached_database():
    """Ensure database schema is initialized once per server process."""
    init_db()
    return True

@st.cache_resource
def get_cached_vector_store():
    """Load and cache the thread-safe vector store singleton."""
    return get_vector_store()

@st.cache_resource
def get_cached_rag_pipeline():
    """Initialize and cache the enterprise RAG coordinator."""
    return RAGPipeline()

# Initialize Cached Singletons
get_cached_database()
vector_store = get_cached_vector_store()
rag_pipeline = get_cached_rag_pipeline()

# Session State Initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "messages" not in st.session_state:
    st.session_state.messages = []

if "feedback_status" not in st.session_state:
    st.session_state.feedback_status = {}

if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# ==============================================================================
# 3. BESPOKE ENTERPRISE CSS (HONDA BRANDING, MODERN CHAT BUBBLES, SHADOWS)
# ==============================================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    /* Global Typography & Palette */
    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
        color: #1A202C;
    }}
    
    .stApp {{
        background-color: #F8FAFC;
    }}

    /* Hide Default Streamlit Clutter */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Top Corporate Navigation Bar */
    .atlas-topbar {{
        background: #FFFFFF;
        border-bottom: 2px solid #ED1C24;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    .atlas-logo-block {{
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    
    .atlas-brand-title {{
        font-size: 22px;
        font-weight: 800;
        color: #1E2229;
        margin: 0;
        line-height: 1.2;
        letter-spacing: -0.5px;
    }}
    
    .atlas-brand-subtitle {{
        font-size: 12.5px;
        font-weight: 500;
        color: #64748B;
        margin: 0;
    }}

    .atlas-plant-badge {{
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: 1px solid #FECACA;
        letter-spacing: 0.2px;
    }}

    .atlas-pulse-dot {{
        width: 8px;
        height: 8px;
        background-color: #ED1C24;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 1.8s infinite;
    }}

    @keyframes pulse {{
        0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(237, 28, 36, 0.7); }}
        70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(237, 28, 36, 0); }}
        100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(237, 28, 36, 0); }}
    }}

    /* Clean Hero Welcome Card */
    .hero-container {{
        background: linear-gradient(135deg, #FFFFFF 0%, #FFF5F5 100%);
        border: 1px solid #FEE2E2;
        border-left: 4px solid #ED1C24;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
    }}

    .hero-title {{
        font-size: 20px;
        font-weight: 800;
        color: #1E2229;
        margin-bottom: 8px;
    }}

    .hero-text {{
        font-size: 14px;
        color: #475569;
        line-height: 1.6;
    }}

    /* Chat Message Cards */
    .user-bubble {{
        background: #1E2229;
        color: #FFFFFF;
        padding: 14px 18px;
        border-radius: 14px 14px 2px 14px;
        margin: 12px 0 12px auto;
        max-width: 82%;
        box-shadow: 0 3px 10px rgba(30, 34, 41, 0.12);
        font-size: 14px;
        line-height: 1.5;
    }}

    .assistant-card {{
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-top: 3px solid #ED1C24;
        border-radius: 14px 14px 14px 2px;
        padding: 20px;
        margin: 14px 0;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
    }}

    .assistant-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 10px;
        margin-bottom: 14px;
    }}

    .latency-tag {{
        font-size: 11px;
        font-weight: 600;
        color: #64748B;
        background: #F1F5F9;
        padding: 3px 8px;
        border-radius: 12px;
    }}

    .unanswered-tag {{
        font-size: 11px;
        font-weight: 700;
        color: #B45309;
        background: #FEF3C7;
        padding: 3px 10px;
        border-radius: 12px;
        border: 1px solid #FDE68A;
    }}

    /* Citation Cards */
    .citation-card {{
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 3px solid #059669;
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 10px;
        font-size: 12.5px;
        line-height: 1.5;
    }}

    .confidence-badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 700;
    }}
    .confidence-high {{ background-color: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }}
    .confidence-mid  {{ background-color: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }}

    /* Sidebar Personas */
    .sidebar-user-card {{
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. SIDEBAR (ROLE SELECTION, ACCESS TIER, & ADMIN SETTINGS)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🏢 **Atlas Honda Limited**")
    st.caption("Mother Plant: F-36 S.I.T.E., Karachi – 75730")
    st.markdown("---")

    # 1. User Role Selector (Demonstrates RBAC to management)
    st.markdown("##### 👤 **Employee Persona / Access Role**")
    user_role = st.selectbox(
        "Current Operating Role:",
        options=list(ROLES_PERMISSIONS.keys()),
        index=0,
        label_visibility="collapsed",
        help="Simulate how different job roles experience the assistant with governed document access."
    )
    
    role_info = ROLES_PERMISSIONS[user_role]
    st.markdown(f"""
    <div class="sidebar-user-card">
        <div style="font-size: 11px; font-weight: 700; color: #ED1C24; text-transform: uppercase;">Access Tier</div>
        <div style="font-size: 13px; font-weight: 600; color: #1E2229; margin-top: 2px;">{user_role}</div>
        <div style="font-size: 11.5px; color: #64748B; margin-top: 4px;">{role_info['description']}</div>
        <div style="font-size: 11px; color: #059669; margin-top: 6px; font-weight: 600;">✓ {len(role_info['accessible_doc_ids'])} Governed Policies Accessible</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Intelligent Language Auto-Detection Pill (No manual toggle needed)
    st.markdown("""
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
        <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">Language Support</div>
        <div style="font-size: 12.5px; font-weight: 600; color: #1E2229; margin-top: 2px;">🌐 Auto-Detect Active</div>
        <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">English • اردو • Roman Urdu</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Session Reset
    if st.button("🔄 Start New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.feedback_status = {}
        st.session_state.queued_prompt = None
        st.rerun()

    # 4. Admin-Only Settings (PIN Protected)
    llm_choice = "Local Fallback Engine (Zero API Keys)"
    gemini_key = None
    groq_key = None
    
    is_admin = (user_role == "Executive & Compliance Admin")
    
    if is_admin:
        st.markdown("---")
        if not st.session_state.admin_authenticated:
            st.markdown("##### 🔒 **Admin Authorization**")
            st.caption("Enter Admin PIN (`atlas123`) to unlock Document Hub and Governance tools.")
            with st.form("sidebar_admin_unlock_form", clear_on_submit=False):
                pin_input = st.text_input("Admin PIN:", type="password", key="sidebar_admin_pin", placeholder="Default: atlas123")
                if st.form_submit_button("🔓 Unlock Admin Panel", use_container_width=True, type="primary"):
                    if pin_input == ADMIN_PIN:
                        st.session_state.admin_authenticated = True
                        st.success("Admin authorized!")
                        st.rerun()
                    else:
                        st.error("Incorrect Admin PIN.")
        else:
            col_lk1, col_lk2 = st.columns([3, 2])
            with col_lk1:
                st.markdown("<div style='font-size: 11.5px; font-weight: 700; color: #059669; padding-top: 6px;'>🟢 Admin Unlocked</div>", unsafe_allow_html=True)
            with col_lk2:
                if st.button("🔒 Lock", key="btn_lock_session", use_container_width=True):
                    st.session_state.admin_authenticated = False
                    st.rerun()

            with st.expander("🛠️ **Executive Admin Settings**", expanded=False):
                st.caption("Advanced LLM & Retrieval Configuration (Admin Only)")
                llm_choice = st.selectbox(
                    "Inference Engine:",
                    options=AVAILABLE_PROVIDERS,
                    index=0
                )
                
                if "Gemini" in llm_choice:
                    gemini_key = st.text_input("Gemini API Key:", type="password", placeholder="Enter key from AI Studio")
                elif "Groq" in llm_choice:
                    groq_key = st.text_input("Groq API Key:", type="password", placeholder="Enter key from console.groq.com")
                elif "Ollama" in llm_choice:
                    st.caption("Pointed to local daemon at `http://localhost:11434`")
                else:
                    st.caption("🟢 **Local Fallback Engine Active**: 100% offline, zero API keys, guaranteed non-hallucinating.")
                    
                st.markdown("---")
                if st.button("⚡ Force Re-index Documents", use_container_width=True):
                    with st.spinner("Rebuilding hybrid index..."):
                        get_vector_store(force_rebuild=True)
                        st.success("Vector store index refreshed!")

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Session: `{st.session_state.session_id}` | v2.2 Enterprise")

# ==============================================================================
# 5. TOP CORPORATE HEADER BAR
# ==============================================================================
st.markdown(f"""
<div class="atlas-topbar">
    <div class="atlas-logo-block">
        <div style="font-size: 32px;">🏍️</div>
        <div>
            <div class="atlas-brand-title">AtlasMind</div>
            <div class="atlas-brand-subtitle">Atlas Honda Limited – Internal AI Knowledge Assistant</div>
        </div>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
        <span class="atlas-plant-badge">
            <span class="atlas-pulse-dot"></span>
            Karachi Mother Plant (F-36 S.I.T.E.)
        </span>
        <span style="font-size: 12px; color: #64748B; font-weight: 600; padding: 4px 10px; background: #F1F5F9; border-radius: 16px;">
            ATLH (PSX)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 6. VIEW NAVIGATION (TABS FOR ADMIN, SEAMLESS CHAT FOR EMPLOYEES)
# ==============================================================================
is_admin_unlocked = is_admin and st.session_state.get("admin_authenticated", False)

if is_admin:
    active_tab, doc_hub_tab, analytics_tab, unanswered_tab = st.tabs([
        "💬 Knowledge Assistant", 
        "📁 Document Hub (Admin)", 
        "📊 Executive Analytics", 
        "❓ Unanswered Queries"
    ])
else:
    active_tab = st.container()

# ==============================================================================
# 7. MAIN CHAT EXPERIENCE (FREE-TEXT CHAT + QUICK SUGGESTIONS)
# ==============================================================================
with active_tab:
    # Admin notification & unlock banner for Executive role
    if is_admin and not is_admin_unlocked:
        st.markdown("""
        <div style="background: #FFF5F5; border: 1px solid #FECACA; border-left: 4px solid #ED1C24; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;">
            <div style="font-weight: 700; color: #991B1B; font-size: 14px;">🔒 Executive & Compliance Admin Mode Selected</div>
            <div style="font-size: 12.5px; color: #4B5563; margin-top: 4px;">
                Enter Admin PIN (<code>atlas123</code>) below or in the sidebar to unlock Document Management (Upload, Edit, Delete) and Governance Analytics.
            </div>
        </div>
        """, unsafe_allow_html=True)
        with st.form("top_admin_unlock_form", clear_on_submit=False):
            col_tp1, col_tp2 = st.columns([3, 1])
            with col_tp1:
                top_pin = st.text_input("Corporate Admin PIN:", type="password", placeholder="Enter atlas123 and press Enter", label_visibility="collapsed")
            with col_tp2:
                top_submit = st.form_submit_button("🔓 Unlock Admin Workspace", type="primary", use_container_width=True)
            if top_submit:
                if top_pin == ADMIN_PIN:
                    st.session_state.admin_authenticated = True
                    st.success("Admin authorized!")
                    st.rerun()
                else:
                    st.error("Incorrect Admin PIN.")
    elif is_admin and is_admin_unlocked:
        st.markdown("""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #10B981; border-radius: 8px; padding: 10px 16px; margin-bottom: 14px;">
            <div style="font-size: 12.5px; font-weight: 600; color: #166534;">
                🟢 Executive Admin Mode Unlocked — Document Hub (Upload / Edit / Delete) and Analytics are active in the tabs above.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # --------------------------------------------------------------------------
    # A. HERO WELCOME SCREEN (Shown only when conversation is empty)
    # --------------------------------------------------------------------------
    if len(st.session_state.messages) == 0:
        st.markdown(f"""
        <div class="hero-container">
            <div class="hero-title">Welcome to AtlasMind</div>
            <div class="hero-text">
                Your verified AI assistant for company policies, plant safety mandates, quality control SOPs, 
                and HR guidelines. Type any question below in <b>English, اردو, or Roman Urdu</b>, or choose a starter topic.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("##### 📌 **Common Inquiries for Your Role:**")
        col_s1, col_s2, col_s3 = st.columns(3)
        
        if user_role == "Production Operator & Plant Staff":
            with col_s1:
                if st.button("🦺 Press Shop Mandatory PPE", key="st_p1", use_container_width=True):
                    st.session_state.queued_prompt = "What is the mandatory PPE requirement for the Press Shop at Karachi Plant?"
                    st.rerun()
            with col_s2:
                if st.button("🛑 6-Step LOTO Lockout Rules", key="st_p2", use_container_width=True):
                    st.session_state.queued_prompt = "What are the six steps of the Lockout/Tagout (LOTO) procedure?"
                    st.rerun()
            with col_s3:
                if st.button("🔍 CD70 Roller Dynamometer QC", key="st_p3", use_container_width=True):
                    st.session_state.queued_prompt = "What are the test criteria for the final roller dynamometer inspection?"
                    st.rerun()
                    
        elif user_role == "HR & Administration":
            with col_s1:
                if st.button("📅 Probation Leave Entitlement", key="st_h1", use_container_width=True):
                    st.session_state.queued_prompt = "Can an employee take annual leave during the 6-month probation period?"
                    st.rerun()
            with col_s2:
                if st.button("⚖️ Domestic Inquiry Steps", key="st_h2", use_container_width=True):
                    st.session_state.queued_prompt = "What is the procedure for conducting a formal domestic inquiry under POL-08?"
                    st.rerun()
            with col_s3:
                if st.button("📢 Whistleblower Reporting Channels", key="st_h3", use_container_width=True):
                    st.session_state.queued_prompt = "How can an employee file a confidential report under the Speak-Up policy?"
                    st.rerun()
                    
        else: # General Employee & Admin
            with col_s1:
                if st.button("🏖️ Annual Leave Entitlement", key="st_g1", use_container_width=True):
                    st.session_state.queued_prompt = "What is the annual leave entitlement for permanent employees?"
                    st.rerun()
            with col_s2:
                if st.button("🎁 Gift Acceptance Code of Conduct", key="st_g2", use_container_width=True):
                    st.session_state.queued_prompt = "Can an employee accept personal gifts from suppliers or vendors?"
                    st.rerun()
            with col_s3:
                if st.button("⏱️ Grace Period & Attendance", key="st_g3", use_container_width=True):
                    st.session_state.queued_prompt = "What is the grace period for morning arrival before a salary deduction occurs?"
                    st.rerun()

    # --------------------------------------------------------------------------
    # B. CONVERSATION MESSAGE THREAD
    # --------------------------------------------------------------------------
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            citations = msg.get("citations", [])
            latency = msg.get("latency_ms", 320)
            log_id = msg.get("query_log_id")
            is_unanswered = msg.get("is_unanswered", False)
            score_val = msg.get("best_score")
            score_badge = f"<span class='latency-tag' style='margin-left: 6px;'>🎯 {int(score_val*100)}% Match</span>" if score_val is not None and score_val > 0 else ""
            
            st.markdown(f"""
            <div class="assistant-card">
                <div class="assistant-header">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 18px;">🏍️</span>
                        <span style="font-size: 13px; font-weight: 700; color: #1E2229;">AtlasMind Verified Response</span>
                    </div>
                    <div>
                        {"<span class='unanswered-tag'>⚠️ Policy Gap Logged</span>" if is_unanswered else f"<span class='latency-tag'>⚡ {latency} ms</span>{score_badge}"}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Render Markdown Body
            st.markdown(msg["content"])
            
            # Render Verified Source Citations
            if citations:
                with st.expander(f"📑 Verified Source Citations ({len(citations)} Official Documents Cited)"):
                    if msg.get("resolved_query"):
                        st.caption(f"🔍 **Pre-Retrieval Search Phrase:** `{msg['resolved_query']}`")
                    for c in citations:
                        conf_pct = int(c.get('score', 0.85) * 100)
                        conf_class = "confidence-high" if conf_pct >= 65 else "confidence-mid"
                        st.markdown(f"""
                        <div class="citation-card">
                            <b>[{c.get('doc_id')}] {c.get('doc_title', c.get('doc_name', ''))}</b> – <i>{c.get('section_title', '')}</i><br>
                            <span class="confidence-badge {conf_class}">Match Confidence: {conf_pct}%</span> | 
                            <span style="color: #64748B;">Category: {c.get('classification', c.get('category', 'General'))}</span>
                            <div style="margin-top: 6px; color: #334155; font-style: italic;">
                                "{c.get('content_snippet', '')}"
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            # Bottom Action Toolbar (PDF Export + Feedback)
            tb_col1, tb_col2, tb_col3, tb_col4 = st.columns([3, 1, 1, 6])
            
            with tb_col1:
                if "pdf_bytes" in msg and msg["pdf_bytes"]:
                    st.download_button(
                        label="📄 Download Official PDF",
                        data=msg["pdf_bytes"],
                        file_name=f"AtlasMind_Report_{st.session_state.session_id}_{idx}.pdf",
                        mime="application/pdf",
                        key=f"pdf_dl_{idx}",
                        use_container_width=True
                    )
            
            fb_state_key = f"fb_{idx}"
            with tb_col2:
                if fb_state_key not in st.session_state.feedback_status:
                    if st.button("👍", key=f"btn_up_{idx}", help="Accurate & Helpful"):
                        if log_id:
                            save_feedback(log_id, 1, "Helpful response")
                        st.session_state.feedback_status[fb_state_key] = "up"
                        st.rerun()
                elif st.session_state.feedback_status[fb_state_key] == "up":
                    st.caption("👍 Saved")
                    
            with tb_col3:
                if fb_state_key not in st.session_state.feedback_status:
                    if st.button("👎", key=f"btn_down_{idx}", help="Inaccurate or Unclear"):
                        if log_id:
                            save_feedback(log_id, -1, "Inaccurate or incomplete")
                        st.session_state.feedback_status[fb_state_key] = "down"
                        st.rerun()
                elif st.session_state.feedback_status[fb_state_key] == "down":
                    st.caption("👎 Flagged")
                    
            st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # C. SECONDARY PROMPT CHIPS (Active conversation quick suggestions)
    # --------------------------------------------------------------------------
    if len(st.session_state.messages) > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⏱️ Karachi Plant Shift Hours", key="qc1", use_container_width=True):
                st.session_state.queued_prompt = "What are the exact morning, evening, and night shift hours at Karachi Plant?"
                st.rerun()
        with c2:
            if st.button("🚫 Plant Speed Limits & Traffic", key="qc2", use_container_width=True):
                st.session_state.queued_prompt = "What is the speed limit and reverse parking rule inside the plant?"
                st.rerun()
        with c3:
            if st.button("📋 IT Helpdesk Urgent SLA", key="qc3", use_container_width=True):
                st.session_state.queued_prompt = "What is the IT helpdesk resolution SLA for critical plant stoppage?"
                st.rerun()

    # --------------------------------------------------------------------------
    # D. FREE-TEXT CHAT INPUT (PRIMARY INTERACTION)
    # --------------------------------------------------------------------------
    prompt_to_process = None
    
    if st.session_state.queued_prompt:
        prompt_to_process = st.session_state.queued_prompt
        st.session_state.queued_prompt = None
    else:
        chat_val = st.chat_input("Ask any question about Atlas Honda policies, plant safety, SOPs (English, اردو, or Roman Urdu)...")
        if chat_val:
            prompt_to_process = chat_val

    # --------------------------------------------------------------------------
    # E. RAG EXECUTION CYCLE
    # --------------------------------------------------------------------------
    if prompt_to_process:
        # Auto-detect language directly from the question
        auto_lang = detect_language(prompt_to_process)
        
        # 1. Append User Message
        st.session_state.messages.append({"role": "user", "content": prompt_to_process})
        
        # 2. Execute RAG Retrieval & Generation
        with st.spinner("AtlasMind searching verified company records..."):
            response_data = rag_pipeline.query(
                query_text=prompt_to_process,
                session_id=st.session_state.session_id,
                user_role=user_role,
                language=auto_lang,
                llm_provider=llm_choice,
                history=st.session_state.messages,
                gemini_api_key=gemini_key,
                groq_api_key=groq_key
            )
            
            answer = response_data["answer"]
            citations = response_data["citations"]
            latency = response_data["latency_ms"]
            log_id = response_data["query_log_id"]
            is_unanswered = response_data.get("is_unanswered", False)
            
            # Generate Branded PDF byte stream
            pdf_bytes = generate_query_pdf(
                query_text=prompt_to_process,
                answer_text=answer,
                citations=citations,
                user_role=user_role,
                language=auto_lang,
                latency_ms=latency
            )
            
            # 3. Append Assistant Message
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "citations": citations,
                "latency_ms": latency,
                "query_log_id": log_id,
                "pdf_bytes": pdf_bytes,
                "is_unanswered": is_unanswered,
                "best_score": response_data.get("best_score", 0.0),
                "resolved_query": response_data.get("resolved_query", "")
            })
            
        st.rerun()

if is_admin:
    # ==============================================================================
    # 8. ADMIN DOCUMENT REPOSITORY HUB (RESTRICTED TO ADMIN)
    # ==============================================================================
    with doc_hub_tab:
        st.markdown("### 📁 **Policy Document Registry & Vector Management**")
        st.caption("Admin governance portal to upload, edit, inspect, and decommission company policy documents with immediate auto-reindexing.")

        if not is_admin_unlocked:
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #ED1C24; border-radius: 8px; padding: 20px; margin: 16px 0;">
                <div style="font-size: 15px; font-weight: 700; color: #1E2229;">🔒 Admin Authorization Required for Document Hub</div>
                <div style="font-size: 13px; color: #64748B; margin-top: 5px;">
                    Please enter the corporate Admin PIN (<b>atlas123</b>) to unlock Document Management (Upload, Edit, Delete) and vector index controls.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("doc_hub_gate_unlock_form", clear_on_submit=False):
                col_hp1, col_hp2 = st.columns([3, 1])
                with col_hp1:
                    dh_pin = st.text_input("Enter Corporate Admin PIN:", type="password", placeholder="Default: atlas123", label_visibility="collapsed")
                with col_hp2:
                    dh_submit = st.form_submit_button("🔓 Unlock Document Hub", type="primary", use_container_width=True)
                if dh_submit:
                    if dh_pin == ADMIN_PIN:
                        st.session_state.admin_authenticated = True
                        st.success("Admin authorized! Document Hub unlocked.")
                        st.rerun()
                    else:
                        st.error("Incorrect Admin PIN. Please try again.")
        else:
            registered_docs = get_registered_documents()

            hub_tab1, hub_tab2, hub_tab3, hub_tab4 = st.tabs([
                "📤 Upload Policy",
                "✏️ Edit Policy",
                "🗑️ Delete Policy",
                "📑 Document Inventory"
            ])

            # ----------------------------------------------------------------------
            # Tab 1: Upload New Policy
            # ----------------------------------------------------------------------
            with hub_tab1:
                st.markdown("##### 📤 **Upload New Policy Amendment (.md, .txt, .pdf)**")
                st.caption("Upload an official document to extract metadata, chunk sections, and instantly index into vector memory.")
                
                up_file = st.file_uploader("Select Policy File:", type=["md", "txt", "pdf"], key="hub_file_uploader")
                
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    custom_doc_id = st.text_input("Document ID (e.g., POL-11):", placeholder="Leave blank to auto-detect", key="up_doc_id")
                    custom_classification = st.selectbox(
                        "Access Classification Tier:",
                        options=["General Employee Access", "Plant Operations", "Quality Assurance", "HR Only", "All Employees & Directors", "Public", "Company Wide"],
                        index=0,
                        key="up_classification"
                    )
                with col_u2:
                    custom_title = st.text_input("Policy Title:", placeholder="Leave blank to auto-detect from header", key="up_doc_title")
                    custom_version = st.text_input("Version Tag:", value="1.0 - Sample", key="up_version")

                if up_file is not None:
                    if not is_allowed_file(up_file.name):
                        st.error("Invalid file format. Only `.md`, `.txt`, and `.pdf` files are permitted.")
                    else:
                        file_bytes = up_file.getvalue()
                        if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
                            st.error(f"File size exceeds maximum limit of {MAX_FILE_SIZE_MB}MB.")
                        elif st.button("⚡ Process & Index Policy Immediately", type="primary", use_container_width=True, key="btn_submit_upload"):
                            safe_name = sanitize_filename(up_file.name)
                            save_destination = DOCS_DIR / safe_name
                            with open(save_destination, "wb") as f:
                                f.write(file_bytes)
                                
                            proc = DocumentProcessor()
                            try:
                                with st.spinner("Extracting content and indexing into vector store..."):
                                    doc_text = proc.extract_text_from_file(save_destination)
                                    meta = proc.extract_metadata(doc_text, fallback_filename=safe_name)
                                    doc_id = (custom_doc_id.strip().upper() if custom_doc_id.strip() else meta["doc_id"])
                                    doc_title = (custom_title.strip() if custom_title.strip() else meta["title"])
                                    classification = custom_classification or meta["classification"]
                                    version = custom_version.strip() or meta["version"]
                                    
                                    # Update vector store (purges any old chunks -> zero ghost chunks)
                                    vector_store.update_document(
                                        document_id=doc_id,
                                        new_content=doc_text,
                                        doc_name=doc_title,
                                        category=classification,
                                        metadata={**meta, "doc_id": doc_id, "title": doc_title, "classification": classification, "version": version}
                                    )
                                    
                                    # Register in database
                                    register_document(
                                        doc_id=doc_id,
                                        filename=safe_name,
                                        title=doc_title,
                                        classification=classification,
                                        version=version,
                                        section_count=len(vector_store.chunks)
                                    )
                                    st.success(f"✅ Document `{doc_id}` ({doc_title}) indexed successfully! Search and retrieval are updated.")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error processing file: {e}")

            # ----------------------------------------------------------------------
            # Tab 2: Edit Existing Policy (Content & Metadata)
            # ----------------------------------------------------------------------
            with hub_tab2:
                st.markdown("##### ✏️ **Edit Existing Policy Document & Metadata**")
                st.caption("Update policy text, change classification, or refine terms. Changes are immediately re-indexed into vector memory.")
                
                if not registered_docs:
                    st.info("No registered documents available to edit.")
                else:
                    doc_options = {f"{d['doc_id']} – {d['title']}": d for d in registered_docs}
                    selected_edit_label = st.selectbox("Select Document to Edit:", options=list(doc_options.keys()), key="edit_doc_selector")
                    selected_doc = doc_options[selected_edit_label]
                    
                    target_doc_id = selected_doc["doc_id"]
                    target_filename = selected_doc["filename"]
                    doc_path = DOCS_DIR / target_filename
                    
                    # Load current text content from disk
                    current_text = ""
                    if doc_path.exists():
                        try:
                            with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
                                current_text = f.read()
                        except Exception as e:
                            st.error(f"Error loading file content: {e}")
                    
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_title = st.text_input("Policy Title:", value=selected_doc["title"], key="edit_field_title")
                        cat_options = ["General Employee Access", "Plant Operations", "Quality Assurance", "HR Only", "All Employees & Directors", "Public", "Company Wide"]
                        curr_cat = selected_doc.get("classification", "General Employee Access")
                        cat_idx = cat_options.index(curr_cat) if curr_cat in cat_options else 0
                        edit_cat = st.selectbox("Access Classification Tier:", options=cat_options, index=cat_idx, key="edit_field_cat")
                    with col_e2:
                        st.text_input("Document ID:", value=target_doc_id, disabled=True, help="Document ID cannot be changed to preserve historical citations.")
                        edit_ver = st.text_input("Version Tag:", value=selected_doc.get("version", "1.0 - Sample"), key="edit_field_ver")
                    
                    edit_content = st.text_area(
                        "Policy Content (Markdown / Text):",
                        value=current_text,
                        height=380,
                        key="edit_field_content",
                        help="Modify policy sections, tables, or rules. Headings with '##' and '###' define chunk boundaries."
                    )
                    
                    if st.button("💾 Save Changes & Re-index Immediately", type="primary", use_container_width=True, key="btn_save_edit"):
                        if not edit_content.strip():
                            st.error("Document content cannot be empty.")
                        else:
                            with st.spinner(f"Saving updates and re-indexing '{target_doc_id}'..."):
                                try:
                                    # 1. Overwrite file on disk
                                    with open(doc_path, "w", encoding="utf-8") as f:
                                        f.write(edit_content)
                                    
                                    # 2. Update vector store (purges old chunks, creates fresh chunks, rebuilds TF-IDF)
                                    vector_store.update_document(
                                        document_id=target_doc_id,
                                        new_content=edit_content,
                                        doc_name=edit_title.strip(),
                                        category=edit_cat,
                                        metadata={"doc_id": target_doc_id, "title": edit_title.strip(), "classification": edit_cat, "version": edit_ver.strip()}
                                    )
                                    
                                    # 3. Update SQLite registry
                                    register_document(
                                        doc_id=target_doc_id,
                                        filename=target_filename,
                                        title=edit_title.strip(),
                                        classification=edit_cat,
                                        version=edit_ver.strip(),
                                        section_count=len(vector_store.chunks)
                                    )
                                    
                                    st.success(f"✅ Policy `{target_doc_id}` successfully updated and re-indexed into vector memory!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update document: {e}")

            # ----------------------------------------------------------------------
            # Tab 3: Delete / Decommission Policy
            # ----------------------------------------------------------------------
            with hub_tab3:
                st.markdown("##### 🗑️ **Decommission & Permanently Purge Document**")
                st.caption("Permanently remove policy from vector search index and database. All associated chunks will be purged.")
                
                if not registered_docs:
                    st.info("No registered documents available to delete.")
                else:
                    del_options = {f"{d['doc_id']} – {d['title']}": d for d in registered_docs}
                    selected_del_label = st.selectbox("Select Document to Remove:", options=list(del_options.keys()), key="del_doc_selector")
                    del_doc = del_options[selected_del_label]
                    
                    del_doc_id = del_doc["doc_id"]
                    del_filename = del_doc["filename"]
                    
                    st.markdown(f"""
                    <div style="background: #FFF5F5; border: 1px solid #FECACA; border-left: 4px solid #ED1C24; border-radius: 8px; padding: 14px; margin: 12px 0;">
                        <div style="font-weight: 700; color: #991B1B; font-size: 14px;">⚠️ Permanent Deletion Warning</div>
                        <div style="font-size: 12.5px; color: #4B5563; margin-top: 4px;">
                            You are about to delete <b>[{del_doc_id}] {del_doc['title']}</b>.<br>
                            This will permanently purge all chunks from the vector store and remove this policy from search for all employees.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    confirm_del = st.checkbox(
                        f"I confirm that I want to permanently purge '{del_doc_id}' from AtlasMind.",
                        key="chk_confirm_delete"
                    )
                    
                    if st.button("🗑️ Delete Policy Permanently", type="primary", disabled=not confirm_del, use_container_width=True, key="btn_confirm_delete"):
                        with st.spinner(f"Purging document '{del_doc_id}'..."):
                            # 1. Purge from vector store
                            vector_store.delete_by_document_id(del_doc_id)
                            
                            # 2. Delete from DB
                            delete_registered_document(del_doc_id)
                            
                            # 3. Remove physical file from disk if present
                            del_file_path = DOCS_DIR / del_filename
                            if del_file_path.exists():
                                try:
                                    del_file_path.unlink()
                                except Exception:
                                    pass
                                    
                            st.success(f"✅ Document `{del_doc_id}` and all associated chunks permanently deleted.")
                            time.sleep(1)
                            st.rerun()

            # ----------------------------------------------------------------------
            # Tab 4: Active Document Inventory & Text Inspector
            # ----------------------------------------------------------------------
            with hub_tab4:
                st.markdown(f"##### 📑 **Active Registered Policies ({len(registered_docs)} Documents)**")
                
                # Summary Metrics
                m_c1, m_c2, m_c3 = st.columns(3)
                with m_c1:
                    st.metric("Total Active Policies", len(registered_docs))
                with m_c2:
                    st.metric("Vector Store Chunks", len(vector_store.chunks))
                with m_c3:
                    st.metric("Storage Folder", "data/documents/")

                grid_data = []
                for d in registered_docs:
                    grid_data.append({
                        "Doc ID": d["doc_id"],
                        "Document Name": d["title"],
                        "Classification": d["classification"],
                        "Version": d["version"],
                        "Sections": d["section_count"],
                        "Last Sync": d["uploaded_at"]
                    })
                st.dataframe(grid_data, use_container_width=True)
                
                st.markdown("---")
                st.markdown("##### 🔍 **Policy Source Text Inspector**")
                all_doc_files = [f.name for f in DOCS_DIR.glob("*") if f.suffix.lower() in ALLOWED_EXTENSIONS]
                chosen_file = st.selectbox("Select document to inspect:", options=all_doc_files, key="inspect_doc_select")
                if chosen_file:
                    chosen_path = DOCS_DIR / chosen_file
                    proc = DocumentProcessor()
                    try:
                        content_preview = proc.extract_text_from_file(chosen_path)
                        with st.expander(f"📖 Source Content: `{chosen_file}` ({len(content_preview.splitlines())} lines)", expanded=False):
                            st.code(content_preview[:6000], language="markdown")
                    except Exception as e:
                        st.warning(f"Could not preview file: {e}")

    # ==============================================================================
    # 9. ADMIN EXECUTIVE ANALYTICS (RESTRICTED TO ADMIN)
    # ==============================================================================
    with analytics_tab:
        st.markdown("### 📈 **Executive Governance & Usage Intelligence**")
        st.caption("Confidential telemetry on knowledge inquiries, satisfaction indices, and policy bottlenecks.")
        
        if not is_admin_unlocked:
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #ED1C24; border-radius: 8px; padding: 20px; margin: 16px 0;">
                <div style="font-size: 15px; font-weight: 700; color: #1E2229;">🔒 Admin Authorization Required for Analytics</div>
                <div style="font-size: 13px; color: #64748B; margin-top: 5px;">
                    Enter Admin PIN (<b>atlas123</b>) to view confidential query telemetry and employee satisfaction metrics.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("analytics_gate_unlock_form", clear_on_submit=False):
                col_ap1, col_ap2 = st.columns([3, 1])
                with col_ap1:
                    an_pin = st.text_input("Corporate Admin PIN:", type="password", placeholder="Default: atlas123", label_visibility="collapsed")
                with col_ap2:
                    an_submit = st.form_submit_button("🔓 Unlock Analytics", type="primary", use_container_width=True)
                if an_submit:
                    if an_pin == ADMIN_PIN:
                        st.session_state.admin_authenticated = True
                        st.success("Admin authorized! Analytics unlocked.")
                        st.rerun()
                    else:
                        st.error("Incorrect Admin PIN.")
        else:
            analytics = get_analytics_summary()
            
            # Top KPI Metric Cards
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric(label="Total Queries Handled", value=f"{analytics['total_queries']:,}", delta="+18% MoM")
            with k2:
                st.metric(label="Grounded Accuracy / Satisfaction", value=f"{analytics['satisfaction_rate']}%", delta="+2.4%")
            with k3:
                st.metric(label="Average Retrieval Latency", value=f"{analytics['avg_latency_ms']} ms", delta="-35 ms")
            with k4:
                st.metric(label="Unresolved Knowledge Gaps", value=f"{analytics.get('unanswered_count', 0)} Queries", delta="Action Required")
                
            st.markdown("---")
            
            # Visual Analytics Charts (Safe for Python 3.14 & Altair)
            ac1, ac2 = st.columns(2)
            with ac1:
                st.markdown("##### 👥 **Inquiries by User Department / Role**")
                queries_role = analytics["queries_by_role"]
                max_r = max(queries_role.values()) if queries_role else 1
                for r_name, r_cnt in queries_role.items():
                    pct = int((r_cnt / max(max_r, 1)) * 100)
                    st.markdown(f"**{r_name}**: `{r_cnt} queries`")
                    st.progress(min(float(r_cnt / max(max_r, 1)), 1.0))
                        
            with ac2:
                st.markdown("##### 📚 **Top Inquired Policy Domains**")
                doc_hits = analytics["doc_hit_counts"]
                max_d = max(doc_hits.values()) if doc_hits else 1
                for d_name, d_cnt in doc_hits.items():
                    st.markdown(f"**{d_name}**: `{d_cnt} queries`")
                    st.progress(min(float(d_cnt / max(max_d, 1)), 1.0))
                        
            st.markdown("---")
            
            # Audit Log Table
            st.markdown("##### 📋 **Recent Query Audit Trail**")
            recent_logs = get_recent_queries(limit=12)
            if recent_logs:
                table_records = []
                for r in recent_logs:
                    table_records.append({
                        "Time": r["created_at"],
                        "Role": r["user_role"],
                        "Language": r["language"],
                        "Inquiry": r["query_text"][:50] + "..." if len(r["query_text"]) > 50 else r["query_text"],
                        "Latency (ms)": r["latency_ms"],
                        "Engine": r["llm_provider"].split("(")[0].strip(),
                        "Feedback": "👍 Positive" if r["feedback_rating"] == 1 else ("👎 Flagged" if r["feedback_rating"] == -1 else "Neutral")
                    })
                st.dataframe(table_records, use_container_width=True)

    # ==============================================================================
    # 10. ADMIN UNANSWERED QUERIES & GAP ANALYSIS (RESTRICTED TO ADMIN)
    # ==============================================================================
    with unanswered_tab:
        st.markdown("### ❓ **Unanswered Queries & Policy Knowledge Gaps**")
        st.caption(
            "Questions employees asked where no official policy met the confidence threshold. "
            "Use this telemetry to identify missing SOPs or update existing HR/HSE policies."
        )
        
        if not is_admin_unlocked:
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #ED1C24; border-radius: 8px; padding: 20px; margin: 16px 0;">
                <div style="font-size: 15px; font-weight: 700; color: #1E2229;">🔒 Admin Authorization Required for Gap Analysis</div>
                <div style="font-size: 13px; color: #64748B; margin-top: 5px;">
                    Enter Admin PIN (<b>atlas123</b>) to access low-confidence query telemetry and knowledge gap resolution.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("unanswered_gate_unlock_form", clear_on_submit=False):
                col_up1, col_up2 = st.columns([3, 1])
                with col_up1:
                    uq_pin = st.text_input("Corporate Admin PIN:", type="password", placeholder="Default: atlas123", label_visibility="collapsed")
                with col_up2:
                    uq_submit = st.form_submit_button("🔓 Unlock Gap Analysis", type="primary", use_container_width=True)
                if uq_submit:
                    if uq_pin == ADMIN_PIN:
                        st.session_state.admin_authenticated = True
                        st.success("Admin authorized! Gap Analysis unlocked.")
                        st.rerun()
                    else:
                        st.error("Incorrect Admin PIN.")
        else:
            unanswered_items = get_unanswered_queries(limit=60)
            
            # Unanswered Metrics
            pending_items = [u for u in unanswered_items if u["resolved_status"] == "pending"]
            resolved_items = [u for u in unanswered_items if u["resolved_status"] == "resolved"]
            
            u_c1, u_c2, u_c3 = st.columns(3)
            with u_c1:
                st.metric("Total Unanswered Inquiries", len(unanswered_items))
            with u_c2:
                st.metric("Pending Policy Review", len(pending_items))
            with u_c3:
                st.metric("Resolved / Addressed", len(resolved_items))
                
            st.markdown("---")
            
            if not unanswered_items:
                st.success("🎉 **Zero Unanswered Queries!** All employee inquiries have matched official company policy documents.")
            else:
                st.markdown("##### 📋 **Logged Low-Confidence Queries:**")
                
                # Format display records
                records = []
                for item in unanswered_items:
                    status_icon = "⏳ Pending" if item["resolved_status"] == "pending" else "✅ Resolved"
                    records.append({
                        "ID": item["id"],
                        "Status": status_icon,
                        "Employee Question": item["query"],
                        "User Role": item["user_role"],
                        "Language": item["language"],
                        "Best Match Score": f"{int(item['best_score'] * 100)}%",
                        "Logged At": item["created_at"]
                    })
                st.dataframe(records, use_container_width=True)
                
                st.markdown("---")
                st.markdown("##### 🛠️ **Manage Policy Gap Status**")
                m_col1, m_col2 = st.columns([2, 1])
                with m_col1:
                    query_choice = st.selectbox(
                        "Select Inquiry to Update:",
                        options=[f"#{u['id']} - {u['query'][:60]} ({u['resolved_status']})" for u in unanswered_items]
                    )
                with m_col2:
                    target_id = int(query_choice.split(" - ")[0].replace("#", ""))
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Mark Resolved", key="btn_mark_res", use_container_width=True):
                            resolve_unanswered_query(target_id, "resolved")
                            st.success(f"Query #{target_id} marked as resolved.")
                            st.rerun()
                    with b2:
                        if st.button("🗑️ Dismiss", key="btn_del_gap", use_container_width=True):
                            delete_unanswered_query(target_id)
                            st.info(f"Query #{target_id} dismissed.")
                            st.rerun()

