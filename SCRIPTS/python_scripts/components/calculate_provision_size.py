#!/usr/bin/env python3
"""
Calculate total download size for a provisioning script
"""

import os
import sys
import re
import requests
import argparse
import json
from pathlib import Path

def extract_urls_from_script(script_path):
    """Extract all download URLs from a provisioning script."""
    urls = []
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Extract URLs from array declarations
    arrays = [
        'WORKFLOWS', 'INPUT', 'CHECKPOINT_MODELS', 'CLIP_MODELS', 
        'UNET_MODELS', 'LORA_MODELS', 'VAE_MODELS', 'ESRGAN_MODELS',
        'CONTROLNET_MODELS', 'TEXT_ENCODER_MODELS', 'DIFFUSION_MODELS', 'NODES'
    ]
    
    for array_name in arrays:
        # Find array declaration
        pattern = rf'{array_name}=\((.*?)\)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            array_content = match.group(1)
            # Extract URLs from array content
            url_pattern = r'"(https?://[^"]+)"'
            found_urls = re.findall(url_pattern, array_content)
            urls.extend(found_urls)
    
    # Filter out API endpoints, regex patterns, and other non-downloadable URLs
    filtered_urls = []
    for url in urls:
        # Skip API endpoints
        if '/api/' in url:
            continue
        # Skip URLs that are clearly regex patterns
        if any(char in url for char in ['[', ']', '(', ')', '\\', '^', '$', '?', '*', '+']):
            continue
        # Skip URLs that don't look like file downloads
        if url.endswith(('whoami-v2', 'models')):
            continue
        # Only include URLs that look like actual downloads
        if any(domain in url for domain in ['github.com', 'huggingface.co', 'civitai.com']) or url.endswith(('.json', '.safetensors', '.pt', '.ckpt', '.pth', '.bin')):
            filtered_urls.append(url)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in filtered_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return unique_urls

def get_file_size_from_url(url):
    """Get file size from URL using HEAD request."""
    try:
        # Handle GitHub raw URLs
        if 'github.com' in url and '/raw/' in url:
            response = requests.head(url, allow_redirects=True, timeout=10)
        # Handle Hugging Face URLs
        elif 'huggingface.co' in url:
            response = requests.head(url, allow_redirects=True, timeout=10)
        else:
            response = requests.head(url, allow_redirects=True, timeout=10)
        
        if response.status_code == 200:
            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)
            else:
                # Some servers don't provide content-length, try a partial GET
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status()
                # Try to get size from stream
                total_size = 0
                for chunk in response.iter_content(chunk_size=1024):
                    if not chunk:
                        break
                    total_size += len(chunk)
                    # Only sample first 1MB to estimate
                    if total_size > 1024 * 1024:
                        break
                response.close()
                return None  # Unable to determine size without full download
        else:
            print(f"Warning: Could not access {url} (status: {response.status_code})")
            return None
    except Exception as e:
        print(f"Warning: Error accessing {url}: {e}")
        return None

def estimate_package_sizes():
    """Estimate download sizes for common packages."""
    # Rough estimates for common packages (in bytes)
    package_estimates = {
        'triton': 200 * 1024 * 1024,  # ~200MB
        'sageattention': 50 * 1024 * 1024,  # ~50MB
        'huggingface_hub': 10 * 1024 * 1024,  # ~10MB
        'hf-transfer': 5 * 1024 * 1024,  # ~5MB
        'torch': 800 * 1024 * 1024,  # ~800MB (if not pre-installed)
        'torchvision': 100 * 1024 * 1024,  # ~100MB
        'transformers': 50 * 1024 * 1024,  # ~50MB
    }
    return package_estimates

def extract_packages_from_script(script_path):
    """Extract package lists from provisioning script."""
    packages = []
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Extract PIP packages
    pip_pattern = r'PIP_PACKAGES=\((.*?)\)'
    match = re.search(pip_pattern, content, re.DOTALL)
    if match:
        pip_content = match.group(1)
        # Extract package names from array content
        package_pattern = r'"([^"]+)"'
        found_packages = re.findall(package_pattern, pip_content)
        packages.extend(found_packages)
    
    # Extract APT packages
    apt_pattern = r'APT_PACKAGES=\((.*?)\)'
    match = re.search(apt_pattern, content, re.DOTALL)
    if match:
        apt_content = match.group(1)
        # Extract package names from array content
        package_pattern = r'"([^"]+)"'
        found_packages = re.findall(package_pattern, apt_content)
        # APT packages are usually smaller, add them with minimal estimate
        for pkg in found_packages:
            packages.append(f"apt:{pkg}")
    
    return packages

def update_config_files(script_name, recommended_size):
    """Update matching config files with recommended disk size."""
    # Extract base name without .sh extension
    base_name = script_name.replace('.sh', '')
    
    # Find config directory
    base_dir = Path(__file__).parent.parent.parent.parent
    config_dir = base_dir / "TEMPLATES" / "3_configs"
    
    if not config_dir.exists():
        return []
    
    updated_files = []
    
    # Look for config files containing the base name
    for config_file in config_dir.glob("*.json"):
        if base_name in config_file.stem:
            try:
                # Read config file
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Check if it has instance_config.disk_size
                if 'instance_config' in config and 'disk_size' in config['instance_config']:
                    old_size = config['instance_config']['disk_size']
                    # Update disk size
                    config['instance_config']['disk_size'] = int(recommended_size)
                    
                    # Write back to file
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    updated_files.append((config_file.name, old_size, int(recommended_size)))
                
            except Exception as e:
                print(f"Warning: Could not update {config_file.name}: {e}")
    
    return updated_files

def calculate_total_size(script_path, verbose=False, update_configs=False):
    """Calculate total download size for a provisioning script."""
    print(f"Analyzing provisioning script: {script_path}")
    print("=" * 60)
    
    # Extract URLs
    urls = extract_urls_from_script(script_path)
    print(f"Found {len(urls)} download URLs:")
    
    total_size = 0
    url_sizes = []
    
    for i, url in enumerate(urls, 1):
        if verbose:
            print(f"[{i}/{len(urls)}] Checking: {url}")
        else:
            print(f"[{i}/{len(urls)}] {os.path.basename(url)}")
        
        size = get_file_size_from_url(url)
        if size:
            size_gb = size / (1024 ** 3)
            total_size += size
            url_sizes.append((url, size))
            if verbose:
                print(f"  Size: {size_gb:.3f} GB")
        else:
            print(f"  Size: Unknown")
            url_sizes.append((url, None))
    
    print("\n" + "=" * 60)
    print("DOWNLOAD BREAKDOWN:")
    print("=" * 60)
    
    for url, size in url_sizes:
        filename = os.path.basename(url)
        if size:
            size_gb = size / (1024 ** 3)
            print(f"{filename:<50} {size_gb:>8.3f} GB")
        else:
            print(f"{filename:<50} {'Unknown':>8}")
    
    # Calculate package sizes
    packages = extract_packages_from_script(script_path)
    package_estimates = estimate_package_sizes()
    
    print(f"\n{'='*60}")
    print("PACKAGE ESTIMATES:")
    print("=" * 60)
    
    package_total = 0
    for package in packages:
        if package.startswith('apt:'):
            pkg_name = package[4:]
            # APT packages are typically small
            estimated_size = 10 * 1024 * 1024  # 10MB estimate
            print(f"{pkg_name:<50} {'~0.010 GB (APT)':>15}")
            package_total += estimated_size
        else:
            # Clean package name (remove version specifiers)
            clean_name = re.split(r'[>=<]', package)[0].strip()
            estimated_size = package_estimates.get(clean_name, 20 * 1024 * 1024)  # Default 20MB
            size_gb = estimated_size / (1024 ** 3)
            print(f"{clean_name:<50} {f'~{size_gb:.3f} GB':>15}")
            package_total += estimated_size
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print("=" * 60)
    
    known_files = sum(size for _, size in url_sizes if size is not None)
    unknown_files = len([size for _, size in url_sizes if size is None])
    
    print(f"Files with known sizes:      {known_files / (1024**3):8.3f} GB")
    print(f"Estimated package sizes:     {package_total / (1024**3):8.3f} GB")
    
    # Calculate recommended disk size
    total_data = known_files + package_total
    recommended_size = max(100, total_data / (1024**3) * 3.0)
    
    if unknown_files > 0:
        print(f"Unknown size files:          {unknown_files:8} files")
        print(f"Estimated total (minimum):   {total_data / (1024**3):8.3f} GB")
        print(f"Recommended disk size:       {recommended_size:8.1f} GB")
    else:
        print(f"Total estimated size:        {total_data / (1024**3):8.3f} GB")
        print(f"Recommended disk size:       {recommended_size:8.1f} GB")
    
    # Update config files if requested
    if update_configs:
        script_name = os.path.basename(script_path)
        updated_files = update_config_files(script_name, recommended_size)
        
        if updated_files:
            print(f"\n{'='*60}")
            print("UPDATED CONFIG FILES:")
            print("=" * 60)
            for filename, old_size, new_size in updated_files:
                print(f"{filename:<45} {old_size:>3} GB → {new_size:>3} GB")
        else:
            print(f"\n{'='*60}")
            print("No matching config files found to update.")
    
    return recommended_size

def main():
    parser = argparse.ArgumentParser(description='Calculate total download size for provisioning scripts')
    parser.add_argument('script_path', help='Path to the provisioning script')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--list-files', '-l', action='store_true', help='List all URLs found in script')
    parser.add_argument('--update-configs', '-u', action='store_true', help='Update matching config files with recommended disk size')
    
    args = parser.parse_args()
    
    script_path = Path(args.script_path)
    
    # If just filename provided, look in standard locations
    if not script_path.is_absolute() and not script_path.exists():
        # Try to find in provisioning scripts directory
        base_dir = Path(__file__).parent.parent.parent.parent
        possible_paths = [
            base_dir / "TEMPLATES" / "2_provisioning_scripts" / args.script_path,
            base_dir / "TEMPLATES" / "2_provisioning_scripts" / "archive" / args.script_path,
        ]
        
        for path in possible_paths:
            if path.exists():
                script_path = path
                break
        else:
            print(f"Error: Script not found: {args.script_path}")
            print("Available scripts:")
            scripts_dirs = [
                base_dir / "TEMPLATES" / "2_provisioning_scripts",
                base_dir / "TEMPLATES" / "2_provisioning_scripts" / "archive"
            ]
            all_scripts = []
            for scripts_dir in scripts_dirs:
                if scripts_dir.exists():
                    for script_file in scripts_dir.glob("*.sh"):
                        all_scripts.append(script_file.name)
            # Remove duplicates and sort
            for script_name in sorted(set(all_scripts)):
                print(f"  {script_name}")
            sys.exit(1)
    
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)
    
    if args.list_files:
        urls = extract_urls_from_script(script_path)
        print(f"URLs found in {script_path}:")
        for i, url in enumerate(urls, 1):
            print(f"{i:2}. {url}")
        print(f"\nTotal: {len(urls)} URLs")
    else:
        calculate_total_size(script_path, args.verbose, args.update_configs)

if __name__ == "__main__":
    main()