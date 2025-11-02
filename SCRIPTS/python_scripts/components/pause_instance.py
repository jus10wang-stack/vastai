#!/usr/bin/env python3
"""
Pause/Unpause Vast.ai instances by instance ID - works for specific instances or all instances
"""

import sys
import os
import json
import argparse
import requests
import time
import datetime
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ssh_utils import get_ssh_command_string

def monitor_instance_startup(instance_id, log_file=None):
    """Monitor instance startup with detailed provisioning progress like create_and_monitor."""
    import sys
    import os
    import io
    from contextlib import redirect_stdout, redirect_stderr
    
    # Add the components directory to path if needed
    components_dir = os.path.dirname(os.path.abspath(__file__))
    if components_dir not in sys.path:
        sys.path.append(components_dir)
    
    from monitor_instance import VastInstanceMonitor
    
    def log_message(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        print(formatted_message)
        if log_file:
            with open(log_file, 'a') as f:
                f.write(formatted_message + "\n")
    
    try:
        log_message(f"🔄 Starting detailed monitoring for instance {instance_id}...")
        print("=" * 60)
        
        # Create a custom stdout/stderr capture that writes to both console and log file
        class TeeOutput:
            def __init__(self, log_file_path):
                self.log_file_path = log_file_path
                self.buffer = io.StringIO()
            
            def write(self, text):
                # Write to console
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
                sys.__stdout__.flush()
        
        # Redirect output to capture monitoring details
        if log_file:
            tee = TeeOutput(log_file)
            with redirect_stdout(tee):
                # Create and use the VastInstanceMonitor for detailed monitoring
                monitor = VastInstanceMonitor(instance_id)
                success = monitor.monitor(max_wait_minutes=15, poll_interval=10)
        else:
            # No log file, just run normally
            monitor = VastInstanceMonitor(instance_id)
            success = monitor.monitor(max_wait_minutes=15, poll_interval=10)
        
        if success:
            log_message(f"✅ Instance {instance_id} is fully ready and operational!")
            
            # Add practical SSH command for easy access
            try:
                # Get current SSH details for this instance
                import requests
                api_key = os.getenv("VAST_API_KEY")
                if api_key:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    response = requests.get("https://console.vast.ai/api/v0/instances/", headers=headers, timeout=30)
                    instances = response.json().get('instances', [])
                    
                    for instance in instances:
                        if str(instance.get('id')) == str(instance_id):
                            ssh_host = instance.get('ssh_host')
                            ssh_port = instance.get('ssh_port', 0)  # Use correct API port

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

def pause_single_instance(instance_id, force=False):
    """Stop a specific instance by ID."""
    return change_instance_state(instance_id, "stop", force)

def unpause_single_instance(instance_id, force=False, monitor=True):
    """Start a specific instance by ID with optional monitoring."""
    success = change_instance_state(instance_id, "start", force)
    
    if success and monitor:
        print(f"\n⏳ Waiting 10 seconds for instance to begin startup...")
        time.sleep(10)
        
        print(f"\n🔍 Starting monitoring for instance {instance_id}...")
        monitor_success = monitor_instance_startup(instance_id)
        
        if monitor_success:
            print(f"\n🎉 Instance {instance_id} is fully ready and operational!")
        else:
            print(f"\n⚠️ Instance {instance_id} started but monitoring had issues.")
            print(f"💡 Instance may still be initializing. Check manually with: ./vai list")
    elif success and not monitor:
        print(f"\n✅ Instance {instance_id} start request sent successfully")
        print(f"💡 Use './vai list' to check startup progress, or restart with monitoring")
            
    return success

def change_instance_state(instance_id, action, force=False):
    """Change instance state (stop/start)."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    action_verb = "stop" if action == "stop" else "start"
    action_emoji = "⏸️" if action == "stop" else "▶️"
    
    try:
        print(f"🔍 Fetching instance {instance_id} details...")
        
        # Get instance details first
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Find the specific instance
        instances = data.get('instances', [])
        target_instance = None
        for instance in instances:
            if str(instance.get('id')) == str(instance_id):
                target_instance = instance
                break
        
        if not target_instance:
            print(f"❌ Instance {instance_id} not found")
            return False
        
        # Show instance details
        status = target_instance.get('actual_status', 'unknown')
        gpu_name = target_instance.get('gpu_name', 'unknown')
        cost_per_hour = target_instance.get('dph_total', 0)
        
        print(f"📋 Instance Details:")
        print(f"  ID: {instance_id}")
        print(f"  Status: {status}")
        print(f"  GPU: {gpu_name}")
        print(f"  Cost: ${cost_per_hour:.4f}/hour")
        
        # Check if action makes sense for current status
        if action == "stop" and status in ["stopped", "exited"]:
            print(f"⚠️ Instance {instance_id} is already stopped/exited")
            return True
        elif action == "start" and status == "running":
            print(f"⚠️ Instance {instance_id} is already running")
            return True
        
        # Confirmation unless --force is used
        if not force:
            response = input(f"\n{action_emoji} Are you sure you want to {action_verb} instance {instance_id}? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print(f"⏹️ {action_verb.capitalize()} aborted")
                return False
        
        print(f"{action_emoji} {action_verb.capitalize()}ing instance {instance_id}...")
        
        # Stop/start the instance using the correct API format
        action_url = f"https://console.vast.ai/api/v0/instances/{instance_id}/"
        
        # Prepare the state change payload
        if action == "stop":
            payload = {"state": "stopped"}
        else:  # start
            payload = {"state": "running"}
        
        headers["Content-Type"] = "application/json"
        response = requests.put(action_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print(f"✅ Instance {instance_id} {action_verb}d successfully")
            return True
        else:
            print(f"❌ Failed to {action_verb} instance {instance_id}: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error {action_verb}ing instance: {e}")
        return False

def change_all_instances_state(action, force=False):
    """Stop or start ALL instances."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    action_verb = "stop" if action == "stop" else "start"
    action_emoji = "⏸️" if action == "stop" else "▶️"
    if action == "stop":
        target_status = "running"
    else:  # start
        target_statuses = ["stopped", "exited"]  # Both stopped and exited can be started
    
    try:
        print("🔍 Fetching all instances...")
        
        # Get all instances
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        instances = data.get('instances', [])
        
        if not instances:
            print("✅ No instances found")
            return True
        
        # Filter instances that can be stopped/started
        actionable_instances = []
        for instance in instances:
            status = instance.get('actual_status', 'unknown')
            if action == "stop":
                if status == target_status:  # running instances can be stopped
                    actionable_instances.append(instance)
            else:  # start
                if status in target_statuses:  # stopped or exited instances can be started
                    actionable_instances.append(instance)
        
        if not actionable_instances:
            if action == "stop":
                print("✅ No running instances found to stop")
            else:
                print("✅ No stopped or exited instances found to start")
            return True
        
        print(f"📋 Found {len(actionable_instances)} instances that can be {action_verb}d:")
        
        total_cost = 0
        for instance in actionable_instances:
            instance_id = instance.get('id')
            status = instance.get('actual_status', 'unknown')
            gpu_name = instance.get('gpu_name', 'unknown')
            cost_per_hour = instance.get('dph_total', 0)
            total_cost += cost_per_hour
            
            print(f"  - Instance {instance_id} ({status}) - {gpu_name} - ${cost_per_hour:.4f}/hour")
        
        print(f"\n💰 Total cost affected: ${total_cost:.4f}/hour")
        
        # Global confirmation unless --force is used
        if not force:
            response = input(f"\n{action_emoji} Are you sure you want to {action_verb} ALL {len(actionable_instances)} instances? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print(f"⏹️ {action_verb.capitalize()} aborted")
                return False
        
        print(f"\n{action_emoji} Proceeding to {action_verb} {len(actionable_instances)} instances...")
        
        # Stop/start all instances
        success_count = 0
        started_instances = []  # Track instances that need monitoring
        
        for instance in actionable_instances:
            instance_id = instance.get('id')
            gpu_name = instance.get('gpu_name', 'unknown')
            print(f"\n🔄 {action_verb.capitalize()}ing instance {instance_id} ({gpu_name})...")
            
            try:
                # Use the correct API format for state change
                action_url = f"https://console.vast.ai/api/v0/instances/{instance_id}/"
                
                # Prepare the state change payload
                if action == "stop":
                    payload = {"state": "stopped"}
                else:  # start
                    payload = {"state": "running"}
                
                headers["Content-Type"] = "application/json"
                response = requests.put(action_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"✅ Instance {instance_id} {action_verb} request sent")
                    
                    # If starting, add to monitoring list
                    if action == "start":
                        started_instances.append({
                            'id': instance_id,
                            'gpu_name': gpu_name
                        })
                else:
                    print(f"❌ Failed to {action_verb} instance {instance_id}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error {action_verb}ing instance {instance_id}: {e}")
        
        # For bulk start operations, monitor each instance with separate log files
        if action == "start" and started_instances:
            print(f"\n🔍 Starting monitoring for {len(started_instances)} instances...")
            print("⏳ Each instance will be monitored separately with individual log files")
            
            # Wait a bit for instances to begin starting
            print(f"\n⏳ Waiting 15 seconds for instances to begin startup...")
            time.sleep(15)
            
            for instance_info in started_instances:
                instance_id = instance_info['id']
                gpu_name = instance_info['gpu_name']
                
                # Create log file for this instance
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = f"startup_{instance_id}_{timestamp}.log"
                # Get the SCRIPTS directory (where logs should go)
                scripts_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                log_dir = os.path.join(scripts_dir, "logs", "startup")
                
                # Ensure log directory exists
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, log_filename)
                
                print(f"\n🔄 Starting monitoring for instance {instance_id} ({gpu_name})")
                print(f"📝 Log file: SCRIPTS/logs/startup/{log_filename}")
                
                # Start monitoring in background (we'll do sequential for now, could be parallel later)
                monitor_success = monitor_instance_startup(instance_id, log_path)
                
                if monitor_success:
                    print(f"✅ Instance {instance_id} fully ready")
                else:
                    print(f"⚠️ Instance {instance_id} monitoring had issues - check log file")
            
            print(f"\n📊 Startup monitoring completed for all instances")
            print(f"📝 Individual logs saved in: SCRIPTS/logs/startup/")
            print(f"💡 Use './vai list' to check current status")
        
        print(f"\n📊 Final Summary: {success_count}/{len(actionable_instances)} instances {action_verb}ped")
        if action == "stop":
            print(f"💰 Saved: ${total_cost:.4f}/hour in costs")
        else:
            print(f"💰 Resumed: ${total_cost:.4f}/hour in costs")
        return success_count == len(actionable_instances)
        
    except Exception as e:
        print(f"❌ Error fetching instances: {e}")
        return False

def list_all_instances():
    """List all instances with their details."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    try:
        print("🔍 Fetching all instances...")
        
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        instances = data.get('instances', [])
        
        if not instances:
            print("✅ No instances found")
            return True
        
        print(f"📋 Found {len(instances)} instances:")
        print("=" * 80)
        
        running_count = 0
        stopped_count = 0
        total_cost = 0
        
        for instance in instances:
            instance_id = instance.get('id')
            status = instance.get('actual_status', 'unknown')
            gpu_name = instance.get('gpu_name', 'unknown')
            cost_per_hour = instance.get('dph_total', 0)
            
            status_emoji = "🟢" if status == "running" else "🔴" if status == "stopped" else "🟡"
            
            print(f"{status_emoji} Instance {instance_id}")
            print(f"   Status: {status}")
            print(f"   GPU: {gpu_name}")
            print(f"   Cost: ${cost_per_hour:.4f}/hour")
            print()
            
            if status == "running":
                running_count += 1
                total_cost += cost_per_hour
            elif status == "stopped":
                stopped_count += 1
        
        print(f"📊 Summary: {running_count} running, {stopped_count} stopped")
        print(f"💰 Total running cost: ${total_cost:.4f}/hour")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching instances: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Stop/Start Vast.ai instances")
    parser.add_argument("action", nargs="?", choices=["pause", "unpause", "stop", "start"], help="Action to perform (stop/pause or start/unpause)")
    parser.add_argument("instance_id", nargs="?", help="Vast.ai instance ID (optional when using --all or --list)")
    parser.add_argument("--list", "-l", action="store_true", help="List all instances")
    parser.add_argument("--all", "-a", action="store_true", help="Apply action to ALL applicable instances")
    parser.add_argument("--force", "-f", action="store_true", help="Force action without confirmation")
    parser.add_argument("--no-monitor", action="store_true", help="Skip monitoring during start operations")
    
    args = parser.parse_args()
    
    # Handle --list flag
    if args.list:
        success = list_all_instances()
        sys.exit(0 if success else 1)
    
    # Require action for other operations
    if not args.action:
        print("❌ Action (stop/start) is required when not using --list")
        print("Usage examples:")
        print("  python pause_instance.py stop 26003629       # Stop specific instance")
        print("  python pause_instance.py start 26003629      # Start specific instance")
        print("  python pause_instance.py stop --all          # Stop ALL running instances")
        print("  python pause_instance.py start --all         # Start ALL stopped instances")
        print("  python pause_instance.py --list              # List all instances")
        sys.exit(1)
    
    # Handle --all flag
    if args.all:
        if args.instance_id:
            print("⚠️ Instance ID ignored when using --all")
        # Convert pause/unpause to stop/start for backwards compatibility
        action = args.action
        if action == "pause":
            action = "stop"
        elif action == "unpause":
            action = "start"
        success = change_all_instances_state(action, args.force)
        sys.exit(0 if success else 1)
    
    # Require instance_id for single action
    if not args.instance_id:
        print(f"❌ Instance ID is required when not using --all")
        print("Usage examples:")
        print(f"  python pause_instance.py {args.action} 26003629")
        print(f"  python pause_instance.py {args.action} --all")
        sys.exit(1)
    
    # Perform single instance action
    if args.action == "pause" or args.action == "stop":
        success = pause_single_instance(args.instance_id, args.force)
    else:  # unpause/start
        monitor = not args.no_monitor  # Enable monitoring unless --no-monitor is used
        success = unpause_single_instance(args.instance_id, args.force, monitor)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()