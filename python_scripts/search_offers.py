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
        # Build query object according to API docs
        query_filters = {
            "verified": {"eq": True},
            "external": {"eq": False}, 
            "rentable": {"eq": True},
            "rented": {"eq": False},
            "dph_total": {"lte": dph_max},
            "num_gpus": {"eq": num_gpus},
            "gpu_name": {"eq": gpu_name},
            "inet_up": {"gte": inet_up_min},
            "inet_down": {"gte": inet_down_min}
        }
        
        payload = {
            "q": query_filters,
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
                print(f"Trying endpoint: {endpoint}")
                print(f"Payload: {json.dumps(payload, indent=2)}")
                
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
                print(f"Status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Response type: {type(data)}")
                    
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        # Try different possible keys
                        offers = data.get("offers", data.get("data", data.get("results", [])))
                        return offers if isinstance(offers, list) else []
                        
                else:
                    print(f"Error response: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error for {endpoint}: {e}")
                continue
                
        return []
    
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
    
    # Perform search with proper parameters
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