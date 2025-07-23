# Docker Build Fix Guide

## 🚨 **The Problem**
The error "couldn't find a bake definition" occurs because:
- The `docker buildx bake` command looks for `docker-bake.hcl` in the current directory
- The build script was running from `docker/` directory
- But `docker-bake.hcl` is in the project root directory

## ✅ **Solution Applied**
I've fixed the `docker/build.sh` script to change to the parent directory before running the bake command.

## 🚀 **How to Use the Fixed Build Script**

### **Option 1: Run from anywhere (recommended)**
```bash
# The script now works from any location
cd /Users/nickwei/kami/Kokoro-FastAPI
./docker/build.sh

# Or with a specific version
./docker/build.sh v1.2.3
```

### **Option 2: Run from docker directory**
```bash
cd /Users/nickwei/kami/Kokoro-FastAPI/docker
./build.sh
```

### **Option 3: Run from project root**
```bash
cd /Users/nickwei/kami/Kokoro-FastAPI
docker buildx bake --push
```

## 🐳 **Available Build Targets**

The `docker-bake.hcl` defines several targets:

### **Production Builds (multi-platform)**
```bash
# Build both CPU and GPU versions
VERSION=v1.0.0 docker buildx bake --push

# Build only CPU version
VERSION=v1.0.0 docker buildx bake cpu --push

# Build only GPU version  
VERSION=v1.0.0 docker buildx bake gpu --push
```

### **Development Builds (single platform, faster)**
```bash
# Build dev versions (faster, local only)
docker buildx bake dev

# Build only CPU dev version
docker buildx bake cpu-dev

# Build only GPU dev version
docker buildx bake gpu-dev
```

## 🛠️ **Troubleshooting**

### **If you still get bake definition errors:**

1. **Check if docker-bake.hcl exists:**
   ```bash
   ls -la /Users/nickwei/kami/Kokoro-FastAPI/docker-bake.hcl
   ```

2. **Run from the correct directory:**
   ```bash
   cd /Users/nickwei/kami/Kokoro-FastAPI
   pwd  # Should show the project root
   docker buildx bake --help
   ```

3. **Verify docker buildx is available:**
   ```bash
   docker buildx version
   docker buildx ls
   ```

### **If buildx is not available:**
```bash
# Install buildx plugin
docker buildx install

# Or use regular docker build for single platform
docker build -f docker/cpu/Dockerfile -t kokoro-fastapi-cpu .
docker build -f docker/gpu/Dockerfile -t kokoro-fastapi-gpu .
```

## 📋 **Build Script Options**

The enhanced build script now supports:

### **Basic Usage**
```bash
./docker/build.sh                    # Build with "latest" tag
./docker/build.sh v1.2.3            # Build with specific version
```

### **Environment Variables**
```bash
# Customize the build
REGISTRY=your-registry.com \
OWNER=your-username \
REPO=your-repo \
VERSION=v1.0.0 \
./docker/build.sh
```

### **Local Development**
```bash
# For faster local builds (no push, single platform)
cd /Users/nickwei/kami/Kokoro-FastAPI
docker buildx bake dev --load
```

## 🎯 **What the Fixed Script Does**

1. **Changes to project root**: `cd "$(dirname "$0")/.."`
2. **Finds docker-bake.hcl**: Now in the correct directory
3. **Builds both images**: CPU and GPU versions
4. **Pushes to registry**: Multi-platform builds
5. **Shows progress**: Clear status messages

## 🚀 **Expected Output**
```bash
$ ./docker/build.sh v1.0.0
Building CPU and GPU images...
[+] Building 45.2s (23/23) FINISHED
 => [cpu internal] load build definition from Dockerfile
 => [gpu internal] load build definition from Dockerfile
 => => transferring dockerfile: 1.23kB
 => [cpu internal] load .dockerignore
 => [gpu internal] load .dockerignore
 ...
Build complete!
Created images with version: v1.0.0
```

Your Docker build should now work correctly! 🎉
