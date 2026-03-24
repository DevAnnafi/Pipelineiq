# PipelineIQ

PipelineIQ is a GitLab Duo agent that automatically diagnoses CI/CD pipeline failures using Claude (Anthropic). When a pipeline fails, GitLab sends a webhook to PipelineIQ, which fetches the failed job logs, sends them to Claude for root cause analysis, and posts a structured diagnosis with fix recommendations directly on the commit — turning hours of manual debugging into an automated 20-second workflow.

## How It Works

1. A GitLab CI/CD pipeline fails
2. GitLab sends a webhook event to PipelineIQ
3. PipelineIQ fetches the failed job logs via the GitLab REST API
4. Logs are sent to Claude (claude-opus-4-6) for analysis
5. Claude's diagnosis and suggested fixes are posted as a comment on the commit

## Tech Stack

- Python + FastAPI
- Anthropic Claude API (claude-opus-4-6)
- GitLab Webhooks + REST API
- httpx, python-dotenv

## Setup

### Prerequisites

- Python 3.10+
- A GitLab account
- An Anthropic API key
- ngrok (for local development)

### Installation

1. Clone the repo:
```bash
git clone https://gitlab.com/DevAnnafi/pipelineiq.git
cd pipelineiq
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create your `.env` file:
```bash
cp .env.example .env
```

4. Fill in your environment variables (see below)

5. Run the server:
```bash
uvicorn agent:app --reload
```

6. Expose it publicly with ngrok:
```bash
ngrok http 8000
```

7. Add your ngrok URL as a GitLab webhook:
   - Go to your GitLab project → Settings → Webhooks
   - URL: `https://your-ngrok-url.ngrok.io/webhook`
   - Trigger: Pipeline events only
   - Add your webhook secret

## Environment Variables

Create a `.env` file in the project root with the following:

| Variable | Description |
|----------|-------------|
| `GITLAB_TOKEN` | GitLab personal access token (with `api` scope) |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GITLAB_WEBHOOK_SECRET` | Webhook secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |

## Project Structure
```
pipelineiq/
├── agent.py              # Main FastAPI webhook handler
├── tools/
│   └── fetch_logs.py     # Fetches failed job logs via GitLab API
├── prompts/
│   └── diagnose.py       # Builds Claude prompt from logs
├── requirements.txt
├── .env.example
├── .gitlab-ci.yml
└── README.md
```

## Example Output

When a pipeline fails, PipelineIQ automatically posts a comment on your commit:
```
CI/CD Pipeline Failure Analysis

Job: run_tests

1) Root Cause
pytest is not installed. The requirements.txt file does not include pytest
as a test dependency. When the job runs python -m pytest, Python cannot
find the module and exits with code 1.

2) Suggested Fix
Add pytest to your pipeline install step:
  - pip install -r requirements.txt
  - pip install pytest
  - python -m pytest
```

## License

MIT License — see [LICENSE](LICENSE) for details.