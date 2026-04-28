"""
notifications/slack.py
Posts pipeline failure diagnosis summaries to a Slack channel
via Incoming Webhooks.
"""

import httpx
import os
import re

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_ENABLED = bool(SLACK_WEBHOOK_URL)


def _truncate(text: str, max_len: int = 2800) -> str:
    return text if len(text) <= max_len else text[:max_len] + "\n…_(truncated)_"


def _extract_severity(diagnosis: str) -> tuple[str, str]:
    """Return (emoji, color) based on recurrence risk if present in diagnosis."""
    upper = diagnosis.upper()
    if "RECURRENCE RISK\nHIGH" in upper or "RISK** HIGH" in upper:
        return "🔴", "#E01E5A"
    if "RECURRENCE RISK\nMEDIUM" in upper or "RISK** MEDIUM" in upper:
        return "🟡", "#ECB22E"
    return "🟢", "#36C5F0"


async def send_slack_notification(
    project_name: str,
    project_url: str,
    pipeline_id: int,
    branch: str,
    commit_sha: str,
    commit_url: str,
    failed_job_names: list[str],
    diagnosis_text: str,
    mr_url: str | None = None,
) -> bool:
    """
    Send a rich Slack message with the pipeline failure digest.
    Returns True on success.
    """
    if not SLACK_ENABLED:
        return False

    emoji, color = _extract_severity(diagnosis_text)
    jobs_str = ", ".join(f"`{j}`" for j in failed_job_names)
    short_sha = commit_sha[:8]

    mr_block = (
        [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Auto-Fix MR:* <{mr_url}|View Draft MR →>",
                },
            }
        ]
        if mr_url
        else []
    )

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} Pipeline Failure — {project_name}",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Pipeline:*\n<{project_url}/-/pipelines/{pipeline_id}|#{pipeline_id}>",
                            },
                            {"type": "mrkdwn", "text": f"*Branch:*\n`{branch}`"},
                            {
                                "type": "mrkdwn",
                                "text": f"*Commit:*\n<{commit_url}|{short_sha}>",
                            },
                            {"type": "mrkdwn", "text": f"*Failed Jobs:*\n{jobs_str}"},
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🤖 PipelineIQ Diagnosis*\n\n{_truncate(diagnosis_text)}",
                        },
                    },
                    *mr_block,
                ],
            }
        ]
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
        if resp.status_code != 200:
            print(f"[slack] Notification failed ({resp.status_code}): {resp.text}")
            return False

    print(f"[slack] Notification sent for pipeline #{pipeline_id}")
    return True