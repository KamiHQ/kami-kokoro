"""
GPU Monitoring Service for Kokoro FastAPI

Provides GPU utilization monitoring and logging capabilities.
"""

import time
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from loguru import logger
import torch

try:
    import GPUtil
    GPU_UTIL_AVAILABLE = True
except ImportError:
    GPU_UTIL_AVAILABLE = False

try:
    import nvidia_ml_py3 as nvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False


@dataclass
class GPUInfo:
    """GPU information data class"""
    id: int
    name: str
    load: float  # GPU utilization (0-1)
    memory_used: float  # MB
    memory_total: float  # MB
    memory_percent: float  # 0-100
    temperature: Optional[float] = None  # Celsius
    power_draw: Optional[float] = None  # Watts
    power_limit: Optional[float] = None  # Watts


class GPUMonitor:
    """GPU monitoring service with multiple backends"""
    
    def __init__(self):
        self.nvml_initialized = False
        self.last_check_time = 0
        self.cache_duration = 1.0  # Cache for 1 second to avoid excessive polling
        self._cached_info = None
        
        # Try to initialize NVML for detailed monitoring
        if NVML_AVAILABLE:
            try:
                nvml.nvmlInit()
                self.nvml_initialized = True
                logger.debug("🔧 NVML (nvidia-ml-py3) initialized for detailed GPU monitoring")
            except Exception as e:
                logger.debug(f"⚠️ NVML initialization failed: {e}")
        
        # Log available monitoring capabilities
        capabilities = []
        if self.nvml_initialized:
            capabilities.append("NVML (detailed)")
        if GPU_UTIL_AVAILABLE:
            capabilities.append("GPUtil (basic)")
        if torch.cuda.is_available():
            capabilities.append("PyTorch CUDA")
        
        if capabilities:
            logger.info(f"🖥️ GPU monitoring available: {', '.join(capabilities)}")
        else:
            logger.info("🖥️ No GPU monitoring libraries available")
    
    def get_gpu_info(self, use_cache: bool = True) -> List[GPUInfo]:
        """Get GPU information using available monitoring backends"""
        current_time = time.time()
        
        # Return cached data if recent enough
        if use_cache and self._cached_info and (current_time - self.last_check_time) < self.cache_duration:
            return self._cached_info
        
        gpu_info = []
        
        try:
            if self.nvml_initialized:
                gpu_info = self._get_nvml_info()
            elif GPU_UTIL_AVAILABLE:
                gpu_info = self._get_gputil_info()
            elif torch.cuda.is_available():
                gpu_info = self._get_torch_info()
        except Exception as e:
            logger.debug(f"⚠️ GPU monitoring error: {e}")
            return []
        
        # Cache the results
        self._cached_info = gpu_info
        self.last_check_time = current_time
        
        return gpu_info
    
    def _get_nvml_info(self) -> List[GPUInfo]:
        """Get detailed GPU info using NVML"""
        gpu_info = []
        device_count = nvml.nvmlDeviceGetCount()
        
        for i in range(device_count):
            handle = nvml.nvmlDeviceGetHandleByIndex(i)
            
            # Basic info
            name = nvml.nvmlDeviceGetName(handle).decode('utf-8')
            
            # Memory info
            mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
            memory_total = mem_info.total / (1024 * 1024)  # Convert to MB
            memory_used = mem_info.used / (1024 * 1024)
            memory_percent = (mem_info.used / mem_info.total) * 100
            
            # Utilization
            util = nvml.nvmlDeviceGetUtilizationRates(handle)
            load = util.gpu / 100.0  # Convert to 0-1 scale
            
            # Temperature
            try:
                temperature = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
            except:
                temperature = None
            
            # Power
            try:
                power_draw = nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to Watts
            except:
                power_draw = None
                
            try:
                power_limit = nvml.nvmlDeviceGetPowerManagementLimitConstraints(handle)[1] / 1000.0
            except:
                power_limit = None
            
            gpu_info.append(GPUInfo(
                id=i,
                name=name,
                load=load,
                memory_used=memory_used,
                memory_total=memory_total,
                memory_percent=memory_percent,
                temperature=temperature,
                power_draw=power_draw,
                power_limit=power_limit
            ))
        
        return gpu_info
    
    def _get_gputil_info(self) -> List[GPUInfo]:
        """Get basic GPU info using GPUtil"""
        gpu_info = []
        gpus = GPUtil.getGPUs()
        
        for gpu in gpus:
            gpu_info.append(GPUInfo(
                id=gpu.id,
                name=gpu.name,
                load=gpu.load,
                memory_used=gpu.memoryUsed,
                memory_total=gpu.memoryTotal,
                memory_percent=(gpu.memoryUsed / gpu.memoryTotal) * 100,
                temperature=gpu.temperature if hasattr(gpu, 'temperature') else None
            ))
        
        return gpu_info
    
    def _get_torch_info(self) -> List[GPUInfo]:
        """Get basic GPU info using PyTorch CUDA"""
        gpu_info = []
        
        if not torch.cuda.is_available():
            return gpu_info
        
        device_count = torch.cuda.device_count()
        
        for i in range(device_count):
            device = f"cuda:{i}"
            name = torch.cuda.get_device_name(i)
            
            # Memory info
            memory_allocated = torch.cuda.memory_allocated(device) / (1024 * 1024)  # MB
            memory_reserved = torch.cuda.memory_reserved(device) / (1024 * 1024)   # MB
            memory_total = torch.cuda.get_device_properties(device).total_memory / (1024 * 1024)  # MB
            
            # Use reserved memory as "used" since it's what PyTorch has allocated
            memory_used = memory_reserved
            memory_percent = (memory_used / memory_total) * 100
            
            gpu_info.append(GPUInfo(
                id=i,
                name=name,
                load=0.0,  # PyTorch doesn't provide utilization
                memory_used=memory_used,
                memory_total=memory_total,
                memory_percent=memory_percent
            ))
        
        return gpu_info
    
    def get_gpu_summary(self) -> Optional[str]:
        """Get a concise GPU summary for logging"""
        gpus = self.get_gpu_info()
        
        if not gpus:
            return None
        
        if len(gpus) == 1:
            gpu = gpus[0]
            parts = [f"GPU: {gpu.load*100:.1f}%"]
            parts.append(f"Mem: {gpu.memory_percent:.1f}%")
            if gpu.temperature:
                parts.append(f"Temp: {gpu.temperature}°C")
            if gpu.power_draw:
                parts.append(f"Power: {gpu.power_draw:.1f}W")
            return " | ".join(parts)
        else:
            # Multiple GPUs - show average stats
            avg_load = sum(g.load for g in gpus) / len(gpus) * 100
            avg_memory = sum(g.memory_percent for g in gpus) / len(gpus)
            return f"GPUs({len(gpus)}): Avg Load: {avg_load:.1f}% | Avg Mem: {avg_memory:.1f}%"
    
    def log_gpu_stats(self, level: str = "debug"):
        """Log detailed GPU statistics"""
        gpus = self.get_gpu_info()
        
        if not gpus:
            return
        
        log_func = getattr(logger, level, logger.debug)
        
        for gpu in gpus:
            parts = [f"🖥️ GPU {gpu.id} ({gpu.name})"]
            parts.append(f"Load: {gpu.load*100:.1f}%")
            parts.append(f"Memory: {gpu.memory_used:.0f}MB/{gpu.memory_total:.0f}MB ({gpu.memory_percent:.1f}%)")
            
            if gpu.temperature:
                parts.append(f"Temp: {gpu.temperature}°C")
            if gpu.power_draw:
                power_str = f"Power: {gpu.power_draw:.1f}W"
                if gpu.power_limit:
                    power_str += f"/{gpu.power_limit:.1f}W"
                parts.append(power_str)
            
            log_func(" | ".join(parts))


# Global GPU monitor instance
_gpu_monitor = None

def get_gpu_monitor() -> GPUMonitor:
    """Get the global GPU monitor instance"""
    global _gpu_monitor
    if _gpu_monitor is None:
        _gpu_monitor = GPUMonitor()
    return _gpu_monitor
