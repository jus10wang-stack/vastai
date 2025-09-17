#!/usr/bin/env python3
"""
Execute a specific workflow file on ComfyUI instance
Auto-fetches SSH info and uses standard workflow directory.
"""

import sys
import os
from dotenv import load_dotenv
import requests

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

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
                    # Apply port correction (Vast.ai bug workaround)
                    ssh_port = ssh_port + 1
                    print(f"✅ Found SSH info: {ssh_host}:{ssh_port}")
                    return ssh_host, ssh_port
                else:
                    raise ValueError("Instance found but SSH details not available")
        
        raise ValueError(f"Instance {instance_id} not found")
        
    except Exception as e:
        raise RuntimeError(f"Failed to get instance info: {e}")

def main():
    if len(sys.argv) < 4:
        print("Usage: python execute_workflow.py <instance_id> <workflow_filename> <image_filename> \"<prompt>\"")
        print("Example: python execute_workflow.py 26003629 wan2-2-I2V-FP8-Lightning.json test-image.png \"im a potato\"")
        print("")
        print("Workflow files should be located in: /workspace/ComfyUI/user/default/workflows/")
        print("Available workflows:")
        print("  - wan2-2-I2V-FP8-Lightning.json")
        print("")
        print("Image files should be located in: TEMPLATES/images/")
        print("Available images:")
        print("  - test-image.png")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    workflow_filename = sys.argv[2]
    image_filename = sys.argv[3]
    prompt = sys.argv[4] if len(sys.argv) > 4 else "A beautiful scene"
    
    # Get the script directory to build absolute paths
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # Hardcode the workflow base path - this is always the same
    workflow_path = f"/workspace/ComfyUI/user/default/workflows/{workflow_filename}"
    
    # Hardcode the image base path - always use TEMPLATES/images/
    image_path = os.path.join(script_dir, "TEMPLATES", "images", image_filename)
    
    try:
        # Auto-fetch SSH info from Vast.ai API
        ssh_host, ssh_port = get_instance_ssh_info(instance_id)
        
        controller = ComfyUIController(instance_id, ssh_host, ssh_port)
        
        print(f"🎯 Executing workflow: {workflow_filename}")
        print(f"📂 Full path: {workflow_path}")
        print(f"🖼️ Image: {image_path}")
        print(f"💭 Prompt: {prompt}")
        
        if controller.connect():
            try:
                prompt_id = controller.run_workflow_from_file(
                    workflow_path, 
                    image_path, 
                    prompt
                )
                print(f'🎉 Success! Job ID: {prompt_id}')
                print(f'🔍 To view live progress: python SCRIPTS/python_scripts/components/view_job_logs.py follow <log_filename>')
                print(f'📋 To list jobs: python SCRIPTS/python_scripts/components/view_job_logs.py list')
            except Exception as e:
                print(f'❌ Error: {e}')
            finally:
                controller.disconnect()
        else:
            print('❌ Failed to connect')
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()