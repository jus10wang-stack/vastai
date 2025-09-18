#!/usr/bin/env python3
"""
Workflow Template Analyzer - Extract configurable parameters from ComfyUI workflows
and generate clean, editable configuration files.
"""

import sys
import os
import json
import argparse
from pathlib import Path

def extract_configurable_params(workflow_data):
    """Extract all configurable parameters from a workflow JSON."""
    config = {
        "workflow_name": "",
        "description": "",
        "input": {},
        "models": {},
        "sampling": {},
        "output": {},
        "advanced": {}
    }
    
    # Node type handlers - define what parameters to extract from each node type
    node_handlers = {
        "CLIPTextEncode": extract_text_encode_params,
        "LoadImage": extract_load_image_params,
        "KSamplerAdvanced": extract_sampler_params,
        "UNETLoader": extract_unet_params,
        "CLIPLoader": extract_clip_params,
        "VAELoader": extract_vae_params,
        "LoraLoaderModelOnly": extract_lora_params,
        "ModelSamplingSD3": extract_sampling_params,
        "WanImageToVideo": extract_video_params,
        "CreateVideo": extract_create_video_params,
        "SaveVideo": extract_save_video_params,
        "RIFE VFI": extract_interpolation_params
    }
    
    nodes = workflow_data.get("nodes", [])
    
    for node in nodes:
        node_type = node.get("type")
        node_id = node.get("id")
        node_title = node.get("title", f"Node {node_id}")
        
        if node_type in node_handlers:
            node_config = node_handlers[node_type](node)
            merge_node_config(config, node_config, node_type, node_title)
    
    return config

def extract_text_encode_params(node):
    """Extract parameters from CLIPTextEncode nodes (prompts)."""
    title = node.get("title", "")
    widgets_values = node.get("widgets_values", [])
    
    if "Positive" in title:
        return {"input": {"positive_prompt": widgets_values[0] if widgets_values else ""}}
    elif "Negative" in title:
        return {"input": {"negative_prompt": widgets_values[0] if widgets_values else ""}}
    
    return {}

def extract_load_image_params(node):
    """Extract parameters from LoadImage nodes."""
    widgets_values = node.get("widgets_values", [])
    return {"input": {"image": widgets_values[0] if widgets_values else "input.png"}}

def extract_sampler_params(node):
    """Extract sampling parameters from KSamplerAdvanced nodes."""
    title = node.get("title", "")
    widgets_values = node.get("widgets_values", [])
    
    if len(widgets_values) >= 10:
        stage_key = "stage1" if "1." in title else "stage2" if "2." in title else "default"
        
        return {"sampling": {stage_key: {
            "add_noise": widgets_values[0],
            "seed": widgets_values[1] if widgets_values[1] != "randomize" else "random",
            "seed_mode": widgets_values[2],
            "steps": widgets_values[3],
            "cfg": widgets_values[4],
            "sampler": widgets_values[5],
            "scheduler": widgets_values[6],
            "start_step": widgets_values[7],
            "end_step": widgets_values[8],
            "return_with_leftover_noise": widgets_values[9]
        }}}
    
    return {}

def extract_unet_params(node):
    """Extract UNET model parameters."""
    widgets_values = node.get("widgets_values", [])
    model_name = widgets_values[0] if widgets_values else ""
    weight_dtype = widgets_values[1] if len(widgets_values) > 1 else "fp8_e4m3fn"
    
    # Determine if this is high or low noise model
    model_key = "unet_high" if "high_noise" in model_name else "unet_low" if "low_noise" in model_name else "unet"
    
    return {"models": {model_key: {"name": model_name, "dtype": weight_dtype}}}

def extract_clip_params(node):
    """Extract CLIP model parameters."""
    widgets_values = node.get("widgets_values", [])
    if widgets_values:
        return {"models": {"clip": {
            "name": widgets_values[0],
            "type": widgets_values[1] if len(widgets_values) > 1 else "wan",
            "device": widgets_values[2] if len(widgets_values) > 2 else "default"
        }}}
    return {}

def extract_vae_params(node):
    """Extract VAE model parameters."""
    widgets_values = node.get("widgets_values", [])
    return {"models": {"vae": widgets_values[0] if widgets_values else ""}}

def extract_lora_params(node):
    """Extract LoRA parameters."""
    widgets_values = node.get("widgets_values", [])
    if widgets_values:
        lora_name = widgets_values[0]
        strength = widgets_values[1] if len(widgets_values) > 1 else 1.0
        
        # Determine if this is high or low LoRA
        lora_key = "lora_high" if "HIGH" in lora_name else "lora_low" if "LOW" in lora_name else "lora"
        
        return {"models": {lora_key: {"name": lora_name, "strength": strength}}}
    return {}

def extract_sampling_params(node):
    """Extract model sampling parameters."""
    widgets_values = node.get("widgets_values", [])
    return {"advanced": {"model_sampling_shift": widgets_values[0] if widgets_values else 8.0}}

def extract_video_params(node):
    """Extract video generation parameters from WanImageToVideo."""
    widgets_values = node.get("widgets_values", [])
    if len(widgets_values) >= 4:
        return {"video_settings": {
            "width": widgets_values[0],
            "height": widgets_values[1],
            "length": widgets_values[2],
            "batch_size": widgets_values[3]
        }}
    return {}

def extract_create_video_params(node):
    """Extract video creation parameters."""
    widgets_values = node.get("widgets_values", [])
    return {"video_settings": {"fps": widgets_values[0] if widgets_values else 16}}

def extract_save_video_params(node):
    """Extract video save parameters."""
    widgets_values = node.get("widgets_values", [])
    if len(widgets_values) >= 3:
        return {"output": {
            "filename_prefix": widgets_values[0],
            "format": widgets_values[1],
            "codec": widgets_values[2]
        }}
    return {}

def extract_interpolation_params(node):
    """Extract frame interpolation parameters."""
    widgets_values = node.get("widgets_values", [])
    if len(widgets_values) >= 6:
        return {"interpolation": {
            "enabled": True,
            "model": widgets_values[0],
            "clear_cache_frames": widgets_values[1],
            "multiplier": widgets_values[2],
            "fast_mode": widgets_values[3],
            "ensemble": widgets_values[4],
            "scale_factor": widgets_values[5]
        }}
    return {}

def merge_node_config(main_config, node_config, node_type, node_title):
    """Merge a node's configuration into the main config."""
    for section, values in node_config.items():
        if section not in main_config:
            main_config[section] = {}
        
        if isinstance(values, dict):
            main_config[section].update(values)
        else:
            main_config[section] = values

def generate_config_template(workflow_path):
    """Generate a clean configuration template from a workflow JSON."""
    print(f"🔍 Analyzing workflow: {workflow_path}")
    
    with open(workflow_path, 'r') as f:
        workflow_data = json.load(f)
    
    # Extract workflow name from filename
    workflow_name = Path(workflow_path).stem
    
    # Extract configurable parameters
    config = extract_configurable_params(workflow_data)
    config["workflow_name"] = workflow_name
    config["description"] = f"Configuration for {workflow_name} workflow"
    
    # Clean up empty sections
    config = {k: v for k, v in config.items() if v}
    
    return config

def save_config_template(config, output_path):
    """Save the configuration template to a file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration template saved: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Analyze ComfyUI workflow and generate configuration template")
    parser.add_argument("workflow_file", help="Path to workflow JSON file")
    parser.add_argument("--output", "-o", help="Output path for config template (auto-generated if not specified)")
    parser.add_argument("--pretty", "-p", action="store_true", help="Pretty print the configuration to console")
    
    args = parser.parse_args()
    
    workflow_path = args.workflow_file
    
    if not os.path.exists(workflow_path):
        print(f"❌ Workflow file not found: {workflow_path}")
        sys.exit(1)
    
    try:
        # Generate configuration template
        config = generate_config_template(workflow_path)
        
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            # Auto-generate output path in TEMPLATES/configs/
            workflow_name = Path(workflow_path).stem
            script_dir = Path(__file__).parent.parent.parent.parent  # Get to project root
            output_path = script_dir / "TEMPLATES" / "configs" / f"{workflow_name}.json"
        
        # Save configuration template
        save_config_template(config, output_path)
        
        # Pretty print if requested
        if args.pretty:
            print("\n📋 Generated Configuration Template:")
            print("=" * 50)
            print(json.dumps(config, indent=2))
        
        print(f"\n💡 Usage:")
        print(f"1. Edit the config file: {output_path}")
        print(f"2. Run: python execute_workflow_config.py <instance_id> {Path(output_path).name}")
        
    except Exception as e:
        print(f"❌ Error analyzing workflow: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()