import os
import mlflow
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate

# Import from the shared directory we created earlier
from models.models import FacilityFact

groq_key = os.environ.get("GROQ_API_KEY")

class MedicalIDP:
    def __init__(self):
        # Point this logic to your dedicated backend experiment
        mlflow.set_experiment("/Shared/IDP-Backend-API")
        
        # Uses GPT-4 or Databricks DBRX via LangChain
        self.llm = ChatGroq(
            model="llama3-70b-8192",
            temperature=0,
            api_key=groq_key
        )

    def extract_from_text(self, text: str):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical data extraction agent. Extract facility facts into structured JSON."),
            ("user", "{text}")
        ])
        
        # Automatically validates the LLM output against your Pydantic model
        chain = prompt | self.llm.with_structured_output(FacilityFact)
        
        # Start the tracking run
        with mlflow.start_run(run_name="IDP_Extraction"):
            result = chain.invoke({"text": text})
            
            # Log metrics for your dashboard
            mlflow.log_param("text_length", len(text))
            mlflow.log_param("model_used", "gpt-4-turbo")
            
            return result