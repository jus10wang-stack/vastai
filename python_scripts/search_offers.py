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

def search_gpu(gpu_name, index=0):
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
        # print(offers)
        
        # Filter and sort by price like CLI does
        filtered = [o for o in offers if o['dph_total'] <= 1 and o.get('inet_up', 0) >= 1000 and o.get('inet_down', 0) > 1000]
        filtered.sort(key=lambda x: x['dph_total'])
        
        print(f"Found {len(filtered)} {gpu_name} offers under $1/hr with good internet:")
        for i, offer in enumerate(filtered[:10]):
            print(f"[{i}] ID: {offer['id']:<10} | GPU: {offer.get('gpu_name', 'N/A')} | DPH: ${offer['dph_total']:.4f} | Down: {offer.get('inet_down', 0):.0f}Mbps | NumGPUs: {offer.get('num_gpus', 0)} | Verification: {offer.get('verification', 'N/A')} | Rentable: {offer.get('rentable', False)} | Rented: {offer.get('rented', False)} | Region: {offer.get('geolocation', 'Unknown')}")
        
        # Return the ID at the specified index
        if 0 <= index < len(filtered):
            return filtered[index]['id']
        else:
            return None
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Check if index is provided as command line argument
    index = 0
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1])
        except ValueError:
            print("Invalid index provided. Using default index 0")
    
    selected_id = search_gpu("RTX 3060", index)
    if selected_id:
        print(f"\nSelected ID at index {index}: {selected_id}")
    else:
        print(f"\nNo offer found at index {index}")