#!/bin/bash
# triton + sage_attention
# reference guide: https://www.nextdiffusion.ai/tutorials/fast-image-to-video-comfyui-wan2-2-lightx2v-lora

source /venv/main/bin/activate
COMFYUI_DIR=${WORKSPACE}/ComfyUI

# GitHub configuration - use environment variables or defaults
GITHUB_USER=${GITHUB_USER:-"jiso007"}
GITHUB_BRANCH=${GITHUB_BRANCH:-"main"}

# Packages are installed after nodes so we can fix them...

APT_PACKAGES=(
    "python3"
    "python3-venv"
    "python3-pip"
)

PIP_PACKAGES=(
    "triton>=3.0.0"
    "sageattention==1.0.6"
    "huggingface_hub"
    "hf-transfer"
)

NODES=(
    "https://github.com/pythongosssss/ComfyUI-Custom-Scripts"
    "https://github.com/rgthree/rgthree-comfy"
    "https://github.com/chrisgoringe/cg-use-everywhere"
    "https://github.com/orssorbit/ComfyUI-wanBlockswap"
    "https://github.com/PGCRT/CRT-Nodes"
)

WORKFLOWS=(
    "https://raw.githubusercontent.com/${GITHUB_USER}/vastai/refs/heads/${GITHUB_BRANCH}/TEMPLATES/1_workflows/test2.json"
)

INPUT=(
)

CHECKPOINT_MODELS=(
)

CLIP_MODELS=(
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
)

UNET_MODELS=(
)

LORA_MODELS=(
    "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
    "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
)

VAE_MODELS=(
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"
)

ESRGAN_MODELS=(
)

CONTROLNET_MODELS=(
)

TEXT_ENCODER_MODELS=(
)

DIFFUSION_MODELS=(
)

### DO NOT EDIT BELOW HERE UNLESS YOU KNOW WHAT YOU ARE DOING ###

function provisioning_start() {
    provisioning_print_header
    provisioning_get_apt_packages
    provisioning_get_pip_packages
    provisioning_setup_hf_transfer
    provisioning_update_comfyui
    provisioning_get_nodes
    workflows_dir="${COMFYUI_DIR}/user/default/workflows"
    mkdir -p "${workflows_dir}"
    provisioning_get_files \
        "${workflows_dir}" \
        "${WORKFLOWS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/input" \
        "${INPUT[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/checkpoints" \
        "${CHECKPOINT_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/unet" \
        "${UNET_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/loras" \
        "${LORA_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/controlnet" \
        "${CONTROLNET_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/clip" \
        "${CLIP_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/vae" \
        "${VAE_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/esrgan" \
        "${ESRGAN_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/text_encoders" \
        "${TEXT_ENCODER_MODELS[@]}"
    provisioning_get_files \
        "${COMFYUI_DIR}/models/diffusion_models" \
        "${DIFFUSION_MODELS[@]}"
    provisioning_print_end
}

function provisioning_get_apt_packages() {
    if [[ -n $APT_PACKAGES ]]; then
            sudo apt-get update && sudo apt-get install -y ${APT_PACKAGES[@]}
    fi
}

function provisioning_setup_hf_transfer() {
    export HF_HUB_ENABLE_HF_TRANSFER=1
    echo "HF Transfer enabled for faster downloads"
}

function provisioning_get_pip_packages() {
    if [[ -n $PIP_PACKAGES ]]; then
            pip install --no-cache-dir ${PIP_PACKAGES[@]}
    fi
}

# We must be at release tag v0.3.34 or greater for fp8 support
provisioning_update_comfyui() {
    required_tag="v0.3.34"
    cd ${COMFYUI_DIR}
    git fetch --all --tags
    current_commit=$(git rev-parse HEAD)
    required_commit=$(git rev-parse "$required_tag")
    if git merge-base --is-ancestor "$current_commit" "$required_commit"; then
        git checkout "$required_tag"
        pip install --no-cache-dir -r requirements.txt
    fi
}

function provisioning_get_nodes() {
    for repo in "${NODES[@]}"; do
        dir="${repo##*/}"
        path="${COMFYUI_DIR}/custom_nodes/${dir}"
        requirements="${path}/requirements.txt"
        if [[ -d $path ]]; then
            if [[ ${AUTO_UPDATE,,} != "false" ]]; then
                printf "Updating node: %s...\n" "${repo}"
                ( cd "$path" && git pull )
                if [[ -e $requirements ]]; then
                   pip install --no-cache-dir -r "$requirements"
                fi
            fi
        else
            printf "Downloading node: %s...\n" "${repo}"
            git clone "${repo}" "${path}" --recursive
            if [[ -e $requirements ]]; then
                pip install --no-cache-dir -r "${requirements}"
            fi
        fi
    done
}

function provisioning_get_files() {
    if [[ -z $2 ]]; then return 1; fi
    
    dir="$1"
    mkdir -p "$dir"
    shift
    arr=("$@")
    printf "Downloading %s model(s) to %s...\n" "${#arr[@]}" "$dir"
    for url in "${arr[@]}"; do
        printf "Downloading: %s\n" "${url}"
        provisioning_download "${url}" "${dir}"
        printf "\n"
    done
}

function provisioning_print_header() {
    printf "\n##############################################\n#                                            #\n#          Provisioning container            #\n#                                            #\n#         This will take some time           #\n#                                            #\n# Your container will be ready on completion #\n#                                            #\n##############################################\n\n"
}

function provisioning_print_end() {
    printf "\nProvisioning complete:  Application will start now\n\n"
}

function provisioning_has_valid_hf_token() {
    [[ -n "$HF_TOKEN" ]] || return 1
    url="https://huggingface.co/api/whoami-v2"

    response=$(curl -o /dev/null -s -w "%{http_code}" -X GET "$url" \
        -H "Authorization: Bearer $HF_TOKEN" \
        -H "Content-Type: application/json")

    # Check if the token is valid
    if [ "$response" -eq 200 ]; then
        return 0
    else
        return 1
    fi
}

function provisioning_has_valid_civitai_token() {
    [[ -n "$CIVITAI_TOKEN" ]] || return 1
    url="https://civitai.com/api/v1/models?hidden=1&limit=1"

    response=$(curl -o /dev/null -s -w "%{http_code}" -X GET "$url" \
        -H "Authorization: Bearer $CIVITAI_TOKEN" \
        -H "Content-Type: application/json")

    # Check if the token is valid
    if [ "$response" -eq 200 ]; then
        return 0
    else
        return 1
    fi
}

# Download from $1 URL to $2 file path
function provisioning_download() {
    local url="$1"
    local target_dir="$2"
    
    # Check if this is a Hugging Face URL
    if [[ $url =~ ^https://huggingface\.co/([^/]+)/([^/]+)/resolve/[^/]+/(.+)$ ]]; then
        local org_or_user="${BASH_REMATCH[1]}"
        local repo="${BASH_REMATCH[2]}"
        local file_path="${BASH_REMATCH[3]}"
        
        local repo_id="${org_or_user}/${repo}"
        local filename=$(basename "$file_path")
        
        echo "Using HF Transfer for faster download..."
        echo "Repository: $repo_id"
        echo "File: $file_path"
        
        # Ensure HF Transfer is enabled
        export HF_HUB_ENABLE_HF_TRANSFER=1
        
        # Use Python to download via huggingface_hub with hf_transfer
        python - <<EOF
import os
import sys
import shutil

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("✗ Error: huggingface_hub not installed. Please ensure pip packages are installed.", file=sys.stderr)
    sys.exit(1)

import time

# Enable HF Transfer
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '1'

# Set token if available
hf_token = os.environ.get('HF_TOKEN', '')

try:
    # Start timing
    start_time = time.time()
    
    # Download file (cached internally)
    print(f"Downloading with HF Transfer...")
    cached_file = hf_hub_download(
        repo_id="$repo_id",
        filename="$file_path",
        token=hf_token if hf_token else None,
        force_download=False
    )
    
    # Copy to target directory
    target_path = os.path.join("$target_dir", "$filename")
    os.makedirs("$target_dir", exist_ok=True)
    shutil.copy2(cached_file, target_path)
    
    # Calculate download time
    elapsed = time.time() - start_time
    file_size = os.path.getsize(target_path) / (1024*1024)  # MB
    speed = file_size / elapsed if elapsed > 0 else 0
    
    print(f"✓ Downloaded to: {target_path}")
    print(f"  Size: {file_size:.1f} MB | Time: {elapsed:.1f}s | Speed: {speed:.1f} MB/s")
    
except Exception as e:
    print(f"✗ Error downloading: {e}", file=sys.stderr)
    sys.exit(1)
EOF
        # Check if the download succeeded
        if [ $? -ne 0 ]; then
            echo "Failed to download using HF Transfer, falling back to wget..."
            wget -qnc --content-disposition --show-progress -e dotbytes="4M" -P "$target_dir" "$url"
        fi
        
    elif [[ -n $CIVITAI_TOKEN && $url =~ ^https://([a-zA-Z0-9_-]+\.)?civitai\.com(/|$|\?) ]]; then
        # Use curl for Civitai with Authorization header
        echo "Using curl for Civitai download with API key..."
        
        # Extract filename from Content-Disposition header or URL
        local temp_header_file=$(mktemp)
        local filename=""
        
        # First, get headers to determine filename
        curl -L -I -H "Authorization: Bearer $CIVITAI_TOKEN" "$url" > "$temp_header_file" 2>/dev/null
        
        # Try to extract filename from Content-Disposition header
        if grep -qi "content-disposition" "$temp_header_file"; then
            filename=$(grep -i "content-disposition" "$temp_header_file" | sed -n 's/.*filename[*]*=["]*\([^";]*\).*/\1/p' | tr -d '\r\n')
        fi
        
        # Fallback: extract from URL or use generic name
        if [[ -z "$filename" ]]; then
            if [[ $url =~ \?.*$ ]]; then
                # URL has query params, extract model ID and create filename
                model_id=$(echo "$url" | sed -n 's/.*models\/\([0-9]*\).*/\1/p')
                filename="civitai_model_${model_id}.safetensors"
            else
                filename=$(basename "$url")
            fi
        fi
        
        # Clean filename (remove any invalid characters)
        filename=$(echo "$filename" | sed 's/[^a-zA-Z0-9._-]/_/g')
        
        local target_path="$target_dir/$filename"
        
        echo "Downloading to: $target_path"
        
        # Download with curl
        curl -L -H "Authorization: Bearer $CIVITAI_TOKEN" \
             --progress-bar \
             -o "$target_path" \
             "$url"
        
        # Clean up temp file
        rm -f "$temp_header_file"
        
        # Show download result
        if [[ -f "$target_path" ]]; then
            local file_size=$(du -h "$target_path" | cut -f1)
            echo "✓ Downloaded: $filename ($file_size)"
        else
            echo "✗ Download failed for: $url"
            return 1
        fi
    else
        # Fall back to wget for other URLs
        wget -qnc --content-disposition --show-progress -e dotbytes="4M" -P "$target_dir" "$url"
    fi
}

# Allow user to disable provisioning if they started with a script they didn't want
if [[ ! -f /.noprovisioning ]]; then
    provisioning_start
fi