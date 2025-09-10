#!/usr/bin/env python3
"""
Search for vast.ai GPU offers using the API
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def search_rtx_3060():
    url = "https://console.vast.ai/api/v0/search/asks/"
    
    payload = json.dumps({
        "body": {
            "q": {
                "verified": {},
                "rentable": {},
                "external": {},
                "rented": {},
                "reliability2": {},
                "num_gpus": "1",
                "gpu_name": "RTX 3060",
                "dph_total": {"lte": 0.2},
                "inet_up": {"gte": 100},
                "inet_down": {"gt": 100},
                "cuda_max_good": {},
                "gpu_ram": {},
                "dlperf_per_dphtotal": {},
                "direct_port_count": {},
                "geolocation": {},
                "bw_nvlink": {},
                "compute_cap": {},
                "cpu_arch": {},
                "cpu_cores": {},
                "cpu_ghz": {},
                "datacenter": {},
                "disk_bw": {},
                "dlperf": {},
                "dlperf_usd": {},
                "driver_version": {},
                "duration": {},
                "flops_usd": {},
                "gpu_arch": {},
                "gpu_max_power": {},
                "gpu_max_temp": {},
                "gpu_mem_bw": {},
                "gpu_total_ram": {},
                "gpu_frac": {},
                "gpu_display_active": {},
                "has_avx": {},
                "pci_gen": {},
                "storage_cost": {},
                "static_ip": {},
                "total_flops": {},
                "ubuntu_version": {},
                "vms_enabled": {},
                "machine_id": {}
            }
        }
    })
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("VAST_API_KEY")}'
    }
    
    response = requests.put(url, headers=headers, data=payload)
    
    if response.status_code == 200:
        data = response.json()
        offers = data.get('offers', [])
        
        # Filter and sort by price like CLI does
        filtered = [o for o in offers if o['dph_total'] <= 0.2 and o.get('inet_up', 0) >= 100 and o.get('inet_down', 0) > 100]
        filtered.sort(key=lambda x: x['dph_total'])
        
        print(f"Found {len(filtered)} RTX 3060 offers under $0.20/hr with good internet:")
        for offer in filtered[:10]:
            print(f"ID: {offer['id']:<10} Price: ${offer['dph_total']:.4f}/hr Up: {offer.get('inet_up', 0):.0f}Mbps Down: {offer.get('inet_down', 0):.0f}Mbps {offer.get('geolocation', 'Unknown')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    search_rtx_3060()