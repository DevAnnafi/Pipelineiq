"""
playbooks/loader.py
Loads team-defined remediation rules from rules.yaml and formats them
for injection into Claude prompts.
"""

import os
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

RULES_PATH = os.getenv("PIPELINEIQ_RULES_PATH", "playbooks/rules.yaml")


def load_playbook_rules() -> str:
    """
    Load rules.yaml and return a formatted string ready for prompt injection.
    Returns empty string if file doesn't exist or yaml is unavailable.
    """
    rules_file = Path(RULES_PATH)
    if not rules_file.exists():
        return ""

    if not YAML_AVAILABLE:
        return rules_file.read_text()

    try:
        with open(rules_file) as f:
            rules = yaml.safe_load(f)

        if not rules or "playbooks" not in rules:
            return ""

        formatted = []
        for rule in rules["playbooks"]:
            name = rule.get("name", "Unnamed Rule")
            trigger = rule.get("trigger", "")
            action = rule.get("action", "")
            priority = rule.get("priority", "normal")
            formatted.append(
                f"- Rule: {name} (priority: {priority})\n"
                f"  Trigger: {trigger}\n"
                f"  Recommended Action: {action}"
            )

        return "\n".join(formatted)

    except Exception as e:
        print(f"[playbook] Warning: could not load rules.yaml — {e}")
        return ""