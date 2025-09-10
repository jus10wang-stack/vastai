#!/usr/bin/env python3
"""
Debug script to test vast.ai API and compare with CLI
"""

import subprocess
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_cli():
    """Test if the CLI works"""
    print("Testing CLI...")
    try:
        result = subprocess.run([
            "vastai", "search", "offers", 
            "dph<0.2 num_gpus=1 gpu_name=RTX_3060", 
            "--raw", "--limit", "5"
        ], capture_output=True, text=True, check=True)
        
        data = json.loads(result.stdout)
        print(f"CLI works! Found {len(data)} offers")
        
        if data:
            print("First offer keys:", list(data[0].keys()))
            print("Sample offer:", json.dumps(data[0], indent=2)[:500] + "...")
            
        return True, data
    except Exception as e:
        print(f"CLI failed: {e}")
        return False, None

def test_api_endpoints():
    """Test different API endpoints"""
    api_key = os.getenv('VAST_API_KEY')
    if not api_key:
        print("No API key found")
        return
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    endpoints_to_try = [
        "https://console.vast.ai/api/v0/bundles",
        "https://console.vast.ai/api/v0/offers",
        "https://console.vast.ai/api/v0/bundles/",
        "https://console.vast.ai/api/v0/offers/",
        "https://vast.ai/api/v0/bundles",
        "https://vast.ai/api/v0/offers"
    ]
    
    simple_params = {"limit": 5}
    
    for endpoint in endpoints_to_try:
        print(f"\nTrying: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers, params=simple_params, timeout=10)
            print(f"Status: {response.status_code}")
            
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            if 'application/json' in content_type:
                try:
                    data = response.json()
                    print("Success! JSON response received")
                    if isinstance(data, list) and data:
                        print(f"Got {len(data)} items")
                        print("First item keys:", list(data[0].keys()))
                    elif isinstance(data, dict):
                        print("Dict response keys:", list(data.keys()))
                    return endpoint, data
                except json.JSONDecodeError:
                    print("Failed to parse JSON")
            else:
                print(f"Got HTML/other content: {response.text[:100]}...")
                
        except Exception as e:
            print(f"Error: {e}")
    
    return None, None

def main():
    print("=== vast.ai API Debug ===\n")
    
    # Test CLI first
    cli_works, cli_data = test_cli()
    
    # Test API endpoints
    working_endpoint, api_data = test_api_endpoints()
    
    print("\n=== Summary ===")
    print(f"CLI works: {cli_works}")
    print(f"Working API endpoint: {working_endpoint}")
    
    if working_endpoint:
        print(f"API key is valid and endpoint {working_endpoint} works!")
    else:
        print("No working API endpoint found")

if __name__ == "__main__":
    main()