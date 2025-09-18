#!/usr/bin/env python3
"""
Search for vast.ai GPU offers using the API
"""

import requests
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def search_gpu(gpu_name, index=0, min_disk_size=100):
    url = "https://console.vast.ai/api/v0/search/asks/"
    
    payload = json.dumps({
    "q": {
        "num_gpus": {
        "eq": 1
        },
        "verified": {
        "eq": True
        },
        "rentable": {
        "eq": True
        },
        "rented": {
        "eq": False
        },
        "gpu_name": {
        "eq": gpu_name
        }
    },
    "limit": 30
    })

    # payload = json.dumps({
    #     "body": {
    #         "q": {
    #             "verified": {"eq": True},
    #             "rentable": {"eq": True},
    #             "external": {},
    #             "rented": {"eq": False},
    #             "reliability2": {},
    #             "num_gpus": "1",
    #             "gpu_name": "RTX 4060",
    #             "dph_total": {"lte": 0.2},
    #             "inet_up": {"gte": 100},
    #             "inet_down": {"gt": 100},
    #             "cuda_max_good": {},
    #             "gpu_ram": {},
    #             "dlperf_per_dphtotal": {},
    #             "direct_port_count": {},
    #             "geolocation": {},
    #             "bw_nvlink": {},
    #             "compute_cap": {},
    #             "cpu_arch": {},
    #             "cpu_cores": {},
    #             "cpu_ghz": {},
    #             "datacenter": {},
    #             "disk_bw": {},
    #             "dlperf": {},
    #             "dlperf_usd": {},
    #             "driver_version": {},
    #             "duration": {},
    #             "flops_usd": {},
    #             "gpu_arch": {},
    #             "gpu_max_power": {},
    #             "gpu_max_temp": {},
    #             "gpu_mem_bw": {},
    #             "gpu_total_ram": {},
    #             "gpu_frac": {},
    #             "gpu_display_active": {},
    #             "has_avx": {},
    #             "pci_gen": {},
    #             "storage_cost": {},
    #             "static_ip": {},
    #             "total_flops": {},
    #             "ubuntu_version": {},
    #             "vms_enabled": {},
    #             "machine_id": {}
    #         }
    #     }
    # })
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("VAST_API_KEY")}'
    }
    
    response = requests.put(url, headers=headers, data=payload)
    
    if response.status_code == 200:
        data = response.json()
        offers = data.get('offers', [])
        print(f"Total offers received: {len(offers)}")
        
        # Filter and sort by inet_down_cost (cheapest bandwidth first)
        filtered = [o for o in offers if o['dph_total'] <= 1 and o.get('inet_up', 0) >= 100 and o.get('inet_down', 0) >= 800]
        
        # Apply bandwidth cost filter
        filtered = [o for o in filtered if o.get('inet_down_cost', float('inf')) <= 0.002 and o.get('inet_up_cost', float('inf')) <= 0.002]
        
        # Apply disk size filter
        filtered = [o for o in filtered if o.get('disk_space', 0) >= min_disk_size]
        
        # Calculate total costs for each offer before sorting
        for offer in filtered:
            runtime_hours = 10 / 60
            compute_cost = offer['dph_total'] * runtime_hours
            download_cost = offer.get('inet_down_cost', 0) * 100
            offer['_total_cost'] = compute_cost + download_cost
        
        # Sort by lowest 10min total cost
        filtered.sort(key=lambda x: x.get('_total_cost', float('inf')))
        
        print(f"Found {len(filtered)} {gpu_name} offers under $1/hr with good internet, low bandwidth costs, and {min_disk_size}GB+ disk:")
        print("Sorted by lowest 10min total cost. Assuming: 10min runtime, 100GB download")
        for i, offer in enumerate(filtered[:10]):
            down_cost_tb = offer.get('inet_down_cost', 0) * 1000  # Convert $/GB to $/TB
            up_cost_tb = offer.get('inet_up_cost', 0) * 1000  # Convert $/GB to $/TB
            
            # Calculate total cost for 10 minutes runtime + 100GB download
            runtime_hours = 10 / 60  # 10 minutes to hours (0.1667)
            compute_cost = offer['dph_total'] * runtime_hours
            download_cost = offer.get('inet_down_cost', 0) * 100  # 100GB download
            total_cost = compute_cost + download_cost
            
            # Format bandwidth costs with appropriate precision
            down_display = f"${down_cost_tb:.4f}/TB" if down_cost_tb > 0.01 else f"${down_cost_tb:.6f}/TB"
            
            # Get disk space in GB
            disk_space = offer.get('disk_space', 0)
            
            print(f"[{i}] ID: {offer['id']:<10} | GPU: {offer.get('gpu_name', 'N/A')} | DPH: ${offer['dph_total']:.4f} | Disk: {disk_space:.0f}GB | Down: {offer.get('inet_down', 0):.0f}Mbps ({down_display}) | 10min Total: ${total_cost:.4f} | Region: {offer.get('geolocation', 'Unknown')}")
        
        # Return the ID at the specified index
        if 0 <= index < len(filtered):
            return filtered[index]['id']
        else:
            return None
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Default values
    gpu_name = "RTX 3060"
    index = 0
    min_disk_size = 100
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        try:
            # First argument is index
            index = int(sys.argv[1])
        except ValueError:
            print("Invalid index provided. Using default index 0")
    
    if len(sys.argv) > 2:
        # Second argument is gpu_name
        gpu_name = sys.argv[2]
        
    if len(sys.argv) > 3:
        try:
            # Third argument is min_disk_size
            min_disk_size = int(sys.argv[3])
        except ValueError:
            print("Invalid disk size provided. Using default 100GB")
    
    selected_id = search_gpu(gpu_name, index, min_disk_size)
    if selected_id:
        print(f"\nSelected ID at index {index}: {selected_id}")
    else:
        print(f"\nNo offer found at index {index}")