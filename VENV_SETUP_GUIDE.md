# Virtual Environment Setup Guide for Kokoro-FastAPI

## 🎯 **Quick Start Commands**

You've already created the virtual environment with:
```bash
python -m venv kokoro
```

Now follow these steps:

### **1. Activate the Virtual Environment**
```bash
# Activate (run this every time you want to work on the project)
source kokoro/bin/activate

# You should see (kokoro) at the start of your prompt
(kokoro) ~/kami/Kokoro-FastAPI »
```

### **2. Upgrade pip (recommended)**
```bash
pip install --upgrade pip
```

### **3. Install the Project Dependencies**

Choose one of these installation methods:

#### **Option A: CPU-only Installation (lighter, works everywhere)**
```bash
pip install -e ".[cpu]"
```

#### **Option B: GPU Installation (if you have NVIDIA GPU)**
```bash
pip install -e ".[gpu]"
```

#### **Option C: Development Installation (includes all extras)**
```bash
pip install -e ".[cpu,dev]"  # or .[gpu,dev] for GPU
```

### **4. Install Additional GPU Monitoring Dependencies**
```bash
# For enhanced GPU monitoring (optional)
pip install gputil nvidia-ml-py3
```

### **5. Verify Installation**
```bash
# Check if main dependencies are installed
python -c "import fastapi; print('FastAPI installed')"
python -c "import torch; print('PyTorch installed')"
python -c "import loguru; print('Loguru installed')"

# Test the enhanced logging
python -c "from api.src.services.gpu_monitor import get_gpu_monitor; print('GPU monitor available')"
```

## 🔧 **Working with the Virtual Environment**

### **Daily Usage**
```bash
# 1. Navigate to project directory
cd /Users/nickwei/kami/Kokoro-FastAPI

# 2. Activate virtual environment
source kokoro/bin/activate

# 3. Run the application
python -m api.src.main
# or
uvicorn api.src.main:app --reload --host 0.0.0.0 --port 8880
```

### **Deactivate When Done**
```bash
deactivate
```

### **Check What's Installed**
```bash
pip list
pip show kokoro-fastapi
```

## 🚀 **Test the Enhanced Logging**

Once installed, you can test the new logging features:

```bash
# Start the server
python -m api.src.main

# In another terminal, test the logging
python test_logging.py

# Test GPU monitoring (if available)
python test_gpu_monitoring.py

# Check GPU stats endpoint
curl http://localhost:8880/debug/gpu
```

## 📝 **Environment Variables**

Create a `.env` file in the project root:
```bash
# Logging configuration
LOG_REQUESTS=true
LOG_REQUEST_BODIES=true
LOG_USER_AGENTS=true
LOG_GPU_STATS=true
LOG_GPU_ON_REQUESTS=false
GPU_STATS_INTERVAL=30

# Server configuration
HOST=0.0.0.0
PORT=8880
```

## 🛠️ **Troubleshooting**

### **If installation fails:**
```bash
# Update pip and try again
pip install --upgrade pip setuptools wheel
pip install -e ".[cpu]"
```

### **If GPU monitoring doesn't work:**
```bash
# Check if NVIDIA drivers are available
nvidia-smi

# Install GPU monitoring libraries
pip install gputil nvidia-ml-py3
```

### **If you get import errors:**
```bash
# Make sure you're in the virtual environment
source kokoro/bin/activate

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall in development mode
pip install -e .
```

## 🎉 **You're Ready!**

Your virtual environment is now set up with:
- ✅ Enhanced request logging with unique request IDs
- ✅ Concurrent request handling
- ✅ GPU monitoring and logging
- ✅ Configurable logging levels
- ✅ Request body sanitization
- ✅ Performance timing categories

The enhanced logging will provide detailed insights into:
- 🔄 Every incoming request with correlation IDs
- ⏱️ Processing times with performance categories
- 🖥️ GPU utilization during TTS operations
- 📊 System resource monitoring
- 🎯 Request/response correlation for debugging
