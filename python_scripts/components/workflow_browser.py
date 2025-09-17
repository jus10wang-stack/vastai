#!/usr/bin/env python3
"""
ComfyUI Workflow Browser - View and inspect workflows
"""

import json
import sys
import os
from typing import Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def print_workflow_summary(workflow: Dict, title: str = "Workflow Summary"):
    """Print a readable summary of a workflow."""
    print("\n" + "=" * 60)
    print(f"📋 {title}")
    print("=" * 60)
    
    for node_id, node in workflow.items():
        node_type = node.get('class_type', 'Unknown')
        inputs = node.get('inputs', {})
        
        print(f"🔸 Node {node_id}: {node_type}")
        
        # Show key inputs
        for input_name, input_value in inputs.items():
            if isinstance(input_value, list):
                # Connection to another node
                print(f"   📎 {input_name}: connected to node {input_value[0]} (slot {input_value[1]})")
            else:
                # Direct value
                if isinstance(input_value, str) and len(input_value) > 50:
                    display_value = input_value[:47] + "..."
                else:
                    display_value = input_value
                print(f"   📝 {input_name}: {display_value}")
        print()

def browse_queue(controller: ComfyUIController):
    """Browse the current ComfyUI queue."""
    try:
        queue_info = controller.get_queue_status()
        
        print("\n" + "=" * 60)
        print("📋 COMFYUI QUEUE STATUS")
        print("=" * 60)
        
        running = queue_info.get('queue_running', [])
        pending = queue_info.get('queue_pending', [])
        
        if running:
            print("🏃 Currently Running:")
            for i, item in enumerate(running):
                prompt_id = item[1]  # Queue item format: [number, prompt_id, prompt_data]
                print(f"   {i+1}. Prompt ID: {prompt_id}")
        
        if pending:
            print("⏳ Pending in Queue:")
            for i, item in enumerate(pending):
                prompt_id = item[1]
                print(f"   {i+1}. Prompt ID: {prompt_id}")
        
        if not running and not pending:
            print("✅ Queue is empty")
            
    except Exception as e:
        print(f"❌ Error getting queue: {e}")

def main():
    if len(sys.argv) < 4:
        print("ComfyUI Workflow Browser")
        print("\nUsage:")
        print("  # View a workflow file")
        print("  python workflow_browser.py <instance_id> <ssh_host> <ssh_port> view <workflow_path>")
        print("  ")
        print("  # Compare original vs modified")
        print("  python workflow_browser.py <instance_id> <ssh_host> <ssh_port> compare <original> <modified>")
        print("  ")
        print("  # Check queue status")
        print("  python workflow_browser.py <instance_id> <ssh_host> <ssh_port> queue")
        print("")
        print("Examples:")
        print("  python workflow_browser.py 26003629 ssh9.vast.ai 13629 view /workspace/ComfyUI/user/default/workflows/wan2-2-I2V-FP8-Lightning.json")
        print("  python workflow_browser.py 26003629 ssh9.vast.ai 13629 compare /workspace/ComfyUI/user/default/workflows/wan2-2-I2V-FP8-Lightning.json /tmp/modified_workflow.json")
        print("  python workflow_browser.py 26003629 ssh9.vast.ai 13629 queue")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    ssh_host = sys.argv[2]
    ssh_port = int(sys.argv[3])
    command = sys.argv[4]
    
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect")
            sys.exit(1)
        
        if command == "view":
            if len(sys.argv) < 6:
                print("❌ Missing workflow path")
                sys.exit(1)
            
            workflow_path = sys.argv[5]
            workflow = controller.load_workflow_from_file(workflow_path)
            print_workflow_summary(workflow, f"Workflow: {workflow_path}")
            
        elif command == "compare":
            if len(sys.argv) < 7:
                print("❌ Missing workflow paths")
                sys.exit(1)
            
            original_path = sys.argv[5]
            modified_path = sys.argv[6]
            
            original = controller.load_workflow_from_file(original_path)
            modified = controller.load_workflow_from_file(modified_path)
            
            print_workflow_summary(original, f"Original: {original_path}")
            print_workflow_summary(modified, f"Modified: {modified_path}")
            
            controller.audit_workflow_changes(original, modified, "your-image.png", "your prompt")
            
        elif command == "queue":
            browse_queue(controller)
            
        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        controller.disconnect()

if __name__ == "__main__":
    main()