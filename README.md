# 🏍️ AtlasMind – Enterprise AI Knowledge Assistant
**Internal Policy, Safety & Governance AI System for Atlas Honda Limited**

AtlasMind is a role-governed enterprise AI knowledge assistant built for an internal-policy use case at **Atlas Honda Limited**. It provides grounded answers across HR policies, plant safety guidelines, quality SOPs, and governance documents.

---

## 🌟 Key Features

* **Bilingual Auto-Detection**: Understands English, Urdu Script, and Roman Urdu.
* **Grounded Responses**: Returns answers with source-policy citations.
* **Role-Based Access Control (RBAC)** across General Employee, Plant Staff, HR, and Executive/Compliance personas.
* **Executive Document Hub** for policy upload, editing, deletion, inventory, and vector-store re-indexing.
* **Local Fallback Engine** using TF-IDF cosine similarity and rule-based extraction, with optional Gemini, Groq, and Ollama providers.
* **Corporate PDF Export** for generated answers.

---

## 🚀 Quickstart

```bash
git clone https://github.com/muzammiliqbalofficial/atlasmind.git
cd atlasmind
pip install -r requirements.txt
```

Configure an admin PIN through the environment. **No default admin credential is shipped in the repository.**

```bash
export ATLAS_ADMIN_PIN="choose-a-strong-local-secret"
streamlit run app.py
```

On Windows PowerShell:

```powershell
$env:ATLAS_ADMIN_PIN="choose-a-strong-local-secret"
streamlit run app.py
```

Open `http://localhost:8501`.

---

## ☁️ Streamlit Community Cloud

When deploying, add `ATLAS_ADMIN_PIN` through the deployment's secret/environment configuration rather than committing it to GitHub. Use a unique value for each deployment and rotate it if it is ever exposed.

---

## 🔒 Security Notes

* The repository intentionally contains **no fallback admin PIN**.
* `ATLAS_ADMIN_PIN` is read from the runtime environment.
* Never commit real credentials, API keys, or deployment secrets.
* The role selector demonstrates governed retrieval behavior; production deployments should use an identity provider and server-side authorization rather than treating a UI-selected role as identity.
