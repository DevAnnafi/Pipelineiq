"""
notifications/email.py
Sends pipeline failure diagnosis summaries via SMTP.
Supports plain-text and HTML multipart emails.
"""

import os
import smtplib
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

# ── SMTP config (set in .env) ─────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO_RAW = os.getenv("EMAIL_TO", "")          # comma-separated recipients
EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASSWORD and EMAIL_TO_RAW)

EMAIL_TO: list[str] = [e.strip() for e in EMAIL_TO_RAW.split(",") if e.strip()]


def _build_html(
    project_name: str,
    project_url: str,
    pipeline_id: int,
    branch: str,
    commit_sha: str,
    failed_job_names: list[str],
    diagnosis_text: str,
    mr_url: str | None,
) -> str:
    jobs_html = "".join(f"<li><code>{j}</code></li>" for j in failed_job_names)
    diagnosis_html = diagnosis_text.replace("\n", "<br>")
    mr_section = (
        f'<p>🔧 <strong>Auto-Fix MR:</strong> <a href="{mr_url}">View Draft MR →</a></p>'
        if mr_url
        else ""
    )
    short_sha = commit_sha[:10]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #1a1a1a; max-width: 700px; margin: 0 auto; padding: 24px; }}
    .header {{ background: #fc6d26; color: white; padding: 16px 24px;
               border-radius: 8px 8px 0 0; }}
    .header h1 {{ margin: 0; font-size: 20px; }}
    .meta {{ background: #f5f5f5; padding: 16px 24px; border-left: 4px solid #fc6d26; }}
    .meta table {{ border-collapse: collapse; width: 100%; }}
    .meta td {{ padding: 4px 8px; }}
    .meta td:first-child {{ font-weight: bold; width: 120px; color: #555; }}
    .diagnosis {{ background: #fff; border: 1px solid #e0e0e0;
                  padding: 20px 24px; border-radius: 0 0 8px 8px; }}
    .diagnosis h2 {{ color: #fc6d26; font-size: 16px; margin-top: 0; }}
    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
    .footer {{ color: #888; font-size: 12px; margin-top: 16px; text-align: center; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>🔴 Pipeline Failure — {project_name}</h1>
    <p style="margin:4px 0 0; font-size:13px; opacity:0.9;">PipelineIQ Automatic Diagnosis · {now}</p>
  </div>
  <div class="meta">
    <table>
      <tr><td>Pipeline</td><td><a href="{project_url}/-/pipelines/{pipeline_id}">#{pipeline_id}</a></td></tr>
      <tr><td>Branch</td><td><code>{branch}</code></td></tr>
      <tr><td>Commit</td><td><code>{short_sha}</code></td></tr>
      <tr><td>Failed Jobs</td><td><ul style="margin:0;padding-left:18px">{jobs_html}</ul></td></tr>
    </table>
    {mr_section}
  </div>
  <div class="diagnosis">
    <h2>🤖 PipelineIQ Diagnosis</h2>
    <p>{diagnosis_html}</p>
  </div>
  <div class="footer">Sent by PipelineIQ · <a href="{project_url}">View Project</a></div>
</body>
</html>
"""


def send_email_notification(
    project_name: str,
    project_url: str,
    pipeline_id: int,
    branch: str,
    commit_sha: str,
    failed_job_names: list[str],
    diagnosis_text: str,
    mr_url: str | None = None,
) -> bool:
    """
    Send an HTML+plaintext email digest of the pipeline failure.
    Returns True on success.  Note: synchronous (SMTP) — called in a thread pool.
    """
    if not EMAIL_ENABLED:
        return False

    subject = (
        f"[PipelineIQ] Pipeline #{pipeline_id} failed on {project_name} "
        f"({branch}) — {', '.join(failed_job_names[:2])}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    # Plain-text fallback
    plain = textwrap.dedent(f"""\
        PipelineIQ — Pipeline Failure Alert
        ====================================
        Project : {project_name}
        Pipeline: #{pipeline_id}
        Branch  : {branch}
        Commit  : {commit_sha[:10]}
        Jobs    : {', '.join(failed_job_names)}
        {"MR      : " + mr_url if mr_url else ""}

        --- Diagnosis ---

        {diagnosis_text}
    """)

    html = _build_html(
        project_name, project_url, pipeline_id, branch,
        commit_sha, failed_job_names, diagnosis_text, mr_url,
    )

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"[email] Notification sent to {EMAIL_TO} for pipeline #{pipeline_id}")
        return True
    except Exception as e:
        print(f"[email] Failed to send notification: {e}")
        return False