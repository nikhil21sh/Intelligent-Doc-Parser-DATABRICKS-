import os
from dotenv import load_dotenv
import mlflow
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from the .env file FIRST
load_dotenv()

# Now MLflow will automatically find the DATABRICKS_HOST and DATABRICKS_TOKEN
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/Intelligent-Doc-Parser-DATABRICKS")
def log_tags_sync(tags: dict):
    """Synchronous MLflow logging function."""
    with mlflow.start_run(run_name="Day1_Skeleton_Test"):
        mlflow.set_tags(tags)
        print(f"Logged custom tags to MLflow: {tags}")

async def log_citations_async(row_ids: list):
    """Wraps MLflow in a thread pool to avoid blocking LangGraph's hot path."""
    loop = asyncio.get_running_loop()
    tags = {
        "step": "reason_node",
        "cited_row_ids": ",".join(row_ids),
        "confidence_score": "0.95"
    }
    
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, log_tags_sync, tags)

async def main():
    print("Testing Async MLflow Tracing...")
    await log_citations_async(["uuid-1234", "uuid-5678", "uuid-91011"])
    print("Test complete. Check your Databricks MLflow UI.")

if __name__ == "__main__":
    asyncio.run(main())