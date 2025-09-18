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

def start_monitoring(instance_id):
    """Start monitoring the created instance using VastInstanceMonitor"""
    print(f"\n🔍 Starting monitoring for instance {instance_id}...")
    print("=" * 60)
    
    try:
        monitor = VastInstanceMonitor(instance_id)
        success = monitor.monitor(max_wait_minutes=60, poll_interval=10)
        return success
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
    selected_offer_id = search_gpu(gpu_name, index)
    
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

if __name__ == "__main__":
    main()