# Vast.ai GPU Selection Guide

This document outlines the optimal GPU configurations for running ComfyUI with video generation models on Vast.ai.

## Recommended GPU Configurations

### High-End Options (Preferred)

#### RTX 4090 / RTX 6000 Ada
**Specifications:**
- GPU RAM: ≥ 40GB
- Cost: ≤ $0.40/hour
- Performance: ≥ 80 TFLOPS

**Search Command:**
```bash
vastai search offers "gpu_ram>=40 dph<0.4 total_flops>=80 num_gpus=1" -o "dph,gpu_ram"
```

**Use Cases:**
- Large video generation models (Wan2.2, LTX Video)
- High-resolution outputs
- Complex workflows with multiple models loaded simultaneously

---

### Mid-Range Option

#### RTX 5090
**Specifications:**
- GPU RAM: ≥ 21GB
- Cost: ≤ $0.40/hour
- Performance: ≥ 100 TFLOPS

**Search Command:**
```bash
vastai search offers "gpu_ram>=21 dph<0.4 total_flops>=100 num_gpus=1" -o "dph,gpu_ram"
```

**Use Cases:**
- Standard video generation workflows
- Moderate resolution outputs
- Single model inference

## Selection Criteria Priority

1. **GPU RAM** - Most critical for loading large models
2. **Cost per Hour** - Budget optimization
3. **TFLOPS** - Processing speed and efficiency
4. **Availability** - Instance availability in your region

## Additional Considerations

### Model Requirements
- **Wan2.2 Models**: Require ~14-20GB VRAM
- **Text Encoders**: Additional 2-4GB VRAM
- **VAE Models**: Additional 1-2GB VRAM

### Performance Optimizations
- SageAttention: Reduces memory usage by ~30%
- FP8 Models: Half the memory footprint of FP16
- Triton: Optimized CUDA kernels for better performance

## Quick Reference Commands

```bash
# Search for high-end GPUs
vastai search offers "gpu_ram>=40 dph<0.4 total_flops>=80 num_gpus=1" -o "dph,gpu_ram"

# Search for mid-range GPUs
vastai search offers "gpu_ram>=21 dph<0.4 total_flops>=100 num_gpus=1" -o "dph,gpu_ram"

# Filter by specific GPU models
vastai search offers "gpu_name:RTX_4090 dph<0.5" -o "dph,gpu_ram"
```


