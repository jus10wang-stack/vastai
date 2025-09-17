#!/usr/bin/env python3
"""
ComfyUI API Control via SSH
Programmatically modify and execute ComfyUI workflows on a remote Vast.ai instance.
"""

import paramiko
import json
import os
import sys
import time
import uuid
import threading
import copy
from datetime import datetime
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class ComfyUIController:
    def __init__(self, instance_id: str, ssh_host: str, ssh_port: int, ssh_key_path: Optional[str] = None):
        """
        Initialize ComfyUI controller for a Vast.ai instance.
        
        Args:
            instance_id: The Vast.ai instance ID
            ssh_host: SSH host (e.g., ssh5.vast.ai)
            ssh_port: SSH port number
            ssh_key_path: Path to SSH private key (auto-detects if not provided)
        """
        self.instance_id = instance_id
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        
        # Auto-detect SSH key if not provided
        if ssh_key_path:
            self.ssh_key_path = ssh_key_path
        else:
            possible_keys = [
                "~/.ssh/id_ed25519_vastai",
                "~/.ssh/id_ed25519",
                "~/.ssh/id_rsa"
            ]
            
            for key_path in possible_keys:
                full_path = os.path.expanduser(key_path)
                if os.path.exists(full_path):
                    self.ssh_key_path = full_path
                    break
            else:
                raise ValueError("No SSH key found. Please provide ssh_key_path.")
        
        self.ssh_client = None
        self.comfyui_url = "http://127.0.0.1:8188"
        
        # Logging setup
        self.logs_dir = os.path.expanduser("~/wsl-cursor-projects/vastai/logs/comfyui_jobs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.last_log_position = 0
        
    def connect(self):
        """Establish SSH connection to the instance."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            key = paramiko.Ed25519Key.from_private_key_file(self.ssh_key_path)
            
            print(f"🔗 Connecting to {self.ssh_host}:{self.ssh_port}...")
            self.ssh_client.connect(
                hostname=self.ssh_host,
                port=self.ssh_port,
                username='root',
                pkey=key,
                timeout=30
            )
            print("✅ SSH connection established")
            return True
            
        except Exception as e:
            print(f"❌ SSH connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            print("🔌 SSH connection closed")
    
    def upload_image(self, local_image_path: str, remote_filename: Optional[str] = None) -> str:
        """
        Upload an image to the ComfyUI input directory.
        
        Args:
            local_image_path: Path to the local image file
            remote_filename: Optional custom filename on remote (uses local filename if not provided)
            
        Returns:
            The filename used on the remote instance
        """
        if not os.path.exists(local_image_path):
            raise FileNotFoundError(f"Local image not found: {local_image_path}")
        
        if not remote_filename:
            remote_filename = os.path.basename(local_image_path)
        
        # Check common ComfyUI installation paths
        possible_paths = [
            f"/workspace/ComfyUI/input/{remote_filename}",
            f"/root/ComfyUI/input/{remote_filename}",
            f"/ComfyUI/input/{remote_filename}"
        ]
        
        # Find the correct path by checking which directory exists
        remote_path = None
        for path in ["/workspace/ComfyUI/input", "/root/ComfyUI/input", "/ComfyUI/input"]:
            stdin, stdout, stderr = self.ssh_client.exec_command(f"test -d {path} && echo 'exists'")
            if stdout.read().decode().strip() == 'exists':
                remote_path = f"{path}/{remote_filename}"
                break
        
        if not remote_path:
            # Create the workspace directory if none exist
            self.ssh_client.exec_command("mkdir -p /workspace/ComfyUI/input")
            remote_path = f"/workspace/ComfyUI/input/{remote_filename}"
        
        print(f"📤 Uploading {local_image_path} to {remote_path}...")
        
        sftp = self.ssh_client.open_sftp()
        try:
            sftp.put(local_image_path, remote_path)
            print(f"✅ Image uploaded: {remote_filename}")
            return remote_filename
        finally:
            sftp.close()
    
    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Execute a command via SSH and return stdout, stderr, and exit code."""
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_code
    
    def get_latest_workflow(self) -> Dict:
        """Fetch the latest workflow from ComfyUI history."""
        print("📥 Fetching latest workflow from ComfyUI...")
        
        cmd = f'curl -s -X GET "{self.comfyui_url}/history"'
        stdout, stderr, exit_code = self.execute_command(cmd)
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to fetch history: {stderr}")
        
        history = json.loads(stdout)
        if not history:
            raise RuntimeError("No workflow history found. Please run a workflow in ComfyUI first.")
        
        # Get the most recent prompt ID
        latest_prompt_id = list(history.keys())[0]
        workflow_data = history[latest_prompt_id]["prompt"][2]
        
        print(f"✅ Found latest workflow (ID: {latest_prompt_id})")
        return workflow_data
    
    def modify_workflow(self, workflow: Dict, image_filename: str, prompt_text: str, 
                       prompt_node_id: str = "6", image_node_id: str = "62") -> Dict:
        """
        Modify workflow with new image and prompt.
        
        Args:
            workflow: The workflow dictionary
            image_filename: Filename of the image in ComfyUI/input/
            prompt_text: The new prompt text
            prompt_node_id: Node ID for the positive prompt (default: "6")
            image_node_id: Node ID for the image loader (default: "62")
            
        Returns:
            Modified workflow dictionary
        """
        print(f"🔧 Modifying workflow with prompt: '{prompt_text}' and image: '{image_filename}'")
        
        # Update positive prompt
        if prompt_node_id in workflow:
            old_prompt = workflow[prompt_node_id]["inputs"].get("text", "")
            workflow[prompt_node_id]["inputs"]["text"] = prompt_text
            print(f"✅ Updated prompt in node {prompt_node_id}")
            print(f"   Old: '{old_prompt}'")
            print(f"   New: '{prompt_text}'")
        else:
            print(f"⚠️ Warning: Prompt node {prompt_node_id} not found")
            print(f"   Available nodes: {list(workflow.keys())}")
        
        # Update image
        if image_node_id in workflow:
            old_image = workflow[image_node_id]["inputs"].get("image", "")
            workflow[image_node_id]["inputs"]["image"] = image_filename
            print(f"✅ Updated image in node {image_node_id}")
            print(f"   Old: '{old_image}'")
            print(f"   New: '{image_filename}'")
        else:
            print(f"⚠️ Warning: Image node {image_node_id} not found")
            print(f"   Available nodes: {list(workflow.keys())}")
        
        return workflow
    
    def get_node_info(self, node_type: str) -> Dict:
        """Get node input configuration from ComfyUI API."""
        try:
            cmd = f'curl -s http://127.0.0.1:8188/object_info/{node_type}'
            stdout, stderr, exit_code = self.execute_command(cmd)
            
            if exit_code == 0:
                return json.loads(stdout)
            return {}
        except:
            return {}
    
    def map_widget_values_to_inputs(self, node_type: str, widget_values: list, inputs_config: list) -> Dict:
        """
        Dynamically map widget values to input names by analyzing the mismatch.
        
        Args:
            node_type: The type of the node
            widget_values: List of widget values from the workflow
            inputs_config: List of input definitions from the workflow node
            
        Returns:
            Dictionary mapping input names to values
        """
        api_inputs = {}
        
        # Get only the widget inputs (those without links)
        widget_inputs = [input_def for input_def in inputs_config 
                        if input_def.get('widget') is not None and input_def.get('link') is None]
        
        # If we have more widget_values than widget_inputs, there might be extra/unused values
        if len(widget_values) > len(widget_inputs):
            print(f"⚠️ Node {node_type}: {len(widget_values)} widget values but only {len(widget_inputs)} widget inputs")
            print(f"   Widget values: {widget_values}")
            print(f"   Widget inputs: {[inp['name'] for inp in widget_inputs]}")
            
            # Try to intelligently map by skipping obvious non-input values
            widget_index = 0
            for input_def in widget_inputs:
                input_name = input_def['name']
                
                # For each expected input, try to find the best matching value
                if widget_index < len(widget_values):
                    value = widget_values[widget_index]
                    
                    # If this value seems wrong for this input type, try next value
                    if self._value_seems_wrong_for_input(input_name, value, widget_values, widget_index):
                        widget_index += 1
                        if widget_index < len(widget_values):
                            value = widget_values[widget_index]
                    
                    api_inputs[input_name] = value
                    widget_index += 1
        else:
            # Simple 1:1 mapping when counts match
            for i, input_def in enumerate(widget_inputs):
                if i < len(widget_values):
                    api_inputs[input_def['name']] = widget_values[i]
        
        return api_inputs
    
    def _value_seems_wrong_for_input(self, input_name: str, value, all_values: list, current_index: int) -> bool:
        """Check if a value seems wrong for a given input and we should skip it."""
        
        # Common patterns where widget_values has extra items
        if input_name == "steps" and isinstance(value, str) and value in ["randomize", "fixed"]:
            return True
        
        if input_name == "start_at_step" and isinstance(value, str) and value in ["beta", "euler", "simple"]:
            return True
            
        if input_name == "sampler_name" and isinstance(value, (int, float)):
            return True
            
        if input_name == "return_with_leftover_noise" and isinstance(value, (int, float)) and value > 1:
            return True
        
        return False

    def load_workflow_from_file(self, workflow_path: str) -> Dict:
        """
        Load a workflow JSON file from the remote instance and convert to API format.
        
        Args:
            workflow_path: Path to the workflow JSON file on the remote instance
            
        Returns:
            Workflow dictionary in API prompt format
        """
        print(f"📥 Loading workflow from {workflow_path}...")
        
        cmd = f"cat {workflow_path}"
        stdout, stderr, exit_code = self.execute_command(cmd)
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to read workflow file: {stderr}")
        
        try:
            workflow_data = json.loads(stdout)
            
            # Convert ComfyUI workflow format to API prompt format
            if 'nodes' in workflow_data:
                print("🔄 Converting workflow format to API format...")
                prompt = {}
                
                for node in workflow_data['nodes']:
                    node_id = str(node['id'])
                    node_type = node['type']
                    
                    # Start with empty inputs
                    api_inputs = {}
                    
                    # Handle node connections first
                    if 'inputs' in node and isinstance(node['inputs'], list):
                        for input_def in node['inputs']:
                            if input_def.get('link') is not None:
                                link_id = input_def['link']
                                input_name = input_def['name']
                                
                                # Find the source node for this link
                                for link in workflow_data.get('links', []):
                                    if link[0] == link_id:  # link format: [id, from_node, from_slot, to_node, to_slot, type]
                                        source_node_id = link[1]
                                        source_slot = link[2]
                                        api_inputs[input_name] = [str(source_node_id), source_slot]
                                        break
                    
                    # Handle widget values dynamically
                    if 'widgets_values' in node and node['widgets_values'] and 'inputs' in node:
                        widget_inputs = self.map_widget_values_to_inputs(
                            node_type, 
                            node['widgets_values'], 
                            node['inputs']
                        )
                        api_inputs.update(widget_inputs)
                    
                    prompt[node_id] = {
                        "class_type": node_type,
                        "inputs": api_inputs
                    }
                
                print("✅ Workflow loaded and converted to API format")
                return prompt
            else:
                # Already in prompt format
                print("✅ Workflow loaded (already in API format)")
                return workflow_data
                
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in workflow file: {e}")
    
    def queue_prompt(self, workflow: Dict) -> str:
        """
        Queue a workflow for execution.
        
        Args:
            workflow: The workflow dictionary to execute
            
        Returns:
            The prompt ID of the queued job
        """
        print("🚀 Queueing workflow...")
        
        client_id = str(uuid.uuid4())
        payload = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        # Create a temporary file with the payload
        temp_payload_file = f"/tmp/comfyui_payload_{client_id}.json"
        
        # Write payload to temporary file
        cmd = f"echo '{json.dumps(payload)}' > {temp_payload_file}"
        self.execute_command(cmd)
        
        # Queue the prompt
        cmd = f'curl -s -X POST -H "Content-Type: application/json" -d @{temp_payload_file} "{self.comfyui_url}/prompt"'
        stdout, stderr, exit_code = self.execute_command(cmd)
        
        # Clean up temporary file
        self.execute_command(f"rm -f {temp_payload_file}")
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to queue prompt: {stderr}")
        
        response = json.loads(stdout)
        prompt_id = response.get("prompt_id")
        
        if not prompt_id:
            raise RuntimeError(f"Failed to get prompt ID: {response}")
        
        print(f"✅ Job queued! Prompt ID: {prompt_id}")
        return prompt_id
    
    def run_workflow(self, local_image_path: str, prompt_text: str, 
                    prompt_node_id: str = "6", image_node_id: str = "62") -> str:
        """
        Complete workflow: upload image, modify workflow, and queue execution.
        
        Args:
            local_image_path: Path to the local image file
            prompt_text: The prompt text to use
            prompt_node_id: Node ID for the positive prompt (default: "6")
            image_node_id: Node ID for the image loader (default: "62")
            
        Returns:
            The prompt ID of the queued job
        """
        print("=" * 50)
        print("🎨 ComfyUI Workflow Execution")
        print("=" * 50)
        print(f"📸 Image: {local_image_path}")
        print(f"💭 Prompt: {prompt_text}")
        print("=" * 50)
        
        # Upload image
        image_filename = self.upload_image(local_image_path)
        
        # Get latest workflow
        workflow = self.get_latest_workflow()
        
        # Modify workflow
        modified_workflow = self.modify_workflow(
            workflow, 
            image_filename, 
            prompt_text,
            prompt_node_id,
            image_node_id
        )
        
        # Queue execution
        prompt_id = self.queue_prompt(modified_workflow)
        
        print("=" * 50)
        print("🎉 Workflow submitted successfully!")
        print(f"📁 Output will appear in ComfyUI/output/")
        print("=" * 50)
        
        return prompt_id
    
    def get_queue_status(self) -> Dict:
        """Get current queue status from ComfyUI."""
        cmd = f'curl -s -X GET "{self.comfyui_url}/queue"'
        stdout, stderr, exit_code = self.execute_command(cmd)
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to get queue status: {stderr}")
        
        return json.loads(stdout)
    
    def get_history_item(self, prompt_id: str) -> Dict:
        """Get a specific item from history by prompt ID."""
        cmd = f'curl -s -X GET "{self.comfyui_url}/history/{prompt_id}"'
        stdout, stderr, exit_code = self.execute_command(cmd)
        
        if exit_code != 0:
            return {}
        
        try:
            return json.loads(stdout)
        except:
            return {}
    
    def audit_workflow_changes(self, original_workflow: Dict, modified_workflow: Dict, 
                              image_filename: str, prompt_text: str):
        """Show a detailed audit of what changed in the workflow."""
        print("\n" + "=" * 60)
        print("🔍 WORKFLOW AUDIT")
        print("=" * 60)
        
        changes_found = False
        
        # Check each node for changes
        for node_id, modified_node in modified_workflow.items():
            if node_id in original_workflow:
                orig_inputs = original_workflow[node_id].get('inputs', {})
                mod_inputs = modified_node.get('inputs', {})
                
                # Check for input changes
                for input_name, new_value in mod_inputs.items():
                    old_value = orig_inputs.get(input_name)
                    
                    if old_value != new_value:
                        changes_found = True
                        node_type = modified_node.get('class_type', 'Unknown')
                        print(f"📝 Node {node_id} ({node_type}) - {input_name}:")
                        print(f"   Old: {old_value}")
                        print(f"   New: {new_value}")
                        
                        # Highlight our specific changes
                        if input_name == "text" and new_value == prompt_text:
                            print("   ✅ This is your custom prompt!")
                        elif input_name == "image" and new_value == image_filename:
                            print("   ✅ This is your uploaded image!")
                        print()
        
        if not changes_found:
            print("⚠️ No changes detected in workflow")
        
        print("=" * 60)
    
    def save_modified_workflow(self, workflow: Dict, output_path: str):
        """Save the modified workflow to a file for inspection."""
        cmd = f"echo '{json.dumps(workflow, indent=2)}' > {output_path}"
        self.execute_command(cmd)
        print(f"💾 Modified workflow saved to: {output_path}")
    
    def convert_api_to_workflow_format(self, api_workflow: Dict, original_workflow_data: Dict, 
                                       image_filename: str, prompt_text: str) -> Dict:
        """
        Convert API format back to workflow format for ComfyUI UI compatibility.
        
        Args:
            api_workflow: The API format workflow
            original_workflow_data: The original workflow file data (with nodes, links, etc.)
            image_filename: The new image filename
            prompt_text: The new prompt text
            
        Returns:
            Workflow in ComfyUI UI format
        """
        # Start with the original workflow structure
        ui_workflow = original_workflow_data.copy()
        
        # Update the specific nodes with our changes
        if 'nodes' in ui_workflow:
            for node in ui_workflow['nodes']:
                node_id = str(node['id'])
                
                # Update prompt node (node 6)
                if node_id == "6" and node.get('type') == 'CLIPTextEncode':
                    if 'widgets_values' in node:
                        node['widgets_values'][0] = prompt_text
                        print(f"✅ Updated UI workflow node {node_id} prompt: '{prompt_text}'")
                
                # Update image node (node 62) 
                elif node_id == "62" and node.get('type') == 'LoadImage':
                    if 'widgets_values' in node:
                        node['widgets_values'][0] = image_filename
                        print(f"✅ Updated UI workflow node {node_id} image: '{image_filename}'")
        
        return ui_workflow
    
    def save_ui_compatible_workflow(self, api_workflow: Dict, original_workflow_data: Dict,
                                   image_filename: str, prompt_text: str, output_path: str):
        """Save a ComfyUI UI-compatible version of the modified workflow."""
        ui_workflow = self.convert_api_to_workflow_format(
            api_workflow, original_workflow_data, image_filename, prompt_text
        )
        
        cmd = f"echo '{json.dumps(ui_workflow, indent=2)}' > {output_path}"
        self.execute_command(cmd)
        print(f"💾 UI-compatible workflow saved to: {output_path}")
        print(f"   You can drag this file into ComfyUI web interface!")
    
    def create_job_log_file(self, job_id: str, workflow_path: str, image_filename: str, 
                           prompt_text: str, original_workflow: dict, modified_workflow: dict, 
                           prompt_node_id: str = "6", image_node_id: str = "62") -> str:
        """Create a new job log file with detailed metadata."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract workflow name from path
        workflow_name = os.path.basename(workflow_path).replace('.json', '').replace('_', '-')
        job_id_short = job_id[:8] if len(job_id) > 8 else job_id
        
        # Create log filename
        log_filename = f"{timestamp}_{self.instance_id}_{workflow_name}_{job_id_short}.log"
        log_path = os.path.join(self.logs_dir, log_filename)
        
        # Analyze modifications made to the workflow
        modifications = self.analyze_workflow_modifications(original_workflow, modified_workflow, image_filename, prompt_text, prompt_node_id, image_node_id)
        
        # Organized metadata
        metadata = {
            "execution_info": {
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "status": "queued"
            },
            "instance_info": {
                "instance_id": self.instance_id,
                "ssh_host": self.ssh_host,
                "ssh_port": self.ssh_port,
                "ssh_connection": f"{self.ssh_host}:{self.ssh_port}"
            },
            "workflow_info": {
                "template_file": os.path.basename(workflow_path),
                "workflow_name": workflow_name,
                "template_path": workflow_path
            },
            "modifications": modifications,
            "performance": {
                "queue_time": None,
                "execution_time": None,
                "total_duration": None,
                "start_timestamp": datetime.now().isoformat()
            }
        }
        
        # Write initial log file
        with open(log_path, 'w') as f:
            f.write("=== JOB METADATA ===\n")
            f.write(json.dumps(metadata, indent=2))
            f.write("\n\n=== LIVE TERMINAL OUTPUT ===\n")
        
        print(f"📝 Job log created: {log_filename}")
        return log_path
    
    def analyze_workflow_modifications(self, original_workflow: dict, modified_workflow: dict, 
                                     image_filename: str, prompt_text: str, prompt_node_id: str, image_node_id: str) -> dict:
        """Analyze what modifications were made to the workflow."""
        modifications = {
            "nodes_modified": [],
            "summary": {
                "prompt_changes": 0,
                "image_changes": 0,
                "other_changes": 0
            }
        }
        
        # Check specific nodes we know we modified
        prompt_node_changes = []
        image_node_changes = []
        
        # Check prompt node
        if prompt_node_id in modified_workflow:
            node_type = modified_workflow[prompt_node_id].get('class_type', 'Unknown')
            old_prompt = original_workflow.get(prompt_node_id, {}).get('inputs', {}).get('text', '')
            new_prompt = modified_workflow[prompt_node_id].get('inputs', {}).get('text', '')
            
            if old_prompt != new_prompt:
                prompt_node_changes.append({
                    "input_name": "text",
                    "change_type": "prompt",
                    "description": "Updated prompt text",
                    "old_value": old_prompt,
                    "new_value": new_prompt
                })
                modifications["summary"]["prompt_changes"] += 1
                
                modifications["nodes_modified"].append({
                    "node_id": prompt_node_id,
                    "node_type": node_type,
                    "node_name": self.get_node_display_name(node_type),
                    "changes": prompt_node_changes
                })
        
        # Check image node
        if image_node_id in modified_workflow:
            node_type = modified_workflow[image_node_id].get('class_type', 'Unknown')
            old_image = original_workflow.get(image_node_id, {}).get('inputs', {}).get('image', '')
            new_image = modified_workflow[image_node_id].get('inputs', {}).get('image', '')
            
            if old_image != new_image:
                image_node_changes.append({
                    "input_name": "image",
                    "change_type": "image",
                    "description": "Updated image file",
                    "old_value": old_image,
                    "new_value": new_image
                })
                modifications["summary"]["image_changes"] += 1
                
                modifications["nodes_modified"].append({
                    "node_id": image_node_id,
                    "node_type": node_type,
                    "node_name": self.get_node_display_name(node_type),
                    "changes": image_node_changes
                })
        
        # Check for any other unexpected changes
        for node_id, modified_node in modified_workflow.items():
            if node_id not in [prompt_node_id, image_node_id] and node_id in original_workflow:
                orig_inputs = original_workflow[node_id].get('inputs', {})
                mod_inputs = modified_node.get('inputs', {})
                node_type = modified_node.get('class_type', 'Unknown')
                
                node_changes = []
                
                # Check for input changes
                for input_name, new_value in mod_inputs.items():
                    old_value = orig_inputs.get(input_name)
                    
                    if old_value != new_value and not isinstance(new_value, list):  # Skip node connections
                        node_changes.append({
                            "input_name": input_name,
                            "change_type": "other",
                            "description": f"Changed {input_name}",
                            "old_value": old_value,
                            "new_value": new_value
                        })
                        modifications["summary"]["other_changes"] += 1
                
                if node_changes:
                    modifications["nodes_modified"].append({
                        "node_id": node_id,
                        "node_type": node_type,
                        "node_name": self.get_node_display_name(node_type),
                        "changes": node_changes
                    })
        
        return modifications
    
    def get_node_display_name(self, node_type: str) -> str:
        """Get a human-readable display name for a node type."""
        node_names = {
            "CLIPTextEncode": "Text Prompt Encoder",
            "LoadImage": "Image Loader", 
            "VAELoader": "VAE Model Loader",
            "CLIPLoader": "CLIP Model Loader",
            "UNETLoader": "Diffusion Model Loader",
            "LoraLoaderModelOnly": "LoRA Model Loader",
            "ModelSamplingSD3": "Model Sampling Configuration",
            "KSamplerAdvanced": "Advanced Sampler",
            "WanImageToVideo": "Image-to-Video Generator",
            "RIFE VFI": "Video Frame Interpolation",
            "CreateVideo": "Video Creator",
            "SaveVideo": "Video Saver",
            "VAEDecode": "VAE Decoder"
        }
        return node_names.get(node_type, node_type)
    
    def update_job_status(self, log_path: str, new_status: str, total_duration_seconds: float = None):
        """Update the job status in the log file metadata."""
        try:
            # Read current log
            with open(log_path, 'r') as f:
                content = f.read()
            
            # Find and update metadata section
            if "=== JOB METADATA ===" in content:
                parts = content.split("=== LIVE TERMINAL OUTPUT ===")
                metadata_section = parts[0].replace("=== JOB METADATA ===\n", "")
                
                try:
                    metadata = json.loads(metadata_section)
                    metadata["execution_info"]["status"] = new_status
                    metadata["execution_info"]["last_updated"] = datetime.now().isoformat()
                    
                    # Add total duration when job completes
                    if new_status in ["completed", "failed", "timeout"] and total_duration_seconds:
                        minutes = int(total_duration_seconds // 60)
                        seconds = int(total_duration_seconds % 60)
                        metadata["performance"]["total_duration"] = f"{minutes}m {seconds}s"
                        metadata["performance"]["total_duration_seconds"] = total_duration_seconds
                        metadata["execution_info"]["completion_timestamp"] = datetime.now().isoformat()
                    
                    # Rewrite file with updated metadata
                    with open(log_path, 'w') as f:
                        f.write("=== JOB METADATA ===\n")
                        f.write(json.dumps(metadata, indent=2))
                        f.write("\n\n=== LIVE TERMINAL OUTPUT ===\n")
                        if len(parts) > 1:
                            # Strip leading whitespace from terminal content to prevent accumulating newlines
                            terminal_content = parts[1].lstrip('\n')
                            f.write(terminal_content)
                    
                    if total_duration_seconds:
                        print(f"📊 Job {new_status} - Duration: {minutes}m {seconds}s")
                    else:
                        print(f"📊 Job status updated to: {new_status}")
                except json.JSONDecodeError:
                    print("⚠️ Could not update job status - invalid metadata format")
        except Exception as e:
            print(f"⚠️ Error updating job status: {e}")
    
    def update_job_performance_metrics(self, log_path: str, updates: dict):
        """Update specific performance metrics in the log file metadata."""
        try:
            if not os.path.exists(log_path):
                print(f"⚠️ Log file not found: {log_path}")
                return
                
            with open(log_path, 'r') as f:
                content = f.read()
            
            if "=== JOB METADATA ===" in content:
                parts = content.split("=== LIVE TERMINAL OUTPUT ===")
                metadata_section = parts[0].replace("=== JOB METADATA ===\n", "")
                
                try:
                    metadata = json.loads(metadata_section)
                    
                    # Update execution_info fields
                    if "status" in updates:
                        metadata["execution_info"]["status"] = updates["status"]
                    if "last_updated" in updates:
                        metadata["execution_info"]["last_updated"] = updates["last_updated"]
                    
                    # Update performance fields
                    performance_fields = ["queue_time", "execution_time", "execution_start_time", "current_duration"]
                    for field in performance_fields:
                        if field in updates:
                            metadata["performance"][field] = updates[field]
                    
                    # Rewrite file with updated metadata
                    with open(log_path, 'w') as f:
                        f.write("=== JOB METADATA ===\n")
                        f.write(json.dumps(metadata, indent=2))
                        f.write("\n\n=== LIVE TERMINAL OUTPUT ===\n")
                        if len(parts) > 1:
                            # Strip leading whitespace from terminal content to prevent accumulating newlines
                            terminal_content = parts[1].lstrip('\n')
                            f.write(terminal_content)
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️ Error parsing metadata JSON: {e}")
            
        except Exception as e:
            print(f"⚠️ Error updating performance metrics: {e}")
    
    def append_terminal_output(self, log_path: str, new_lines: list):
        """Append new terminal output lines with timestamps."""
        if not new_lines:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        with open(log_path, 'a') as f:
            for line in new_lines:
                if line.strip():  # Only log non-empty lines
                    f.write(f"[{timestamp}] {line.strip()}\n")
    
    def get_comfyui_logs_since_position(self, last_position: int) -> Tuple[list, int]:
        """Get ComfyUI log lines since the last position."""
        try:
            cmd = f'wc -l /var/log/portal/comfyui.log'
            stdout, stderr, exit_code = self.execute_command(cmd)
            
            if exit_code != 0:
                return [], last_position
                
            current_line_count = int(stdout.strip().split()[0])
            
            if current_line_count <= last_position:
                return [], last_position
            
            # Get new lines since last position
            lines_to_read = current_line_count - last_position
            cmd = f'tail -n {lines_to_read} /var/log/portal/comfyui.log'
            stdout, stderr, exit_code = self.execute_command(cmd)
            
            if exit_code == 0:
                new_lines = stdout.strip().split('\n')
                return new_lines, current_line_count
            else:
                return [], last_position
                
        except Exception as e:
            print(f"⚠️ Error reading ComfyUI logs: {e}")
            return [], last_position
    
    def monitor_job_progress(self, job_id: str, log_path: str, max_wait_seconds: int = 600):
        """Monitor job progress and capture live terminal output."""
        print(f"🔍 Starting job monitoring for {job_id}")
        start_time = time.time()
        
        # Update status to running
        self.update_job_status(log_path, "running")
        
        # Set log position to current end to capture only NEW output from this point forward
        try:
            cmd = 'wc -l /var/log/portal/comfyui.log'
            stdout, stderr, exit_code = self.execute_command(cmd)
            if exit_code == 0:
                current_line_count = int(stdout.strip().split()[0])
                self.last_log_position = current_line_count
                print(f"📍 Starting log capture from line {current_line_count} (only new logs will be captured)")
            else:
                self.last_log_position = 0
                print("⚠️ Could not determine log position, capturing all logs")
        except:
            self.last_log_position = 0
            print("⚠️ Error getting log position, capturing all logs")
        
        execution_started = False
        queue_end_time = None
        
        while time.time() - start_time < max_wait_seconds:
            try:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Get job status from ComfyUI history
                history_item = self.get_history_item(job_id)
                
                # Get new log lines
                new_lines, self.last_log_position = self.get_comfyui_logs_since_position(self.last_log_position)
                
                # Check if execution started by looking for execution indicators in new logs
                if new_lines and not execution_started:
                    for line in new_lines:
                        # Look for various execution start indicators
                        if any(indicator in line.lower() for indicator in [
                            "got prompt", "processing", "requested to load", 
                            "% | ", "|██", "it/s]"  # Progress bars
                        ]):
                            execution_started = True
                            queue_end_time = current_time
                            queue_duration = queue_end_time - start_time
                            print(f"🚀 Job execution started after {queue_duration:.1f}s queue time")
                            # Update metadata with queue time and execution start
                            self.update_job_performance_metrics(log_path, {
                                "queue_time": f"{queue_duration:.1f}s",
                                "execution_start_time": datetime.now().isoformat(),
                                "status": "executing"
                            })
                            break
                
                # Append new terminal output
                if new_lines:
                    self.append_terminal_output(log_path, new_lines)
                
                # Update last_updated timestamp periodically (every 10 seconds or when there are new logs)
                if new_lines or int(elapsed_time) % 10 == 0:
                    execution_time = current_time - queue_end_time if execution_started and queue_end_time else None
                    performance_update = {
                        "last_updated": datetime.now().isoformat(),
                        "current_duration": f"{elapsed_time:.1f}s"  # Always show running duration
                    }
                    if execution_time:
                        performance_update["execution_time"] = f"{execution_time:.1f}s"
                    
                    self.update_job_performance_metrics(log_path, performance_update)
                
                # Check if job is complete
                if history_item:
                    # Job found in history - it's completed
                    total_duration = time.time() - start_time
                    final_execution_time = (current_time - queue_end_time) if queue_end_time else total_duration
                    
                    self.update_job_status(log_path, "completed", total_duration)
                    self.append_execution_summary(log_path, history_item, total_duration)
                    print(f"✅ Job {job_id} completed - Total: {total_duration:.1f}s, Execution: {final_execution_time:.1f}s")
                    return True
                
                time.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                print(f"⚠️ Error monitoring job: {e}")
                time.sleep(5)
        
        # Timeout
        total_duration = time.time() - start_time
        self.update_job_status(log_path, "timeout", total_duration)
        print(f"⏰ Job monitoring timed out after {max_wait_seconds}s")
        return False
    
    def append_execution_summary(self, log_path: str, history_item: Dict, total_time: float):
        """Append execution summary to the log file."""
        try:
            outputs = history_item.get('outputs', {})
            output_files = []
            
            for node_id, node_output in outputs.items():
                if 'videos' in node_output:
                    for video in node_output['videos']:
                        output_files.append({
                            "type": "video",
                            "filename": video.get('filename', 'unknown'),
                            "node_id": node_id
                        })
                if 'images' in node_output:
                    for image in node_output['images']:
                        output_files.append({
                            "type": "image", 
                            "filename": image.get('filename', 'unknown'),
                            "node_id": node_id
                        })
            
            summary = {
                "total_time": f"{total_time:.1f}s",
                "output_files": output_files,
                "final_status": "completed",
                "completion_time": datetime.now().isoformat()
            }
            
            with open(log_path, 'a') as f:
                f.write(f"\n=== EXECUTION SUMMARY ===\n")
                f.write(json.dumps(summary, indent=2))
                f.write("\n")
                
        except Exception as e:
            print(f"⚠️ Error writing execution summary: {e}")
    
    def run_workflow_from_file(self, workflow_file_path: str, local_image_path: str, 
                              prompt_text: str, prompt_node_id: str = "6", 
                              image_node_id: str = "62") -> str:
        """
        Load a workflow from a JSON file and execute it with custom image and prompt.
        
        Args:
            workflow_file_path: Path to the workflow JSON file on the remote instance
            local_image_path: Path to the local image file
            prompt_text: The prompt text to use
            prompt_node_id: Node ID for the positive prompt (default: "6")
            image_node_id: Node ID for the image loader (default: "62")
            
        Returns:
            The prompt ID of the queued job
        """
        print("=" * 50)
        print("🎨 ComfyUI Workflow Execution (from file)")
        print("=" * 50)
        print(f"📄 Workflow: {workflow_file_path}")
        print(f"📸 Image: {local_image_path}")
        print(f"💭 Prompt: {prompt_text}")
        print("=" * 50)
        
        # Upload image
        image_filename = self.upload_image(local_image_path)
        
        # Load the original workflow file data (for UI format conversion)
        cmd = f"cat {workflow_file_path}"
        stdout, stderr, exit_code = self.execute_command(cmd)
        if exit_code != 0:
            raise RuntimeError(f"Failed to read workflow file: {stderr}")
        original_workflow_data = json.loads(stdout)
        
        # Load workflow from file (converted to API format)
        original_workflow = self.load_workflow_from_file(workflow_file_path)
        
        # Create a deep copy before modifying to preserve original for comparison
        modified_workflow = self.modify_workflow(
            copy.deepcopy(original_workflow), 
            image_filename, 
            prompt_text,
            prompt_node_id,
            image_node_id
        )
        
        # Show audit of changes
        self.audit_workflow_changes(original_workflow, modified_workflow, image_filename, prompt_text)
        
        # Save both formats for inspection
        self.save_modified_workflow(modified_workflow, "/tmp/modified_workflow_api.json")
        self.save_ui_compatible_workflow(modified_workflow, original_workflow_data, 
                                        image_filename, prompt_text, "/tmp/modified_workflow_ui.json")
        
        # Queue execution
        prompt_id = self.queue_prompt(modified_workflow)
        
        # Create job log file with detailed analysis
        log_path = self.create_job_log_file(prompt_id, workflow_file_path, image_filename, prompt_text, original_workflow, modified_workflow, prompt_node_id, image_node_id)
        
        # Start background monitoring using the standalone monitor script
        import subprocess
        import sys
        
        try:
            monitor_script = os.path.join(os.path.dirname(__file__), "monitor_job.py")
            cmd = [
                sys.executable, monitor_script,
                str(self.instance_id), self.ssh_host, str(self.ssh_port), 
                prompt_id, log_path
            ]
            
            # Start the monitor as a completely separate process
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"🔗 Background monitoring started as separate process")
            
        except Exception as e:
            print(f"❌ Failed to start background monitoring: {e}")
            # Fallback to thread-based monitoring
            def background_monitor():
                bg_controller = ComfyUIController(self.instance_id, self.ssh_host, self.ssh_port)
                try:
                    if bg_controller.connect():
                        bg_controller.monitor_job_progress(prompt_id, log_path, max_wait_seconds=7200)
                finally:
                    if bg_controller and hasattr(bg_controller, 'ssh_client') and bg_controller.ssh_client:
                        bg_controller.disconnect()
            
            monitor_thread = threading.Thread(target=background_monitor, daemon=True)
            monitor_thread.start()
        
        print("=" * 50)
        print("🎉 Workflow submitted successfully!")
        print(f"📁 Output will appear in ComfyUI/output/")
        print(f"📝 Live logs: {os.path.basename(log_path)}")
        print("=" * 50)
        
        return prompt_id


def main():
    """Example usage of the ComfyUI controller."""
    if len(sys.argv) < 5:
        print("Usage: python comfyui_api.py <instance_id> <ssh_host> <ssh_port> <image_path> \"<prompt>\"")
        print("Example: python comfyui_api.py 12345 ssh5.vast.ai 22222 ./image.jpg \"A beautiful sunset\"")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    ssh_host = sys.argv[2]
    ssh_port = int(sys.argv[3])
    image_path = sys.argv[4]
    prompt = sys.argv[5] if len(sys.argv) > 5 else "A beautiful scene"
    
    # Create controller
    controller = ComfyUIController(instance_id, ssh_host, ssh_port)
    
    try:
        # Connect
        if not controller.connect():
            sys.exit(1)
        
        # Run workflow
        prompt_id = controller.run_workflow(image_path, prompt)
        
        print(f"\n✅ Success! Your job ID is: {prompt_id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()