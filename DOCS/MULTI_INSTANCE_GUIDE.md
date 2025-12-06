# Multi-Instance SSH Tunnel Management Guide

## Overview

The Vast.ai toolkit now supports **automatic SSH tunnel management** with **dynamic port allocation**, allowing you to run multiple instances simultaneously and access each one via a different `localhost` port.

### Key Features

- ✅ **Automatic Port Allocation**: Each instance gets a unique local port (8188, 8189, 8190, ...)
- ✅ **Background Tunnels**: SSH tunnels run in background, terminal stays free
- ✅ **Persistent State**: Tunnel info saved to `~/.vai_tunnels.json` and `~/.vai_ports.json`
- ✅ **Easy Management**: Simple commands to list, create, and close tunnels
- ✅ **Zero Configuration**: Fully automatic when using `vai create`

---

## Quick Start: Multiple Instances

### Example: Create 3 Instances with Different Localhost Ports

```bash
# Terminal 1: Create first instance
$ vai create config1.json
# Instance A created (ID: 12345)
# Tunnel auto-created: http://localhost:8188

# Terminal 2: Create second instance (while first is still running)
$ vai create config2.json
# Instance B created (ID: 12346)
# Tunnel auto-created: http://localhost:8189  ← AUTO-INCREMENT!

# Terminal 3: Create third instance
$ vai create config3.json
# Instance C created (ID: 12347)
# Tunnel auto-created: http://localhost:8190  ← AUTO-INCREMENT!
```

**Result**: You can now access all 3 ComfyUI instances simultaneously:
- http://localhost:8188 → Instance A (12345)
- http://localhost:8189 → Instance B (12346)
- http://localhost:8190 → Instance C (12347)

---

## How It Works

### Automatic Tunnel Creation (via `vai create`)

When you run `vai create <config>`, the system:

1. **Creates the Vast.ai instance**
2. **Monitors until ComfyUI is ready**
3. **Auto-allocates next available local port** (checks `~/.vai_ports.json`)
4. **Creates SSH tunnel in background** using `ssh -N -L <port>:localhost:8188`
5. **Saves tunnel state** to `~/.vai_tunnels.json`
6. **Displays localhost URL** for immediate access

**No manual SSH commands needed!**

---

## Manual Tunnel Management

### Create Tunnel Manually

If you already have an instance running but no tunnel:

```bash
$ vai tunnel 12345
🔗 Creating SSH tunnel for instance 12345...
✅ Tunnel created successfully!
   PID: 98234
   Access at: http://localhost:8188

🌐 Access ComfyUI at: http://localhost:8188
💡 To close: vai tunnel --stop 12345
```

### List All Active Tunnels

```bash
$ vai tunnel --list

📡 Active SSH Tunnels:
================================================================================
Instance ID     SSH Host:Port                  Local Port   PID
--------------------------------------------------------------------------------
12345           ssh4.vast.ai:42785             8188         98234
12346           ssh5.vast.ai:38921             8189         98235
12347           ssh6.vast.ai:51203             8190         98236
================================================================================
Total: 3 active tunnel(s)
```

### Close Specific Tunnel

```bash
$ vai tunnel --stop 12345
🔒 Closing SSH tunnel for instance 12345...
✅ Closed tunnel for instance 12345 (port 8188, PID 98234)
✅ Released port 8188 for instance 12345
```

### Close All Tunnels

```bash
$ vai tunnel --stop-all
🔒 Closing all SSH tunnels...
🔒 Closing 3 tunnel(s)...
   Closed tunnel for instance 12345 (port 8188, PID 98234)
   Closed tunnel for instance 12346 (port 8189, PID 98235)
   Closed tunnel for instance 12347 (port 8190, PID 98236)
✅ All tunnels closed
```

---

## Port Allocation System

### How Ports Are Assigned

The **PortAllocator** (`SCRIPTS/python_scripts/utils/port_allocator.py`) manages port assignments:

1. **Base port**: 8188 (default for ComfyUI)
2. **Auto-increment**: 8189, 8190, 8191, ...
3. **Availability check**: Uses `socket` to verify port is free
4. **Persistent state**: Saved to `~/.vai_ports.json`

### Port State File (`~/.vai_ports.json`)

```json
{
  "12345": 8188,
  "12346": 8189,
  "12347": 8190
}
```

**What this means**:
- Instance 12345 → localhost:8188
- Instance 12346 → localhost:8189
- Instance 12347 → localhost:8190

### Port Cleanup

When you destroy an instance, the port is **automatically released** and can be reused:

```bash
$ vai destroy 12345
# Port 8188 is now free for next instance
```

---

## Tunnel State Persistence

### Tunnel State File (`~/.vai_tunnels.json`)

```json
{
  "12345": {
    "local_port": 8188,
    "ssh_host": "ssh4.vast.ai",
    "ssh_port": 42785,
    "remote_port": 8188,
    "pid": 98234,
    "created_at": "2025-12-05T10:30:00",
    "ssh_key_path": "/home/user/.ssh/id_ed25519"
  },
  "12346": {
    "local_port": 8189,
    "ssh_host": "ssh5.vast.ai",
    "ssh_port": 38921,
    "remote_port": 8188,
    "pid": 98235,
    "created_at": "2025-12-05T10:31:00",
    "ssh_key_path": "/home/user/.ssh/id_ed25519"
  }
}
```

### Automatic Cleanup

The system automatically cleans up:
- **Dead tunnels**: If PID no longer exists, entry is removed
- **Stale allocations**: Ports for non-existent instances are freed

---

## Advanced Usage

### Custom Port Range

If you want to use a different base port (e.g., 9000 instead of 8188):

**Edit `port_allocator.py` initialization**:
```python
# In create_and_monitor_config.py or tunnel_manager.py
allocator = PortAllocator(base_port=9000)
```

Result: Instances will use ports 9000, 9001, 9002, ...

### SSH Tunnel Options

Tunnels are created with these SSH options:
- `-N`: No remote command execution (just tunnel)
- `-L <local>:localhost:<remote>`: Port forwarding
- `-o ServerAliveInterval=60`: Keepalive every 60 seconds
- `-o ServerAliveCountMax=3`: Max 3 keepalive failures before disconnect
- `-o StrictHostKeyChecking=no`: Auto-accept host keys

### Background Process Management

Tunnels run as **detached background processes**:
```bash
# Check if tunnel is running
$ ps aux | grep "ssh -N -L 8188"

# Manually kill tunnel (alternative to vai tunnel --stop)
$ kill <PID>
```

---

## Troubleshooting

### Problem: Port Already in Use

**Symptom**:
```
❌ Port 8188 is already in use
```

**Solution**:
```bash
# List active tunnels
$ vai tunnel --list

# Close conflicting tunnel
$ vai tunnel --stop <instance_id>

# Or find process manually
$ lsof -i :8188
$ kill <PID>
```

### Problem: Tunnel Process Died

**Symptom**:
```
⚠️ Found dead tunnel for instance 12345, recreating...
```

**Solution**:
The system auto-detects dead tunnels and recreates them:
```bash
$ vai tunnel 12345
# Will recreate tunnel automatically
```

### Problem: SSH Connection Failed

**Symptom**:
```
❌ SSH tunnel process died immediately after launch
```

**Possible causes**:
1. SSH key not found → Check: `vai ssh-key`
2. Instance not ready → Wait a few more minutes
3. Firewall blocking SSH → Check network settings

**Solution**:
```bash
# Verify SSH key
$ vai ssh-key

# Test SSH manually
$ ssh -p <ssh_port> root@<ssh_host>

# Retry tunnel creation
$ vai tunnel <instance_id>
```

### Problem: Can't Access Localhost URL

**Symptom**:
Browser shows "Connection refused" at http://localhost:8188

**Check**:
1. Is tunnel running?
   ```bash
   $ vai tunnel --list
   ```

2. Is ComfyUI ready on remote instance?
   ```bash
   $ vai cancel <instance_id> --list
   # Should show ComfyUI is running
   ```

3. Test tunnel manually:
   ```bash
   $ curl http://localhost:8188
   # Should return HTML
   ```

---

## Integration with Workflows

### Using with `vai exec`

Once tunnels are created, you can execute workflows as usual:

```bash
# Create instances with auto-tunnels
$ vai create config1.json  # Instance A → localhost:8188
$ vai create config2.json  # Instance B → localhost:8189

# Execute workflows
$ vai exec 12345 config1.json  # Runs on Instance A
$ vai exec 12346 config2.json  # Runs on Instance B (parallel!)

# Both workflows run simultaneously on different instances
```

### Using with `vai oneshot`

`vai oneshot` also supports auto-tunnel creation:

```bash
$ vai oneshot config1.json
# Creates instance, auto-creates tunnel, executes workflow, extracts results
```

---

## Technical Architecture

### Components

1. **PortAllocator** (`utils/port_allocator.py`)
   - Manages local port assignments
   - Checks port availability using `socket`
   - Persists state to `~/.vai_ports.json`

2. **TunnelManager** (`utils/tunnel_manager.py`)
   - Creates SSH tunnels via `subprocess.Popen`
   - Tracks tunnel PIDs for lifecycle management
   - Auto-detects dead tunnels
   - Persists state to `~/.vai_tunnels.json`

3. **Integration** (`create_and_monitor_config.py`)
   - Auto-creates tunnels after instance is ready
   - Fetches SSH info from Vast.ai API
   - Displays localhost URL with allocated port

### Data Flow

```
vai create config.json
    ↓
create_instance() → Vast.ai API
    ↓
start_monitoring_with_failsafe() → Wait for SSH ready
    ↓
TunnelManager.create_tunnel()
    ↓
PortAllocator.allocate() → Get next available port (e.g., 8189)
    ↓
subprocess.Popen("ssh -N -L 8189:localhost:8188 ...")
    ↓
Save state to ~/.vai_tunnels.json
    ↓
Display: "Access at http://localhost:8189"
```

---

## Best Practices

### 1. Clean Up Tunnels When Done

Always close tunnels for destroyed instances:
```bash
$ vai destroy 12345
$ vai tunnel --stop 12345  # Free up port 8188
```

### 2. List Tunnels Regularly

Check active tunnels to avoid orphaned processes:
```bash
$ vai tunnel --list
```

### 3. Use Auto-Tunnel with `vai create`

Don't manually create tunnels unless necessary—`vai create` handles it automatically.

### 4. Monitor Tunnel Health

If ComfyUI becomes inaccessible, check tunnel status:
```bash
$ vai tunnel --list
# Verify PID is still running
$ ps -p <PID>
```

---

## FAQ

### Q: What happens if I create 10 instances?

**A**: Each gets a unique port:
- Instance 1 → localhost:8188
- Instance 2 → localhost:8189
- ...
- Instance 10 → localhost:8197

No limit (up to port 65535).

### Q: Do tunnels survive terminal close?

**A**: Yes! Tunnels run as detached background processes. They persist until:
- You manually close them (`vai tunnel --stop`)
- SSH connection fails
- System reboot

### Q: Can I use custom SSH keys per instance?

**A**: Yes! Specify in config file:
```json
{
  "instance_config": {
    "ssh_key_path": "/path/to/custom/key"
  }
}
```

### Q: What if port 8188 is already used by another app?

**A**: The allocator auto-skips occupied ports:
```
Port 8188 occupied → Try 8189
Port 8189 occupied → Try 8190
Port 8190 free → Allocate 8190
```

### Q: How do I reset all tunnels/ports?

**A**: Delete state files:
```bash
$ rm ~/.vai_tunnels.json
$ rm ~/.vai_ports.json
$ vai tunnel --stop-all
```

---

## Summary

### Before (Manual SSH Tunnels)

```bash
# Terminal 1
$ vai create config.json
$ ssh -p 42785 root@ssh4.vast.ai -L 8188:localhost:8188
# Must keep terminal open

# Terminal 2 (second instance fails!)
$ vai create config2.json
$ ssh -p 38921 root@ssh5.vast.ai -L 8188:localhost:8188
ERROR: Port 8188 already in use!
```

### After (Automatic Tunnel Management)

```bash
# Terminal 1
$ vai create config.json
# Auto-tunnel: localhost:8188
# Terminal free!

# Terminal 2
$ vai create config2.json
# Auto-tunnel: localhost:8189  ← AUTO-INCREMENT
# Terminal free!

# Open browser
http://localhost:8188  # Instance A
http://localhost:8189  # Instance B
```

**Result**: Seamless multi-instance workflow with zero manual SSH commands! 🎉
