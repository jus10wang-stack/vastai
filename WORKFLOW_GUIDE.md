# ComfyUI Workflow Guide

This guide walks through the complete workflow from creating a ComfyUI workflow to running it on Vast.ai instances.

## 📋 Phase 1: Prepare Your Workflow

### 1️⃣ Create your workflow in ComfyUI
- Design and test locally
- Export as `workflow.json`
- Place in `TEMPLATES/1_workflows/`

### 2️⃣ Create provisioning script
- Copy template: `TEMPLATES/2_provisioning_scripts/template.sh`
- Rename to match workflow: `workflow.sh`
- Update script with required models

### 3️⃣ Analyze workflow requirements
```bash
vai workflow analyze workflow.json
```
- Reviews nodes and dependencies
- Identifies required models
- Runs `vai calculate` automatically

### 4️⃣ Calculate disk requirements
```bash
vai calculate workflow.sh --update-configs
```
- Scans all model downloads
- Calculates total disk usage
- Updates all config files

### 5️⃣ Create user-friendly config
- Edit `workflow-user_friendly.json`
- Set prompt placeholders
- Configure image inputs
- Adjust parameters

## ⚡ Phase 2: Run Your Workflow

### Option A: Manual control
```bash
vai create workflow.json         # Create & provision
vai exec 12345 workflow.json     # Execute workflow
vai extract 12345 content        # Download results
vai destroy 12345                # Clean up
```

### Option B: One command
```bash
vai oneshot workflow.json        # All steps automated
vai oneshot workflow.json --destroy  # + auto cleanup
```

## 📁 File Structure

```
TEMPLATES/
├── workflows/
│   └── workflow.json              # ComfyUI workflow
├── provisioning_scripts/
│   └── workflow.sh                # Model downloads
├── configs/
│   ├── workflow.json              # Auto-generated
│   └── workflow-user_friendly.json # User inputs
├── prompts/
│   └── prompt.txt                 # Text prompts
└── images/
    └── input.png                  # Input images
```

## 💡 Tips

- Use descriptive names: `sdxl-portrait-upscale.json`
- Test workflows locally before deploying
- Keep provisioning scripts minimal
- Use `--update-configs` to sync disk sizes
- Check logs in `SCRIPTS/logs/` for debugging

## 📊 Workflow Example

Let's walk through a real example:

1. **Export workflow**: Save ComfyUI workflow as `wan2-i2v-lightning.json`

2. **Create provisioning script**: `wan2-i2v-lightning.sh`
   ```bash
   wget -P models/diffusion_models/ \
     "https://huggingface.co/nyanko7/wan/resolve/main/wan_fp16.safetensors"
   wget -P models/vae/ \
     "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors"
   ```

3. **Analyze workflow**:
   ```bash
   vai workflow analyze wan2-i2v-lightning.json
   ```

4. **Update configs**:
   ```bash
   vai calculate wan2-i2v-lightning.sh --update-configs
   ```

5. **Configure inputs**: Edit `wan2-i2v-lightning-user_friendly.json`:
   ```json
   {
     "workflow_name": "wan2-i2v-lightning",
     "node_modifications": {
       "6": {
         "inputs": {
           "text": "TEMPLATES/5_prompts/sample-prompt.txt"
         }
       },
       "62": {
         "inputs": {
           "image": "TEMPLATES/4_images/test-image.png"
         }
       }
     }
   }
   ```

6. **Run workflow**:
   ```bash
   vai oneshot wan2-i2v-lightning-user_friendly.json --destroy
   ```

## 🔍 Monitoring & Logs

- **Startup logs**: `SCRIPTS/logs/startup/`
- **Job logs**: `SCRIPTS/logs/comfyui_jobs/`
- **Instance status**: `vai list`
- **Job status**: `vai cancel <instance> --list`

## 🎯 Common Use Cases

### Image-to-Video
```bash
vai oneshot i2v-workflow.json --destroy
```

### Batch Processing
```bash
for config in TEMPLATES/3_configs/*-user_friendly.json; do
  vai oneshot "$config" --destroy
done
```

### Debug Failed Workflow
```bash
vai create debug-workflow.json
vai exec 12345 debug-workflow.json
# SSH in to debug
ssh -p 22222 root@ssh.vast.ai -L 8188:localhost:8188
```

For more help: `vai help <command>`