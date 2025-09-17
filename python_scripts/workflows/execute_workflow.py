#!/usr/bin/env python3
"""
Execute a specific workflow file on ComfyUI instance
"""

import sys
import os

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def main():
    if len(sys.argv) < 5:
        print("Usage: python execute_workflow.py <instance_id> <ssh_host> <ssh_port> <workflow_path> <image_path> \"<prompt>\"")
        print("Example: python execute_workflow.py 26003629 ssh9.vast.ai 13629 /workspace/ComfyUI/user/default/workflows/wan2-2-I2V-FP8-Lightning.json ./test-image.png \"im a potato\"")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    ssh_host = sys.argv[2]
    ssh_port = int(sys.argv[3])
    workflow_path = sys.argv[4]
    image_path = sys.argv[5]
    prompt = sys.argv[6] if len(sys.argv) > 6 else "A beautiful scene"
    
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    if controller.connect():
        try:
            prompt_id = controller.run_workflow_from_file(
                workflow_path, 
                image_path, 
                prompt
            )
            print(f'🎉 Success! Job ID: {prompt_id}')
        except Exception as e:
            print(f'❌ Error: {e}')
        finally:
            controller.disconnect()
    else:
        print('❌ Failed to connect')

if __name__ == "__main__":
    main()