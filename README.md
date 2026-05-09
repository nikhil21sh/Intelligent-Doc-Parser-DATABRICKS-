# MedMap AI: Bridging Medical Deserts 🌍🏥
**Live Demo:** [Insert your Databricks App URL here]
**Demo Video:** [Insert YouTube/Loom Link here]

## The Problem
By 2030, the world will face a shortage of 10 million healthcare workers. In regions like Ghana, a patient may be 200km from the nearest ICU, while critical medical resources remain siloed in unstructured text reports. 

## Our Solution
MedMap AI is an intelligent orchestration layer that reduces the time it takes to connect patients with lifesaving treatment. We built an **Intelligent Document Parsing (IDP) Agent** that extracts and verifies medical facility capabilities from messy, unstructured data to map medical deserts and coordinate resources.

**Key Features:**
* **Automated Extraction:** Uses few-shot prompting to extract procedures, equipment, and capabilities into structured Pydantic models.
* **Anomaly Detection:** Rule-based engine flags suspicious claims (e.g., claiming an ICU without backup power).
* **Agentic Orchestration:** A reasoning loop powered by LangGraph that plans interventions and identifies infrastructure gaps.
* **Step-Level Citations:** Every AI claim is traced back to specific facility row IDs using **MLflow**.

## Architecture & Tech Stack
Built natively on the Databricks ecosystem:
* **Data Layer:** Databricks **Delta Lake** for structured data and DBFS for raw file storage.
* **Backend:** FastAPI, LanceDB (Vector Search), and SentenceTransformers. Hosted via **Databricks Apps**.
* **AI & Orchestration:** **LangGraph**, Llama-3.3-70b, and **Databricks MLflow** for experiment tracking and step-level citation logging.
* **Frontend:** React, Vite, Tailwind CSS, and Leaflet.js.

## Running Locally
1. Clone the repository.
2. `cd frontend && npm install && npm run build`
3. `cd ../backend && pip install -r requirements.txt`
4. Create a `.env` file with your `GROQ_API_KEY`.
5. Run the FastAPI server: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
