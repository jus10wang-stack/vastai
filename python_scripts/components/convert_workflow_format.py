#!/usr/bin/env python3
"""
Convert workflow between API and UI formats
"""

import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def main():
    if len(sys.argv) < 8:
        print("Convert workflow to UI-compatible format")
        print("\nUsage:")
        print("  python convert_workflow_format.py <instance_id> <ssh_host> <ssh_port> <original_workflow_path> <image_filename> <prompt_text> <output_path>")
        print("")
        print("Example:")
        print("  python convert_workflow_format.py 26003629 ssh9.vast.ai 13629 /workspace/ComfyUI/user/default/workflows/wan2-2-I2V-FP8-Lightning.json test-image.png \"im a potato\" /tmp/modified_workflow_ui.json")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    ssh_host = sys.argv[2] 
    ssh_port = int(sys.argv[3])
    original_path = sys.argv[4]
    image_filename = sys.argv[5]
    prompt_text = sys.argv[6]
    output_path = sys.argv[7]
    
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect")
            sys.exit(1)
        
        # Load the original workflow file data
        cmd = f"cat {original_path}"
        stdout, stderr, exit_code = controller.execute_command(cmd)
        if exit_code != 0:
            raise RuntimeError(f"Failed to read workflow file: {stderr}")
        original_workflow_data = json.loads(stdout)
        
        # Convert to API format first
        api_workflow = controller.load_workflow_from_file(original_path)
        
        # Modify it
        modified_workflow = controller.modify_workflow(api_workflow, image_filename, prompt_text)
        
        # Convert back to UI format
        controller.save_ui_compatible_workflow(
            modified_workflow, 
            original_workflow_data, 
            image_filename, 
            prompt_text, 
            output_path
        )
        
        print("✅ Conversion complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        controller.disconnect()

if __name__ == "__main__":
    main()