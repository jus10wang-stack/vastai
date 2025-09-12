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
    
    payload = json.dumps({
            "disk": 48,
            "image": "vastai/comfy:@vastai-automatic-tag",
            "env": {
                "OPEN_BUTTON_PORT": "1111",
                "OPEN_BUTTON_TOKEN": "1",
                "JUPYTER_DIR": "/",
                "DATA_DIRECTORY": "/workspace/",
                "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
                "PROVISIONING_SCRIPT": "https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_1.sh",
                "COMFYUI_ARGS": "--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention"
            },
            "args": ["-p", "1111:1111", "-p", "8080:8080", "-p", "8384:8384", "-p", "72299:72299", "-p", "8188:8188"],
            "onstart_cmd": "entrypoint.sh",
            "runtype": "ssh",
            "target_state": "running"
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
    if len(sys.argv) != 2:
        print("Usage: python create_instance.py <OFFER_ID>")
        print("Example: python create_instance.py 20089849")
        sys.exit(1)
    
    create_instance(sys.argv[1])