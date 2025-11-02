# VAI - Vast.ai Workflow Command Interface

A streamlined command-line interface for managing Vast.ai GPU instances and executing ComfyUI workflows.

## Quick Start

```bash
# Show all available commands
./vai

# Create and monitor a new instance
./vai cm

# Execute a workflow on an existing instance
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json TEMPLATES/4_images/test-image.png "cat in space"
```

## Commands

### Primary Workflows

#### `vai cm` - Create and Monitor Instance
Creates a new Vast.ai instance, monitors until ready.

```bash
# Use defaults (index=0, RTX 3060, provision_test_3.sh)
./vai cm

# Custom offer index
./vai cm 1

# Custom GPU type
./vai cm 1 "RTX 4090"

# Full customization
./vai cm 1 "RTX 4090" provision_test_1.sh
```

**Parameters:**
- `INDEX` - Offer index to select (default: 0)
- `GPU_NAME` - GPU to search for (default: "RTX 3060")
- `PROVISIONING_SCRIPT` - Script to use (default: "provision_test_3.sh")

#### `vai exec` - Execute Workflow
Executes a ComfyUI workflow on an existing instance.

```bash
./vai exec <instance_id> <workflow_file> <image_path> "<prompt>"
```

**Examples:**
```bash
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json ./image.png "beautiful landscape"
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json TEMPLATES/4_images/test-image.png "cinematic cat video"
```

**Parameters:**
- `INSTANCE_ID` - Your Vast.ai instance ID
- `WORKFLOW_FILE` - Workflow filename (located in `/workspace/ComfyUI/user/default/workflows/`)
- `IMAGE_PATH` - Path to your input image
- `PROMPT` - Text description for generation

## Complete End-to-End Workflow

### Step 1: Create Instance
```bash
# Create and monitor instance with custom settings
./vai cm 1 "RTX 4090" provision_test_1.sh
```

This will:
- Search for RTX 4090 offers
- Select offer at index 1
- Create instance with provision_test_1.sh
- Monitor until ready
- Display instance ID when complete

### Step 2: Execute Workflow
```bash
# Use the instance ID from step 1
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json TEMPLATES/4_images/test-image.png "a majestic cat in space, cinematic lighting"
```

This will:
- Auto-fetch SSH connection details
- Upload your image
- Execute the workflow with your prompt
- Start background monitoring
- Provide job ID for tracking

## Help System

```bash
# General help
./vai
./vai help

# Command-specific help
./vai cm --help
./vai exec --help
```

## Available Resources

### Provisioning Scripts
Located in `TEMPLATES/2_provisioning_scripts/`:
- `provision_test_1.sh` - Basic setup
- `provision_test_2.sh` - Enhanced setup 
- `provision_test_3.sh` - Full setup (default)

### Workflow Files
Located on instance at `/workspace/ComfyUI/user/default/workflows/`:
- `wan2-2-I2V-FP8-Lightning.json` - Image-to-video generation

### Template Images
Located in `TEMPLATES/4_images/`:
- `test-image.png` - Sample input image

## Prerequisites

1. **Environment Setup:**
   ```bash
   # Ensure you have VAST_API_KEY in your environment
   export VAST_API_KEY="your_api_key_here"
   ```

2. **Dependencies:**
   ```bash
   # Install using Poetry (recommended)
   poetry install
   ```

3. **SSH Key:**
   - SSH key should be at `~/.ssh/id_ed25519_vastai` or similar
   - Key should be registered with your Vast.ai account

## Examples

### Basic Usage
```bash
# Quick start with defaults
./vai cm

# When instance is ready (use the instance ID shown)
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json TEMPLATES/4_images/test-image.png "epic mountain landscape"
```

### Advanced Usage
```bash
# High-end GPU with custom provisioning
./vai cm 0 "RTX 4090" provision_test_2.sh

# Custom workflow execution
./vai exec 26003629 my-custom-workflow.json ./my-image.jpg "detailed anime character, studio lighting"
```

### Production Workflow
```bash
# 1. Create production instance
./vai cm 2 "RTX 4090" provision_test_1.sh

# 2. Execute multiple workflows
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json ./input1.png "scene 1 description"
./vai exec 26003629 wan2-2-I2V-FP8-Lightning.json ./input2.png "scene 2 description"
```

## Troubleshooting

### Common Issues

**Command not found:**
```bash
# Make sure you're in the project directory
cd /home/ballsac/wsl-cursor-projects/vastai
./vai help
```

**SSH connection fails:**
```bash
# Verify your SSH key is set up correctly
ls ~/.ssh/id_ed25519_vastai

# Check Vast.ai API key
echo $VAST_API_KEY
```

**Instance creation fails:**
```bash
# Verify your Vast.ai API key and account balance
./vai cm 0  # Try with index 0 first
```

### Getting Help

- Use `./vai <command> --help` for detailed command help
- Check the logs directory: `SCRIPTS/logs/comfyui_jobs/`
- View recent job logs: Check the generated log files for execution details

## File Structure

```
vastai/
├── vai                           # Main command script
├── TEMPLATES/                    # Template files
│   ├── images/                  # Sample images
│   ├── provisioning_scripts/    # Instance setup scripts
│   └── workflows/              # Workflow templates
├── SCRIPTS/                     # All automation scripts
│   └── python_scripts/
│       └── workflows/          # Primary workflow scripts
│           ├── create_and_monitor.py
│           ├── execute_workflow.py
│           └── supplement/     # Legacy scripts
└── VAI_USAGE.md               # This file
```

## Next Steps

1. **Set up environment variables** (VAST_API_KEY)
2. **Try the basic workflow:** `./vai cm` → `./vai exec ...`
3. **Customize for your needs** with different GPUs and provisioning scripts
4. **Monitor your jobs** using the provided log files and monitoring tools

Happy generating! 🚀