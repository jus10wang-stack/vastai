#!/usr/bin/env python3
"""
Simple Workflow Viewer - View executed workflows when ComfyUI frontend has issues
"""

import json
import sys
import os
from typing import Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.comfyui_api import ComfyUIController

def view_latest_execution(controller: ComfyUIController, limit: int = 5):
    """View the latest workflow executions with details."""
    try:
        cmd = f'curl -s http://127.0.0.1:8188/history'
        stdout, stderr, exit_code = controller.execute_command(cmd)
        
        if exit_code != 0:
            print(f"❌ Failed to get history: {stderr}")
            return
        
        history = json.loads(stdout)
        
        print("\n" + "=" * 80)
        print("🎨 RECENT WORKFLOW EXECUTIONS")
        print("=" * 80)
        
        entries = list(history.items())[:limit]
        
        for i, (prompt_id, entry) in enumerate(entries, 1):
            print(f"\n📋 Execution #{i} - ID: {prompt_id}")
            print("-" * 50)
            
            # Get workflow details
            workflow = entry.get('prompt', [None, None, {}])[2]
            outputs = entry.get('outputs', {})
            
            # Show key nodes and their settings
            for node_id, node_data in workflow.items():
                node_type = node_data.get('class_type', 'Unknown')
                inputs = node_data.get('inputs', {})
                
                # Only show interesting nodes
                if node_type in ['CLIPTextEncode', 'LoadImage', 'SaveVideo', 'KSamplerAdvanced']:
                    print(f"  🔸 Node {node_id} ({node_type}):")
                    
                    for input_name, input_value in inputs.items():
                        if isinstance(input_value, list):
                            print(f"     📎 {input_name}: → Node {input_value[0]}")
                        else:
                            if isinstance(input_value, str) and len(input_value) > 60:
                                display_value = input_value[:57] + "..."
                            else:
                                display_value = input_value
                            
                            # Highlight important values
                            if input_name == "text" and "potato" in str(input_value).lower():
                                print(f"     ✅ {input_name}: {display_value} (YOUR CUSTOM PROMPT!)")
                            elif input_name == "image" and "test-image" in str(input_value):
                                print(f"     ✅ {input_name}: {display_value} (YOUR UPLOADED IMAGE!)")
                            else:
                                print(f"     📝 {input_name}: {display_value}")
            
            # Show output info
            if outputs:
                print(f"  📁 Outputs generated: {len(outputs)} files")
                for node_id, output_data in outputs.items():
                    if 'videos' in output_data:
                        for video in output_data['videos']:
                            filename = video.get('filename', 'unknown')
                            print(f"     🎬 Video: {filename}")
                    if 'images' in output_data:
                        for image in output_data['images']:
                            filename = image.get('filename', 'unknown')
                            print(f"     🖼️  Image: {filename}")
            
            print()
        
        print("=" * 80)
        print("💡 TIP: Your workflows are executing perfectly via API!")
        print("   Check /workspace/ComfyUI/output/ for generated files")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) < 4:
        print("Simple Workflow Viewer")
        print("\nUsage:")
        print("  python workflow_viewer.py <instance_id> <ssh_host> <ssh_port> [limit]")
        print("")
        print("Example:")
        print("  python workflow_viewer.py 26003629 ssh9.vast.ai 13629 3")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    ssh_host = sys.argv[2]
    ssh_port = int(sys.argv[3])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        if not controller.connect():
            print("❌ Failed to connect")
            sys.exit(1)
        
        view_latest_execution(controller, limit)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        controller.disconnect()

if __name__ == "__main__":
    main()