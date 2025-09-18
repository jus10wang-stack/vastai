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

def cancel_all_jobs(instance_id, ssh_host, ssh_port, force=False):
    """Cancel all active jobs (running + pending) for an instance."""
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect to instance")
            return False
        
        print(f"🔍 Finding all active jobs for instance {instance_id}...")
        
        # Get all active jobs
        queue_status = controller.get_queue_status()
        running_jobs = queue_status.get('queue_running', [])
        pending_jobs = queue_status.get('queue_pending', [])
        
        all_jobs = []
        
        # Collect running jobs
        for item in running_jobs:
            if len(item) >= 2:
                all_jobs.append({
                    'job_id': item[1],
                    'status': 'running',
                    'position': 0
                })
        
        # Collect pending jobs
        for idx, item in enumerate(pending_jobs):
            if len(item) >= 2:
                all_jobs.append({
                    'job_id': item[1],
                    'status': 'pending',
                    'position': idx + 1
                })
        
        if not all_jobs:
            print("✅ No active jobs found - nothing to cancel")
            return True
        
        print(f"📋 Found {len(all_jobs)} active jobs:")
        for job in all_jobs:
            print(f"  - {job['job_id']} ({job['status']})")
        
        # Confirmation unless --force is used
        if not force:
            response = input(f"\n⚠️ Are you sure you want to cancel ALL {len(all_jobs)} jobs? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("⏹️ Cancellation aborted")
                return False
        
        print(f"\n🛑 Cancelling all {len(all_jobs)} jobs...")
        
        success_count = 0
        for job in all_jobs:
            job_id = job['job_id']
            status = job['status']
            
            print(f"\n🔄 Cancelling {status} job: {job_id}")
            
            if status == 'running':
                success = cancel_running_job(controller, job_id)
            else:  # pending
                success = cancel_pending_job(controller, job_id)
            
            if success:
                success_count += 1
                print(f"✅ Successfully cancelled {job_id}")
            else:
                print(f"❌ Failed to cancel {job_id}")
        
        print(f"\n📊 Summary: {success_count}/{len(all_jobs)} jobs cancelled successfully")
        return success_count == len(all_jobs)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        controller.disconnect()

def cancel_all_jobs_all_instances(ssh_host, ssh_port, force=False):
    """Cancel all active jobs across ALL instances."""
    import requests
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    try:
        print("🔍 Fetching all instances...")
        
        # Get all instances from Vast.ai API
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        instances = data.get('instances', [])
        active_instances = [inst for inst in instances if inst.get('actual_status') == 'running']
        
        if not active_instances:
            print("✅ No running instances found")
            return True
        
        print(f"📋 Found {len(active_instances)} running instances")
        
        # First pass: Count jobs and collect instance info
        instances_with_jobs = []
        total_jobs = 0
        
        for instance in active_instances:
            instance_id = str(instance.get('id'))
            print(f"\n🔍 Checking instance {instance_id}...")
            
            # Get dynamic SSH info for this instance (not hardcoded defaults)
            instance_ssh_host = instance.get('ssh_host')
            instance_ssh_port = instance.get('ssh_port')
            
            if not instance_ssh_host or not instance_ssh_port:
                print(f"⚠️ No SSH info available for instance {instance_id} - skipping")
                continue
            
            # Use the port directly from API
            
            print(f"🔗 Using SSH: {instance_ssh_host}:{instance_ssh_port}")
            
            # Get job count for this instance
            controller = ComfyUIController(instance_id, instance_ssh_host, instance_ssh_port)
            
            try:
                if not controller.connect():
                    print(f"⚠️ Could not connect to instance {instance_id} - skipping")
                    continue
                
                queue_status = controller.get_queue_status()
                running_jobs = queue_status.get('queue_running', [])
                pending_jobs = queue_status.get('queue_pending', [])
                instance_job_count = len(running_jobs) + len(pending_jobs)
                
                if instance_job_count == 0:
                    print(f"✅ No jobs found on instance {instance_id}")
                else:
                    print(f"📋 Found {instance_job_count} jobs on instance {instance_id}")
                    total_jobs += instance_job_count
                    instances_with_jobs.append({
                        'instance_id': instance_id,
                        'ssh_host': instance_ssh_host,
                        'ssh_port': instance_ssh_port,
                        'job_count': instance_job_count
                    })
                    
            except Exception as e:
                print(f"⚠️ Error processing instance {instance_id}: {e}")
            finally:
                controller.disconnect()
        
        if total_jobs == 0:
            print("✅ No active jobs found across all instances")
            return True
        
        # Global confirmation unless --force is used
        if not force:
            response = input(f"\n⚠️ Found {total_jobs} total jobs across {len(instances_with_jobs)} instances. Cancel ALL? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("⏹️ Cancellation aborted")
                return False
        
        # Second pass: Actually cancel the jobs
        total_cancelled = 0
        print(f"\n🛑 Proceeding to cancel {total_jobs} jobs...")
        
        for instance_info in instances_with_jobs:
            instance_id = instance_info['instance_id']
            instance_ssh_host = instance_info['ssh_host']
            instance_ssh_port = instance_info['ssh_port']
            
            print(f"\n🔄 Cancelling jobs on instance {instance_id}...")
            success = cancel_all_jobs(instance_id, instance_ssh_host, instance_ssh_port, True)  # Force=True to avoid multiple prompts
            if success:
                total_cancelled += instance_info['job_count']
        
        print(f"\n📊 Final Summary: {total_cancelled}/{total_jobs} jobs cancelled across all instances")
        return total_cancelled == total_jobs
        
    except Exception as e:
        print(f"❌ Error fetching instances: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Cancel ComfyUI jobs by job ID")
    parser.add_argument("instance_id", nargs="?", help="Vast.ai instance ID (optional when using --all)")
    parser.add_argument("job_id", nargs="?", help="Job ID to cancel (optional for --list or --all)")
    parser.add_argument("--host", default="ssh9.vast.ai", help="SSH host (default: ssh9.vast.ai)")
    parser.add_argument("--port", type=int, default=13629, help="SSH port (default: 13629)")
    parser.add_argument("--list", "-l", action="store_true", help="List all active jobs")
    parser.add_argument("--all", "-a", action="store_true", help="Cancel all active jobs (for specific instance or all instances)")
    parser.add_argument("--force", "-f", action="store_true", help="Force cancellation without confirmation")
    
    args = parser.parse_args()
    
    # Handle --all flag
    if args.all:
        if args.instance_id:
            # Cancel all jobs for specific instance
            print(f"🛑 Cancelling all jobs for instance {args.instance_id}...")
            success = cancel_all_jobs(args.instance_id, args.host, args.port, args.force)
            sys.exit(0 if success else 1)
        else:
            # Cancel all jobs for ALL instances
            print("🛑 Cancelling all jobs for ALL instances...")
            success = cancel_all_jobs_all_instances(args.host, args.port, args.force)
            sys.exit(0 if success else 1)
    
    # Require instance_id for other operations
    if not args.instance_id:
        print("❌ Instance ID is required when not using --all")
        print("Usage examples:")
        print("  python cancel_job.py 26003629 abc123def456    # Cancel specific job")
        print("  python cancel_job.py 26003629 --list          # List jobs for instance")
        print("  python cancel_job.py 26003629 --all           # Cancel all jobs for instance")
        print("  python cancel_job.py --all                    # Cancel all jobs for ALL instances")
        sys.exit(1)
    
    if args.list:
        list_active_jobs(args.instance_id, args.host, args.port)
        return
    
    if not args.job_id:
        print("❌ Job ID is required when not using --list or --all")
        print("Usage examples:")
        print(f"  python cancel_job.py {args.instance_id} abc123def456")
        print(f"  python cancel_job.py {args.instance_id} --list")
        print(f"  python cancel_job.py {args.instance_id} --all")
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