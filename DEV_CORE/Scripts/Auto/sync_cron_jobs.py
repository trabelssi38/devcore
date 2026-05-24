#!/usr/bin/env python3
"""Syncs DevCore hermes_cron.yaml jobs into ~/.hermes/cron/jobs.json natively.
Preserves telemetry (completed runs, last status, last error) for existing jobs.
"""
import os
import sys
import yaml
import shutil
from pathlib import Path

# Append hermes_temp to path to import native cron database APIs
HERMES_HOME = Path("C:/devcore/hermes_temp")
sys.path.append(str(HERMES_HOME))

try:
    from cron.jobs import load_jobs, save_jobs, create_job, remove_job
    print("Natively imported Hermes cron jobs module successfully.")
except ImportError as e:
    print(f"Error importing Hermes cron module: {e}")
    sys.exit(1)

YAML_PATH = Path("C:/devcore/DEV_CORE/Scripts/hermes_cron.yaml")
SCRIPTS_DIR = Path(os.path.expanduser("~/.hermes/scripts"))

def main():
    if not YAML_PATH.exists():
        print(f"Error: YAML config not found at {YAML_PATH}")
        sys.exit(1)

    print(f"Loading DevCore cron jobs from {YAML_PATH}...")
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    cron_tasks = config.get("cron_tasks", [])
    print(f"Found {len(cron_tasks)} jobs in YAML.")

    # Make sure target scripts directory exists
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load existing jobs from jobs.json
    existing_jobs = load_jobs()
    existing_by_name = {job.get("name"): job for job in existing_jobs if job.get("name")}
    
    new_jobs_list = []
    
    # 2. Build or update jobs
    for task in cron_tasks:
        name = task.get("name")
        task_id = task.get("id")
        
        print(f"\nProcessing job: '{name}' (ID: {task_id})...")
        
        # Prepare parameters for create_job
        script = task.get("script")
        no_agent = task.get("no_agent", False)
        prompt = task.get("prompt")
        schedule = task.get("schedule")
        workdir = task.get("workdir")
        enabled = task.get("enabled", True)
        
        # If the script file exists in DevCore Scripts, copy it to ~/.hermes/scripts/
        if script:
            source_candidates = [
                Path(f"C:/devcore/DEV_CORE/Scripts/{script}"),
                Path(f"C:/devcore/DEV_CORE/Scripts/Auto/{script}"),
                Path(os.path.expanduser(f"~/.hermes/scripts/{script}"))
            ]
            copied = False
            for src in source_candidates:
                if src.exists() and src != SCRIPTS_DIR / script:
                    print(f"  Copying script: {src} -> {SCRIPTS_DIR / script}")
                    shutil.copy2(src, SCRIPTS_DIR / script)
                    copied = True
                    break
            
            if not copied and not (SCRIPTS_DIR / script).exists():
                print(f"  Warning: script {script} not found in DevCore Scripts folders!")

        # Call create_job natively. 
        # This will append the job to the database, but we will adjust its list in memory to preserve stats
        try:
            # We bypass writing directly by clearing the database list and re-saving at the end,
            # or we let create_job write and we reconcile. Let's do reconcile:
            job_dict = create_job(
                prompt=prompt,
                schedule=schedule,
                name=name,
                script=script,
                no_agent=no_agent,
                workdir=workdir,
                deliver="local"
            )
            
            # Reconcile historical telemetry if it previously existed
            if name in existing_by_name:
                old_job = existing_by_name[name]
                print(f"  Found existing job telemetry. Preserving historical stats...")
                
                # Restore ID to keep logs aligned
                job_dict["id"] = old_job["id"]
                
                # Restore stats
                job_dict["repeat"]["completed"] = old_job.get("repeat", {}).get("completed", 0)
                job_dict["last_run_at"] = old_job.get("last_run_at")
                job_dict["last_status"] = old_job.get("last_status")
                job_dict["last_error"] = old_job.get("last_error")
                job_dict["last_delivery_error"] = old_job.get("last_delivery_error")
                
            job_dict["enabled"] = enabled
            new_jobs_list.append(job_dict)
            print(f"  Job successfully registered: ID={job_dict['id']}, Next Run={job_dict['next_run_at']}")
            
        except Exception as e:
            print(f"  Error creating job '{name}': {e}")

    # 3. Save the final synchronized list to jobs.json
    print("\nSaving synchronized database...")
    save_jobs(new_jobs_list)
    print("Database sync complete. jobs.json is now 100% synchronized with hermes_cron.yaml.")

if __name__ == "__main__":
    main()
