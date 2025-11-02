#!/usr/bin/env python3
"""
Vast.ai Oneshot - Complete Pipeline
Creates instance, monitors until ready, auto-extracts content, and executes workflow.
"""

import sys
import time
import os
import json
import subprocess
import re
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.search_offers import search_gpu
from components.create_instance import create_instance as create_vast_instance
from components.monitor_instance import VastInstanceMonitor
from components.destroy_instance import destroy_instance
from components.comfyui_api import ComfyUIController

def load_instance_config(config_filename, script_dir):
    """Load instance configuration from config file."""
    config_path = os.path.join(script_dir, "TEMPLATES", "configs", config_filename)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    instance_config = config.get("instance_config", {})

    if not instance_config:
        raise ValueError("No instance_config section found in config file")

    # Extract required values with defaults
    gpu_name = instance_config.get("gpu_name", "RTX 5090")
    gpu_index = instance_config.get("gpu_index", 0)
    provisioning_script = instance_config.get("provisioning_script", "provision_test_3.sh")
    disk_size = instance_config.get("disk_size", 100)

    # NEW: Extract optional GitHub configuration
    github_user = instance_config.get("github_user", None)
    github_branch = instance_config.get("github_branch", "main")

    # NEW: Extract optional SSH key path (will use auto-detection if not specified)
    ssh_key_path = instance_config.get("ssh_key_path", None)

    # NEW: Return 7 values instead of 6
    return gpu_name, gpu_index, provisioning_script, disk_size, github_user, github_branch, ssh_key_path

def wait_for_workflow_completion(instance_id, max_wait_minutes=30):
    """Wait for any workflow to complete by monitoring job log files.
    
    Returns True if a workflow completed successfully, False on timeout.
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    logs_dir = os.path.join(script_dir, "SCRIPTS", "logs", "comfyui_jobs")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    poll_interval = 5
    
    print(f"📁 Monitoring job logs in: {logs_dir}")
    
    # Find the most recent log file for this instance
    instance_pattern = f"*_{instance_id}_*"
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Look for log files for this instance
            log_files = []
            if os.path.exists(logs_dir):
                import glob
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
                            print(f"✅ Found completion in: {os.path.basename(latest_log)}")
                            return True
                        elif '"final_status": "cancelled"' in content or '"final_status": "failed"' in content or "Job cancelled" in content or "Job failed" in content:
                            print(f"❌ Job failed or was cancelled: {os.path.basename(latest_log)}")
                            return False
                        elif "executing" in content.lower():
                            # Job is running, continue waiting
                            pass
                            
                except Exception as e:
                    print(f"⚠️ Error reading log file: {e}")
            
            # Show progress every 30 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0:
                print(f"⏱️ Waiting... {int(elapsed)}s / {max_wait_minutes*60}s")
            
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"⚠️ Error monitoring logs: {e}")
            time.sleep(poll_interval)
    
    print(f"⏰ Timeout waiting for workflow completion after {max_wait_minutes} minutes")
    return False

def log_extraction_to_job_log(instance_id, extract_result):
    """Append extraction output to the most recent ComfyUI job log for this instance."""
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        logs_dir = os.path.join(script_dir, "SCRIPTS", "logs", "comfyui_jobs")
        
        if not os.path.exists(logs_dir):
            return
            
        # Find the most recent job log for this instance
        import glob
        log_files = glob.glob(os.path.join(logs_dir, f"*_{instance_id}_*.log"))
        if not log_files:
            return
            
        # Get the most recent log file
        latest_log = max(log_files, key=os.path.getmtime)
        
        # Append extraction section to the job log
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(latest_log, 'a') as f:
            f.write(f"\n\n=== EXTRACTION LOG (Oneshot Auto-Extract) ===\n")
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
            
        print(f"📝 Extraction logged to: {os.path.basename(latest_log)}")
        
    except Exception as e:
        print(f"⚠️ Failed to log extraction: {e}")

def launch_background_monitoring_and_extraction(instance_id, script_dir, auto_destroy=False):
    """Launch background process to monitor workflow completion and auto-extract."""
    try:
        # Create a background script that waits for completion then extracts
        background_script = os.path.join(script_dir, "SCRIPTS", "python_scripts", "workflows", "oneshot_background.py")
        
        # Launch as detached background process
        cmd = [
            sys.executable, background_script,
            str(instance_id), script_dir, str(auto_destroy).lower()
        ]
        
        # Start completely detached process
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent
        )
        
        print(f"🔗 Background monitoring process started")
        
    except Exception as e:
        print(f"❌ Failed to start background monitoring: {e}")
        print(f"💡 You can manually monitor with: vai cancel {instance_id} --list")

def start_monitoring_with_failsafe(instance_id, result_data=None, ssh_key_path=None):
    """Start monitoring the created instance using VastInstanceMonitor with full provisioning"""
    import datetime
    import io
    from contextlib import redirect_stdout
    
    print(f"\n🔍 Starting full monitoring for instance {instance_id}...")
    print("⚠️ Will execute workflow when ComfyUI is fully ready")
    print("=" * 60)
    
    # Extract host information if available
    host_id = None
    if result_data and isinstance(result_data, dict):
        host_id = result_data.get('host_id')
        if host_id:
            print(f"🏠 Host ID: {host_id}")
    
    # Track SSH connection failures
    ssh_fail_start_time = None
    ssh_fail_duration = 0
    max_ssh_fail_minutes = 3
    
    try:
        print(f"🔄 Starting detailed monitoring for instance {instance_id}...")

        # Create the monitor instance with custom SSH key path if provided
        monitor = VastInstanceMonitor(instance_id, ssh_key_path=ssh_key_path)
        
        # Custom monitoring with SSH failure tracking
        start_time = time.time()
        max_wait_minutes = 60
        poll_interval = 10
        max_wait_time = max_wait_minutes * 60
        status_script = monitor.create_status_script()
        
        while time.time() - start_time < max_wait_time:
            # Get instance info
            instance_data = monitor.get_instance_info()
            if not instance_data:
                print("❌ Could not fetch instance data, retrying...")
                time.sleep(poll_interval)
                continue
            
            # Track host ID if not already captured
            if not host_id and instance_data:
                host_id = instance_data.get('host_id')
                if host_id:
                    print(f"🏠 Host ID: {host_id}")
            
            # Get SSH info
            ssh_info = monitor.get_ssh_info(instance_data)
            if not ssh_info:
                print("⏳ Waiting for instance to be ready for SSH...")
                if ssh_fail_start_time is None:
                    ssh_fail_start_time = time.time()
                
                ssh_fail_duration = (time.time() - ssh_fail_start_time) / 60
                
                if ssh_fail_duration >= max_ssh_fail_minutes:
                    print(f"\n🚨 SSH connection failed for {max_ssh_fail_minutes} minutes!")
                    print(f"🏠 Problematic Host ID: {host_id}")
                    print(f"💣 Destroying instance {instance_id} to avoid charges...")
                    
                    # Destroy the instance
                    try:
                        destroy_result = destroy_instance(instance_id, force=True)
                        if destroy_result:
                            print("✅ Instance destroyed successfully")
                        else:
                            print("❌ Failed to destroy instance - manual cleanup may be required")
                    except Exception as e:
                        print(f"❌ Error destroying instance: {e}")
                    
                    return False
                else:
                    print(f"⏰ SSH fail duration: {ssh_fail_duration:.1f} minutes (failsafe at {max_ssh_fail_minutes} minutes)")
                
                time.sleep(poll_interval)
                continue
            
            # SSH info is available, but don't reset timer until actual SSH works
            # (Timer will be reset later if execute_remote_script succeeds)
            
            # Store SSH info for later use
            monitor.current_ssh_info = ssh_info
            
            # Execute status check
            print(f"\n🔗 Connecting to {ssh_info['host']}:{ssh_info['port']}")
            raw_output = monitor.execute_remote_script(ssh_info, status_script)
            
            # Check for SSH errors in output
            if "SSH_NOT_READY" in raw_output or "SSH_ERROR" in raw_output or "SSH_AUTH_ERROR" in raw_output:
                print("⚠️ SSH connection issue detected")
                if ssh_fail_start_time is None:
                    ssh_fail_start_time = time.time()
                
                ssh_fail_duration = (time.time() - ssh_fail_start_time) / 60
                
                if ssh_fail_duration >= max_ssh_fail_minutes:
                    print(f"\n🚨 SSH connection failed for {max_ssh_fail_minutes} minutes!")
                    print(f"🏠 Problematic Host ID: {host_id}")
                    print(f"💣 Destroying instance {instance_id} to avoid charges...")
                    
                    # Destroy the instance
                    try:
                        destroy_result = destroy_instance(instance_id, force=True)
                        if destroy_result:
                            print("✅ Instance destroyed successfully")
                        else:
                            print("❌ Failed to destroy instance - manual cleanup may be required")
                    except Exception as e:
                        print(f"❌ Error destroying instance: {e}")
                    
                    return False
                else:
                    print(f"⏰ SSH fail duration: {ssh_fail_duration:.1f} minutes (failsafe at {max_ssh_fail_minutes} minutes)")
                
                time.sleep(poll_interval)
                continue
            
            # SSH working, reset failure tracking
            if ssh_fail_start_time is not None:
                print("✅ SSH connection restored!")
                ssh_fail_start_time = None
                ssh_fail_duration = 0
            
            # Rest of monitoring logic
            if "STATUS:" not in raw_output:
                print(f"❌ Unexpected script output: {raw_output}")
                time.sleep(poll_interval)
                continue
            
            # Parse and display status
            status_data = monitor.parse_status_output(raw_output)
            monitor.print_status_report(status_data)
            
            # Check if we're done
            if status_data['status'] == 'READY':
                print(f"\n🎉 Instance is fully ready! ComfyUI is accessible.")
                if status_data['tunnel_urls'].get('ComfyUI'):
                    print(f"🎨 ComfyUI URL: {status_data['tunnel_urls']['ComfyUI']}")
                return True
            # Removed ERROR status handling - let timer handle failures instead
            
            # Wait before next check
            print(f"\n⏳ Waiting {poll_interval}s before next check...")
            time.sleep(poll_interval)
        
        # Timeout reached
        print(f"\n⏰ Timeout after {max_wait_minutes} minutes. Instance may still be starting up.")
        return False
        
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        return False

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python oneshot.py <config_filename> [--destroy]")
        print("Example: python oneshot.py wan2-2-I2V-FP8-Lightning-user_friendly.json")
        print("Example: python oneshot.py wan2-2-I2V-FP8-Lightning-user_friendly.json --destroy")
        print("")
        print("This command will:")
        print("1. Create instance from config")
        print("2. Monitor until SSH is ready")
        print("3. Execute workflow immediately")
        print("4. Auto-extract content when done")
        print("5. Auto-destroy instance (if --destroy flag used)")
        print("")
        print("Options:")
        print("  --destroy    Automatically destroy instance after successful extraction")
        print("")
        print("Config files should be located in: TEMPLATES/configs/")
        sys.exit(1)
    
    config_filename = sys.argv[1]
    auto_destroy = len(sys.argv) == 3 and sys.argv[2] == "--destroy"
    
    # Get the script directory to build absolute paths
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    try:
        # Load instance configuration from config file
        gpu_name, gpu_index, provisioning_script, disk_size, github_user, github_branch, ssh_key_path = load_instance_config(config_filename, script_dir)
        
        print("🚀 Vast.ai Oneshot - Complete Pipeline")
        print(f"📋 Config: {config_filename}")
        print(f"🎮 GPU: {gpu_name}")
        print(f"📍 Using offer index: {gpu_index}")
        print(f"📋 Provisioning script: {provisioning_script}")
        print(f"💾 Disk size: {disk_size}GB")
        print("=" * 60)
        
        # Step 1: Search for offers
        print("🔍 Step 1: Searching for GPU offers...")
        selected_offer_id = search_gpu(gpu_name, gpu_index, disk_size)
        
        if not selected_offer_id:
            print("❌ No suitable offer found at that index")
            sys.exit(1)
        
        print(f"✅ Selected offer ID: {selected_offer_id}")
        
        # Step 2: Create the instance
        print("\n🚀 Step 2: Creating instance...")
        try:
            result = create_vast_instance(selected_offer_id, provisioning_script, disk_size, github_user, github_branch)
            
            if result and isinstance(result, dict):
                instance_id = result.get('new_contract')
                if instance_id:
                    print(f"✅ Instance creation completed!")
                    print(f"🆔 Instance ID: {instance_id}")
                    print("\n⏳ Waiting 30 seconds before monitoring...")
                    time.sleep(30)
                    
                    # Step 3: Monitor until fully ready (same as vai create)
                    print("\n🔍 Step 3: Full monitoring until ComfyUI ready...")
                    ready = start_monitoring_with_failsafe(instance_id, result, ssh_key_path)
                    
                    if ready:
                        print("\n⚡ Step 4: Executing workflow immediately...")
                        
                        # Execute workflow
                        vai_path = os.path.join(script_dir, "vai")
                        exec_result = subprocess.run(
                            [vai_path, "exec", str(instance_id), config_filename],
                            cwd=script_dir,
                            text=True,
                            capture_output=False  # Stream output live
                        )
                        
                        if exec_result.returncode == 0:
                            print("\n📋 Workflow submitted successfully!")
                            
                            # Launch background monitoring and extraction
                            print("\n🔄 Starting background monitoring and auto-extraction...")
                            launch_background_monitoring_and_extraction(instance_id, script_dir, auto_destroy)
                            
                            print("\n🎉 Oneshot pipeline launched successfully!")
                            print(f"🆔 Instance ID: {instance_id}")
                            print("🔄 Workflow monitoring and extraction running in background")
                            if auto_destroy:
                                print("💣 Instance will be automatically destroyed after successful extraction")
                            print("📋 Use these commands:")
                            print(f"   vai cancel {instance_id} --list    # Check job status")
                            if not auto_destroy:
                                print(f"   vai extract {instance_id} content  # Manual extract if needed")
                                print(f"   vai destroy {instance_id}         # Destroy when done")
                            print("💡 Terminal is now free for SSH port forwarding!")
                        else:
                            print("\n❌ Workflow execution failed")
                            print(f"💡 Instance {instance_id} is ready for manual debugging")
                    else:
                        print("\n❌ SSH connection failed - instance may have been destroyed")
                    
                    sys.exit(0 if ready else 1)
                else:
                    print("❌ Could not extract instance ID from response")
                    sys.exit(1)
            else:
                print("❌ Failed to create instance")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Error creating instance: {e}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()