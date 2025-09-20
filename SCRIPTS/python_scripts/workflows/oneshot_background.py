#!/usr/bin/env python3
"""
Background workflow monitoring and auto-extraction for oneshot
Monitors ComfyUI job completion and automatically extracts content when done.
"""

import sys
import time
import os
import glob
import subprocess
import datetime

def wait_for_workflow_completion(instance_id, max_wait_minutes=30):
    """Wait for any workflow to complete by monitoring job log files."""
    script_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    logs_dir = os.path.join(script_dir, "SCRIPTS", "logs", "comfyui_jobs")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    poll_interval = 10  # Check every 10 seconds in background
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Look for log files for this instance
            log_files = []
            if os.path.exists(logs_dir):
                log_files = glob.glob(os.path.join(logs_dir, f"*_{instance_id}_*.log"))
                log_files.sort(key=os.path.getmtime, reverse=True)  # Most recent first
            
            # Check the most recent log file
            if log_files:
                latest_log = log_files[0]
                try:
                    with open(latest_log, 'r') as f:
                        content = f.read()
                        
                        # Check for completion indicators
                        if '"final_status": "completed"' in content or "Job completed successfully" in content:
                            return True, latest_log
                        elif '"final_status": "cancelled"' in content or '"final_status": "failed"' in content or "Job cancelled" in content or "Job failed" in content:
                            return False, latest_log
                            
                except Exception:
                    pass  # Continue waiting if log read fails
            
            time.sleep(poll_interval)
            
        except Exception:
            time.sleep(poll_interval)
    
    return False, None  # Timeout

def log_background_status(instance_id, script_dir, message):
    """Log background process status to a dedicated log file."""
    try:
        logs_dir = os.path.join(script_dir, "SCRIPTS", "logs", "comfyui_jobs")
        if not os.path.exists(logs_dir):
            return
            
        # Find the most recent job log for this instance
        log_files = glob.glob(os.path.join(logs_dir, f"*_{instance_id}_*.log"))
        if not log_files:
            return
            
        latest_log = max(log_files, key=os.path.getmtime)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(latest_log, 'a') as f:
            f.write(f"\n[{timestamp}] BACKGROUND: {message}\n")
            
    except Exception:
        pass  # Fail silently in background

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    instance_id = sys.argv[1]
    script_dir = sys.argv[2]
    
    # Log that background monitoring started
    log_background_status(instance_id, script_dir, "Background monitoring started")
    
    # Wait for workflow completion
    workflow_completed, log_file = wait_for_workflow_completion(instance_id, max_wait_minutes=30)
    
    if workflow_completed:
        log_background_status(instance_id, script_dir, "Workflow completed - starting auto-extraction")
        
        # Auto-extract content
        vai_path = os.path.join(script_dir, "vai")
        try:
            extract_result = subprocess.run(
                [vai_path, "extract", str(instance_id), "content"],
                cwd=script_dir,
                text=True,
                capture_output=True,
                timeout=300  # 5 minute timeout for extraction
            )
            
            # Log extraction to the ComfyUI job log
            if os.path.exists(log_file):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open(log_file, 'a') as f:
                    f.write(f"\n\n=== EXTRACTION LOG (Background Auto-Extract) ===\n")
                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Extraction Status: {'SUCCESS' if extract_result.returncode == 0 else 'FAILED'}\n")
                    f.write(f"Return Code: {extract_result.returncode}\n\n")
                    
                    if extract_result.stdout:
                        f.write("--- STDOUT ---\n")
                        f.write(extract_result.stdout)
                        f.write("\n")
                        
                    if extract_result.stderr:
                        f.write("--- STDERR ---\n") 
                        f.write(extract_result.stderr)
                        f.write("\n")
                        
                    f.write("=== END EXTRACTION LOG ===\n")
            
            if extract_result.returncode == 0:
                log_background_status(instance_id, script_dir, "Auto-extraction completed successfully")
            else:
                log_background_status(instance_id, script_dir, f"Auto-extraction failed (code: {extract_result.returncode})")
                
        except Exception as e:
            log_background_status(instance_id, script_dir, f"Auto-extraction error: {str(e)}")
    else:
        log_background_status(instance_id, script_dir, "Workflow did not complete within timeout")

if __name__ == "__main__":
    main()