# GPU Monitoring and Logging

## Overview

The Kokoro FastAPI now includes comprehensive GPU monitoring and logging capabilities to help track GPU utilization, memory usage, temperature, and power consumption during TTS operations.

## Features

### 🖥️ **Multiple Monitoring Backends**

1. **NVML (nvidia-ml-py3)** - Most detailed (recommended)
   - GPU utilization percentage
   - Memory usage (used/total/percent)
   - Temperature monitoring
   - Power consumption and limits
   - Works with NVIDIA GPUs

2. **GPUtil** - Basic monitoring
   - GPU utilization and memory
   - Temperature (if available)
   - Cross-platform support

3. **PyTorch CUDA** - Fallback
   - Memory allocation tracking
   - Device information
   - No utilization metrics

### 📊 **Logging Capabilities**

#### **Periodic GPU Stats Logging**
```
02:45:30 PM | INFO     | gpu_monitor:123 | 🖥️ GPU 0 (NVIDIA GeForce RTX 4090) | Load: 45.2% | Memory: 8192MB/24576MB (33.3%) | Temp: 65°C | Power: 180.5W/450.0W
```

#### **Request-Level GPU Monitoring**
```
02:46:15 PM | INFO     | main:145 | ✅ [a1b2c3d4] POST /v1/audio/speech | Status: 200 | Time: 2.456s | GPU: 67.3% | Mem: 45.1% | Temp: 72°C | Power: 220.1W
```

#### **Manual GPU Stats Endpoint**
```json
GET /debug/gpu
{
  "timestamp": 1690891234.567,
  "gpu_count": 1,
  "gpus": [
    {
      "id": 0,
      "name": "NVIDIA GeForce RTX 4090",
      "utilization_percent": 45.2,
      "memory": {
        "used_mb": 8192.0,
        "total_mb": 24576.0,
        "percent": 33.3
      },
      "temperature_celsius": 65,
      "power_watts": 180.5,
      "power_limit_watts": 450.0
    }
  ]
}
```

## Configuration

### Environment Variables

```bash
# Enable/disable GPU stats logging
LOG_GPU_STATS=true

# Include GPU stats in request logs (for compute-intensive requests)
LOG_GPU_ON_REQUESTS=false

# Periodic logging interval in seconds (0 = disabled)
GPU_STATS_INTERVAL=30
```

### Settings in `core/config.py`

```python
class Settings(BaseSettings):
    # GPU Monitoring Settings
    log_gpu_stats: bool = True           # Whether to log GPU utilization stats
    log_gpu_on_requests: bool = False    # Whether to include GPU stats in request logs
    gpu_stats_interval: int = 30         # Interval in seconds to log GPU stats (0 = disabled)
```

## Installation Requirements

### For Full GPU Monitoring (NVIDIA GPUs)

```bash
# Install nvidia-ml-py3 for detailed monitoring
pip install nvidia-ml-py3

# Or install with GPU extras
pip install -e ".[gpu]"
```

### For Basic GPU Monitoring

```bash
# GPUtil provides basic cross-platform monitoring
pip install gputil
```

### Fallback (PyTorch only)

PyTorch CUDA support is included by default and provides basic memory tracking.

## Usage Examples

### 1. **Monitor GPU During TTS Operations**

```python
# Enable request-level GPU monitoring for TTS endpoints
LOG_GPU_ON_REQUESTS=true

# Make TTS request - GPU stats will be logged
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "kokoro", "input": "Hello world", "voice": "af_heart"}'

# Log output:
# ✅ [a1b2c3d4] POST /v1/audio/speech | Status: 200 | Time: 2.456s | GPU: 67.3% | Mem: 45.1%
```

### 2. **Get Current GPU Stats**

```bash
# Get detailed GPU information
curl http://localhost:8880/debug/gpu

# This also triggers logging of current stats
```

### 3. **Monitor GPU Over Time**

```bash
# Enable periodic logging every 15 seconds
GPU_STATS_INTERVAL=15

# Watch logs for periodic GPU stats:
# 🖥️ GPU 0 (NVIDIA GeForce RTX 4090) | Load: 23.1% | Memory: 4096MB/24576MB (16.7%) | Temp: 58°C
```

### 4. **Production Monitoring Setup**

```bash
# Recommended production settings
LOG_GPU_STATS=true           # Enable GPU monitoring
LOG_GPU_ON_REQUESTS=false    # Disable per-request logging (reduces overhead)
GPU_STATS_INTERVAL=60        # Log stats every minute
```

## Performance Considerations

### **Monitoring Overhead**

- **NVML calls**: ~1-2ms per GPU
- **GPUtil calls**: ~5-10ms per GPU  
- **PyTorch calls**: ~0.1ms per GPU

### **Caching**

The GPU monitor uses intelligent caching:
- Results cached for 1 second by default
- Reduces overhead during high request rates
- Can be bypassed for real-time monitoring

### **Request-Level Monitoring**

Only enabled for compute-intensive endpoints:
- `/v1/audio/speech` (TTS generation)
- `/dev/generate*` (Development endpoints)
- `/dev/captioned*` (Captioned speech)

## Troubleshooting

### **No GPU Detected**

```bash
# Check if NVIDIA drivers are installed
nvidia-smi

# Check if CUDA is available in PyTorch
python -c "import torch; print(torch.cuda.is_available())"

# Check if nvidia-ml-py3 is working
python -c "import nvidia_ml_py3 as nvml; nvml.nvmlInit()"
```

### **Permission Issues**

```bash
# Add user to video group (Linux)
sudo usermod -a -G video $USER

# Or run with appropriate permissions
```

### **Library Installation Issues**

```bash
# Install specific versions
pip install nvidia-ml-py3==12.535.77
pip install gputil==1.4.0

# Check library availability
python -c "
try:
    import nvidia_ml_py3; print('✅ NVML available')
except: print('❌ NVML not available')

try:
    import GPUtil; print('✅ GPUtil available')  
except: print('❌ GPUtil not available')
"
```

## Log Output Examples

### **Startup GPU Detection**

```
02:45:00 PM | INFO     | gpu_monitor:45 | 🖥️ GPU monitoring available: NVML (detailed), GPUtil (basic), PyTorch CUDA
02:45:00 PM | INFO     | main:185 | 🖥️ GPU stats logging enabled (every 30s)
02:45:01 PM | INFO     | gpu_monitor:123 | 🖥️ GPU 0 (NVIDIA GeForce RTX 4090) | Load: 0.0% | Memory: 1024MB/24576MB (4.2%) | Temp: 35°C | Power: 45.2W/450.0W
```

### **During TTS Generation**

```
# Request start
02:46:00 PM | INFO     | main:67 | 🔄 [a1b2c3d4] POST /v1/audio/speech | IP: 192.168.1.100

# Request completion (with GPU stats if enabled)
02:46:02 PM | INFO     | main:145 | ✅ [a1b2c3d4] POST /v1/audio/speech | Status: 200 | Time: 2.456s | GPU: 67.3% | Mem: 45.1% | Temp: 72°C | Power: 220.1W

# Periodic monitoring
02:46:30 PM | INFO     | gpu_monitor:123 | 🖥️ GPU 0 (NVIDIA GeForce RTX 4090) | Load: 12.5% | Memory: 6144MB/24576MB (25.0%) | Temp: 68°C | Power: 125.3W/450.0W
```

### **Multiple GPUs**

```
02:47:00 PM | INFO     | gpu_monitor:123 | 🖥️ GPU 0 (NVIDIA GeForce RTX 4090) | Load: 45.2% | Memory: 8192MB/24576MB (33.3%) | Temp: 65°C | Power: 180.5W/450.0W
02:47:00 PM | INFO     | gpu_monitor:123 | 🖥️ GPU 1 (NVIDIA GeForce RTX 4090) | Load: 23.1% | Memory: 4096MB/24576MB (16.7%) | Temp: 58°C | Power: 120.2W/450.0W

# Summary in request logs for multiple GPUs
02:47:30 PM | INFO     | main:145 | ✅ [b2c3d4e5] POST /v1/audio/speech | Status: 200 | Time: 1.234s | GPUs(2): Avg Load: 34.2% | Avg Mem: 25.0%
```

## Benefits

1. **🔍 Performance Monitoring**: Track GPU utilization during TTS operations
2. **🛡️ Resource Management**: Monitor memory usage to prevent OOM errors  
3. **🌡️ Thermal Monitoring**: Track GPU temperature for thermal throttling detection
4. **⚡ Power Monitoring**: Monitor power consumption and efficiency
5. **📊 Capacity Planning**: Historical data for scaling decisions
6. **🚨 Alerting**: Easy integration with monitoring systems

## Integration with Monitoring Systems

The structured logging format makes it easy to integrate with:
- **Prometheus + Grafana**: Parse logs for metrics visualization
- **ELK Stack**: Index GPU metrics in Elasticsearch
- **CloudWatch**: Stream logs to AWS CloudWatch
- **Custom Monitoring**: Parse structured log output

The GPU monitoring system provides comprehensive visibility into GPU resource usage, helping optimize performance and ensure reliable operation of the Kokoro TTS service! 🚀
