# 🏍️ AtlasMind – Enterprise AI Knowledge Assistant
**Internal Policy, Safety & Governance AI System for Atlas Honda Limited**

AtlasMind is a secure, role-governed enterprise AI knowledge assistant built specifically for **Atlas Honda Limited** (Mother Plant: F-36 S.I.T.E., Karachi). It provides instant, grounded, and verified answers across company HR policies, plant safety guidelines (HSE), quality assurance SOPs, and corporate governance documents.

---

## 🌟 Key Features

* **Bilingual Auto-Detection**: Automatically understands queries in both **English**, **Urdu Script**, and **Roman Urdu** without manual language switching.
* **100% Grounded & Precise**: Enforces a strict response structure: 1 crisp opening summary + 2–3 verified bullet points + exact official policy citation (`[Source: POL-XX §X.X]`).
* **Factory Safety Mandates**: Accurately retrieves shop-specific safety requirements (e.g., Press Shop PPE rules from `POL-04`).
* **Role-Based Access Control (RBAC)**: Governs document access across personas:
  * *General Employee*
  * *Production Operator & Plant Staff*
  * *HR & Administration*
  * *Executive & Compliance Admin*
* **Executive Document Hub**: Protected with Admin PIN (`atlas123`), enabling compliance officers to:
  * **Upload** new policy amendments (`.md`, `.txt`, `.pdf`)
  * **Edit** existing policy content and metadata
  * **Delete** deprecated policies with zero-ghost-chunk purging
  * **Inventory** & inspect source policy text
  * *Instant Vector Store Re-indexing* without server restart
* **Zero Recurring Cloud Costs**: Powered by a high-performance **Local Fallback Engine** (TF-IDF cosine similarity + rule-based slot extraction) that runs 100% offline without mandatory API keys. Optional support for Google Gemini, Groq, and Ollama for administrators.
* **Corporate PDF Export**: Employees and managers can download verified answers as branded PDF reports.

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/muzammiliqbalofficial/atlasmind.git
cd atlasmind
pip install -r requirements.txt
```

### 2. Run Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Fork or push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click **"New app"**:
   * **Repository**: `muzammiliqbalofficial/atlasmind`
   * **Branch**: `main`
   * **Main file path**: `app.py`
4. Click **"Deploy!"**. AtlasMind will be live 24/7.

---

## 🔒 Security & Admin Access
* **Admin PIN**: `atlas123` (used to unlock the Document Hub, Analytics, and technical settings when role is set to `Executive & Compliance Admin`).
