#!/usr/bin/env python3
"""
Cancel ComfyUI jobs by job ID - works for both pending and running jobs
"""

import sys
import os
import json
import argparse

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def find_job_in_queue(controller, job_id):
    """Find a job in the current queue and return its status."""
    try:
        queue_status = controller.get_queue_status()
        
        # Check running jobs
        for item in queue_status.get('queue_running', []):
            if len(item) >= 2 and item[1] == job_id:
                return {
                    'status': 'running',
                    'position': 0,
                    'data': item
                }
        
        # Check pending jobs
        for idx, item in enumerate(queue_status.get('queue_pending', [])):
            if len(item) >= 2 and item[1] == job_id:
                return {
                    'status': 'pending', 
                    'position': idx + 1,
                    'data': item
                }
        
        return None
        
    except Exception as e:
        print(f"❌ Error checking queue: {e}")
        return None

def cancel_running_job(controller, job_id):
    """Cancel the currently running job using interrupt endpoint."""
    try:
        cmd = f'curl -s -X POST "{controller.comfyui_url}/interrupt"'
        stdout, stderr, exit_code = controller.execute_command(cmd)
        
        if exit_code == 0:
            print("✅ Sent interrupt signal to running job")
            
            # Wait and verify the cancellation
            print("⏳ Verifying cancellation...")
            import time
            for i in range(10):  # Check for up to 20 seconds
                time.sleep(2)
                
                # Check if job is still in running queue
                queue_status = controller.get_queue_status()
                running_jobs = queue_status.get('queue_running', [])
                still_running = any(item[1] == job_id for item in running_jobs if len(item) >= 2)
                
                if not still_running:
                    print(f"✅ Job successfully cancelled after {(i+1)*2} seconds")
                    return True
                    
                print(f"   Still cancelling... ({(i+1)*2}s)")
            
            print("⚠️ Interrupt sent but job may still be processing (timeout after 20s)")
            return True  # We did send the interrupt, even if verification timed out
            
        else:
            print(f"❌ Failed to interrupt job: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error interrupting job: {e}")
        return False

def cancel_pending_job(controller, job_id):
    """Cancel a pending job by removing it from the queue."""
    try:
        # Prepare the delete request payload
        delete_payload = {"delete": [job_id]}
        
        cmd = f'curl -s -X POST "{controller.comfyui_url}/queue" -H "Content-Type: application/json" -d \'{json.dumps(delete_payload)}\''
        stdout, stderr, exit_code = controller.execute_command(cmd)
        
        if exit_code == 0:
            print(f"✅ Removed job {job_id} from pending queue")
            return True
        else:
            print(f"❌ Failed to remove job from queue: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error removing job from queue: {e}")
        return False

def cancel_job(instance_id, ssh_host, ssh_port, job_id, force=False):
    """Cancel a ComfyUI job by its ID."""
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect to instance")
            return False
        
        print(f"🔍 Looking for job {job_id}...")
        
        # First, find the job in the current queue
        job_info = find_job_in_queue(controller, job_id)
        
        if job_info:
            status = job_info['status']
            position = job_info['position']
            
            print(f"📋 Job found: {status} (position {position})")
            
            if status == 'running':
                print(f"🛑 Cancelling running job {job_id}...")
                success = cancel_running_job(controller, job_id)
            elif status == 'pending':
                print(f"🗑️ Removing pending job {job_id} from queue...")
                success = cancel_pending_job(controller, job_id)
            
            if success:
                print(f"✅ Job {job_id} cancelled successfully")
                return True
            else:
                print(f"❌ Failed to cancel job {job_id}")
                return False
                
        else:
            # Job not found in current queue - check if it's in history (already completed)
            print(f"🔍 Job not found in queue, checking history...")
            history_item = controller.get_history_item(job_id)
            
            if history_item:
                print(f"📝 Job {job_id} is already completed/finished - cannot cancel")
                print(f"💡 Use: python view_job_logs.py list - to see recent jobs")
                return False
            else:
                print(f"❌ Job {job_id} not found in queue or history")
                print(f"💡 Check the job ID or use: python view_job_logs.py list")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        controller.disconnect()

def list_active_jobs(instance_id, ssh_host, ssh_port):
    """List all active (running + pending) jobs."""
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect to instance")
            return
        
        queue_status = controller.get_queue_status()
        running_jobs = queue_status.get('queue_running', [])
        pending_jobs = queue_status.get('queue_pending', [])
        
        print("📋 Active ComfyUI Jobs:")
        print("=" * 60)
        
        if running_jobs:
            print("🔄 RUNNING:")
            for idx, item in enumerate(running_jobs):
                if len(item) >= 2:
                    job_id = item[1]
                    print(f"  {idx + 1}. Job ID: {job_id}")
                    print(f"     Status: Running")
                    print()
        
        if pending_jobs:
            print("⏳ PENDING:")
            for idx, item in enumerate(pending_jobs):
                if len(item) >= 2:
                    job_id = item[1]
                    print(f"  {idx + 1}. Job ID: {job_id}")
                    print(f"     Status: Pending (position {idx + 1})")
                    print()
        
        if not running_jobs and not pending_jobs:
            print("✅ No active jobs found")
            print("💡 Use: python view_job_logs.py list - to see recent completed jobs")
        
        total_jobs = len(running_jobs) + len(pending_jobs)
        print(f"Total active jobs: {total_jobs}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        controller.disconnect()

def main():
    parser = argparse.ArgumentParser(description="Cancel ComfyUI jobs by job ID")
    parser.add_argument("instance_id", help="Vast.ai instance ID")
    parser.add_argument("job_id", nargs="?", help="Job ID to cancel (optional for --list)")
    parser.add_argument("--host", default="ssh9.vast.ai", help="SSH host (default: ssh9.vast.ai)")
    parser.add_argument("--port", type=int, default=13629, help="SSH port (default: 13629)")
    parser.add_argument("--list", "-l", action="store_true", help="List all active jobs")
    parser.add_argument("--force", "-f", action="store_true", help="Force cancellation without confirmation")
    
    args = parser.parse_args()
    
    if args.list:
        list_active_jobs(args.instance_id, args.host, args.port)
        return
    
    if not args.job_id:
        print("❌ Job ID is required when not using --list")
        print("Usage examples:")
        print(f"  python cancel_job.py {args.instance_id} abc123def456")
        print(f"  python cancel_job.py {args.instance_id} --list")
        sys.exit(1)
    
    # Confirmation unless --force is used
    if not args.force:
        response = input(f"Are you sure you want to cancel job {args.job_id}? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("⏹️ Cancellation aborted")
            return
    
    success = cancel_job(args.instance_id, args.host, args.port, args.job_id, args.force)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()