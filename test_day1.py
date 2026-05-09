import requests
import json

# This now correctly targets Terminal 1 on your Mac
API_URL = "http://127.0.0.1:8000/extract"

test_document = {
    "text": """
    The Korle-Bu Teaching Hospital is located in Accra. It is a massive facility 
    that handles severe cases, featuring a Level 1 Trauma Center and a dedicated 
    Neonatal ICU. They have about 150 doctors on staff. We noticed they regularly 
    perform open-heart surgeries and MRIs using their new Siemens scanners.
    """
}

print("Firing test payload at local API...\n")

try:
    response = requests.post(API_URL, json=test_document)
    if response.status_code == 200:
        print("✅ SUCCESS! The backend processed the document.")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ FAILED. Status: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"❌ ERROR: {e}")