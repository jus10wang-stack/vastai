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

def get_provisioning_script_url(provisioning_script, github_user=None, github_branch="main"):
    """
    Get provisioning script URL with flexible configuration options.

    Supports three modes:
    1. Full URL: Use the provided URL directly
    2. GitHub user specified: Construct URL from user/branch
    3. Auto-detect: Use VASTAI_GITHUB_USER env var or default to "jiso007"

    Args:
        provisioning_script: Either a full URL or just filename (e.g., "test2.sh")
        github_user: GitHub username (optional, falls back to env var/default)
        github_branch: GitHub branch name (default: "main")

    Returns:
        str: Full URL to the provisioning script

    Examples:
        >>> get_provisioning_script_url("https://raw.github.com/.../script.sh")
        "https://raw.github.com/.../script.sh"  # Returns as-is

        >>> get_provisioning_script_url("test2.sh", github_user="jus10wang-stack")
        "https://raw.githubusercontent.com/jus10wang-stack/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/test2.sh"

        >>> os.environ["VASTAI_GITHUB_USER"] = "alice"
        >>> get_provisioning_script_url("test.sh")
        "https://raw.githubusercontent.com/alice/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/test.sh"
    """
    # Mode 1: Full URL provided - use it directly
    if provisioning_script.startswith("http://") or provisioning_script.startswith("https://"):
        return provisioning_script

    # Mode 2 & 3: Construct URL from components
    # Handle empty/None github_user - fall back to env var or default
    if not github_user:  # Catches None, empty string, and other falsy values
        github_user = os.getenv("VASTAI_GITHUB_USER", "jiso007")

    # Handle empty/None github_branch - use default
    if not github_branch:
        github_branch = "main"

    # Construct the full URL
    return f"https://raw.githubusercontent.com/{github_user}/vastai/refs/heads/{github_branch}/TEMPLATES/2_provisioning_scripts/{provisioning_script}"

def create_instance(offer_id, provisioning_script="provision_test_3.sh", disk_size=100, github_user=None, github_branch="main"):
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
    #         "PROVISIONING_SCRIPT": f"https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/{provisioning_script}"
    #     }
    # })
    
    # Determine the actual GitHub user to use (for both provisioning script URL and env var)
    actual_github_user = github_user if github_user else os.getenv("VASTAI_GITHUB_USER", "jiso007")
    actual_github_branch = github_branch if github_branch else "main"

    # Option O: Working config + try docker_options for ports
    payload = json.dumps({
        "image": "vastai/comfy:@vastai-automatic-tag",
        "disk": disk_size,
        "env": {
            "OPEN_BUTTON_PORT": "1111",
            "OPEN_BUTTON_TOKEN": "1",
            "JUPYTER_DIR": "/",
            "DATA_DIRECTORY": "/workspace/",
            "PORTAL_CONFIG": "localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing",
            "PROVISIONING_SCRIPT": get_provisioning_script_url(provisioning_script, github_user, github_branch),
            "COMFYUI_ARGS": "--disable-auto-launch --port 8188 --listen 0.0.0.0 --enable-cors-header --use-sage-attention",
            "GITHUB_USER": actual_github_user,
            "GITHUB_BRANCH": actual_github_branch
        },
        "runtype": "ssh",
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
    response = requests.put(url, headers=headers, data=payload, timeout=30)
    
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