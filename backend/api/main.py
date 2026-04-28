from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import nest_asyncio
import uvicorn

# Corrected imports based on your repository structure
from models.models import FacilityFact
from backend.idp.extraction import MedicalIDP

app = FastAPI(title="Virtue Foundation IDP API")
idp_engine = MedicalIDP()

# Secure payload model to prevent URL length limits
class DocumentRequest(BaseModel):
    text: str

@app.get("/health")
def check_health():
    return {"status": "online", "system": "Databricks-Accenture-IDP"}

@app.post("/extract")
async def process_document(payload: DocumentRequest):
    try:
        extracted_data = idp_engine.extract_from_text(payload.text)
        return {"status": "success", "data": extracted_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/deserts")
async def find_deserts(region: str):
    # Logic will go here to query Delta Lake on Day 3
    return {"message": f"Analyzing medical deserts in {region}"}

@app.get("/facilities")
async def get_all_facilities():
    # Will eventually connect to Databricks SQL
    return {"message": "Connection to Delta Lake successful", "data": []}

# ==========================================
# DATABRICKS CLUSTER EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    # nest_asyncio prevents Databricks notebook cells from blocking the event loop
    nest_asyncio.apply()
    
    print("Starting FastAPI on Databricks Driver Node (Port 8000)...")
    # Bind to 0.0.0.0 so the internal Databricks proxy can route traffic to it
    uvicorn.run(app, host="0.0.0.0", port=8000)