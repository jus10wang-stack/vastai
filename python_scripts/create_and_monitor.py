#!/usr/bin/env python3
"""
Create and Monitor Vast.ai Instance
Runs search_and_create.py and automatically monitors the created instance.
"""

import subprocess
import sys
import os
import re
import time

def extract_instance_id(output_text):
    """Extract instance ID from create_instance.py output"""
    # Look for the pattern "Instance ID: XXXXX"
    match = re.search(r'Instance ID:\s*(\d+)', output_text)
    if match:
        return match.group(1)
    
    # Alternative pattern: "new_contract: XXXXX" in JSON output
    match = re.search(r'new_contract[\'\"]*:\s*(\d+)', output_text)
    if match:
        return match.group(1)
    
    return None

def run_search_and_create(index=0):
    """Run search_and_create.py and capture output"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_script = os.path.join(script_dir, "search_and_create.py")
    
    if not os.path.exists(search_script):
        print(f"❌ Script not found: {search_script}")
        return None, None
    
    print(f"🚀 Running search_and_create.py with index {index}...")
    
    try:
        # Run the script and capture both stdout and stderr with timeout
        process = subprocess.Popen(
            [sys.executable, search_script, str(index)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time while capturing it with timeout
        output_lines = []
        instance_id_found = False
        timeout = 120  # 2 minutes timeout
        start_time = time.time()
        
        while True:
            # Check for timeout
            if time.time() - start_time > timeout:
                print(f"\n⚠️ Timeout after {timeout}s, terminating search_and_create.py")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                break
                
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
                
            if line:
                line_clean = line.rstrip()
                print(line_clean)
                output_lines.append(line)
                
                # Check if we got an instance ID - if so, we can proceed
                if "Instance ID:" in line_clean and not instance_id_found:
                    instance_id_found = True
                    print("\n✅ Instance ID detected, continuing...")
        
        # Wait for process to complete or timeout
        try:
            return_code = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("\n⚠️ Process didn't exit cleanly, but continuing...")
            process.kill()
            return_code = 0  # Assume success if we got instance ID
            
        full_output = ''.join(output_lines)
        
        return return_code, full_output
        
    except Exception as e:
        print(f"❌ Error running search_and_create.py: {e}")
        return None, None

def start_monitoring(instance_id):
    """Start monitoring the created instance"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_script = os.path.join(script_dir, "monitor_instance.py")
    
    if not os.path.exists(monitor_script):
        print(f"❌ Monitor script not found: {monitor_script}")
        return False
    
    print(f"\\n🔍 Starting monitoring for instance {instance_id}...")
    print("=" * 60)
    
    try:
        result = subprocess.run([sys.executable, monitor_script, instance_id])
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running monitor: {e}")
        return False

def main():
    # Get index from command line or use default
    index = 0
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid index provided. Usage: python create_and_monitor.py [INDEX]")
            sys.exit(1)
    
    print("🎯 Vast.ai Instance Creator & Monitor")
    print(f"📍 Using offer index: {index}")
    print("=" * 60)
    
    # Step 1: Create the instance
    return_code, output = run_search_and_create(index)
    
    if return_code != 0 or output is None:
        print("❌ Failed to create instance")
        sys.exit(1)
    
    # Step 2: Extract instance ID
    instance_id = extract_instance_id(output)
    
    if not instance_id:
        print("❌ Could not extract instance ID from output")
        print("🔍 Full output was:")
        print(output)
        print("\\n💡 You can manually run: python monitor_instance.py <INSTANCE_ID>")
        sys.exit(1)
    
    print(f"\\n✅ Instance created successfully!")
    print(f"🆔 Instance ID: {instance_id}")
    print("\\n⏳ Waiting 30 seconds before starting monitoring...")
    time.sleep(30)
    
    # Step 3: Start monitoring  
    success = start_monitoring(instance_id)
    
    if success:
        print("\\n🎉 Instance is ready and monitoring completed successfully!")
    else:
        print(f"\\n⚠️ Monitoring completed with issues. Instance ID: {instance_id}")
        print("💡 You can manually check status with: python monitor_instance.py {instance_id}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()