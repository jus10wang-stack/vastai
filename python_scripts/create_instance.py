#!/usr/bin/env python3
"""
Create a vast.ai instance using the API
"""

import requests
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def create_instance(offer_id):
    url = f"https://console.vast.ai/api/v0/asks/{offer_id}/"
    
    # Method 1: Using template_hash_id only (current working method)
    # payload = json.dumps({
    #     "template_hash_id": "008d76dd092d69db5fab9af1a0f017e2"
    # })
    
    # Method 2: Using template_hash_id with overrides (if needed)
    # payload = json.dumps({
    #     "template_hash_id": "008d76dd092d69db5fab9af1a0f017e2",
    #     "disk": 48,  # Override disk size
    #     "env": {
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh"
    #     }
    # })
    
    # Method 3: Full configuration without template
    # Option C: Minimal configuration to test
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter"
    # })
    
    # Option D: Add basic env variables
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh"
    #     }
    # })
    
    # Option E: Add PORTAL_CONFIG and more settings
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention",
    #         "OPEN_BUTTON_PORT": "1111",
    #         "OPEN_BUTTON_TOKEN": "1"
    #     },
    #     "use_ssh": True,
    #     "use_jupyter_lab": True
    # })
    
    # Option F: Without PORTAL_CONFIG
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "use_ssh": True,
    #     "use_jupyter_lab": True
    # })
    
    # Option G: Just env variables, no other flags
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     }
    # })
    
    # Option H: Add onstart command
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "onstart": "cd /workspace && ./entrypoint.sh"
    # })
    
    # Option I: Try ssh runtype instead
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "ssh",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention",
    #         "PORTAL_CONFIG": "localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter"
    #     },
    #     "onstart": "cd /workspace && ./entrypoint.sh"
    # })
    
    # Option J: Working configuration with docker_options for ports
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "runtype": "jupyter",
    #     "env": {
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "onstart": "cd /workspace && ./entrypoint.sh",
    #     "docker_options": "-p 8188:8188 -p 8080:8080"
    # })
    
    # Back to template - this is the only reliable way
    # payload = json.dumps({
    #     "template_hash_id": "008d76dd092d69db5fab9af1a0f017e2",
    #     "disk": 100,
    #     "env": {
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh"
    #     }
    # })
    
    # Option K: Exact CLI command replica
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 100,
    #     "runtype": "ssh",
    #     "args": ["-p", "1111:1111", "-p", "8080:8080", "-p", "8384:8384", "-p", "72299:72299", "-p", "8188:8188"],
    #     "env": {
    #         "OPEN_BUTTON_PORT": "1111",
    #         "OPEN_BUTTON_TOKEN": "1",
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "onstart": "entrypoint.sh",
    #     "use_ssh": True
    # })
    
    # Option M: CLI to API translation (NO TEMPLATE)
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 100,
    #     "env": {
    #         "OPEN_BUTTON_PORT": "1111",
    #         "OPEN_BUTTON_TOKEN": "1", 
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "runtype": "ssh",
    #     "onstart": "entrypoint.sh",
    #     "use_ssh": True,
    #     "args": ["-p", "1111:1111", "-p", "8080:8080", "-p", "8384:8384", "-p", "72299:72299", "-p", "8188:8188"]
    # })
    
    # Option N: Try without args field, different runtype
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 100,
    #     "env": {
    #         "OPEN_BUTTON_PORT": "1111",
    #         "OPEN_BUTTON_TOKEN": "1", 
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "runtype": "jupyter",
    #     "onstart": "entrypoint.sh"
    # })
    
    # Option O: Working config + try docker_options for ports
    payload = json.dumps({
        "image": "vastai/comfy:@vastai-automatic-tag",
        "disk": 100,
        "env": {
            "OPEN_BUTTON_PORT": "1111",
            "OPEN_BUTTON_TOKEN": "1", 
            "JUPYTER_DIR": "/",
            "DATA_DIRECTORY": "/workspace/",
            "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
            "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
            "COMFYUI_ARGS": "--disable-auto-launch --port 8188 --listen 0.0.0.0 --enable-cors-header --use-sage-attention"
        },
        "runtype": "jupyter",
        "onstart": "entrypoint.sh",
        "docker_options": "-p 1111:1111 -p 8080:8080 -p 8188:8188"
    })
    
    # Option A: Using pipe-delimited PORTAL_CONFIG (your original format)
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 48,
    #     "env": {
    #         "OPEN_BUTTON_PORT": "1111",
    #         "OPEN_BUTTON_TOKEN": "1",
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "runtype": "jupyter",
    #     "use_ssh": True,
    #     "use_jupyter_lab": True,
    #     "jupyter_dir": "/",
    #     "onstart": "cd /workspace && ./entrypoint.sh"
    # })
    
    # Option B: Using JSON format for PORTAL_CONFIG (as shown in API docs)
    # payload = json.dumps({
    #     "image": "vastai/comfy:@vastai-automatic-tag",
    #     "disk": 100,
    #     "env": {
    #         "OPEN_BUTTON_PORT": "1111",
    #         "OPEN_BUTTON_TOKEN": "1",
    #         "JUPYTER_DIR": "/",
    #         "DATA_DIRECTORY": "/workspace/",
    #         "PORTAL_CONFIG": "{\"ports\": [8080, 8188]}",  # Simplified as per API example
    #         "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_3.sh",
    #         "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
    #     },
    #     "runtype": "jupyter",
    #     "use_ssh": True,
    #     "use_jupyter_lab": True,
    #     "jupyter_dir": "/",
    #     "onstart": "cd /workspace && ./entrypoint.sh"
    # })

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("VAST_API_KEY")}'
    }
    
    print(f"Creating instance {offer_id}...")
    print(f"URL: {url}")
    print(f"Payload: {payload}")
    
    # DON'T ACTUALLY EXECUTE - COSTS MONEY
    response = requests.put(url, headers=headers, data=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Instance created successfully!")
        print(f"Instance ID: {data.get('new_contract')}")
        return data
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_instance.py <OFFER_ID>")
        print("Example: python create_instance.py 20089849")
        sys.exit(1)
    
    create_instance(sys.argv[1])