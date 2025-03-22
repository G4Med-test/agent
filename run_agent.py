#!/usr/bin/env python3

import os
import time
import json
import tempfile
import subprocess
from github import Github
from datetime import datetime
import requests

# Load configuration
with open("config.json") as f:
    config = json.load(f)

DISPATCHER_REPO = config["dispatcher_repo"]
SERVER_NAME = config["server_name"]
PREFERRED_REPOS = config.get("preferred_repositories", [])
MAX_JOBS_PER_CYCLE = config.get("max_jobs_per_cycle", 1)
SCHEDULER = config.get("scheduler", "lsf").lower()

# GitHub authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable not set")

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(DISPATCHER_REPO)

def download_job_json(issue_body_url):
    r = requests.get(issue_body_url)
    r.raise_for_status()
    return r.json()

def create_submission_script(job, workdir):
    """Create submission script based on scheduler type."""
    macro_dir = job["input_folder"]
    container_image = job["container_image"]
    output_folder = job["output_folder"]
    job_id = job['job_id']

    if SCHEDULER == "lsf":
        lines = [
            "#!/bin/bash",
            f"#BSUB -J {job_id}",
            f"mkdir -p {output_folder}",
            f"for macrofile in {macro_dir}/*.mac; do",
            f"  apptainer exec {container_image} /LowEFrag -m $macrofile > $output_folder/$(basename $macrofile).log",
            "done",
        ]
    elif SCHEDULER == "slurm":
        lines = [
            "#!/bin/bash",
            f"#SBATCH --job-name={job_id}",
            f"mkdir -p {output_folder}",
            f"for macrofile in {macro_dir}/*.mac; do",
            f"  apptainer exec {container_image} /LowEFrag -m $macrofile > $output_folder/$(basename $macrofile).log",
            "done",
        ]
    elif SCHEDULER == "pbs":
        lines = [
            "#!/bin/bash",
            f"#PBS -N {job_id}",
            f"mkdir -p {output_folder}",
            f"cd $PBS_O_WORKDIR",
            f"for macrofile in {macro_dir}/*.mac; do",
            f"  apptainer exec {container_image} /LowEFrag -m $macrofile > $output_folder/$(basename $macrofile).log",
            "done",
        ]
    else:
        raise ValueError(f"Unsupported scheduler type: {SCHEDULER}")

    script_path = os.path.join(workdir, f"{SCHEDULER}_job.sh")
    with open(script_path, "w") as f:
        f.write("\n".join(lines))
    return script_path

def submit_to_scheduler(script_path):
    """Submit based on scheduler."""
    commands = {
        "lsf": f"bsub < {script_path}",
        "slurm": f"sbatch {script_path}",
        "pbs": f"qsub {script_path}"
    }

    submit_cmd = commands.get(SCHEDULER)
    if not submit_cmd:
        raise RuntimeError(f"No submission command defined for scheduler {SCHEDULER}")

    try:
        result = subprocess.run(submit_cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"{SCHEDULER.upper()} submission failed:", result.stderr)
            return False
        print(f"{SCHEDULER.upper()} submission output:", result.stdout)
        return True
    except Exception as e:
        print(f"Exception during scheduler submission: {e}")
        return False

def claim_issue(issue):
    issue.create_comment(f"Claimed by `{SERVER_NAME}` at {datetime.utcnow().isoformat()}Z")

def close_issue(issue, release_url):
    issue.create_comment(f"Job completed by `{SERVER_NAME}`.\nResults and release: {release_url}")
    issue.edit(state="closed")

def main():
    open_issues = repo.get_issues(state="open")
    jobs_claimed = 0

    for issue in open_issues:
        if jobs_claimed >= MAX_JOBS_PER_CYCLE:
            break

        comments = issue.get_comments()
        if any(SERVER_NAME in c.body or "Claimed by" in c.body for c in comments):
            continue

        try:
            lines = issue.body.splitlines()
            json_url = next(line.strip() for line in lines if line.strip().startswith("https://"))
            job_data = download_job_json(json_url)
        except Exception as e:
            print(f"Failed to parse job JSON from issue #{issue.number}: {e}")
            continue

        print(f"Claiming issue #{issue.number} for job {job_data['job_id']}")
        claim_issue(issue)

        with tempfile.TemporaryDirectory() as workdir:
            script_path = create_submission_script(job_data, workdir)
            success = submit_to_scheduler(script_path)

            if success:
                dummy_release_url = f"https://github.com/{job_data['repository']}/releases"
                close_issue(issue, dummy_release_url)
                print(f"Job {job_data['job_id']} submitted and issue closed.")
                jobs_claimed += 1
            else:
                issue.create_comment(f"Submission failed by `{SERVER_NAME}`.")
                print(f"Submission failed for job {job_data['job_id']}")

if __name__ == "__main__":
    main()
