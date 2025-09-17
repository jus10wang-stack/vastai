#!/usr/bin/env python3
"""
Quick script to get portal URLs for a specific Vast.ai instance
"""

import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

def get_instance_portal_urls(instance_id):
    """Get portal URLs for a specific Vast.ai instance"""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return None
    
    print(f"🔍 Fetching portal URLs for instance {instance_id}...")
    
    # Fetch instance details from Vast.ai API
    api_url = "https://console.vast.ai/api/v0/instances/"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Find our instance in the list
        instances = data.get('instances', [])
        target_instance = None
        
        for instance in instances:
            if str(instance.get('id')) == str(instance_id):
                target_instance = instance
                break
        
        if not target_instance:
            print(f"❌ Instance {instance_id} not found in your instances list")
            return None
        
        # Display instance basic info
        status = target_instance.get("actual_status", "unknown")
        print(f"📋 Instance Status: {status}")
        
        if status != "running":
            print(f"⚠️ Instance is not running (status: {status})")
            print("   Portal URLs are only available when instance is running")
            return None
        
        # Extract portal URLs from the instance data
        portal_urls = {}
        
        # Check for direct URLs in the instance data
        if 'ports' in target_instance and target_instance['ports']:
            ports_info = target_instance['ports']
            print(f"🔍 Found ports info: {ports_info}")
            
            # Look for common ComfyUI ports and services
            for port_mapping in ports_info:
                if isinstance(port_mapping, dict):
                    internal_port = port_mapping.get('PrivatePort') or port_mapping.get('internal_port')
                    external_port = port_mapping.get('PublicPort') or port_mapping.get('external_port') 
                    
                    if internal_port == 8188:  # ComfyUI default port
                        host = target_instance.get('public_ipaddr') or target_instance.get('ssh_host')
                        if host and external_port:
                            portal_urls['ComfyUI'] = f"http://{host}:{external_port}"
                    elif internal_port == 8080:  # Jupyter
                        host = target_instance.get('public_ipaddr') or target_instance.get('ssh_host')
                        if host and external_port:
                            portal_urls['Jupyter'] = f"http://{host}:{external_port}"
        
        # Also check for tunnel URLs (these are more common for Vast.ai)
        # Look for label or metadata that might contain tunnel URLs
        if 'label' in target_instance:
            label = target_instance['label']
            print(f"📝 Instance label: {label}")
        
        # Display all relevant instance information
        print("\n" + "="*60)
        print(f"📊 INSTANCE {instance_id} DETAILS")
        print("="*60)
        print(f"Status: {status}")
        print(f"SSH Host: {target_instance.get('ssh_host', 'N/A')}")
        print(f"SSH Port: {target_instance.get('ssh_port', 'N/A')}")
        print(f"Public IP: {target_instance.get('public_ipaddr', 'N/A')}")
        
        if portal_urls:
            print(f"\n🌐 DIRECT PORTAL URLS:")
            for service, url in portal_urls.items():
                print(f"   {service}: {url}")
        else:
            print(f"\n⚠️ No direct portal URLs found in API response")
            print(f"   This is normal for Vast.ai instances that use tunnel URLs")
        
        # For tunnel URLs, we need to SSH into the instance and check logs
        print(f"\n💡 TO GET TUNNEL URLS:")
        print(f"   Tunnel URLs are typically found in the instance logs at /var/log/*.log")
        print(f"   You can use the monitor_instance.py script to get them:")
        print(f"   python /home/ballsac/wsl-cursor-projects/vastai/python_scripts/components/monitor_instance.py {instance_id}")
        
        # Also show the raw instance data for debugging
        print(f"\n🔍 RAW INSTANCE DATA (for debugging):")
        print(f"   Keys available: {list(target_instance.keys())}")
        
        # Look specifically for any URL-like fields
        url_fields = ['url', 'tunnel_url', 'web_url', 'portal_url', 'public_url']
        for field in url_fields:
            if field in target_instance and target_instance[field]:
                print(f"   {field}: {target_instance[field]}")
        
        return target_instance
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API error: {e}")
        return None

def main():
    instance_id = "26003629"  # Hardcoded for this specific request
    
    print(f"🚀 Getting portal URLs for Vast.ai instance {instance_id}")
    print(f"🔑 Using VAST_API_KEY from environment variables")
    
    result = get_instance_portal_urls(instance_id)
    
    if result:
        print(f"\n✅ Successfully retrieved instance information!")
        print(f"\nℹ️ For live tunnel URLs and real-time status, run:")
        print(f"   python /home/ballsac/wsl-cursor-projects/vastai/python_scripts/components/monitor_instance.py {instance_id}")
    else:
        print(f"\n❌ Failed to retrieve instance information")
        sys.exit(1)

if __name__ == "__main__":
    main()