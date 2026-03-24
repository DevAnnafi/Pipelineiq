def build_prompt(failed_logs):
    prompt = "You are a CI/CD expert. Analyze the following failed pipeline logs:\n\n "

    for job in failed_logs:
        prompt += f"Job: {job['job_name']}\nLog:\n{job['log']}\n\n"

    prompt += "For each failed job, provide: 1) root cause 2) suggested fix"

    return prompt
