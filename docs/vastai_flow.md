# Vast.ai Workflow

This document outlines the complete workflow for deploying and managing ComfyUI instances on Vast.ai with custom provisioning.

## Prerequisites

### GitHub Setup
- [X] Create provisioning script in repository
- [X] Upload custom files for provisioning script ingestion:
  - [X] Workflows
  - [X] Models
  - [X] Configuration files

### Instance Discovery
- [ ] Script to find specific GPU offering that meets requirements

## Instance Deployment

### Instant CLI Method
The instant CLI method creates and configures instances through command-line interface:

1. **Create Instance**
   - [X] Deploy template with custom provisioning script
   - [X] Install performance optimizations:
     - [X] SageAttention for 8-bit attention
     - [X] Triton for custom CUDA kernels
   - [X] Load required models automatically

## Execution Methods

### API Method
This method keeps image/prompt/settings on local machine for reference and control.

**Process:**
1. [ ] Script checks if instance is ready
2. [ ] Execute API call with parameters:
   - [ ] Input image
   - [ ] Text prompt
   - [ ] Generation settings

**Advantages:**
- Local control of inputs
- Easy parameter modification
- Real-time status monitoring

### OnStart Method
This method embeds everything within the template, eliminating polling but requiring all assets in instance storage.

**Process:**
1. [ ] Execute API call with pre-loaded parameters:
   - [ ] Input image (stored in instance)
   - [ ] Text prompt (pre-configured)
   - [ ] Generation settings (template defaults)

**Advantages:**
- No polling required
- Faster execution
- Self-contained deployment

## Cleanup

### Post-Processing
1. [ ] Extract generated content to local storage
2. [ ] Download outputs and logs
3. [ ] Destroy instance and storage volume to minimize costs

## Workflow Summary

```mermaid
graph TD
    A[GitHub: Create Provisioning Script] --> B[GitHub: Upload Custom Files]
    B --> C[Script: Find GPU]
    C --> D[Script: Create Instance]
    D --> E[Install Dependencies]
    E --> F{Execution Method?}
    F -->|API Method| G[Poll Instance Status]
    F -->|OnStart Method| H[Direct Execution]
    G --> I[Execute API Call]
    H --> I
    I --> J[Extract Content]
    J --> K[Destroy Instance]
```

## Configuration Files

- **Provisioning Script**: `provisioning_scripts/provision_test_1.sh`
- **CLI Templates**: 
  - `vastai_cli_template/ssh/example_cli_command.txt` - Basic template
  - `vastai_cli_template/ssh/example_cli_command_fix.txt` - Single env string format
  - `vastai_cli_template/ssh/example_cli_command_fix_separate_env.txt` - Separate env flags
  - `vastai_cli_template/ssh/example_cli_command_fix_double_quotes.txt` - Windows compatible (recommended)
- **Workflows**: `template_workflows/`
