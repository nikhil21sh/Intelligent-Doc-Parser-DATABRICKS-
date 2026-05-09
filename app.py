"""
app.py — Databricks Apps entry point
Serves both the FastAPI backend and the built React frontend.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.api.main import app  # your FastAPI app