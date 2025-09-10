# Vast.ai Tools

Tools and scripts for managing vast.ai GPU instances, including provisioning scripts, CLI templates, and Python automation tools.

## Quick Start

### Prerequisites
- Python 3.8+
- Poetry (recommended) or pip
- vast.ai CLI installed and configured
- vast.ai API key

### Installation

#### Option 1: Using Poetry (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd vastai

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# VAST_API_KEY=your_api_key_here
```

#### Option 2: Using pip
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your API key
```

### Getting Your API Key
1. Go to https://console.vast.ai/
2. Click on "API Keys" in your account settings
3. Create a new API key
4. Add it to your `.env` file

## Usage

### Python Scripts

#### Search for GPU Offers
```bash
# Using Poetry
poetry run python python_scripts/search_offers.py

# Or use the shortcut
poetry run search-offers

# Using pip/direct Python
python python_scripts/search_offers.py
```

#### Simple CLI Wrapper
```bash
poetry run python python_scripts/search_offers_simple.py
```

### CLI Templates

Navigate to `vastai_cli_template/ssh/` for various CLI command templates:

- `example_cli_command.txt` - Basic template
- `example_cli_command_fix.txt` - Single env string format (Linux/Mac)
- `example_cli_command_fix_double_quotes.txt` - Windows compatible

#### Example Usage
```bash
# Replace <OFFER_ID> with actual offer ID from search results
vastai create instance <OFFER_ID> --image vastai/comfy:@vastai-automatic-tag --args "-p 1111:1111 -p 8080:8080 -p 8384:8384 -p 72299:72299 -p 8188:8188" --env "OPEN_BUTTON_PORT=1111" --env "OPEN_BUTTON_TOKEN=1" --env "JUPYTER_DIR=/" --env "DATA_DIRECTORY=/workspace/" --env "PORTAL_CONFIG=localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing" --env "PROVISIONING_SCRIPT=https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/provisioning_scripts/provision_test_1.sh" --env "COMFYUI_ARGS=--disable-auto-launch --port 18188 --enable-cors-header --use-sage-attention" --onstart-cmd "entrypoint.sh" --disk 48 --ssh --direct
```

### Provisioning Scripts

The `provisioning_scripts/` folder contains setup scripts that run on instance startup:

- `provision_test_1.sh` - ComfyUI setup with Triton and SageAttention

#### Features:
- Installs performance optimizations (Triton, SageAttention)
- Downloads ComfyUI custom nodes
- Sets up text encoders and diffusion models
- Configures workflows automatically

### GPU Selection

Use the search criteria in `docs/vastai_gpu.md` to find optimal GPUs:

```bash
# High-end GPUs (40GB+ VRAM)
vastai search offers "gpu_ram>=40 dph<0.4 total_flops>=80 num_gpus=1 inet_up>100 inet_down>100" -o "dph,gpu_ram"

# Mid-range GPUs (21GB+ VRAM)  
vastai search offers "gpu_ram>=21 dph<0.4 total_flops>=100 num_gpus=1 inet_up>100 inet_down>100" -o "dph,gpu_ram"
```

## Access Your Instance

Once your instance is running:

1. **Get instance details:**
   ```bash
   vastai show instances
   ```

2. **Access via web:**
   - Instance Portal: `http://<instance-ip>:1111`
   - ComfyUI: `http://<instance-ip>:8188`
   - Jupyter: `http://<instance-ip>:8080`

3. **Access via SSH:**
   ```bash
   ssh root@<instance-ip>
   ```

## Development

### Poetry Commands
```bash
# Activate shell
poetry shell

# Add dependencies
poetry add package-name

# Run tests
poetry run pytest

# Format code
poetry run black python_scripts/

# Lint code  
poetry run flake8 python_scripts/
```

### File Structure
```
vastai/
├── docs/                           # Documentation
│   ├── vastai_flow.md             # Workflow guide
│   └── vastai_gpu.md              # GPU selection guide
├── provisioning_scripts/          # Instance setup scripts
│   └── provision_test_1.sh       # ComfyUI provisioning
├── python_scripts/               # Python automation tools
│   ├── search_offers.py          # API-based offer search
│   └── search_offers_simple.py   # CLI wrapper approach
├── template_workflows/           # ComfyUI workflows
├── vastai_cli_template/         # CLI command templates
│   └── ssh/                     # SSH instance templates
├── .env.example                 # Environment template
├── pyproject.toml              # Poetry configuration
└── README.md                   # This file
```

## Troubleshooting

### Common Issues

1. **"No configuration found in YAML"**
   - Check your provisioning script URL is accessible
   - Ensure environment variables are properly quoted

2. **"Unknown flag" warnings**
   - Use the correct CLI template for your OS
   - Windows: Use double quotes template
   - Linux/Mac: Use single quotes template

3. **API Authentication Errors**
   - Verify your API key in `.env`
   - Check `vastai show user` works

4. **Instance won't start services**
   - Check provisioning logs: `/var/log/portal/provisioning.log`
   - Verify all URLs in provisioning script are accessible

### Getting Help
- Check the vast.ai documentation: https://docs.vast.ai/
- Review instance logs in the vast.ai console
- Use `vastai show instances` to check instance status

## License

This project is licensed under the MIT License.