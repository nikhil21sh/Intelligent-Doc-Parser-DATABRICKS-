"""
app.py — Databricks Apps entry point
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# ── Read Groq key from Databricks Secrets at startup ──────────────────────
# This runs inside the Apps container which has Databricks SDK pre-installed
# and is already authenticated via DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET
try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    secret_val = w.secrets.get_secret(
        scope = "medmap-secrets",
        key   = "GROQ_API_KEY"
    ).value
    # SDK returns base64 — decode it
    import base64
    os.environ["GROQ_API_KEY"] = base64.b64decode(secret_val).decode("utf-8")
    print("GROQ_API_KEY loaded from Databricks Secrets")
except Exception as e:
    print(f"Warning: could not load GROQ_API_KEY from secrets: {e}")
    # Fallback — will fail at extraction time but won't crash startup

os.environ.setdefault("INTERN1_API_BASE", "http://127.0.0.1:8000")

from backend.api.main import app  # your FastAPI app
