"""
db/history.py
Lightweight SQLite store for pipeline failure history.
Used by the recurring-failure detector to identify systemic issues.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.getenv("PIPELINEIQ_DB_PATH", "pipelineiq_history.db")


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_failures (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                pipeline_id INTEGER NOT NULL,
                job_name    TEXT NOT NULL,
                stage       TEXT NOT NULL,
                root_cause  TEXT,          -- short label extracted from Claude diagnosis
                commit_sha  TEXT,
                branch      TEXT,
                recorded_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_job ON pipeline_failures(project_id, job_name)"
        )


def record_failures(
    project_id: int,
    pipeline_id: int,
    failed_jobs: list[dict],
    root_causes: dict[str, str],  # job_name -> short cause label
    commit_sha: str,
    branch: str,
):
    """Persist each failed job for later trend analysis."""
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            project_id,
            pipeline_id,
            job["job_name"],
            job["stage"],
            root_causes.get(job["job_name"], ""),
            commit_sha,
            branch,
            now,
        )
        for job in failed_jobs
    ]
    with _conn() as con:
        con.executemany(
            """
            INSERT INTO pipeline_failures
                (project_id, pipeline_id, job_name, stage, root_cause,
                 commit_sha, branch, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_recurring_failures(project_id: int, window: int = 10) -> list[dict]:
    """
    Return jobs that have failed more than once in the last `window` pipelines
    for this project.  Sorted by recurrence count descending.
    """
    with _conn() as con:
        rows = con.execute(
            """
            SELECT job_name, stage, COUNT(*) as fail_count,
                   GROUP_CONCAT(DISTINCT root_cause) as causes
            FROM pipeline_failures
            WHERE project_id = ?
              AND id >= (
                  SELECT COALESCE(MIN(id), 0)
                  FROM (
                      SELECT DISTINCT pipeline_id, MIN(id) as id
                      FROM pipeline_failures
                      WHERE project_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
              )
            GROUP BY job_name, stage
            HAVING fail_count > 1
            ORDER BY fail_count DESC
            """,
            (project_id, project_id, window),
        ).fetchall()
    return [dict(r) for r in rows]