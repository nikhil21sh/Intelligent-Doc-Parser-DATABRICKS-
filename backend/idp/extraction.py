import os
import json
import time
import mlflow
import hashlib
import lancedb
from typing import List, Optional, Dict, Any

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from sentence_transformers import SentenceTransformer

from backend.models.models import FacilityFact, SearchResult

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY")
MODEL_NAME    = "llama-3.3-70b-versatile"
EMBED_MODEL   = "all-MiniLM-L6-v2"   # small, fast, runs on Free Edition CPU
LANCEDB_PATH  = "./lancedb_store"     # swap for /Volumes/... path on Databricks
MAX_RETRIES   = 3


# ── Few-shot examples ─────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = [
    {
        "text": (
            "Korle-Bu Teaching Hospital in Accra, Ghana is a large public tertiary facility "
            "with 2000 beds and 487 doctors. It offers cardiology, general surgery, and emergency "
            "medicine. Equipment includes a Siemens 1.5T MRI, CT scanner, and piped oxygen. "
            "The ICU has 40 beds. A diesel backup generator covers the entire facility."
        ),
        "output": {
            "name": "Korle-Bu Teaching Hospital",
            "location": "Greater Accra",
            "facility_type_id": "hospital",
            "operator_type_id": "public",
            "specialties": ["cardiology", "generalSurgery", "emergencyMedicine"],
            "procedure": ["open heart surgery", "haemodialysis"],
            "equipment": ["Siemens 1.5T MRI scanner", "CT scanner", "piped oxygen", "diesel backup generator"],
            "capability": ["Level I Trauma Center", "ICU with 40 beds", "24-hour emergency services"],
            "num_doctors": 487,
            "capacity": 2000,
            "address_state_or_region": "Greater Accra",
            "address_city": "Accra"
        }
    },
    {
        "text": (
            "Tamale Teaching Hospital serves the Northern region with 58 doctors and 650 beds. "
            "Specialises in general surgery and internal medicine. Has an 8-bed ICU. "
            "Equipment: X-ray machine, oxygen concentrators. No backup generator documented."
        ),
        "output": {
            "name": "Tamale Teaching Hospital",
            "location": "Northern",
            "facility_type_id": "hospital",
            "operator_type_id": "public",
            "specialties": ["generalSurgery", "internalMedicine"],
            "procedure": ["general surgery", "appendectomy"],
            "equipment": ["X-ray machine", "oxygen concentrators"],
            "capability": ["ICU with 8 beds", "emergency department"],
            "num_doctors": 58,
            "capacity": 650,
            "address_state_or_region": "Northern",
            "address_city": "Tamale"
        }
    }
]


def _build_few_shot_text() -> str:
    parts = []
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        # Serialise the output dict to indented JSON, then escape all braces
        json_str     = json.dumps(ex["output"], indent=2)
        escaped_json = json_str.replace("{", "{{").replace("}", "}}")
        parts.append(
            f"Example {i}:\nINPUT: {ex['text']}\n"
            f"OUTPUT: {escaped_json}"
        )
    return "\n\n".join(parts)


# ── MedicalIDP class ──────────────────────────────────────────────────────────

class MedicalIDP:
    """
    Intelligent Document Parsing engine for Ghana medical facility data.
    Handles: LLM extraction, vector embedding, LanceDB indexing, semantic search.
    """

    def __init__(self):
        self._mlflow_enabled = False
        try:
            import os
            os.environ["MLFLOW_ENABLE_DB_SDK"] = "true"
            mlflow.set_tracking_uri("databricks")
            mlflow.set_experiment("/Shared/IDP-Backend-API")
            self._mlflow_enabled = True
        except Exception as e:
            print(f"MLflow disabled: {e}")

        self.llm = ChatGroq(
            model=MODEL_NAME,
            temperature=0,
            api_key=GROQ_API_KEY
        )

        print(f"Loading embedding model '{EMBED_MODEL}'...")
        self.embedder = SentenceTransformer(EMBED_MODEL)

        self.db    = lancedb.connect(LANCEDB_PATH)
        self.table = None

        try:
            self.table = self.db.open_table("facilities")
            print(f"Loaded existing LanceDB index: {self.table.count_rows()} records")
        except Exception:
            print("No LanceDB index found — call build_index_from_records() to create one")

        self._zero_shot_chain = self._make_zero_shot_prompt() | self.llm.with_structured_output(FacilityFact)
        self._few_shot_chain  = self._make_few_shot_prompt()  | self.llm.with_structured_output(FacilityFact)
        # Active chain — few-shot wins the MLflow experiment
        self._chain = self._few_shot_chain

    # ── Prompts ───────────────────────────────────────────────────────────────

    def _make_zero_shot_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a medical data extraction agent for the Virtue Foundation Ghana project. "
                "Extract facility facts from the input text into structured JSON. "
                "Return only fields explicitly stated — never hallucinate. "
                "Specialties must use exact values: internalMedicine, familyMedicine, pediatrics, "
                "cardiology, generalSurgery, emergencyMedicine, gynecologyAndObstetrics, "
                "orthopedicSurgery, dentistry, ophthalmology."
            ),
            ("user", "{text}")
        ])

    def _make_few_shot_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a medical data extraction agent for the Virtue Foundation Ghana project. "
                "Extract facility facts from the input text into structured JSON. "
                "Return only fields explicitly stated — never hallucinate. "
                "Specialties must use exact values: internalMedicine, familyMedicine, pediatrics, "
                "cardiology, generalSurgery, emergencyMedicine, gynecologyAndObstetrics, "
                "orthopedicSurgery, dentistry, ophthalmology.\n\n"
                "Examples of correct extraction:\n" + _build_few_shot_text()
            ),
            ("user", "{text}")
        ])

    # ── Extraction ─────────────────────────────────────────────────────────────

    def extract_from_text(self, text: str) -> Dict[str, Any]:
    if self._mlflow_enabled:
        with mlflow.start_run(run_name=f"IDP_Extraction"):
            return self._extract(text)
    else:
        return self._extract(text)


     def _extract(self, text: str) -> Dict[str, Any]:
        mlflow.log_param("text_length", len(text))
            mlflow.log_param("model_used",  MODEL_NAME)
            mlflow.log_param("prompt_type", "few_shot")

            start      = time.time()
            result     = None
            last_error = None

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = self._chain.invoke({"text": text})
                    break
                except Exception as e:
                    last_error = str(e)
                    mlflow.log_param(f"retry_{attempt}_error", last_error[:200])
                    if attempt < MAX_RETRIES:
                        time.sleep(attempt)   # 1s, 2s back-off

            latency = time.time() - start
            mlflow.log_metric("latency_s",             round(latency, 3))
            mlflow.log_metric("retry_count",           attempt - 1)
            mlflow.log_metric("extraction_success",    1 if result else 0)

            if result is None:
                raise RuntimeError(
                    f"Extraction failed after {MAX_RETRIES} attempts. Last error: {last_error}"
                )

            mlflow.log_metric("specialties_extracted", len(result.specialties))
            mlflow.log_metric("procedures_extracted",  len(result.procedure))
            mlflow.log_metric("equipment_extracted",   len(result.equipment))
            mlflow.log_metric("capability_extracted",  len(result.capability))

            return result.model_dump()

    # ── MLflow prompt comparison experiment ───────────────────────────────────

    def run_prompt_comparison(self, test_texts: List[str]) -> Dict[str, Any]:
        """
        Day 2 deliverable: compare zero-shot vs few-shot on a sample of real Ghana texts.
        Logs to MLflow — PM views the comparison chart in Databricks UI.
        Returns dict with winner and mean field counts.
        """
        print("Running zero-shot vs few-shot MLflow experiment...")

        def _field_count(f: FacilityFact) -> int:
            return (len(f.specialties) + len(f.procedure) +
                    len(f.equipment)   + len(f.capability) +
                    (1 if f.num_doctors else 0) +
                    (1 if f.capacity   else 0))

        zs_scores, fs_scores = [], []

        for i, text in enumerate(test_texts):
            for prompt_type, chain, scores in [
                ("zero_shot", self._zero_shot_chain, zs_scores),
                ("few_shot",  self._few_shot_chain,  fs_scores),
            ]:
                with mlflow.start_run(run_name=f"{prompt_type}_text_{i}"):
                    mlflow.log_param("prompt_type", prompt_type)
                    try:
                        res   = chain.invoke({"text": text})
                        score = _field_count(res)
                        mlflow.log_metric("field_count", score)
                        scores.append(score)
                    except Exception:
                        mlflow.log_metric("field_count", 0)
                        scores.append(0)

        mean_zs = sum(zs_scores) / len(zs_scores) if zs_scores else 0
        mean_fs = sum(fs_scores) / len(fs_scores)  if fs_scores  else 0
        winner  = "few_shot" if mean_fs >= mean_zs else "zero_shot"

        with mlflow.start_run(run_name="prompt_comparison_summary"):
            mlflow.log_metric("zero_shot_mean_fields", mean_zs)
            mlflow.log_metric("few_shot_mean_fields",  mean_fs)
            mlflow.log_metric("improvement_pct",
                              round(((mean_fs - mean_zs) / max(mean_zs, 1)) * 100, 1))
            mlflow.log_param("winner", winner)

        print(f"Zero-shot: {mean_zs:.1f} fields | Few-shot: {mean_fs:.1f} fields | Winner: {winner}")
        return {"zero_shot_mean": mean_zs, "few_shot_mean": mean_fs, "winner": winner}

    # ── LanceDB index builder ─────────────────────────────────────────────────

    def build_index_from_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Builds the LanceDB vector index from a list of facility dicts.

        How to call from a Databricks notebook after reading Delta Lake:
            df      = spark.sql("SELECT * FROM main.hackathon.facilities")
            records = [row.asDict() for row in df.collect()]
            idp_engine.build_index_from_records(records)

        Embedding text = capability + procedure + equipment concatenated.
        Falls back to name + location if all three are empty.
        Returns: number of records successfully indexed.
        """
        print(f"Building LanceDB index over {len(records)} records...")

        rows = []
        for rec in records:
            cap_text   = " ".join(rec.get("capability", []) or [])
            proc_text  = " ".join(rec.get("procedure",  []) or [])
            equip_text = " ".join(rec.get("equipment",  []) or [])
            embed_text = f"{cap_text} {proc_text} {equip_text}".strip()

            if not embed_text:
                embed_text = f"{rec.get('name', '')} {rec.get('location', '')}".strip()

            vector = self.embedder.encode(embed_text).tolist()

            rows.append({
                "row_id":                 str(rec.get("row_id", rec.get("name", "unknown"))),
                "name":                   str(rec.get("name", "")),
                "location":               str(rec.get("location", rec.get("address_state_or_region", ""))),
                "address_state_or_region":str(rec.get("address_state_or_region", "")),
                "address_city":           str(rec.get("address_city", "")),
                "facility_type_id":       str(rec.get("facility_type_id", "")),
                "operator_type_id":       str(rec.get("operator_type_id", "")),
                "num_doctors":            int(rec.get("num_doctors", 0) or 0),
                "capacity":               int(rec.get("capacity",    0) or 0),
                "latitude":               float(rec.get("latitude",  0.0) or 0.0),
                "longitude":              float(rec.get("longitude", 0.0) or 0.0),
                "specialties":            json.dumps(rec.get("specialties", []) or []),
                "capability":             json.dumps(rec.get("capability",  []) or []),
                "procedure":              json.dumps(rec.get("procedure",   []) or []),
                "equipment":              json.dumps(rec.get("equipment",   []) or []),
                "embed_text":             embed_text,
                "vector":                 vector,
            })

        try:
            self.db.drop_table("facilities")
        except Exception:
            pass

        self.table = self.db.create_table("facilities", data=rows)
        count = self.table.count_rows()
        print(f"LanceDB index ready: {count} records")
        return count

    # ── Semantic search ───────────────────────────────────────────────────────

    def search(
        self,
        query:     str,
        region:    Optional[str] = None,
        specialty: Optional[str] = None,
        top_k:     int           = 5
    ) -> SearchResult:
        """
        Semantic search over LanceDB index.
        Optional post-filter by region and specialty after vector retrieval.
        Returns SearchResult consumed by agent retrieve_node via POST /search.
        """
        if self.table is None:
            raise RuntimeError(
                "LanceDB index not built. Call build_index_from_records() first."
            )

        query_vector = self.embedder.encode(query).tolist()

        # Retrieve top_k*3 to allow for filtering headroom
        raw = self.table.search(query_vector).limit(top_k * 3).to_list()

        # Post-filter
        filtered = []
        for row in raw:
            if region:
                loc = (row.get("location", "") + " " +
                       row.get("address_state_or_region", "")).lower()
                if region.lower() not in loc:
                    continue
            if specialty:
                specs = json.loads(row.get("specialties", "[]"))
                if not any(specialty.lower() in s.lower() for s in specs):
                    continue
            filtered.append(row)

        top = (filtered if filtered else raw)[:top_k]

        # LanceDB cosine distance → similarity
        distances    = [r.get("_distance", 1.0) for r in top]
        similarities = [max(0.0, 1.0 - (d / 2.0)) for d in distances]
        mean_conf    = round(sum(similarities) / len(similarities), 4) if similarities else 0.0

        facilities = []
        for row in top:
            facilities.append(FacilityFact(
                row_id                  = row.get("row_id"),
                name                    = row.get("name", ""),
                location                = row.get("location", ""),
                facility_type_id        = row.get("facility_type_id"),
                operator_type_id        = row.get("operator_type_id"),
                num_doctors             = row.get("num_doctors", 0),
                capacity                = row.get("capacity",    0),
                latitude                = row.get("latitude"),
                longitude               = row.get("longitude"),
                address_state_or_region = row.get("address_state_or_region"),
                address_city            = row.get("address_city"),
                specialties             = json.loads(row.get("specialties", "[]")),
                capability              = json.loads(row.get("capability",  "[]")),
                procedure               = json.loads(row.get("procedure",   "[]")),
                equipment               = json.loads(row.get("equipment",   "[]")),
            ))

        return SearchResult(
            facilities   = facilities,
            confidence   = mean_conf,
            query        = query,
            result_count = len(facilities)
        )
