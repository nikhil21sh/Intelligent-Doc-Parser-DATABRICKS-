"""
app.py — Databricks Apps entry point
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# ── Fix MLflow OAuth for Databricks Apps ──────────────────────────────────
# Databricks Apps uses OAuth (not PAT), so MLflow needs this flag set
# BEFORE any mlflow import happens anywhere in the codebase.
os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
os.environ["MLFLOW_TRACKING_URI"]      = "databricks"
# Disable MLflow autolog on Apps — it tries to connect at import time
os.environ["MLFLOW_DISABLE_AUTOLOG"]   = "true"
sys.path.insert(0, os.path.dirname(__file__))

# ── Load Groq key from Databricks Secrets ─────────────────────────────────
try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    secret_val = w.secrets.get_secret(
        scope="medmap-secrets",
        key="GROQ_API_KEY"
    ).value
    import base64
    os.environ["GROQ_API_KEY"] = base64.b64decode(secret_val).decode("utf-8")
    print("GROQ_API_KEY loaded from Databricks Secrets")
except Exception as e:
    print(f"Warning: could not load GROQ_API_KEY from secrets: {e}")

os.environ.setdefault("INTERN1_API_BASE", "http://127.0.0.1:8000")

from backend.api.main import app  # your FastAPI app
