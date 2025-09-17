#!/usr/bin/env python3
"""
View ComfyUI job logs - Monitor live progress and view completed jobs
"""

import os
import sys
import time
import json
from datetime import datetime

def get_logs_directory():
    """Get the job logs directory."""
    return os.path.expanduser("~/wsl-cursor-projects/vastai/SCRIPTS/logs/comfyui_jobs")

def list_recent_jobs(limit=10):
    """List recent job log files."""
    logs_dir = get_logs_directory()
    
    if not os.path.exists(logs_dir):
        print("❌ No job logs directory found")
        return []
    
    # Get all log files
    log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
    
    # Sort by filename (which includes timestamp)
    log_files.sort(reverse=True)
    
    return log_files[:limit]

def parse_log_metadata(log_path):
    """Parse job metadata from log file."""
    try:
        with open(log_path, 'r') as f:
            content = f.read()
        
        if "=== JOB METADATA ===" in content:
            parts = content.split("=== LIVE TERMINAL OUTPUT ===")
            metadata_section = parts[0].replace("=== JOB METADATA ===\n", "")
            return json.loads(metadata_section)
    except:
        pass
    
    return {}

def view_log_file(log_path, follow=False):
    """View a specific log file, optionally following it live."""
    if not os.path.exists(log_path):
        print(f"❌ Log file not found: {log_path}")
        return
    
    print(f"📋 Viewing: {os.path.basename(log_path)}")
    print("=" * 80)
    
    if follow:
        # Follow mode - continuously show new content
        print("🔄 Following log file (Ctrl+C to stop)...")
        print("=" * 80)
        
        with open(log_path, 'r') as f:
            # Show existing content
            content = f.read()
            print(content)
            
            # Follow new content
            try:
                while True:
                    new_content = f.read()
                    if new_content:
                        print(new_content, end='')
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️  Stopped following log")
    else:
        # Static view
        with open(log_path, 'r') as f:
            print(f.read())

def main():
    if len(sys.argv) < 2:
        print("ComfyUI Job Log Viewer")
        print("\nUsage:")
        print("  # List recent jobs")
        print("  python view_job_logs.py list")
        print()
        print("  # View specific job log")
        print("  python view_job_logs.py view <log_filename>")
        print()
        print("  # Follow job log in real-time")
        print("  python view_job_logs.py follow <log_filename>")
        print()
        print("Examples:")
        print("  python view_job_logs.py list")
        print("  python view_job_logs.py view 20250917_194523_26003629_wan2-lightning_abc123def.log")
        print("  python view_job_logs.py follow 20250917_194523_26003629_wan2-lightning_abc123def.log")
        sys.exit(1)
    
    command = sys.argv[1]
    logs_dir = get_logs_directory()
    
    if command == "list":
        print("📋 Recent ComfyUI Jobs:")
        print("=" * 80)
        
        log_files = list_recent_jobs()
        
        if not log_files:
            print("📭 No job logs found")
            return
        
        for i, log_file in enumerate(log_files, 1):
            log_path = os.path.join(logs_dir, log_file)
            metadata = parse_log_metadata(log_path)
            
            status = metadata.get('status', 'unknown')
            job_id = metadata.get('job_id', 'unknown')[:8]
            prompt = metadata.get('prompt_text', 'No prompt')[:50]
            workflow = metadata.get('workflow_name', 'unknown')
            
            # Status emoji
            status_emoji = {
                'queued': '⏳',
                'running': '🔄', 
                'completed': '✅',
                'failed': '❌',
                'timeout': '⏰'
            }.get(status, '❓')
            
            print(f"{i:2d}. {status_emoji} {log_file}")
            print(f"     Job: {job_id} | Workflow: {workflow} | Status: {status}")
            print(f"     Prompt: {prompt}{'...' if len(prompt) >= 50 else ''}")
            print()
    
    elif command in ["view", "follow"]:
        if len(sys.argv) < 3:
            print("❌ Please specify a log filename")
            sys.exit(1)
        
        log_filename = sys.argv[2]
        log_path = os.path.join(logs_dir, log_filename)
        
        follow_mode = (command == "follow")
        view_log_file(log_path, follow=follow_mode)
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()