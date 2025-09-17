#!/usr/bin/env python3
"""
Check for running background job monitoring processes
"""

import os
import psutil
import sys
from datetime import datetime

def find_running_job_monitors():
    """Find running Python processes that are monitoring ComfyUI jobs."""
    running_monitors = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if proc.info['name'] == 'python' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                
                # Look for our workflow scripts or monitoring processes
                if any(keyword in cmdline for keyword in [
                    'run_wan2_workflow.py',
                    'monitor_job.py', 
                    'comfyui_api.py',
                    'vastai/python_scripts'
                ]):
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    running_monitors.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline,
                        'started': create_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration': str(datetime.now() - create_time).split('.')[0]
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return running_monitors

def check_ssh_connections():
    """Check for active SSH connections to vast.ai."""
    ssh_connections = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'ssh' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'vast.ai' in cmdline:
                    ssh_connections.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return ssh_connections

def main():
    print("🔍 Checking for running ComfyUI job monitoring processes...")
    print("=" * 70)
    
    running_monitors = find_running_job_monitors()
    
    if running_monitors:
        print(f"📋 Found {len(running_monitors)} running monitoring process(es):")
        print()
        
        for i, monitor in enumerate(running_monitors, 1):
            print(f"{i}. PID: {monitor['pid']}")
            print(f"   Started: {monitor['started']} (running {monitor['duration']})")
            print(f"   Command: {monitor['cmdline']}")
            print()
        
        print("💡 To stop a process: kill <PID>")
        print("💡 To force stop: kill -9 <PID>")
    else:
        print("✅ No running ComfyUI monitoring processes found")
    
    print()
    print("🔗 Checking SSH connections to vast.ai...")
    print("=" * 70)
    
    ssh_connections = check_ssh_connections()
    
    if ssh_connections:
        print(f"📡 Found {len(ssh_connections)} SSH connection(s):")
        print()
        
        for i, conn in enumerate(ssh_connections, 1):
            print(f"{i}. PID: {conn['pid']}")
            print(f"   Command: {conn['cmdline']}")
            print()
    else:
        print("✅ No SSH connections to vast.ai found")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)