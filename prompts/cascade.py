"""
prompts/cascade.py
Builds the Claude prompt for multi-stage cascade failure analysis.
Determines true root cause across dependent stages.
"""

def build_cascade_prompt(stage_logs: list[dict], playbook_rules: str = "") -> str:
    """
    stage_logs: list of {job_name, stage, allow_failure, log}
                ordered by pipeline execution order
    playbook_rules: team-defined remediation rules (from rules.yaml), pre-formatted
    """
    stages_section = ""
    for entry in stage_logs:
        allow_note = " [allow_failure=true]" if entry.get("allow_failure") else ""
        stages_section += (
            f"### Stage: {entry['stage']} | Job: {entry['job_name']}{allow_note}\n"
            f"```\n{entry['log']}\n```\n\n"
        )

    playbook_section = (
        f"\n## Team Playbook Rules\nThe following team-defined rules MUST be incorporated "
        f"into your fix recommendations where applicable:\n\n{playbook_rules}\n"
        if playbook_rules.strip()
        else ""
    )

    return f"""You are a senior DevOps engineer and CI/CD expert. A multi-stage pipeline has failed.
Your job is to perform a cascade failure analysis: identify the TRUE root cause job/stage,
distinguish it from downstream failures that were only triggered because an earlier stage failed,
and provide actionable fix recommendations.

{playbook_section}
## Failed Pipeline Stages (in execution order)

{stages_section}
## Instructions

Respond with EXACTLY this structure — no markdown headers other than what is shown:

**🔍 Cascade Analysis**

**True Root Cause**
Identify the FIRST stage/job where the actual failure originated. Explain why.

**Downstream Casualties**
List any jobs that failed only because a prior stage failed (not independent failures).
If none, write "None — all failures are independent."

**Stage-by-Stage Breakdown**
For each failed job, one bullet: `[stage/job]` — brief diagnosis (1-2 sentences).

**Fix Plan**
Numbered list of concrete fixes in the order they should be applied.
Reference specific files, commands, or config changes where possible.

**Recurrence Risk**
Rate as LOW / MEDIUM / HIGH and explain why in one sentence.
"""