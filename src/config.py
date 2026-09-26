""" 
AtlasMind - Internal AI Knowledge Assistant for Atlas Honda Limited
Configuration and Constants
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "documents"
DB_PATH = DATA_DIR / "atlasmind.db"
EXPORTS_DIR = BASE_DIR / "exports"
STATIC_DIR = BASE_DIR / "static"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Retrieval & Guardrail Thresholds
CONFIDENCE_THRESHOLD = 0.28  # Calibrated for TF-IDF sublinear similarity (avoids false rejections)
ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf"}
MAX_FILE_SIZE_MB = 15

# Admin access must be configured through the deployment environment/secret store.
# There is intentionally no repository-shipped fallback credential.
ADMIN_PIN = os.getenv("ATLAS_ADMIN_PIN")

DEBUG_RETRIEVAL = True  # Print similarity scores to terminal for fine-tuning

# Brand Theme & Visual Tokens
THEME = {
    "brand_name": "AtlasMind",
    "company_name": "Atlas Honda Limited",
    "tagline": "Internal AI Knowledge Assistant",
    "primary_red": "#ED1C24",
    "dark_slate": "#1E2229",
    "accent_red": "#C00F17",
    "light_bg": "#F8F9FA",
    "card_bg": "#FFFFFF",
    "border_color": "#E2E8F0",
    "text_main": "#1A202C",
    "text_muted": "#718096",
    "plant_location": "Mother Plant: F-36, Estate Avenue, S.I.T.E., Karachi"
}

ROLES_PERMISSIONS = {
    "General Employee": {
        "description": "General office staff, dealership reps, and sales team",
        "allowed_categories": ["General Employee Access", "Plant Operations", "Public", "Company Wide"],
        "accessible_doc_ids": ["POL-01", "POL-02", "POL-03", "POL-04", "POL-05", "SOP-06", "POL-09", "SOP-10"]
    },
    "Production Operator & Plant Staff": {
        "description": "Plant floor operators, shift supervisors, QC inspectors, and maintenance technicians",
        "allowed_categories": ["General Employee Access", "Plant Operations", "Quality Assurance", "Public", "Company Wide"],
        "accessible_doc_ids": ["POL-01", "POL-02", "POL-03", "POL-04", "POL-05", "SOP-06", "SOP-07", "POL-09", "SOP-10"]
    },
    "HR & Administration": {
        "description": "Human resources executives, talent acquisition, and personnel officers",
        "allowed_categories": ["General Employee Access", "HR Only", "Public", "Company Wide"],
        "accessible_doc_ids": ["POL-01", "POL-02", "POL-03", "POL-05", "SOP-06", "POL-08", "POL-09", "SOP-10"]
    },
    "Executive & Compliance Admin": {
        "description": "Full access to corporate governance, plant operations, quality audit, and disciplinary records",
        "allowed_categories": ["General Employee Access", "Plant Operations", "Quality Assurance", "HR Only", "Public", "Company Wide", "Confidential"],
        "accessible_doc_ids": ["POL-01", "POL-02", "POL-03", "POL-04", "POL-05", "SOP-06", "SOP-07", "POL-08", "POL-09", "SOP-10"]
    }
}

LANGUAGES = {
    "English": "en",
    "اردو (Urdu Script)": "ur",
    "Roman Urdu": "roman_ur"
}

DEFAULT_LLM_PROVIDER = "Local Fallback Engine (Zero API Keys)"
AVAILABLE_PROVIDERS = [
    "Local Fallback Engine (Zero API Keys)",
    "Google Gemini Free API (Online)",
    "Groq High-Speed API (Online)",
    "Ollama Local Model (Local Server)"
]
