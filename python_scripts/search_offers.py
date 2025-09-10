#!/usr/bin/env python3
"""
Search for vast.ai GPU offers using the API
Equivalent to: vastai search offers "dph<0.2 num_gpus=1 gpu_name=RTX_3060 inet_up>=100 inet_down>100" -o "dph"
"""

import requests
import json
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class VastAIClient:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the vast.ai API client
        
        Args:
            api_key: Your vast.ai API key. If not provided, will look for:
                     1. VAST_API_KEY environment variable
                     2. ~/.config/vastai/vast_api_key file
        """
        self.base_url = "https://console.vast.ai/api/v0"
        self.api_key = api_key or self._get_api_key()
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _get_api_key(self) -> str:
        """Get API key from environment or config file"""
        # Check environment variable
        if 'VAST_API_KEY' in os.environ:
            return os.environ['VAST_API_KEY']
        
        # Check config file (Windows path)
        config_path = os.path.expanduser("~/.config/vastai/vast_api_key")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return f.read().strip()
        
        # Check Windows-specific path
        win_config_path = os.path.expanduser("~/AppData/Local/vastai/vast_api_key")
        if os.path.exists(win_config_path):
            with open(win_config_path, 'r') as f:
                return f.read().strip()
        
        raise ValueError("No API key found. Set VAST_API_KEY env var or run 'vastai set api-key'")
    
    def search_offers(self, 
                     dph_max: float = 0.2,
                     num_gpus: int = 1, 
                     gpu_name: str = "RTX_3060",
                     inet_up_min: int = 100,
                     inet_down_min: int = 100,
                     offer_type: str = "on-demand") -> List[Dict]:
        """Search for GPU offers using the correct API format
        
        Args:
            dph_max: Maximum price per hour
            num_gpus: Number of GPUs
            gpu_name: GPU model name
            inet_up_min: Minimum upload speed
            inet_down_min: Minimum download speed
            offer_type: "on-demand", "interruptible", etc.
            
        Returns:
            List of offer dictionaries
        """
        # API filters don't work, so we'll get all offers and filter client-side
        payload = {
            "type": offer_type,
            "order": [["dph_total", "asc"]]
        }
        
        # Try both possible endpoints from the docs
        endpoints_to_try = [
            f"{self.base_url}/bundles",
            f"{self.base_url}/search/asks"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                # Try both PUT (documented) and GET (working) methods
                try:
                    response = requests.put(endpoint, headers=self.headers, json=payload)
                    if response.status_code == 404:
                        # Try GET method with simplified params
                        params = {"limit": 100}
                        response = requests.get(endpoint, headers=self.headers, params=params)
                except:
                    # Fallback to GET
                    params = {"limit": 100}
                    response = requests.get(endpoint, headers=self.headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if isinstance(data, list):
                        all_offers = data
                    elif isinstance(data, dict):
                        # Try different possible keys
                        all_offers = data.get("offers", data.get("data", data.get("results", [])))
                    else:
                        all_offers = []
                    
                    # Apply client-side filtering if we got unfiltered results
                    if all_offers:
                        filtered_offers = self._apply_filters(
                            all_offers, dph_max, num_gpus, gpu_name, 
                            inet_up_min, inet_down_min
                        )
                        return filtered_offers
                        
                else:
                    print(f"API Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error for {endpoint}: {e}")
                continue
                
        return []
    
    def _apply_filters(self, offers: List[Dict], dph_max: float, num_gpus: int, 
                      gpu_name: str, inet_up_min: int, inet_down_min: int) -> List[Dict]:
        """Apply client-side filtering since API filters don't work properly"""
        filtered = []
        filter_stats = {
            'total': len(offers),
            'price_failed': 0,
            'gpu_count_failed': 0, 
            'gpu_name_failed': 0,
            'inet_up_failed': 0,
            'inet_down_failed': 0,
            'not_verified': 0,
            'rented': 0,
            'not_rentable': 0
        }
        
        # Check GPU name (case-insensitive partial match)
        target_gpu = gpu_name.lower().replace('_', ' ')
        
        # Collect available GPU types for informative error message
        available_gpus = set()
        for offer in offers[:20]:  # Check first 20 offers
            gpu_name_str = offer.get('gpu_name', '')
            if gpu_name_str:
                available_gpus.add(gpu_name_str)
        
        for offer in offers:
            # Check price filter
            if offer.get('dph_total', float('inf')) > dph_max:
                filter_stats['price_failed'] += 1
                continue
                
            # Check GPU count
            if offer.get('num_gpus', 0) != num_gpus:
                filter_stats['gpu_count_failed'] += 1
                continue
                
            # Check GPU name (case-insensitive partial match)
            offer_gpu = offer.get('gpu_name', '').lower()
            if target_gpu not in offer_gpu:
                filter_stats['gpu_name_failed'] += 1
                continue
                
            # Check upload speed
            if offer.get('inet_up', 0) < inet_up_min:
                filter_stats['inet_up_failed'] += 1
                continue
                
            # Check download speed  
            if offer.get('inet_down', 0) < inet_down_min:
                filter_stats['inet_down_failed'] += 1
                continue
                
            # Check if verified and available - handle None values properly
            verified = offer.get('verified')
            if verified is False:  # Only exclude if explicitly False
                filter_stats['not_verified'] += 1
                continue
                
            if offer.get('rented', False) is True:  # Only exclude if explicitly rented
                filter_stats['rented'] += 1
                continue
                
            rentable = offer.get('rentable')
            if rentable is False:  # Only exclude if explicitly not rentable
                filter_stats['not_rentable'] += 1
                continue
                
            filtered.append(offer)
        
        # Print filter statistics and available GPUs if no matches found
        if not filtered:
            print(f"\nNo offers found matching '{target_gpu}'")
            print(f"Available GPU types: {', '.join(sorted(available_gpus))}")
            print(f"\nFilter Statistics:")
            for key, value in filter_stats.items():
                if value > 0:
                    print(f"  {key}: {value}")
        
        # Sort by price (ascending)
        filtered.sort(key=lambda x: x.get('dph_total', float('inf')))
        
        return filtered
    
    def format_offer(self, offer: Dict) -> str:
        """Format an offer for display"""
        return (
            f"ID: {offer.get('id', 'N/A'):<10} "
            f"GPU: {offer.get('gpu_name', 'N/A'):<15} "
            f"VRAM: {offer.get('gpu_ram', 0):.1f}GB "
            f"$/hr: ${offer.get('dph_total', 0):.3f} "
            f"Up: {offer.get('inet_up', 0):.0f}Mbps "
            f"Down: {offer.get('inet_down', 0):.0f}Mbps "
            f"Location: {offer.get('geolocation', 'N/A')}"
        )


def main():
    """Example usage matching the CLI command"""
    
    # Initialize client
    client = VastAIClient()
    
    # Search query matching: vastai search offers "dph<0.2 num_gpus=1 gpu_name=RTX_3060 inet_up>=100 inet_down>100" -o "dph"
    query = "dph_total<0.2 num_gpus=1 gpu_name=RTX_3060 inet_up>=100 inet_down>=100"
    
    print(f"Searching for offers: {query}")
    print("-" * 100)
    
    # Search for RTX 3060 offers
    offers = client.search_offers(
        dph_max=0.2,
        num_gpus=1,
        gpu_name="RTX 3060",
        inet_up_min=100,
        inet_down_min=100
    )
    
    if not offers:
        print("No offers found matching criteria")
        return
    
    # Display results
    print(f"Found {len(offers)} offers:\n")
    
    for offer in offers[:10]:  # Show first 10 results
        print(client.format_offer(offer))
    
    # Example: Show the cheapest offer details
    if offers:
        print("\n" + "=" * 100)
        print("Cheapest offer details:")
        cheapest = offers[0]
        print(json.dumps(cheapest, indent=2))
        
        # Show command to create instance
        print(f"\nTo create instance:")
        print(f"vastai create instance {cheapest['id']} --image <your-image> --disk 48 --ssh --direct")


if __name__ == "__main__":
    main()