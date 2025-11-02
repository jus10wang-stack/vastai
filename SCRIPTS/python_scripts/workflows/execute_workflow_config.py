#!/usr/bin/env python3
"""
Execute ComfyUI workflow using configuration files
Auto-handles image uploads, text prompts, and workflow parameter injection.
"""

import sys
import os
import json
import re
import requests
import tempfile
from pathlib import Path
from dotenv import load_dotenv

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
                    # Use the port directly from API
                    print(f"✅ Found SSH info: {ssh_host}:{ssh_port}")
                    return ssh_host, ssh_port
                else:
                    raise ValueError("Instance found but SSH details not available")
        
        raise ValueError(f"Instance {instance_id} not found")
        
    except Exception as e:
        raise RuntimeError(f"Failed to get instance info: {e}")

def find_files_in_config(config):
    """Find all image and text files referenced in the config (excluding _internal)."""
    image_files = set()
    text_files = set()
    
    def scan_value(value):
        if isinstance(value, str):
            # Check for image files
            if re.match(r'.*\.(png|jpg|jpeg|gif|bmp|webp)$', value, re.IGNORECASE):
                if value != "ComfyUI_00100.png":  # Ignore default
                    image_files.add(value)
            
            # Check for text files
            elif re.match(r'.*\.txt$', value, re.IGNORECASE):
                text_files.add(value)
        
        elif isinstance(value, (list, tuple)):
            for item in value:
                scan_value(item)
        
        elif isinstance(value, dict):
            for key, val in value.items():
                scan_value(val)
    
    # Scan all config sections except _internal
    for key, value in config.items():
        if key != "_internal":
            scan_value(value)
    
    return list(image_files), list(text_files)

def validate_and_prepare_files(image_files, text_files, script_dir):
    """Validate that all required files exist and prepare them for upload."""
    images_dir = os.path.join(script_dir, "TEMPLATES", "images")
    prompts_dir = os.path.join(script_dir, "TEMPLATES", "prompts")
    
    # Validate image files
    missing_images = []
    for img_file in image_files:
        img_path = os.path.join(images_dir, img_file)
        if not os.path.exists(img_path):
            missing_images.append(img_file)
    
    if missing_images:
        print(f"❌ Missing image files in TEMPLATES/4_images/:")
        for img in missing_images:
            print(f"  - {img}")
        raise FileNotFoundError(f"Missing {len(missing_images)} image file(s)")
    
    # Validate text files and load content
    missing_texts = []
    text_content = {}
    for txt_file in text_files:
        txt_path = os.path.join(prompts_dir, txt_file)
        if not os.path.exists(txt_path):
            missing_texts.append(txt_file)
        else:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text_content[txt_file] = f.read().strip()
    
    if missing_texts:
        print(f"❌ Missing text files in TEMPLATES/5_prompts/:")
        for txt in missing_texts:
            print(f"  - {txt}")
        raise FileNotFoundError(f"Missing {len(missing_texts)} text file(s)")
    
    print(f"✅ Found all required files:")
    if image_files:
        print(f"  📸 Images: {', '.join(image_files)}")
    if text_files:
        print(f"  📝 Texts: {', '.join(text_files)}")
    
    return text_content

def load_original_workflow(workflow_name, script_dir):
    """Load the original workflow template for comparison."""
    workflow_path = os.path.join(script_dir, "TEMPLATES", "workflows", f"{workflow_name}.json")
    
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(f"Original workflow not found: {workflow_path}")
    
    with open(workflow_path, 'r') as f:
        return json.load(f)

def apply_config_to_workflow(original_workflow, config):
    """Apply configuration changes to the original workflow."""
    workflow = json.loads(json.dumps(original_workflow))  # Deep copy
    
    parameters = config.get("parameters", {})
    changes_made = 0
    nodes_modified = []
    
    print(f"🔧 Applying configuration changes...")
    
    for param_key, param_config in parameters.items():
        node_id = param_config.get("node_id")
        new_values = param_config.get("values", [])
        
        if not node_id or not new_values:
            continue
        
        # Find the node in the workflow
        node_found = False
        for node in workflow.get("nodes", []):
            if node.get("id") == node_id:
                node_found = True
                original_values = node.get("widgets_values", [])
                
                # Check if values are different
                values_changed = False
                changes = []
                if len(new_values) != len(original_values):
                    values_changed = True
                else:
                    for i, (new_val, orig_val) in enumerate(zip(new_values, original_values)):
                        if new_val != orig_val:
                            values_changed = True
                            changes.append({
                                "index": i,
                                "old_value": orig_val,
                                "new_value": new_val
                            })
                
                if values_changed:
                    print(f"  📝 Node {node_id} ({param_config.get('node_type')}): {original_values} → {new_values}")
                    node["widgets_values"] = new_values
                    changes_made += 1
                    
                    # Track the modification details
                    node_mod_info = {
                        "node_id": str(node_id),
                        "node_type": param_config.get('node_type', node.get('type', 'Unknown')),
                        "node_name": param_config.get('title', node.get('title', f'Node {node_id}')),
                        "changes": []
                    }
                    
                    # Determine change type based on node type
                    if param_config.get('node_type') == 'CLIPTextEncode':
                        node_mod_info["changes"].append({
                            "input_name": "text",
                            "change_type": "prompt",
                            "description": "Updated prompt text",
                            "old_value": original_values[0] if original_values else "",
                            "new_value": new_values[0] if new_values else ""
                        })
                    elif param_config.get('node_type') == 'LoadImage':
                        node_mod_info["changes"].append({
                            "input_name": "image",
                            "change_type": "image",
                            "description": "Updated image file",
                            "old_value": original_values[0] if original_values else "",
                            "new_value": new_values[0] if new_values else ""
                        })
                    else:
                        # Generic change tracking
                        for idx, change in enumerate(changes):
                            node_mod_info["changes"].append({
                                "input_name": f"widget_{idx}",
                                "change_type": "parameter",
                                "description": f"Updated parameter {idx}",
                                "old_value": change["old_value"],
                                "new_value": change["new_value"]
                            })
                    
                    nodes_modified.append(node_mod_info)
                break
        
        if not node_found:
            print(f"⚠️ Warning: Node {node_id} not found in workflow")
    
    print(f"✅ Applied {changes_made} configuration changes")
    return workflow, nodes_modified

def substitute_text_content(config, text_content):
    """Replace .txt file references with actual text content."""
    def replace_text_refs(obj):
        if isinstance(obj, str):
            if obj.endswith('.txt') and obj in text_content:
                return text_content[obj]
            return obj
        elif isinstance(obj, list):
            return [replace_text_refs(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: replace_text_refs(value) for key, value in obj.items()}
        else:
            return obj
    
    return replace_text_refs(config)

def upload_images_to_instance(controller, image_files, script_dir):
    """Upload all required images to the ComfyUI instance."""
    if not image_files:
        print("📸 No images to upload")
        return True
    
    print(f"📸 Uploading {len(image_files)} image(s) to instance...")
    
    images_dir = os.path.join(script_dir, "TEMPLATES", "images")
    
    for img_file in image_files:
        local_path = os.path.join(images_dir, img_file)
        remote_path = f"/workspace/ComfyUI/input/{img_file}"
        
        print(f"  📤 Uploading {img_file}...")
        
        try:
            # Upload via SCP through the controller's SSH connection
            result = controller.upload_file(local_path, remote_path)
            if result:
                print(f"  ✅ {img_file} uploaded successfully")
            else:
                print(f"  ❌ Failed to upload {img_file}")
                return False
        except Exception as e:
            print(f"  ❌ Error uploading {img_file}: {e}")
            return False
    
    return True

def main():
    if len(sys.argv) != 3:
        print("Usage: python execute_workflow_config.py <instance_id> <config_filename>")
        print("Example: python execute_workflow_config.py 26003629 wan2-2-I2V-FP8-Lightning-user_friendly.json")
        print("")
        print("Config files should be located in: TEMPLATES/3_configs/")
        print("Available configs:")
        
        # Show available config files
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        configs_dir = os.path.join(script_dir, "TEMPLATES", "configs")
        if os.path.exists(configs_dir):
            for file in os.listdir(configs_dir):
                if file.endswith('.json'):
                    print(f"  - {file}")
        
        sys.exit(1)
    
    instance_id = sys.argv[1]
    config_filename = sys.argv[2]
    
    # Get the script directory to build absolute paths
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # Load configuration file
    config_path = os.path.join(script_dir, "TEMPLATES", "configs", config_filename)
    
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        workflow_name = config.get("workflow_name")
        if not workflow_name:
            print("❌ No workflow_name found in config")
            sys.exit(1)
        
        print(f"🎯 Executing workflow: {workflow_name}")
        print(f"📋 Config: {config_filename}")
        print("=" * 60)
        
        # Step 1: Find all files referenced in config
        image_files, text_files = find_files_in_config(config)
        
        # Step 2: Validate files and load text content
        text_content = validate_and_prepare_files(image_files, text_files, script_dir)
        
        # Step 3: Substitute text file references with content
        config = substitute_text_content(config, text_content)
        
        # Step 4: Load original workflow and apply config changes
        original_workflow = load_original_workflow(workflow_name, script_dir)
        modified_workflow, nodes_modified = apply_config_to_workflow(original_workflow, config)
        
        # Step 5: Auto-fetch SSH info and connect
        ssh_host, ssh_port = get_instance_ssh_info(instance_id)
        controller = ComfyUIController(instance_id, ssh_host, ssh_port)
        
        if not controller.connect():
            print('❌ Failed to connect to instance')
            sys.exit(1)
        
        try:
            # Step 6: Upload images to instance
            if not upload_images_to_instance(controller, image_files, script_dir):
                print("❌ Failed to upload images")
                sys.exit(1)
            
            # Step 7: Convert workflow to API format and execute
            print(f"\n🚀 Executing workflow on instance {instance_id}...")
            
            # Convert the UI format workflow to API format
            api_workflow = {}
            if 'nodes' in modified_workflow:
                for node in modified_workflow['nodes']:
                    node_id = str(node.get('id'))
                    api_workflow[node_id] = {
                        "class_type": node.get('type'),
                        "inputs": {}
                    }
                    
                    # Add widget values as inputs
                    if 'widgets_values' in node and node['widgets_values']:
                        # Map widget values to inputs based on the node type
                        # For now, we'll use the controller's load_workflow_from_file logic
                        # by saving and re-loading the workflow
                        pass
                    
                    # Add connections
                    if 'inputs' in node and isinstance(node['inputs'], list):
                        for input_def in node['inputs']:
                            if input_def.get('link') is not None:
                                link_id = input_def['link']
                                input_name = input_def['name']
                                
                                # Find the source node for this link
                                for link in modified_workflow.get('links', []):
                                    if link[0] == link_id:
                                        source_node_id = str(link[1])
                                        source_slot = link[2]
                                        api_workflow[node_id]["inputs"][input_name] = [source_node_id, source_slot]
                                        break
            
            # Save the UI format workflow and upload it
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(modified_workflow, tmp)
                tmp_path = tmp.name
            
            # Upload the workflow to the instance
            remote_path = f"/tmp/workflow_{instance_id}_{config_filename}"
            if controller.upload_file(tmp_path, remote_path):
                # Load and convert the workflow to API format
                api_workflow = controller.load_workflow_from_file(remote_path)
                
                # Execute the API format workflow without modifications
                prompt_id = controller.run_workflow_from_json_with_monitoring(
                    api_workflow,
                    workflow_file_path=remote_path,
                    workflow_name=f"workflow-{instance_id}-{config_filename.replace('.json', '')}",
                    nodes_modified=nodes_modified
                )
                
                # Clean up
                os.unlink(tmp_path)
                controller.execute_command(f"rm -f {remote_path}")
            else:
                print("❌ Failed to upload workflow")
                os.unlink(tmp_path)
                sys.exit(1)
            
            if prompt_id:
                print(f'🎉 Success! Job ID: {prompt_id}')
                print(f'🔍 To view live progress: python SCRIPTS/python_scripts/components/view_job_logs.py follow <log_filename>')
                print(f'📋 To list jobs: python SCRIPTS/python_scripts/components/view_job_logs.py list')
            else:
                print('❌ Failed to execute workflow')
                sys.exit(1)
                
        finally:
            controller.disconnect()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()