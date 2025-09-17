# Python Scripts

This directory contains Python scripts for managing Vast.ai instances.

## Directory Structure

### 📦 `components/`
Individual, single-purpose scripts that perform one specific task:

- **`search_offers.py`** - Search for GPU offers with cost optimization
  ```bash
  poetry run python SCRIPTS/python_scripts/components/search_offers.py [INDEX]
  ```

- **`create_instance.py`** - Create an instance from an offer ID
  ```bash
  poetry run python SCRIPTS/python_scripts/components/create_instance.py <OFFER_ID>
  ```

- **`monitor_instance.py`** - Monitor an existing instance until ready
  ```bash
  poetry run python SCRIPTS/python_scripts/components/monitor_instance.py <INSTANCE_ID>
  ```

- **`quick_monitor.py`** - Helper wrapper for monitor_instance.py
  ```bash
  poetry run python SCRIPTS/python_scripts/components/quick_monitor.py <INSTANCE_ID>
  ```

- **`comfyui_api.py`** - Programmatically control ComfyUI workflows via SSH
  ```bash
  poetry run python SCRIPTS/python_scripts/components/comfyui_api.py <instance_id> <ssh_host> <ssh_port> <image_path> "<prompt>"
  ```

### 🔄 `workflows/`
Complete multi-step workflows that combine multiple components:

- **`create_and_monitor.py`** - Complete workflow: Search → Create → Monitor
  ```bash
  # Default: RTX 3060, cheapest option
  poetry run python SCRIPTS/python_scripts/workflows/create_and_monitor.py
  
  # Specify index and GPU type
  poetry run python SCRIPTS/python_scripts/workflows/create_and_monitor.py 1 "RTX 4090"
  ```

- **`search_and_create.py`** - Partial workflow: Search → Create (no monitoring)
  ```bash
  poetry run python SCRIPTS/python_scripts/workflows/search_and_create.py [INDEX]
  ```

- **`run_comfyui_workflow.py`** - Execute ComfyUI workflow with custom image and prompt
  ```bash
  poetry run python SCRIPTS/python_scripts/workflows/run_comfyui_workflow.py <instance_id> <image_path> "<prompt>"
  ```

## Quick Start

For most users, the easiest way is to use the complete workflow:

```bash
# This will search for the cheapest RTX 3060, create it, and monitor until ready
poetry run python SCRIPTS/python_scripts/workflows/create_and_monitor.py
```

## Component Details

### search_offers.py
- Filters for verified providers only
- Requires ≥800 Mbps download, ≥100 Mbps upload
- Filters for bandwidth costs ≤$2/TB
- Sorts by total 10-minute cost (compute + 100GB download)
- Returns the offer ID at the specified index

### create_instance.py
- Takes an offer ID as input
- Uses predefined template with ComfyUI setup
- Returns instance details including instance ID

### monitor_instance.py
- Monitors instance status via SSH
- Shows real-time progress including:
  - Provisioning status
  - Model download progress
  - Service startup
  - Portal URLs when available
- Exits automatically when instance is ready
- Returns success/failure status

## Workflow Details

### create_and_monitor.py
The most complete workflow that handles everything end-to-end:
1. Searches for GPU offers (uses `search_offers.py`)
2. Creates instance with selected offer (uses `create_instance.py`)
3. Monitors until ready (uses `monitor_instance.py`)
4. Exits with appropriate status code

### search_and_create.py
A simpler workflow for when you want to handle monitoring separately:
1. Searches for GPU offers
2. Creates instance with selected offer
3. Prints instance ID for manual monitoring

### run_comfyui_workflow.py
Execute ComfyUI workflows programmatically on running instances:
1. Fetches instance SSH details automatically
2. Uploads your image to the instance
3. Modifies the latest ComfyUI workflow with your prompt and image
4. Queues the workflow for execution

## ComfyUI API Control

The `comfyui_api.py` component provides programmatic control over ComfyUI workflows through SSH. This allows you to:

- **Upload images** to the ComfyUI input directory
- **Fetch and modify workflows** directly from ComfyUI's API
- **Queue custom prompts** without using the web interface
- **Automate video generation** with different images and prompts

### Example Usage

```bash
# First, create and wait for an instance to be ready
poetry run python SCRIPTS/python_scripts/workflows/create_and_monitor.py

# Then run a workflow with your image and prompt
poetry run python SCRIPTS/python_scripts/workflows/run_comfyui_workflow.py 26003525 ./my_image.jpg "A cinematic video of a cat in space"
```

### Node Configuration

By default, the workflow assumes:
- **Node 6**: Positive prompt (CLIPTextEncode)
- **Node 62**: Image loader (LoadImage)

You can specify different node IDs if your workflow uses different nodes:

```bash
poetry run python SCRIPTS/python_scripts/workflows/run_comfyui_workflow.py 26003525 ./image.jpg "prompt" custom_prompt_node custom_image_node
```