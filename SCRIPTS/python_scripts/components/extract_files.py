#!/usr/bin/env python3
"""
Extract Files from ComfyUI Instance via SSH
Flexible extraction script for workflows, images, videos, and other files with organized naming.
Reuses existing SSH infrastructure from monitor_instance.py for modularity.
"""

import sys
import os
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.monitor_instance import VastInstanceMonitor

class ComfyUIExtractor:
    def __init__(self, instance_id, ssh_key_path=None):
        self.instance_id = instance_id
        # Reuse the existing VastInstanceMonitor for SSH functionality
        self.monitor = VastInstanceMonitor(instance_id, ssh_key_path)
    
    def get_ssh_info(self):
        """Get SSH connection details using existing monitor infrastructure"""
        print(f"🔍 Fetching SSH details for instance {self.instance_id}...")
        
        instance_data = self.monitor.get_instance_info()
        if not instance_data:
            return None
        
        ssh_info = self.monitor.get_ssh_info(instance_data)
        return ssh_info
    
    def execute_ssh_command(self, ssh_info, command):
        """Execute a command on the remote instance via SSH using existing infrastructure"""
        print(f"🔗 Executing command on {ssh_info['host']}:{ssh_info['port']}")
        print(f"📋 Command: {command}")
        
        # Use the existing SSH execution from monitor
        output = self.monitor.execute_remote_script(ssh_info, command)
        
        # Check if output indicates an error
        if output and ("SSH_ERROR" in output or "SSH_NOT_READY" in output or "SSH_AUTH_ERROR" in output):
            print(f"❌ SSH command failed: {output}")
            return None
        
        return output
    
    def list_remote_files(self, ssh_info, remote_path, file_pattern="*"):
        """List files in remote directory matching pattern"""
        command = f"find {remote_path} -name '{file_pattern}' -type f 2>/dev/null | head -50"
        output = self.execute_ssh_command(ssh_info, command)
        
        if output:
            files = [f.strip() for f in output.split('\n') if f.strip()]
            return files
        return []
    
    def download_file(self, ssh_info, remote_file_path, local_dir):
        """Download a single file via SCP with organized naming using existing SSH infrastructure"""
        host, port = ssh_info['host'], ssh_info['port']
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract filename and parent directory from remote path
        remote_path = Path(remote_file_path)
        filename = remote_path.name
        
        # Get parent directory relative to common ComfyUI paths
        parent_parts = []
        for part in remote_path.parts:
            if part in ['ComfyUI', 'workspace']:
                # Start collecting from ComfyUI or workspace
                start_collecting = True
                continue
            elif 'ComfyUI' in str(remote_path) and part in ['output', 'input', 'workflows', 'models']:
                parent_parts.append(part)
                break
        
        # If we couldn't determine parent from common paths, use the immediate parent
        if not parent_parts and remote_path.parent.name != '/':
            parent_parts = [remote_path.parent.name]
        
        # Create organized filename: {timestamp}_{instance-id}_{original-filename}
        organized_filename = f"{timestamp}_{self.instance_id}_{filename}"
        
        # Create local directory structure
        if parent_parts:
            local_subdir = os.path.join(local_dir, *parent_parts)
        else:
            local_subdir = local_dir
        
        os.makedirs(local_subdir, exist_ok=True)
        local_file_path = os.path.join(local_subdir, organized_filename)
        
        print(f"📥 Downloading: {remote_file_path}")
        print(f"💾 Saving to: {local_file_path}")
        
        try:
            # Reuse SSH key path and passphrase from monitor
            ssh_key_path = self.monitor.ssh_key_path
            ssh_passphrase = self.monitor.ssh_passphrase
            
            if ssh_passphrase and "jason_desktop" in ssh_key_path:
                # Use expect for encrypted keys with SCP
                expect_script = f"""
spawn scp -i {ssh_key_path} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P {port} root@{host}:{remote_file_path} {local_file_path}
expect {{
    "Enter passphrase for key*" {{
        send "{ssh_passphrase}\\r"
        exp_continue
    }}
    "assphrase for*" {{
        send "{ssh_passphrase}\\r"
        exp_continue  
    }}
    eof
}}
"""
                result = subprocess.run(
                    ['expect', '-c', expect_script],
                    text=True,
                    capture_output=True,
                    timeout=300  # 5 minutes for large files
                )
            else:
                # Regular SCP for unencrypted keys
                scp_cmd = [
                    'scp',
                    '-i', ssh_key_path,
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'BatchMode=yes',
                    '-P', str(port),
                    f'root@{host}:{remote_file_path}',
                    local_file_path
                ]
                
                result = subprocess.run(
                    scp_cmd,
                    text=True,
                    capture_output=True,
                    timeout=300
                )
            
            if result.returncode == 0:
                file_size = os.path.getsize(local_file_path) if os.path.exists(local_file_path) else 0
                print(f"✅ Downloaded successfully ({file_size:,} bytes)")
                return local_file_path
            else:
                print(f"❌ Download failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return None
    
    def extract_workflows(self, ssh_info, local_dir):
        """Extract JSON workflow files from /workspace/ComfyUI/user/default/workflows"""
        print("🔍 Searching for workflow JSON files in /workspace/ComfyUI/user/default/workflows...")
        
        # Workflows (created and saved in session)
        workflow_paths = [
            "/workspace/ComfyUI/user/default/workflows"
        ]
        
        all_workflows = []
        for path in workflow_paths:
            workflows = self.list_remote_files(ssh_info, path, "*.json")
            all_workflows.extend(workflows)
        
        if not all_workflows:
            print("❌ No JSON workflow files found")
            return []
        
        print(f"📋 Found {len(all_workflows)} workflow files:")
        for i, workflow in enumerate(all_workflows, 1):
            print(f"  {i}. {workflow}")
        
        downloaded_files = []
        for workflow in all_workflows:
            local_file = self.download_file(ssh_info, workflow, local_dir)
            if local_file:
                downloaded_files.append(local_file)
        
        return downloaded_files
    
    def extract_content(self, ssh_info, local_dir):
        """Extract images and videos from /workspace/ComfyUI/output"""
        print("🔍 Searching for content files (images/videos) in /workspace/ComfyUI/output...")
        
        # All content file patterns (images + videos) - optimized for speed
        file_patterns = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.mp4"]
        # Commented out for performance: "*.bmp", "*.tiff", "*.webp", "*.avi", "*.mov", "*.mkv", "*.webm"
        
        # Images/Videos (generated output)
        content_paths = [
            "/workspace/ComfyUI/output"
        ]
        
        all_content_files = []
        for path in content_paths:
            for pattern in file_patterns:
                content_files = self.list_remote_files(ssh_info, path, pattern)
                all_content_files.extend(content_files)
        
        # Remove duplicates
        all_content_files = list(set(all_content_files))
        
        if not all_content_files:
            print("❌ No content files found")
            return []
        
        print(f"📋 Found {len(all_content_files)} content files:")
        for i, content_file in enumerate(all_content_files, 1):
            print(f"  {i}. {content_file}")
        
        downloaded_files = []
        for content_file in all_content_files:
            local_file = self.download_file(ssh_info, content_file, local_dir)
            if local_file:
                downloaded_files.append(local_file)
        
        return downloaded_files
    
    def extract_custom(self, ssh_info, local_dir, remote_path, file_pattern="*"):
        """Extract files from custom path with pattern"""
        print(f"🔍 Searching for files in {remote_path} matching '{file_pattern}'...")
        
        files = self.list_remote_files(ssh_info, remote_path, file_pattern)
        
        if not files:
            print(f"❌ No files found matching pattern '{file_pattern}' in {remote_path}")
            return []
        
        print(f"📋 Found {len(files)} files:")
        for i, file in enumerate(files, 1):
            print(f"  {i}. {file}")
        
        downloaded_files = []
        for file in files:
            local_file = self.download_file(ssh_info, file, local_dir)
            if local_file:
                downloaded_files.append(local_file)
        
        return downloaded_files

def main():
    parser = argparse.ArgumentParser(description="Extract files from ComfyUI instance via SSH")
    parser.add_argument("instance_id", help="Vast.ai instance ID")
    parser.add_argument("extract_type", choices=["workflows", "content", "all", "custom"], 
                       help="Type of files to extract")
    parser.add_argument("--output-dir", "-o", default="IMPORT", 
                       help="Local output directory (default: IMPORT)")
    parser.add_argument("--remote-path", "-p", 
                       help="Remote path for custom extraction")
    parser.add_argument("--pattern", "-f", default="*",
                       help="File pattern for custom extraction (default: *)")
    parser.add_argument("--ssh-key", "-k", 
                       help="Path to SSH private key")
    
    args = parser.parse_args()
    
    # Validate custom extraction arguments
    if args.extract_type == "custom":
        if not args.remote_path:
            print("❌ --remote-path is required for custom extraction")
            sys.exit(1)
    
    # Create output directory
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    output_dir = os.path.join(script_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    print("📦 ComfyUI File Extractor")
    print(f"🆔 Instance ID: {args.instance_id}")
    print(f"📁 Extract Type: {args.extract_type}")
    print(f"💾 Output Directory: {output_dir}")
    print("=" * 60)
    
    try:
        # Initialize extractor
        extractor = ComfyUIExtractor(args.instance_id, args.ssh_key)
        
        # Get SSH connection info
        ssh_info = extractor.get_ssh_info()
        if not ssh_info:
            print("❌ Could not establish SSH connection")
            sys.exit(1)
        
        print(f"✅ Connected to {ssh_info['host']}:{ssh_info['port']}")
        
        # Extract files based on type
        downloaded_files = []
        
        if args.extract_type == "workflows":
            downloaded_files = extractor.extract_workflows(ssh_info, output_dir)
        elif args.extract_type == "content":
            downloaded_files = extractor.extract_content(ssh_info, output_dir)
        elif args.extract_type == "all":
            print("🔄 Extracting workflows...")
            downloaded_files.extend(extractor.extract_workflows(ssh_info, output_dir))
            print("\n🔄 Extracting content...")
            downloaded_files.extend(extractor.extract_content(ssh_info, output_dir))
        elif args.extract_type == "custom":
            downloaded_files = extractor.extract_custom(ssh_info, output_dir, args.remote_path, args.pattern)
        
        # Summary
        print(f"\n📊 Extraction Summary:")
        print(f"✅ Successfully downloaded {len(downloaded_files)} files")
        
        if downloaded_files:
            print(f"\n📁 Files saved to:")
            for file in downloaded_files:
                rel_path = os.path.relpath(file, script_dir)
                print(f"  {rel_path}")
        else:
            print("❌ No files were downloaded")
        
        sys.exit(0 if downloaded_files else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()