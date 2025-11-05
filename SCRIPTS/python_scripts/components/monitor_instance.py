#!/usr/bin/env python3
"""
Vast.ai Instance Monitor
Monitors the status, downloads, and readiness of a Vast.ai instance.
Extracts portal URLs and notifies when the system is ready.
"""

import requests
import paramiko
import time
import os
import sys
import re
import textwrap
import socket
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ssh_utils import detect_ssh_key

class VastInstanceMonitor:
    def __init__(self, instance_id, ssh_key_path=None):
        self.instance_id = instance_id
        self.api_key = os.getenv("VAST_API_KEY")
        self.ssh_passphrase = os.getenv("SSH_PASSPHRASE")

        # Auto-detect SSH key if not provided using shared utility
        if ssh_key_path:
            # Expand ~ in path if provided from config
            self.ssh_key_path = os.path.expanduser(ssh_key_path)
        else:
            # Use shared SSH detection utility for consistency across all commands
            self.ssh_key_path = detect_ssh_key()
        
        if not self.api_key:
            raise ValueError("VAST_API_KEY not found in environment variables")
    
    def get_instance_info(self):
        """Fetch instance details from Vast.ai API"""
        print(f"🔍 Fetching details for instance {self.instance_id}...")
        
        # Try the instances endpoint first
        api_url = f"https://console.vast.ai/api/v0/instances/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Find our instance in the list
            instances = data.get('instances', [])
            for instance in instances:
                if str(instance.get('id')) == str(self.instance_id):
                    return instance
            
            print(f"❌ Instance {self.instance_id} not found in instances list")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API error: {e}")
            return None
    
    def get_ssh_info(self, instance_data):
        """Extract SSH connection details from instance data"""
        if not instance_data:
            return None
            
        status = instance_data.get("actual_status", "unknown")
        if status != "running":
            print(f"⚠️ Instance status: {status} (need 'running' for SSH)")
            return None
            
        ssh_host = instance_data.get("ssh_host")
        ssh_port = instance_data.get("ssh_port")
        
        # Use the SSH port directly from the API
        if ssh_host and ssh_port:
            print(f"🔍 Using SSH port {ssh_port} from API")
            
            # Comment out the port detection for now since it's not working reliably
            '''
            print(f"🔍 Testing SSH on API-provided port {ssh_port}...")
            import subprocess
            
            # Test actual SSH connection, not just port
            test_cmd = [
                'ssh', '-i', self.ssh_key_path,
                '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-p', str(ssh_port),
                f'root@{ssh_host}',
                'echo "test"'
            ]
            
            try:
                result = subprocess.run(test_cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    print(f"✅ SSH working on port {ssh_port}")
                else:
                    # Try port+1
                    print(f"⚠️ SSH failed on port {ssh_port}, trying {ssh_port+1}")
                    test_cmd[6] = str(ssh_port + 1)  # Update port in command
                    result = subprocess.run(test_cmd, capture_output=True, timeout=10)
                    if result.returncode == 0:
                        ssh_port = ssh_port + 1
                        print(f"✅ SSH working on corrected port {ssh_port}")
                    else:
                        print(f"❌ SSH failed on both ports {ssh_port} and {ssh_port+1}")
            except subprocess.TimeoutExpired:
                print(f"⚠️ SSH timeout on port {ssh_port}, trying {ssh_port+1}")
                test_cmd[6] = str(ssh_port + 1)
                try:
                    result = subprocess.run(test_cmd, capture_output=True, timeout=10)
                    if result.returncode == 0:
                        ssh_port = ssh_port + 1
                        print(f"✅ SSH working on corrected port {ssh_port}")
                except:
                    print(f"❌ SSH timeout on both ports")
            '''
        
        if not ssh_host or not ssh_port:
            print("❌ SSH connection details not available")
            return None
            
        print(f"🔍 Returning SSH info: {ssh_host}:{ssh_port}")
        return {
            "host": ssh_host,
            "port": ssh_port,
            "status": status
        }
    
    def execute_remote_script(self, ssh_info, script_content):
        """Execute script on remote instance via SSH"""
        host, port = ssh_info['host'], ssh_info['port']
        
        # Use subprocess for more reliable SSH connection
        import subprocess
        import tempfile
        
        try:
            if not os.path.exists(self.ssh_key_path):
                print(f"❌ SSH key not found at {self.ssh_key_path}")
                return "STATUS: SSH_KEY_ERROR"
            
            print(f"🔑 Using SSH key: {self.ssh_key_path}")
            print(f"🔗 Attempting SSH connection to {host}:{port}...")
            
            # Create a temporary file for the script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp_file:
                tmp_file.write(script_content)
                tmp_script_path = tmp_file.name
            
            # Use expect to handle SSH passphrase automatically (only for encrypted keys)
            if self.ssh_passphrase and "jason_desktop" in self.ssh_key_path:
                expect_script = f"""
spawn ssh -i {self.ssh_key_path} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p {port} root@{host} bash -s
expect {{
    "Enter passphrase for key*" {{
        send "{self.ssh_passphrase}\\r"
        exp_continue
    }}
    "assphrase for*" {{
        send "{self.ssh_passphrase}\\r"
        exp_continue  
    }}
    "$ " {{
        send_user "Connected successfully\\n"
    }}
    timeout {{
        send_user "Connection timeout\\n"
        exit 1
    }}
}}
send "{script_content.replace('"', '\\"')}\\n"
send "exit\\n"
expect eof
"""
                
                result = subprocess.run(
                    ['expect', '-c', expect_script],
                    text=True,
                    capture_output=True,
                    timeout=45
                )
            else:
                # Fall back to regular SSH if no passphrase
                ssh_cmd = [
                    'ssh',
                    '-i', self.ssh_key_path,
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'BatchMode=yes',
                    '-o', 'ConnectTimeout=30',
                    '-o', 'ExitOnForwardFailure=no',
                    '-p', str(port),
                    f'root@{host}',
                    'bash -s'
                ]
                
                result = subprocess.run(
                    ssh_cmd,
                    input=script_content,
                    text=True,
                    capture_output=True,
                    timeout=30
                )
            
            # Clean up temp file
            try:
                os.unlink(tmp_script_path)
            except:
                pass
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                # Check for common SSH errors
                stderr = result.stderr.lower()
                
                if 'connection refused' in stderr or 'no route to host' in stderr:
                    print(f"❌ SSH not ready: Instance is still starting up")
                    return "STATUS: SSH_NOT_READY\\nDETAILS: SSH service not available"
                elif 'permission denied' in stderr or 'publickey' in stderr:
                    print(f"❌ SSH authentication failed: Check if your SSH key is added to Vast.ai")
                    return "STATUS: SSH_AUTH_ERROR\\nDETAILS: SSH key not authorized"
                elif 'timeout' in stderr or 'timed out' in stderr or 'banner exchange' in stderr:
                    print(f"❌ SSH timeout: Instance may not be ready yet")
                    return "STATUS: SSH_NOT_READY\\nDETAILS: Connection timeout"
                else:
                    print(f"❌ SSH error (code {result.returncode}): {result.stderr}")
                    return f"STATUS: SSH_ERROR\\nDETAILS: {result.stderr}"
                    
        except subprocess.TimeoutExpired:
            print(f"❌ SSH timeout: Instance is not responding")
            return "STATUS: SSH_NOT_READY\\nDETAILS: SSH connection timeout"
        except FileNotFoundError:
            print(f"❌ SSH command not found. Please install OpenSSH client.")
            return "STATUS: SSH_ERROR\\nDETAILS: SSH client not installed"
        except Exception as e:
            print(f"❌ SSH error: {e}")
            return f"STATUS: SSH_ERROR\\nDETAILS: {str(e)}"
    
    def create_status_script(self):
        """Create the remote status checking script"""
        return textwrap.dedent("""
            #!/bin/bash
            
            # Define log file paths
            ONSTART_LOG="/var/log/onstart.log"
            COMFYUI_LOG="/var/log/portal/comfyui.log"
            
            # Function to extract tunnel URLs
            get_tunnel_urls() {
                echo "TUNNEL_URLS:"
                # Check multiple log patterns for cloudflare tunnels
                for log_file in /var/log/*.log /tmp/*.log ~/.cloudflared/*.log; do
                    if [[ -f "$log_file" ]]; then
                        # Look for various cloudflare tunnel patterns
                        grep -E "(tunnel|cloudflare|https://.*\.trycloudflare\.com)" "$log_file" 2>/dev/null | grep -o 'https://[^[:space:]]*\.trycloudflare\.com[^[:space:]]*' | while read url; do
                            # Determine service by port context
                            if grep -B5 -A5 "$url" "$log_file" | grep -q "8188\|comfyui"; then
                                echo "ComfyUI: $url"
                            elif grep -B5 -A5 "$url" "$log_file" | grep -q "1111\|portal"; then
                                echo "Portal: $url"
                            elif grep -B5 -A5 "$url" "$log_file" | grep -q "8080\|jupyter"; then
                                echo "Jupyter: $url"
                            elif grep -B5 -A5 "$url" "$log_file" | grep -q "8384\|syncthing"; then
                                echo "Syncthing: $url"
                            else
                                # Generic tunnel URL
                                echo "Tunnel: $url"
                            fi
                        done
                    fi
                done
                
                # Also check for tunnel URLs in process output
                ps aux | grep -E "(cloudflared|tunnel)" | grep -o 'https://[^[:space:]]*\.trycloudflare\.com[^[:space:]]*' | while read url; do
                    echo "Active: $url"
                done
            }
            
            # Function to get storage usage
            get_storage_info() {
                echo "STORAGE_INFO:"
                df -h / | tail -n 1 | awk '{
                    used=$3;
                    total=$2;
                    avail=$4;
                    percent=$5;
                    gsub(/%/, "", percent);
                    print "Used: " used " / " total " (" percent "% used, " avail " available)"
                }'
            }

            # Function to get elapsed time since provisioning started
            get_elapsed_time() {
                if [ -f "$ONSTART_LOG" ]; then
                    # Get the creation/modification time of the log file (when provisioning started)
                    log_time=$(stat -c %Y "$ONSTART_LOG" 2>/dev/null || stat -f %m "$ONSTART_LOG" 2>/dev/null)
                    current_time=$(date +%s)
                    elapsed=$((current_time - log_time))

                    # Convert to human readable format
                    minutes=$((elapsed / 60))
                    seconds=$((elapsed % 60))

                    if [ $minutes -gt 0 ]; then
                        echo "ELAPSED_TIME: ${minutes}m ${seconds}s"
                    else
                        echo "ELAPSED_TIME: ${seconds}s"
                    fi
                fi
            }
            
            # Check for final ready state
            if grep -q "To see the GUI go to:" "$ONSTART_LOG" 2>/dev/null; then
                echo "STATUS: READY"
                echo "DETAILS: ComfyUI is fully loaded and running"
                get_elapsed_time
                get_tunnel_urls
                get_storage_info
                echo "LAST_LOG:"
                tail -n 3 "$ONSTART_LOG" | sed 's/^/  /'
                exit 0
            fi

            # Check if ComfyUI is starting after provisioning
            if grep -q "Provisioning complete!" "$ONSTART_LOG" 2>/dev/null; then
                echo "STATUS: STARTING_APP"
                echo "DETAILS: Provisioning complete, ComfyUI starting up"
                get_elapsed_time
                get_tunnel_urls
                get_storage_info
                echo "LAST_LOG:"
                tail -n 5 "$ONSTART_LOG" | sed 's/^/  /'
                exit 0
            fi

            # Check if models are downloading
            DOWNLOAD_COUNT=$(grep -c "✓ Downloaded to:" "$ONSTART_LOG" 2>/dev/null)
            TOTAL_DOWNLOADS=$(grep -c "Downloading.*model(s) to" "$ONSTART_LOG" 2>/dev/null)
            if grep -q "Downloading.*model(s) to" "$ONSTART_LOG" 2>/dev/null; then
                echo "STATUS: DOWNLOADING"
                echo "DETAILS: Downloading models ($DOWNLOAD_COUNT completed)"
                get_elapsed_time

                # Show current download progress - prioritize actual progress lines with MB/s
                current_download=$(grep "Progress:\\|Speed:" "$ONSTART_LOG" 2>/dev/null | tail -n 2)
                if [ -n "$current_download" ]; then
                    echo "CURRENT_DOWNLOAD:"
                    echo "$current_download" | sed 's/^/  /'
                else
                    # Fallback to debug messages if no progress yet
                    current_download=$(grep "Downloading with HF Transfer\\|\\[Initializing\\|\\[Waiting\\|\\[Monitor" "$ONSTART_LOG" 2>/dev/null | tail -n 2)
                    if [ -n "$current_download" ]; then
                        echo "CURRENT_DOWNLOAD:"
                        echo "$current_download" | sed 's/^/  /'
                    fi
                fi

                get_storage_info
                echo "LAST_LOG:"
                tail -n 3 "$ONSTART_LOG" | sed 's/^/  /'
                exit 0
            fi

            # Check if provisioning is in progress
            if [ -f "/.provisioning" ] || grep -q "Provisioning container" "$ONSTART_LOG" 2>/dev/null; then
                echo "STATUS: PROVISIONING"
                echo "DETAILS: Running initial provisioning script"
                get_elapsed_time
                get_storage_info
                echo "LAST_LOG:"
                tail -n 5 "$ONSTART_LOG" 2>/dev/null | sed 's/^/  /'
                exit 0
            fi
            
            # Check for errors (but don't exit - let the timer handle failures)
            # Commented out to prevent premature exits on non-fatal errors
            # if grep -iE "error|failed|traceback" "$ONSTART_LOG" 2>/dev/null | \
            #    grep -vE "failed to sufficiently increase receive buffer size|UDP Buffer Sizes" | \
            #    grep -q .; then
            #     echo "STATUS: ERROR"
            #     echo "DETAILS: Error detected in logs"
            #     echo "ERROR_DETAILS:"
            #     grep -iE "error|failed|traceback" "$ONSTART_LOG" 2>/dev/null | \
            #         grep -vE "failed to sufficiently increase receive buffer size|UDP Buffer Sizes" | \
            #         tail -n 3 | sed 's/^/  /'
            #     get_storage_info
            #     exit 0
            # fi
            
            # Default: still initializing
            echo "STATUS: INITIALIZING"
            echo "DETAILS: Instance booting up, waiting for services to start"
            get_storage_info
            if [ -f "$ONSTART_LOG" ]; then
                echo "LAST_LOG:"
                tail -n 3 "$ONSTART_LOG" | sed 's/^/  /'
            fi
        """)
    
    def parse_status_output(self, output):
        """Parse the status script output into structured data"""
        lines = output.split('\n')
        status_data = {
            'status': 'UNKNOWN',
            'details': '',
            'tunnel_urls': {},
            'last_log': [],
            'current_download': '',
            'error_details': [],
            'storage_info': '',
            'elapsed_time': ''
        }

        current_section = None

        for line in lines:
            if line.startswith('STATUS:'):
                status_data['status'] = line.replace('STATUS: ', '')
            elif line.startswith('DETAILS:'):
                status_data['details'] = line.replace('DETAILS: ', '')
            elif line.startswith('ELAPSED_TIME:'):
                status_data['elapsed_time'] = line.replace('ELAPSED_TIME: ', '')
            elif line.startswith('TUNNEL_URLS:'):
                current_section = 'urls'
            elif line.startswith('LAST_LOG:'):
                current_section = 'log'
            elif line.startswith('CURRENT_DOWNLOAD:'):
                current_section = 'download'
            elif line.startswith('ERROR_DETAILS:'):
                current_section = 'error'
            elif line.startswith('STORAGE_INFO:'):
                current_section = 'storage'
            elif current_section == 'urls' and ':' in line:
                parts = line.split(': ', 1)
                if len(parts) == 2:
                    status_data['tunnel_urls'][parts[0]] = parts[1]
            elif current_section == 'log' and line.startswith('  '):
                status_data['last_log'].append(line[2:])
            elif current_section == 'download' and line.startswith('  '):
                status_data['current_download'] += line[2:] + '\n'
            elif current_section == 'error' and line.startswith('  '):
                status_data['error_details'].append(line[2:])
            elif current_section == 'storage' and line.strip():
                status_data['storage_info'] = line.strip()
        
        return status_data
    
    def print_status_report(self, status_data):
        """Print a formatted status report"""
        status = status_data['status']
        
        # Status emoji mapping
        status_emoji = {
            'READY': '✅',
            'STARTING_APP': '🚀', 
            'DOWNLOADING': '⬇️',
            'PROVISIONING': '⚙️',
            'INITIALIZING': '🔄',
            'ERROR': '❌',
            'SSH_ERROR': '🔑',
            'SSH_NOT_READY': '⏳',
            'SSH_AUTH_ERROR': '🔐',
            'CONNECTION_ERROR': '🌐',
            'UNKNOWN': '❓'
        }
        
        emoji = status_emoji.get(status, '❓')
        
        print(f"\n{emoji} Instance {self.instance_id} - Status: {status}")
        print(f"   {status_data['details']}")

        # Show elapsed time if available
        if status_data['elapsed_time']:
            print(f"   ⏱️  Elapsed: {status_data['elapsed_time']}")

        # Show download progress if downloading
        if status == 'DOWNLOADING' and status_data['current_download']:
            print(f"\n📦 Current Download Progress:")
            for line in status_data['current_download'].strip().split('\n'):
                if line.strip():
                    print(f"   {line}")

        # Show storage info if available
        if status_data['storage_info']:
            print(f"\n💾 Storage: {status_data['storage_info']}")
        
        # Show tunnel URLs if available
        if status_data['tunnel_urls']:
            print(f"\n🌐 Portal URLs:")
            for service, url in status_data['tunnel_urls'].items():
                print(f"   {service}: {url}")
        
        # Show SSH connection commands (only when ready or have SSH access)
        if status in ['READY', 'STARTING_APP', 'DOWNLOADING'] and hasattr(self, 'current_ssh_info'):
            self.print_ssh_commands()
        
        # Show recent logs
        if status_data['last_log']:
            print("\n" + "─" * 65)
            print("📝 Recent Activity:")
            print("─" * 65)
            for log_line in status_data['last_log'][-3:]:
                if log_line.strip():
                    print(f"│ {log_line}")
            print("─" * 65)
        
        # Show errors if any
        if status_data['error_details']:
            print(f"\n⚠️ Error Details:")
            for error_line in status_data['error_details']:
                print(f"   {error_line}")
    
    def print_ssh_commands(self):
        """Print SSH connection commands for manual access"""
        if not hasattr(self, 'current_ssh_info'):
            return
            
        ssh_info = self.current_ssh_info
        host = ssh_info['host']
        port = ssh_info['port']
        
        print(f"\n🔑 SSH Connection Commands:")
        print("─" * 65)
        
        # Basic SSH connection
        print(f"📋 Basic SSH access:")
        print(f"   ssh -p {port} root@{host}")
        
        # SSH with port forwarding for common services
        print(f"\n📋 SSH with port forwarding:")
        print(f"   # ComfyUI (8188)")
        print(f"   ssh -p {port} root@{host} -L 8188:localhost:8188")
        
        print(f"\n   # Multiple services")
        print(f"   ssh -p {port} root@{host} \\")
        print(f"     -L 8188:localhost:8188 \\")  # ComfyUI
        print(f"     -L 8080:localhost:8080 \\")  # Jupyter
        print(f"     -L 8384:localhost:8384 \\")  # Syncthing
        print(f"     -L 1111:localhost:1111")    # Portal
        
        # With key file (if using custom key)
        if self.ssh_key_path and not self.ssh_key_path.endswith('id_ed25519'):
            print(f"\n📋 With custom SSH key:")
            print(f"   ssh -i {self.ssh_key_path} -p {port} root@{host}")
        
        # SCP examples
        print(f"\n📋 File transfer (SCP):")
        print(f"   # Upload file")
        print(f"   scp -P {port} ./local_file.txt root@{host}:/workspace/")
        print(f"   # Download file") 
        print(f"   scp -P {port} root@{host}:/workspace/file.txt ./")
        
        print("─" * 65)
        print("💡 After connecting, ComfyUI is available at http://localhost:8188")
    
    def monitor(self, max_wait_minutes=60, poll_interval=10):
        """Monitor the instance until ready or timeout"""
        print(f"🔍 Starting monitor for instance {self.instance_id}")
        print(f"⏱️ Will check every {poll_interval}s for up to {max_wait_minutes} minutes")
        
        start_time = time.time()
        max_wait_time = max_wait_minutes * 60
        status_script = self.create_status_script()
        
        while time.time() - start_time < max_wait_time:
            # Get instance info
            instance_data = self.get_instance_info()
            if not instance_data:
                print("❌ Could not fetch instance data, retrying...")
                time.sleep(poll_interval)
                continue
            
            # Get SSH info
            ssh_info = self.get_ssh_info(instance_data)
            if not ssh_info:
                print("⏳ Waiting for instance to be ready for SSH...")
                time.sleep(poll_interval)
                continue
            
            # Store SSH info for later use in display
            self.current_ssh_info = ssh_info
            
            # Execute status check
            print(f"\n🔗 Connecting to {ssh_info['host']}:{ssh_info['port']}")
            raw_output = self.execute_remote_script(ssh_info, status_script)
            
            if "STATUS:" not in raw_output:
                print(f"❌ Unexpected script output: {raw_output}")
                time.sleep(poll_interval)
                continue
            
            # Parse and display status
            status_data = self.parse_status_output(raw_output)
            self.print_status_report(status_data)
            
            # Check if we're done
            if status_data['status'] == 'READY':
                print(f"\n🎉 Instance is fully ready! ComfyUI is accessible.")
                if status_data['tunnel_urls'].get('ComfyUI'):
                    print(f"🎨 ComfyUI URL: {status_data['tunnel_urls']['ComfyUI']}")
                return True
            # Removed ERROR status handling - let timer handle failures instead
            
            # Wait before next check
            print(f"\n⏳ Waiting {poll_interval}s before next check...")
            time.sleep(poll_interval)
        
        print(f"\n⏰ Timeout after {max_wait_minutes} minutes. Instance may still be starting up.")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python monitor_instance.py <INSTANCE_ID>")
        print("Example: python monitor_instance.py 12345")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    
    try:
        monitor = VastInstanceMonitor(instance_id)
        success = monitor.monitor(max_wait_minutes=60, poll_interval=10)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()