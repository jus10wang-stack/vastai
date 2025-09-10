#!/usr/bin/env python3
"""
Simple example to search vast.ai offers using subprocess to call the CLI
This is the easiest way if you already have the vast.ai CLI installed
"""

import subprocess
import json

def search_offers(query: str, order: str = "dph", raw: bool = True):
    """Search for vast.ai offers using the CLI
    
    Args:
        query: Search query string
        order: Order by field
        raw: Return raw JSON output
        
    Returns:
        List of offers or raw output
    """
    cmd = [
        "vastai", 
        "search", 
        "offers",
        query,
        "-o", order
    ]
    
    if raw:
        cmd.append("--raw")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if raw:
            return json.loads(result.stdout)
        else:
            return result.stdout
            
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"stderr: {e.stderr}")
        return None


def main():
    # Search query
    query = "dph<0.2 num_gpus=1 gpu_name=RTX_3060 inet_up>=100 inet_down>100"
    
    print(f"Searching: {query}\n")
    
    # Get raw JSON data
    result = search_offers(query)
    
    if result and isinstance(result, list):
        print(f"Found {len(result)} offers\n")
        
        # Display top 5 results
        for i, offer in enumerate(result[:5]):
            print(f"{i+1}. ID: {offer.get('id')} "
                  f"GPU: {offer.get('gpu_name')} "
                  f"$/hr: ${offer.get('dph_total', 0):.3f} "
                  f"VRAM: {offer.get('gpu_ram', 0):.1f}GB")
    
    # Also show formatted output
    print("\nFormatted output:")
    print("-" * 50)
    formatted = search_offers(query, raw=False)
    if formatted:
        print(formatted)


if __name__ == "__main__":
    main()