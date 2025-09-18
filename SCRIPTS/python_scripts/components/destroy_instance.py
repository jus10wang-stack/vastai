#!/usr/bin/env python3
"""
Destroy Vast.ai instances by instance ID - works for specific instances or all instances
"""

import sys
import os
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

def destroy_single_instance(instance_id, force=False):
    """Destroy a specific instance by ID."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    try:
        print(f"🔍 Fetching instance {instance_id} details...")
        
        # Get instance details first
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Find the specific instance
        instances = data.get('instances', [])
        target_instance = None
        for instance in instances:
            if str(instance.get('id')) == str(instance_id):
                target_instance = instance
                break
        
        if not target_instance:
            print(f"❌ Instance {instance_id} not found")
            return False
        
        # Show instance details
        status = target_instance.get('actual_status', 'unknown')
        gpu_name = target_instance.get('gpu_name', 'unknown')
        cost_per_hour = target_instance.get('dph_total', 0)
        
        print(f"📋 Instance Details:")
        print(f"  ID: {instance_id}")
        print(f"  Status: {status}")
        print(f"  GPU: {gpu_name}")
        print(f"  Cost: ${cost_per_hour:.4f}/hour")
        
        # Confirmation unless --force is used
        if not force:
            response = input(f"\n⚠️ Are you sure you want to DESTROY instance {instance_id}? This cannot be undone! (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("⏹️ Destruction aborted")
                return False
        
        print(f"🔥 Destroying instance {instance_id}...")
        
        # Destroy the instance
        destroy_url = f"https://console.vast.ai/api/v0/instances/{instance_id}/"
        response = requests.delete(destroy_url, headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Instance {instance_id} destroyed successfully")
            return True
        else:
            print(f"❌ Failed to destroy instance {instance_id}: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error destroying instance: {e}")
        return False

def list_all_instances():
    """List all instances with their details."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    try:
        print("🔍 Fetching all instances...")
        
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        instances = data.get('instances', [])
        
        if not instances:
            print("✅ No instances found")
            return True
        
        print(f"📋 Found {len(instances)} instances:")
        print("=" * 80)
        
        for instance in instances:
            instance_id = instance.get('id')
            status = instance.get('actual_status', 'unknown')
            gpu_name = instance.get('gpu_name', 'unknown')
            cost_per_hour = instance.get('dph_total', 0)
            
            print(f"🖥️  Instance {instance_id}")
            print(f"   Status: {status}")
            print(f"   GPU: {gpu_name}")
            print(f"   Cost: ${cost_per_hour:.4f}/hour")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching instances: {e}")
        return False

def destroy_all_instances(force=False):
    """Destroy ALL instances."""
    api_key = os.getenv("VAST_API_KEY")
    if not api_key:
        print("❌ VAST_API_KEY not found in environment variables")
        return False
    
    try:
        print("🔍 Fetching all instances...")
        
        # Get all instances
        api_url = "https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        instances = data.get('instances', [])
        
        if not instances:
            print("✅ No instances found to destroy")
            return True
        
        print(f"📋 Found {len(instances)} instances:")
        
        total_cost = 0
        for instance in instances:
            instance_id = instance.get('id')
            status = instance.get('actual_status', 'unknown')
            gpu_name = instance.get('gpu_name', 'unknown')
            cost_per_hour = instance.get('dph_total', 0)
            total_cost += cost_per_hour
            
            print(f"  - Instance {instance_id} ({status}) - {gpu_name} - ${cost_per_hour:.4f}/hour")
        
        print(f"\n💰 Total cost: ${total_cost:.4f}/hour")
        
        # Global confirmation unless --force is used
        if not force:
            response = input(f"\n🔥 Are you sure you want to DESTROY ALL {len(instances)} instances? THIS CANNOT BE UNDONE! (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("⏹️ Destruction aborted")
                return False
        
        print(f"\n🔥 Proceeding to destroy {len(instances)} instances...")
        
        # Destroy all instances
        success_count = 0
        for instance in instances:
            instance_id = instance.get('id')
            print(f"\n🔄 Destroying instance {instance_id}...")
            
            try:
                destroy_url = f"https://console.vast.ai/api/v0/instances/{instance_id}/"
                response = requests.delete(destroy_url, headers=headers)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"✅ Instance {instance_id} destroyed")
                else:
                    print(f"❌ Failed to destroy instance {instance_id}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error destroying instance {instance_id}: {e}")
        
        print(f"\n📊 Final Summary: {success_count}/{len(instances)} instances destroyed")
        print(f"💰 Saved: ${total_cost:.4f}/hour in costs")
        return success_count == len(instances)
        
    except Exception as e:
        print(f"❌ Error fetching instances: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Destroy Vast.ai instances by instance ID")
    parser.add_argument("instance_id", nargs="?", help="Vast.ai instance ID (optional when using --all or --list)")
    parser.add_argument("--list", "-l", action="store_true", help="List all instances")
    parser.add_argument("--all", "-a", action="store_true", help="Destroy ALL instances")
    parser.add_argument("--force", "-f", action="store_true", help="Force destruction without confirmation")
    
    args = parser.parse_args()
    
    # Handle --list flag
    if args.list:
        if args.instance_id:
            print("⚠️ Instance ID ignored when using --list")
        success = list_all_instances()
        sys.exit(0 if success else 1)
    
    # Handle --all flag
    if args.all:
        if args.instance_id:
            print("⚠️ Instance ID ignored when using --all")
        success = destroy_all_instances(args.force)
        sys.exit(0 if success else 1)
    
    # Require instance_id for single destruction
    if not args.instance_id:
        print("❌ Instance ID is required when not using --all or --list")
        print("Usage examples:")
        print("  python destroy_instance.py 26003629        # Destroy specific instance")
        print("  python destroy_instance.py --list          # List all instances")
        print("  python destroy_instance.py --all           # Destroy ALL instances")
        print("  python destroy_instance.py --all --force   # Destroy all without confirmation")
        sys.exit(1)
    
    # Destroy single instance
    success = destroy_single_instance(args.instance_id, args.force)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()