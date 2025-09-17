#!/usr/bin/env python3
"""
Execute wan2-2-I2V-FP8-Lightning workflow on ComfyUI instance
"""

import sys
import os

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def main():
    if len(sys.argv) < 4:
        print("Usage: python run_wan2_workflow.py <instance_id> <image_path> \"<prompt>\"")
        print("Example: python run_wan2_workflow.py 26003629 ./test-image.png \"im a potato\"")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    image_path = sys.argv[2]
    prompt = sys.argv[3] if len(sys.argv) > 3 else "A beautiful scene"
    
    # Hardcoded values for your specific case
    ssh_host = "ssh9.vast.ai"
    ssh_port = 13629
    workflow_path = "/workspace/ComfyUI/user/default/workflows/wan2-2-I2V-FP8-Lightning.json"
    
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    if controller.connect():
        try:
            prompt_id = controller.run_workflow_from_file(
                workflow_path, 
                image_path, 
                prompt
            )
            print(f'🎉 Success! Job ID: {prompt_id}')
            print(f'📝 Background monitoring started - connection will remain open')
            print(f'🔍 To view live progress: python python_scripts/components/view_job_logs.py follow <log_filename>')
            print(f'📋 To list jobs: python python_scripts/components/view_job_logs.py list')
        except Exception as e:
            print(f'❌ Error: {e}')
            controller.disconnect()
    else:
        print('❌ Failed to connect')

if __name__ == "__main__":
    main()