# API Contract: Intern 1 (Backend) <> Intern 2 (Agent)
1. GET `/search`
**Triggered by:** Agent `Retrieve` Node
* **Request:** `?q=string&region=string(optional)`
* **Response:** ```json
  {
    "query_confidence": 0.85,
    "facilities": [
      {
        "unique_id": "uuid",
        "name": "Zebilla District Hospital",
        "specialties": ["internalMedicine"],
        "equipment": ["backup power"],
        "capability": ["Level II trauma center"]
      }
    ]
  }
2. GET /anomalies
Triggered by: Agent Reason Node

Request: ?region=string(optional)

Response:

JSON
{
  "flags": [
    {
      "facility_id": "uuid",
      "flag_type": "missing_equipment",
      "confidence": 0.9,
      "reason_text": "Claims ICU but lacks backup power"
    }
  ]
}
3. GET /deserts
Triggered by: Agent Reason Node (Planning System Step 4)

Request: ?specialty=string&region=string

Response:

JSON
{
  "desert_zones": ["Northern"],
  "coverage_status": "zero_facilities_found"
}