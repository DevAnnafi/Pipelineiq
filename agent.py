from fastapi import FastAPI, Request
from tools.fetch_logs import fetch_failed_logs
from prompts.diagnose import build_prompt
import anthropic
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()

    if payload["object_attributes"]["status"] != "failed":
        return {"status" : "ignored"}

    project_id = payload["project"]["id"]
    pipeline_id = payload["object_attributes"]["id"]

    logs = await fetch_failed_logs(project_id, pipeline_id)

    prompt = build_prompt(logs)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    response_text = message.content[0].text 

    commit_sha = payload["commit"]["id"]
    base_url = "https://gitlab.com/api/v4"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    comment_url = f"{base_url}/projects/{project_id}/repository/commits/{commit_sha}/comments"

    async with httpx.AsyncClient() as http_client:
        await client.post(comment_url, json={"note": response_text}, headers=headers)

    return {"status": "ok"}