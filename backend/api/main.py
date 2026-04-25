from fastapi import FastAPI, HTTPException
from models.models import FacilityFact
from idp.extraction import MedicalIDP

app = FastAPI(title="Virtue Foundation IDP API")
idp_engine = MedicalIDP()

@app.get("/health")
def check_health():
    return {"status": "online", "system": "Databricks-Accenture-IDP"}

@app.post("/extract")
async def process_document(text: str):
    try:
        extracted_data = idp_engine.extract_from_text(text)
        return {"status": "success", "data": extracted_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Placeholder for Day 3: Medical Desert Logic
@app.get("/analytics/deserts")
async def find_deserts(region: str):
    # Logic will go here to query Delta Lake
    return {"message": f"Analyzing medical deserts in {region}"}


@app.get("/facilities")
async def get_all_facilities():
    # This will eventually connect to Databricks SQL
    # For now, it returns a placeholder so the frontend can keep working
    return {"message": "Connection to Delta Lake successful", "data": []}