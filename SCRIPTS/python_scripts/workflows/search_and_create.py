#!/usr/bin/env python3
"""
Search for GPU offers and create an instance with the selected offer
Usage: python search_and_create.py [INDEX] [PROVISIONING_SCRIPT]
Example: python search_and_create.py 1 provision_test_1.sh
"""

import subprocess
import sys
import os

def main():
    # Get index and provisioning script from command line arguments or use defaults
    index = 0
    provisioning_script = "provision_test_3.sh"
    
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1])
        except ValueError:
            print("Invalid index provided. Using default index 0")
            
    if len(sys.argv) > 2:
        provisioning_script = sys.argv[2]
    
    # Run search_offers.py and capture the output
    print(f"Searching for GPU offers and selecting index {index}...")
    components_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "components")
    result = subprocess.run(
        [sys.executable, os.path.join(components_dir, "search_offers.py"), str(index)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("Error running search_offers.py:")
        print(result.stderr)
        sys.exit(1)
    
    # Parse the output to find the selected ID
    output_lines = result.stdout.strip().split('\n')
    selected_id = None
    
    for line in output_lines:
        if line.startswith("Selected ID at index"):
            parts = line.split(":")
            if len(parts) == 2:
                selected_id = parts[1].strip()
                break
    
    if not selected_id:
        print("No offer ID found in search results")
        sys.exit(1)
    
    print(f"\nSelected offer ID: {selected_id}")
    
    # Run create_instance.py with the selected ID and provisioning script
    print(f"\nCreating instance with offer ID {selected_id} using {provisioning_script}...")
    result = subprocess.run(
        [sys.executable, os.path.join(components_dir, "create_instance.py"), selected_id, provisioning_script],
        text=True
    )
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()