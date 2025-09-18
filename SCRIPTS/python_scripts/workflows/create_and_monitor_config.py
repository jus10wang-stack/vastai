#!/usr/bin/env python3
"""
Create and Monitor Vast.ai Instance using Configuration Files
Reads instance settings from workflow config files and creates instances accordingly.
"""

import sys
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.search_offers import search_gpu
from components.create_instance import create_instance as create_vast_instance
from components.monitor_instance import VastInstanceMonitor

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
    
    return gpu_name, gpu_index, provisioning_script, disk_size

def start_monitoring(instance_id):
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
    
    print(f"\n🔍 Starting monitoring for instance {instance_id}...")
    print(f"📝 Log file: SCRIPTS/logs/startup/{log_filename}")
    print("=" * 60)
    
    try:
        log_message(f"🔄 Starting detailed monitoring for instance {instance_id}...")
        
        # Redirect output to capture monitoring details
        tee = TeeOutput(log_path)
        with redirect_stdout(tee):
            monitor = VastInstanceMonitor(instance_id)
            success = monitor.monitor(max_wait_minutes=60, poll_interval=10)
        
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
                            ssh_key_path = '/home/ballsac/.ssh/id_ed25519_vastai'
                            
                            log_message(f"")
                            log_message(f"🔑 SSH Commands for ComfyUI Access:")
                            log_message(f"ssh -i {ssh_key_path} -p {ssh_port} root@{ssh_host} -L 8188:localhost:8188")
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
        print("Config files should be located in: TEMPLATES/configs/")
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
        gpu_name, gpu_index, provisioning_script, disk_size = load_instance_config(config_filename, script_dir)
        
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
            result = create_vast_instance(selected_offer_id, provisioning_script, disk_size)
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
                    success = start_monitoring(instance_id)
                    
                    if success:
                        print("\n🎉 Instance is ready and monitoring completed successfully!")
                        print(f"\n💡 Ready to execute workflow:")
                        print(f"vai exec {instance_id} {config_filename}")
                    else:
                        print(f"\n⚠️ Monitoring completed with issues. Instance ID: {instance_id}")
                        print(f"💡 You can manually check status with: python monitor_instance.py {instance_id}")
                    
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