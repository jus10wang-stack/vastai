# Vast.ai Instance Management Scripts

Scripts for managing and monitoring Vast.ai instances.

## Scripts

### 1. `create_and_monitor.py` - All-in-One Solution ✨
**Recommended**: Creates an instance and automatically monitors it until ready.

```bash
# Create instance using offer index 0 (cheapest) and monitor it
poetry run python python_scripts/create_and_monitor.py 0

# Create instance using offer index 2 and monitor it  
poetry run python python_scripts/create_and_monitor.py 2
```

**Features:**
- ✅ Creates instance using your search_and_create.py
- ✅ Automatically extracts the instance ID
- ✅ Monitors download progress with HF Transfer speeds
- ✅ Shows portal URLs when available
- ✅ Notifies when ComfyUI is ready

### 2. `monitor_instance.py` - Monitor Existing Instance
Monitor an existing instance by ID.

```bash
# Monitor instance with specific ID
poetry run python python_scripts/monitor_instance.py 12345
```

**Features:**
- 📊 Real-time status monitoring
- 📦 Download progress tracking
- 🌐 Portal URL extraction
- ⚡ HF Transfer speed reporting
- 🎯 Ready state detection

### 3. `get_tunnel_urls.sh` - Extract URLs from Running Instance
Get portal URLs from inside a running instance (run via SSH).

```bash
# SSH into instance first, then run:
./get_tunnel_urls.sh
```

## Instance Status Types

- 🔄 **INITIALIZING** - Instance is booting up
- ⚙️ **PROVISIONING** - Installing packages and dependencies  
- ⬇️ **DOWNLOADING** - Downloading models with HF Transfer
- 🚀 **STARTING_APP** - ComfyUI is starting after provisioning
- ✅ **READY** - ComfyUI is fully loaded and accessible
- ❌ **ERROR** - Something went wrong

## Portal URLs

When ready, you'll see URLs like:
- 🎨 **ComfyUI**: `https://xxx.trycloudflare.com` - Main interface
- 🌐 **Portal**: `https://yyy.trycloudflare.com` - Instance management  
- 📓 **Jupyter**: `https://zzz.trycloudflare.com` - Jupyter notebooks
- 🔄 **Syncthing**: `https://www.trycloudflare.com` - File sync

## Example Usage

### Quick Start (Most Common)
```bash
# Create and monitor in one command
poetry run python python_scripts/create_and_monitor.py 0
```

### Manual Monitoring  
```bash
# If you already have an instance ID
poetry run python python_scripts/monitor_instance.py 25736179
```

### Check URLs Only
```bash
# SSH into your instance first
ssh -i ~/.ssh/id_ed25519 root@SSH_HOST -p SSH_PORT

# Then run inside the instance
./get_tunnel_urls.sh
```

## Requirements

- Python 3.6+
- `paramiko` library for SSH
- `requests` library for API calls
- Valid `VAST_API_KEY` in your `.env` file
- SSH key configured with Vast.ai

## Configuration

Make sure your `.env` file contains:
```
VAST_API_KEY=your_vast_ai_api_key_here
```

And your SSH key is in one of these locations:
- `~/.ssh/id_ed25519` (preferred)
- `~/.ssh/id_rsa` (fallback)