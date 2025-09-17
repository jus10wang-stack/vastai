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

def create_instance(offer_id, provisioning_script="provision_test_3.sh"):
    url = f"https://console.vast.ai/api/v0/asks/{offer_id}/"
    
    # Method 1: Using template_hash_id only (current working method)
    # payload = json.dumps({
    #     "template_hash_id": "008d76dd092d69db5fab9af1a0f017e2"
    # })
    
    # Method 2: Using template_hash_id with overrides (if needed)
    # payload = json.dumps({
    #     "template_hash_id": "008d76dd092d69db5fab9af1a0f017e2",
    #     "disk": 100,  # Override disk size
    #     "env": {
    #         "PROVISIONING_SCRIPT": f"https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/TEMPLATES/provisioning_scripts/{provisioning_script}"
    #     }
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
            "PROVISIONING_SCRIPT": f"https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/TEMPLATES/provisioning_scripts/{provisioning_script}",
            "COMFYUI_ARGS": "--disable-auto-launch --port 8188 --listen 0.0.0.0 --enable-cors-header --use-sage-attention"
        },
        "runtype": "jupyter",
        "onstart": "entrypoint.sh",
        "docker_options": "-p 1111:1111 -p 8080:8080 -p 8188:8188"
    })

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
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python create_instance.py <OFFER_ID> [PROVISIONING_SCRIPT]")
        print("Example: python create_instance.py 20089849")
        print("Example: python create_instance.py 20089849 provision_test_1.sh")
        print("Available provisioning scripts:")
        print("  - provision_test_1.sh")
        print("  - provision_test_2.sh") 
        print("  - provision_test_3.sh (default)")
        sys.exit(1)
    
    offer_id = sys.argv[1]
    provisioning_script = sys.argv[2] if len(sys.argv) == 3 else "provision_test_3.sh"
    
    create_instance(offer_id, provisioning_script)