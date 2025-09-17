#!/usr/bin/env python3
"""
Stop background job monitoring processes
"""

import os
import psutil
import sys
import signal
from datetime import datetime

def find_monitoring_processes():
    """Find running job monitoring processes."""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if proc.info['name'] == 'python' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                
                # Look for our workflow scripts
                if any(keyword in cmdline for keyword in [
                    'run_wan2_workflow.py',
                    'monitor_job.py', 
                    'comfyui_api.py'
                ]) and 'vastai/SCRIPTS/python_scripts' in cmdline:
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    processes.append({
                        'pid': proc.info['pid'],
                        'process': proc,
                        'cmdline': cmdline,
                        'started': create_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration': str(datetime.now() - create_time).split('.')[0]
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return processes

def stop_process(pid, force=False):
    """Stop a process by PID."""
    try:
        proc = psutil.Process(pid)
        if force:
            proc.kill()  # SIGKILL
            action = "force killed"
        else:
            proc.terminate()  # SIGTERM
            action = "terminated"
        
        print(f"✅ Process {pid} {action}")
        return True
    except psutil.NoSuchProcess:
        print(f"⚠️ Process {pid} no longer exists")
        return False
    except psutil.AccessDenied:
        print(f"❌ Permission denied to stop process {pid}")
        return False
    except Exception as e:
        print(f"❌ Error stopping process {pid}: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Stop ComfyUI Job Monitoring Processes")
            print()
            print("Usage:")
            print("  python stop_job_monitoring.py           # Interactive mode")
            print("  python stop_job_monitoring.py all       # Stop all processes")
            print("  python stop_job_monitoring.py <PID>     # Stop specific process")
            print("  python stop_job_monitoring.py -f <PID>  # Force stop specific process")
            sys.exit(0)
    
    print("🔍 Finding running ComfyUI job monitoring processes...")
    processes = find_monitoring_processes()
    
    if not processes:
        print("✅ No running ComfyUI monitoring processes found")
        return
    
    print(f"📋 Found {len(processes)} running process(es):")
    print()
    
    for i, proc_info in enumerate(processes, 1):
        print(f"{i}. PID: {proc_info['pid']}")
        print(f"   Started: {proc_info['started']} (running {proc_info['duration']})")
        print(f"   Command: {proc_info['cmdline']}")
        print()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "all":
            print("🛑 Stopping all monitoring processes...")
            for proc_info in processes:
                stop_process(proc_info['pid'])
            return
        
        elif arg == "-f" and len(sys.argv) > 2:
            pid = int(sys.argv[2])
            print(f"🛑 Force stopping process {pid}...")
            stop_process(pid, force=True)
            return
        
        elif arg.isdigit():
            pid = int(arg)
            print(f"🛑 Stopping process {pid}...")
            stop_process(pid)
            return
    
    # Interactive mode
    print("Options:")
    print("  'all' - Stop all processes")
    print("  '<number>' - Stop specific process by number")
    print("  'q' - Quit without stopping anything")
    print()
    
    choice = input("Enter your choice: ").strip().lower()
    
    if choice == 'q':
        print("👋 No processes stopped")
        return
    
    elif choice == 'all':
        print("🛑 Stopping all monitoring processes...")
        for proc_info in processes:
            stop_process(proc_info['pid'])
    
    elif choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(processes):
            proc_info = processes[num - 1]
            print(f"🛑 Stopping process {proc_info['pid']}...")
            stop_process(proc_info['pid'])
        else:
            print(f"❌ Invalid choice: {choice}")
    
    else:
        print(f"❌ Invalid choice: {choice}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)