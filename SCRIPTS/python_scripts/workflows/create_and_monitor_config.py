#!/usr/bin/env python3
"""
Create and Monitor Vast.ai Instance using Configuration Files
Reads instance settings from workflow config files and creates instances accordingly.
"""

import sys
import time
import os
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.search_offers import search_gpu
from components.create_instance import create_instance as create_vast_instance
from components.monitor_instance import VastInstanceMonitor
from components.destroy_instance import destroy_instance
from utils.ssh_utils import get_ssh_command_string

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

def start_monitoring_with_failsafe(instance_id, result_data=None, ssh_key_path=None):
    """Start monitoring the created instance using VastInstanceMonitor with log file"""
    import datetime
    import io
    from contextlib import redirect_stdout
    
    # Create log file for this instance
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"startup_{instance_id}_{timestamp}.log"
    
    # Get the SCRIPTS directory (where logs should go)
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    log_dir = os.path.join(script_dir, "SCRIPTS", "logs", "startup")
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)
    
    def log_message(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        print(formatted_message)
        with open(log_path, 'a') as f:
            f.write(formatted_message + "\n")
    
    # Custom stdout/stderr capture that writes to both console and log file
    class TeeOutput:
        def __init__(self, log_file_path):
            self.log_file_path = log_file_path
        
        def write(self, text):
            # Write to console
            import sys
            sys.__stdout__.write(text)
            # Write to log file with timestamp
            if text.strip() and self.log_file_path:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(self.log_file_path, 'a') as f:
                    # Don't add timestamp to continuation lines or empty lines
                    if text.strip():
                        f.write(f"[{timestamp}] {text}")
                    else:
                        f.write(text)
        
        def flush(self):
            import sys
            sys.__stdout__.flush()
    
    print(f"\n🔍 Starting monitoring for instance {instance_id} with SSH failsafe...")
    print("⚠️  If SSH connection fails for 3 minutes, instance will be automatically destroyed")
    print(f"📝 Log file: SCRIPTS/logs/startup/{log_filename}")
    print("=" * 60)
    
    # Extract host information if available
    host_id = None
    if result_data and isinstance(result_data, dict):
        host_id = result_data.get('host_id')
        if host_id:
            print(f"🏠 Host ID: {host_id}")
            log_message(f"🏠 Host ID: {host_id}")
    
    # Track SSH connection failures
    ssh_fail_start_time = None
    ssh_fail_duration = 0
    max_ssh_fail_minutes = 3
    
    try:
        log_message(f"🔄 Starting detailed monitoring for instance {instance_id}...")

        # Create the monitor instance with custom SSH key path if provided
        monitor = VastInstanceMonitor(instance_id, ssh_key_path=ssh_key_path)
        
        # Custom monitoring with SSH failure tracking and logging
        start_time = time.time()
        max_wait_minutes = 60
        poll_interval = 10
        max_wait_time = max_wait_minutes * 60
        status_script = monitor.create_status_script()
        
        # Redirect output to capture monitoring details
        tee = TeeOutput(log_path)
        
        with redirect_stdout(tee):
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
                        log_message(f"🚨 SSH failsafe triggered after {max_ssh_fail_minutes} minutes")
                        log_message(f"🏠 Problematic Host ID: {host_id}")
                        
                        # Destroy the instance
                        try:
                            destroy_result = destroy_instance(instance_id, force=True)
                            if destroy_result:
                                print("✅ Instance destroyed successfully")
                                log_message("✅ Instance destroyed successfully")
                            else:
                                print("❌ Failed to destroy instance - manual cleanup may be required")
                                log_message("❌ Failed to destroy instance")
                        except Exception as e:
                            print(f"❌ Error destroying instance: {e}")
                            log_message(f"❌ Error destroying instance: {e}")
                        
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
                        log_message(f"🚨 SSH failsafe triggered after {max_ssh_fail_minutes} minutes")
                        log_message(f"🏠 Problematic Host ID: {host_id}")
                        
                        # Destroy the instance
                        try:
                            destroy_result = destroy_instance(instance_id, force=True)
                            if destroy_result:
                                print("✅ Instance destroyed successfully")
                                log_message("✅ Instance destroyed successfully")
                            else:
                                print("❌ Failed to destroy instance - manual cleanup may be required")
                                log_message("❌ Failed to destroy instance")
                        except Exception as e:
                            print(f"❌ Error destroying instance: {e}")
                            log_message(f"❌ Error destroying instance: {e}")
                        
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
                    success = True
                    break
                elif status_data['status'] == 'ERROR':
                    print(f"\n💥 Instance encountered an error. Check the logs above.")
                    success = False
                    break
                
                # Wait before next check
                print(f"\n⏳ Waiting {poll_interval}s before next check...")
                time.sleep(poll_interval)
            else:
                # Timeout reached
                print(f"\n⏰ Timeout after {max_wait_minutes} minutes. Instance may still be starting up.")
                success = False
        
        if success:
            log_message(f"✅ Instance {instance_id} is fully ready and operational!")
            
            # Add practical SSH command for easy access
            try:
                import requests
                api_key = os.getenv("VAST_API_KEY")
                if api_key:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    response = requests.get("https://console.vast.ai/api/v0/instances/", headers=headers)
                    instances = response.json().get('instances', [])
                    
                    for instance in instances:
                        if str(instance.get('id')) == str(instance_id):
                            ssh_host = instance.get('ssh_host')
                            ssh_port = instance.get('ssh_port', 0)

                            # Generate portable SSH command using utility function
                            ssh_command = get_ssh_command_string(ssh_host, ssh_port, local_port=8188, remote_port=8188)

                            log_message(f"")
                            log_message(f"🔑 SSH Commands for ComfyUI Access:")
                            log_message(f"{ssh_command}")
                            log_message(f"Then open: http://localhost:8188")
                            log_message(f"")
                            break
            except Exception as e:
                log_message(f"⚠️ Could not generate SSH command: {e}")
        else:
            log_message(f"⚠️ Monitoring completed with issues for instance {instance_id}")
            
        return success
        
    except Exception as e:
        log_message(f"❌ Error during monitoring: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python create_and_monitor_config.py <config_filename>")
        print("Example: python create_and_monitor_config.py wan2-2-I2V-FP8-Lightning-user_friendly.json")
        print("")
        print("Config files should be located in: TEMPLATES/3_configs/")
        print("Available configs:")
        
        # Show available config files
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        configs_dir = os.path.join(script_dir, "TEMPLATES", "configs")
        if os.path.exists(configs_dir):
            for file in os.listdir(configs_dir):
                if file.endswith('.json'):
                    print(f"  - {file}")
        
        sys.exit(1)
    
    config_filename = sys.argv[1]
    
    # Get the script directory to build absolute paths
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    try:
        # Load instance configuration from config file
        gpu_name, gpu_index, provisioning_script, disk_size, github_user, github_branch, ssh_key_path = load_instance_config(config_filename, script_dir)
        
        print("🎯 Vast.ai Instance Creator & Monitor (Config-based)")
        print(f"📋 Config: {config_filename}")
        print(f"🎮 GPU: {gpu_name}")
        print(f"📍 Using offer index: {gpu_index}")
        print(f"📋 Provisioning script: {provisioning_script}")
        print(f"💾 Disk size: {disk_size}GB")
        print("=" * 60)
        
        # Step 1: Search for offers using the search_gpu function
        selected_offer_id = search_gpu(gpu_name, gpu_index, disk_size)
        
        if not selected_offer_id:
            print("❌ No suitable offer found at that index")
            sys.exit(1)
        
        print(f"\n✅ Selected offer ID: {selected_offer_id}")
        
        # Step 2: Create the instance using the create_instance function
        print("\n🚀 Creating instance...")
        try:
            result = create_vast_instance(selected_offer_id, provisioning_script, disk_size, github_user, github_branch)
            # The create_instance function prints its own output
            
            # Check if instance was created successfully
            if result and isinstance(result, dict):
                # Extract instance ID from the result dictionary
                instance_id = result.get('new_contract')
                if instance_id:
                    print(f"\n✅ Instance creation completed!")
                    print(f"🆔 Instance ID: {instance_id}")
                    print("\n⏳ Waiting 30 seconds before starting monitoring...")
                    time.sleep(30)
                    
                    # Step 3: Start monitoring
                    success = start_monitoring_with_failsafe(instance_id, result, ssh_key_path)
                    
                    if success:
                        print("\n🎉 Instance is ready and monitoring completed successfully!")
                        
                        # Auto-extract content
                        print("\n📥 Auto-extracting content files...")
                        try:
                            vai_path = os.path.join(script_dir, "vai")
                            result = subprocess.run(
                                [vai_path, "extract", str(instance_id), "content"],
                                cwd=script_dir,
                                text=True,
                                capture_output=False  # Let it stream to console/log naturally
                            )
                            
                            if result.returncode == 0:
                                print("✅ Content extraction completed successfully!")
                            else:
                                print("⚠️ Content extraction failed, but instance is ready for manual use")
                                print(f"💡 You can manually run: vai extract {instance_id} content")
                                
                        except Exception as e:
                            print(f"⚠️ Auto-extract error: {e}")
                            print(f"💡 Instance is ready - you can manually run: vai extract {instance_id} content")
                        
                        print(f"\n💡 Ready to execute workflow:")
                        print(f"vai exec {instance_id} {config_filename}")
                    else:
                        print(f"\n⚠️ Monitoring completed with issues.")
                        if result and result.get('host_id'):
                            print(f"🏠 Problematic Host ID: {result.get('host_id')}")
                        print(f"💡 If instance was not destroyed, check manually with: python monitor_instance.py {instance_id}")
                    
                    sys.exit(0 if success else 1)
                else:
                    print("❌ Could not extract instance ID from response")
                    print(f"Response: {result}")
                    sys.exit(1)
            else:
                print("❌ Failed to create instance - no valid response")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Error creating instance: {e}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()