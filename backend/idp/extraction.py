import mlflow
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from models.models import FacilityFact

class MedicalIDP:
    def __init__(self):
        # Uses GPT-4 or Databricks DBRX via LangChain
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

    def extract_from_text(self, text: str):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical data extraction agent. Extract facility facts into structured JSON."),
            ("user", "{text}")
        ])
        
        # This automatically validates the LLM output against your Pydantic model
        chain = prompt | self.llm.with_structured_output(FacilityFact)
        
        with mlflow.start_run(run_name="IDP_Extraction"):
            result = chain.invoke({"text": text})
            mlflow.log_param("text_length", len(text))
            return result