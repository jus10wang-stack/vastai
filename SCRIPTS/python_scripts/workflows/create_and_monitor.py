#!/usr/bin/env python3
"""
Create and Monitor Vast.ai Instance
Coordinates existing scripts to search, create, and monitor instances.
"""

import sys
import time
import os

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.search_offers import search_gpu
from components.create_instance import create_instance as create_vast_instance
from components.monitor_instance import VastInstanceMonitor

def start_monitoring_with_failsafe(instance_id, result_data=None):
    """Start monitoring the created instance with SSH failsafe"""
    import requests
    from components.destroy_instance import destroy_instance
    
    print(f"\n🔍 Starting monitoring for instance {instance_id} with SSH failsafe...")
    print("⚠️  If SSH connection fails for 3 minutes, instance will be automatically destroyed")
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
        monitor = VastInstanceMonitor(instance_id)
        
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
            
            # SSH is available, reset failure tracking
            if ssh_fail_start_time is not None:
                print("✅ SSH connection established!")
                ssh_fail_start_time = None
                ssh_fail_duration = 0
            
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
            elif status_data['status'] == 'ERROR':
                print(f"\n💥 Instance encountered an error. Check the logs above.")
                return False
            
            # Wait before next check
            print(f"\n⏳ Waiting {poll_interval}s before next check...")
            time.sleep(poll_interval)
        
        print(f"\n⏰ Timeout after {max_wait_minutes} minutes. Instance may still be starting up.")
        return False
        
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        return False

def main():
    # Parse command line arguments
    index = 0
    gpu_name = "RTX 3060"
    provisioning_script = "provision_test_3.sh"
    disk_size = 100
    
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid index provided. Usage: python create_and_monitor.py [INDEX] [GPU_NAME] [PROVISIONING_SCRIPT] [DISK_SIZE]")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        gpu_name = sys.argv[2]
        
    if len(sys.argv) > 3:
        provisioning_script = sys.argv[3]
        
    if len(sys.argv) > 4:
        try:
            disk_size = int(sys.argv[4])
        except ValueError:
            print("❌ Invalid disk size provided. Must be a number (GB)")
            sys.exit(1)
    
    print("🎯 Vast.ai Instance Creator & Monitor")
    print(f"🎮 GPU: {gpu_name}")
    print(f"📍 Using offer index: {index}")
    print(f"📋 Provisioning script: {provisioning_script}")
    print(f"💾 Disk size: {disk_size}GB")
    print("=" * 60)
    
    # Step 1: Search for offers using the search_gpu function
    selected_offer_id = search_gpu(gpu_name, index, disk_size)
    
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
                
                # Step 3: Start monitoring with failsafe
                success = start_monitoring_with_failsafe(instance_id, result)
                
                if success:
                    print("\n🎉 Instance is ready and monitoring completed successfully!")
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

if __name__ == "__main__":
    main()