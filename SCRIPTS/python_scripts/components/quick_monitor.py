#!/usr/bin/env python3
"""
Quick Monitor - Simple version that just asks for instance ID
Use this if create_and_monitor.py has issues
"""

import sys
import os
import subprocess

def main():
    if len(sys.argv) != 2:
        print("Usage: python quick_monitor.py <INSTANCE_ID>")
        print("Example: python quick_monitor.py 25984471")
        print()
        print("💡 To get your instance ID:")
        print("1. Run: poetry run python SCRIPTS/python_scripts/search_and_create.py 0")
        print("2. Look for 'Instance ID: XXXXX' in the output")
        print("3. Run this script with that ID")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    
    print(f"🔍 Starting monitor for instance {instance_id}")
    
    # Run the monitor script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_script = os.path.join(script_dir, "monitor_instance.py")
    
    try:
        result = subprocess.run([sys.executable, monitor_script, instance_id])
        sys.exit(result.returncode)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()