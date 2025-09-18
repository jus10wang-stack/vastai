#!/usr/bin/env python3
"""
Run ComfyUI Workflow on Vast.ai Instance
Automatically fetches instance details and executes a workflow with custom image and prompt.
"""

import sys
import os
import re

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController
from dotenv import load_dotenv
import requests

load_dotenv()

def get_instance_ssh_info(instance_id):
    """Fetch SSH connection details for an instance."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        raise ValueError("VAST_API_KEY not found in environment variables")
    
    api_url = "https://console.vast.ai/api/v0/instances/"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print(f"🔍 Fetching instance {instance_id} details...")
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Find our instance
        instances = data.get('instances', [])
        for instance in instances:
            if str(instance.get('id')) == str(instance_id):
                ssh_host = instance.get('ssh_host')
                ssh_port = instance.get('ssh_port')
                
                if ssh_host and ssh_port:
                    # Use the port directly from API
                    print(f"✅ Found SSH info: {ssh_host}:{ssh_port}")
                    return ssh_host, ssh_port
                else:
                    raise ValueError("Instance found but SSH details not available")
        
        raise ValueError(f"Instance {instance_id} not found")
        
    except Exception as e:
        raise RuntimeError(f"Failed to get instance info: {e}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python run_comfyui_workflow.py <instance_id> <image_path> \"<prompt>\"")
        print("Example: python run_comfyui_workflow.py 26003525 ./cat.jpg \"A majestic cat in space\"")
        print("\nOptional: Add node IDs as 4th and 5th arguments")
        print("Example: python run_comfyui_workflow.py 26003525 ./cat.jpg \"A majestic cat\" 6 62")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    image_path = sys.argv[2]
    prompt_text = sys.argv[3]
    
    # Optional: custom node IDs
    prompt_node_id = sys.argv[4] if len(sys.argv) > 4 else "6"
    image_node_id = sys.argv[5] if len(sys.argv) > 5 else "62"
    
    try:
        # Get SSH info from Vast.ai API
        ssh_host, ssh_port = get_instance_ssh_info(instance_id)
        
        # Create controller
        controller = ComfyUIController(instance_id, ssh_host, ssh_port)
        
        # Connect and run workflow
        if controller.connect():
            prompt_id = controller.run_workflow(
                image_path, 
                prompt_text,
                prompt_node_id,
                image_node_id
            )
            
            print(f"\n🎉 Workflow executed successfully!")
            print(f"📋 Prompt ID: {prompt_id}")
            print(f"📁 Check ComfyUI web interface or output directory for results")
        else:
            print("❌ Failed to connect to instance")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'controller' in locals():
            controller.disconnect()


if __name__ == "__main__":
    main()