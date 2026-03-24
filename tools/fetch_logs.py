import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")

async def fetch_failed_logs(project_id, pipeline_id):
    base_url = "https://gitlab.com/api/v4"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/projects/{project_id}/pipelines/{pipeline_id}/jobs", headers=headers)
        data = response.json()
  
        failed_jobs = [job for job in data if job["status"] == "failed"]

        results = []
        for job in failed_jobs:
            job_id = job["id"]
            job_name = job["name"]
            url = f"{base_url}/projects/{project_id}/jobs/{job_id}/trace"
            trace_response = await client.get(url, headers=headers)
            trace_text = trace_response.text


            results.append({"job_name": job_name, "log": trace_text})

    return results