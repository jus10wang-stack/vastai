#!/usr/bin/env python3
"""
Monitor a specific ComfyUI job and update its log file
"""

import sys
import os
import time
import json

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def main():
    if len(sys.argv) < 5:
        print("Monitor ComfyUI Job Progress")
        print("\nUsage:")
        print("  python monitor_job.py <instance_id> <ssh_host> <ssh_port> <job_id> [log_file]")
        print("")
        print("Example:")
        print("  python monitor_job.py 26003629 ssh9.vast.ai 13629 d256f9a0-028c-4600-9a77-c8ae5d26f8b3")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    ssh_host = sys.argv[2]
    ssh_port = int(sys.argv[3])
    job_id = sys.argv[4]
    
    # Find log file if not provided
    if len(sys.argv) > 5:
        log_file = sys.argv[5]
    else:
        logs_dir = os.path.expanduser("~/wsl-cursor-projects/vastai/SCRIPTS/logs/comfyui_jobs")
        log_files = [f for f in os.listdir(logs_dir) if job_id[:8] in f and f.endswith('.log')]
        if not log_files:
            print(f"❌ No log file found for job {job_id[:8]}")
            sys.exit(1)
        log_file = os.path.join(logs_dir, log_files[0])
    
    print(f"🔍 Monitoring job: {job_id}")
    print(f"📝 Log file: {os.path.basename(log_file)}")
    
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect to instance")
            sys.exit(1)
        
        # Monitor the job
        success = controller.monitor_job_progress(job_id, log_file, max_wait_seconds=7200)
        
        if success:
            print("✅ Job monitoring completed successfully")
        else:
            print("⏰ Job monitoring timed out")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        controller.disconnect()

if __name__ == "__main__":
    main()