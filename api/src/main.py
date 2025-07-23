"""
FastAPI OpenAI Compatible API
"""

import os
import sys
import time
import uuid
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import settings
from .routers.debug import router as debug_router
from .routers.development import router as dev_router
from .routers.openai_compatible import router as openai_router
from .routers.web_player import router as web_router
from .services.gpu_monitor import get_gpu_monitor


async def periodic_gpu_monitoring():
    """Background task to periodically log GPU statistics"""
    if not settings.log_gpu_stats or settings.gpu_stats_interval <= 0:
        return
        
    gpu_monitor = get_gpu_monitor()
    
    while True:
        try:
            await asyncio.sleep(settings.gpu_stats_interval)
            gpu_monitor.log_gpu_stats(level="info")
        except asyncio.CancelledError:
            logger.debug("🖥️ GPU monitoring task cancelled")
            break
        except Exception as e:
            logger.error(f"🖥️ Error in GPU monitoring: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests and responses with improved concurrency support"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging if disabled
        if not settings.log_requests:
            return await call_next(request)
            
        # Generate unique request ID for correlation
        request_id = str(uuid.uuid4())[:8]
        
        # Record start time
        start_time = time.time()
        
        # Extract request information
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        content_type = request.headers.get("content-type", "")
        
        # Build log message with request ID
        log_parts = [f"🔄 [{request_id}] {method} {url}", f"IP: {client_ip}"]
        
        if settings.log_user_agents:
            truncated_ua = user_agent[:50] + ('...' if len(user_agent) > 50 else '')
            log_parts.append(f"User-Agent: {truncated_ua}")
        
        # Log the incoming request
        logger.info(" | ".join(log_parts))
        
        # Log request body for specific endpoints (be careful with large payloads)
        body_logged = False
        if (settings.log_request_bodies and 
            method in ["POST", "PUT", "PATCH"] and 
            any(endpoint in url for endpoint in ["/v1/audio/speech", "/dev/", "/debug/"])):
            try:
                # Read body if it's small enough and JSON
                if "application/json" in content_type:
                    # Create a copy of the request body to avoid consuming it
                    body = await request.body()
                    if len(body) < 1000:  # Only log small payloads
                        try:
                            import json
                            body_json = json.loads(body.decode())
                            # Sanitize sensitive data
                            if "input" in body_json:
                                input_text = body_json["input"]
                                if len(input_text) > 100:
                                    body_json["input"] = input_text[:100] + "..."
                            logger.debug(f"📝 [{request_id}] Request body: {json.dumps(body_json, indent=2)}")
                            body_logged = True
                        except:
                            logger.debug(f"📝 [{request_id}] Request body: {body.decode()[:200]}...")
                            body_logged = True
                    else:
                        logger.debug(f"📝 [{request_id}] Request body: [Large payload - {len(body)} bytes]")
                        body_logged = True
                        
                    # Restore the body for downstream handlers by creating a new request
                    # This prevents the "body already consumed" issue in concurrent scenarios
                    async def receive():
                        return {"type": "http.request", "body": body, "more_body": False}
                    
                    # Update the request's receive callable
                    request._receive = receive
                    
            except Exception as e:
                logger.debug(f"📝 [{request_id}] Failed to read request body: {str(e)}")
        
        # Add request ID to request state for downstream use
        request.state.request_id = request_id
        
        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            process_time = time.time() - start_time
            logger.error(
                f"❌ [{request_id}] {method} {url} | "
                f"Error: {str(e)} | "
                f"Time: {process_time:.3f}s"
            )
            raise
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log the response
        status_code = response.status_code
        status_emoji = "✅" if 200 <= status_code < 300 else "⚠️" if 300 <= status_code < 400 else "❌"
        
        # Add timing categories for better monitoring
        timing_category = ""
        if process_time > 10:
            timing_category = " [SLOW]"
        elif process_time > 5:
            timing_category = " [MEDIUM]"
        elif process_time < 0.1:
            timing_category = " [FAST]"
        
        # Build response log message
        log_parts = [
            f"{status_emoji} [{request_id}] {method} {url}",
            f"Status: {status_code}",
            f"Time: {process_time:.3f}s{timing_category}"
        ]
        
        # Add GPU stats if enabled and this is a compute-intensive request
        if (settings.log_gpu_on_requests and 
            method in ["POST", "PUT", "PATCH"] and
            any(endpoint in url for endpoint in ["/v1/audio/speech", "/dev/generate", "/dev/captioned"])):
            try:
                gpu_monitor = get_gpu_monitor()
                gpu_summary = gpu_monitor.get_gpu_summary()
                if gpu_summary:
                    log_parts.append(gpu_summary)
            except Exception as e:
                logger.debug(f"📝 [{request_id}] Failed to get GPU stats: {str(e)}")
            
        logger.info(" | ".join(log_parts))
        
        return response


def setup_logger():
    """Configure loguru logger with custom formatting"""
    config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "<fg #2E8B57>{time:hh:mm:ss A}</fg #2E8B57> | "
                "{level: <8} | "
                "<fg #4169E1>{module}:{line}</fg #4169E1> | "
                "{message}",
                "colorize": True,
                "level": "DEBUG",
            },
        ],
    }
    logger.remove()
    logger.configure(**config)
    logger.level("ERROR", color="<red>")
    
    # Log request logging configuration
    if settings.log_requests:
        features = []
        if settings.log_request_bodies:
            features.append("request bodies")
        if settings.log_user_agents:
            features.append("user agents")
        if settings.log_gpu_on_requests:
            features.append("GPU stats on requests")
        
        feature_str = f" (including {', '.join(features)})" if features else ""
        logger.info(f"🔧 Request logging enabled{feature_str}")
    else:
        logger.info("🔧 Request logging disabled")
    
    # Log GPU monitoring configuration
    if settings.log_gpu_stats:
        if settings.gpu_stats_interval > 0:
            logger.info(f"🖥️ GPU stats logging enabled (every {settings.gpu_stats_interval}s)")
        else:
            logger.info("🖥️ GPU stats logging enabled (manual only)")
    else:
        logger.info("🖥️ GPU stats logging disabled")


# Configure logger
setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for model initialization"""
    from .inference.model_manager import get_manager
    from .inference.voice_manager import get_manager as get_voice_manager
    from .services.temp_manager import cleanup_temp_files

    # Clean old temp files on startup
    await cleanup_temp_files()

    logger.info("Loading TTS model and voice packs...")

    # Initialize GPU monitoring
    gpu_monitoring_task = None
    if settings.log_gpu_stats and settings.gpu_stats_interval > 0:
        gpu_monitoring_task = asyncio.create_task(periodic_gpu_monitoring())
        logger.info(f"🖥️ Started GPU monitoring task (every {settings.gpu_stats_interval}s)")

    try:
        # Initialize managers
        model_manager = await get_manager()
        voice_manager = await get_voice_manager()

        # Initialize model with warmup and get status
        device, model, voicepack_count = await model_manager.initialize_with_warmup(
            voice_manager
        )

    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        if gpu_monitoring_task:
            gpu_monitoring_task.cancel()
        raise

    boundary = "░" * 2 * 12
    startup_msg = f"""

{boundary}

    ╔═╗┌─┐┌─┐┌┬┐
    ╠╣ ├─┤└─┐ │ 
    ╚  ┴ ┴└─┘ ┴
    ╦╔═┌─┐┬┌─┌─┐
    ╠╩╗│ │├┴┐│ │
    ╩ ╩└─┘┴ ┴└─┘

{boundary}
                """
    startup_msg += f"\nModel warmed up on {device}: {model}"
    if device == "mps":
        startup_msg += "\nUsing Apple Metal Performance Shaders (MPS)"
    elif device == "cuda":
        startup_msg += f"\nCUDA: {torch.cuda.is_available()}"
    else:
        startup_msg += "\nRunning on CPU"
    startup_msg += f"\n{voicepack_count} voice packs loaded"

    # Add web player info if enabled
    if settings.enable_web_player:
        startup_msg += (
            f"\n\nBeta Web Player: http://{settings.host}:{settings.port}/web/"
        )
        startup_msg += f"\nor http://localhost:{settings.port}/web/"
    else:
        startup_msg += "\n\nWeb Player: disabled"

    startup_msg += f"\n{boundary}\n"
    logger.info(startup_msg)
    
    # Log initial GPU status if enabled
    if settings.log_gpu_stats:
        try:
            gpu_monitor = get_gpu_monitor()
            gpu_monitor.log_gpu_stats(level="info")
        except Exception as e:
            logger.debug(f"🖥️ Failed to log initial GPU stats: {e}")

    yield
    
    # Cleanup: Cancel GPU monitoring task
    if gpu_monitoring_task:
        gpu_monitoring_task.cancel()
        try:
            await gpu_monitoring_task
        except asyncio.CancelledError:
            pass
        logger.info("🖥️ GPU monitoring task stopped")


# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    openapi_url="/openapi.json",  # Explicitly enable OpenAPI schema
)

# Add CORS middleware if enabled
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add request logging middleware if enabled
if settings.log_requests:
    app.add_middleware(RequestLoggingMiddleware)

# Include routers
logger.info("🛣️  Setting up API routes...")
app.include_router(openai_router, prefix="/v1")
logger.debug("✅ OpenAI-compatible routes: /v1/audio/speech, /v1/models, /v1/audio/voices")

app.include_router(dev_router)  # Development endpoints
logger.debug("✅ Development routes: /dev/phonemize, /dev/generate_from_phonemes, /dev/captioned_speech")

app.include_router(debug_router)  # Debug endpoints
logger.debug("✅ Debug routes: /debug/threads, /debug/storage, /debug/system, /debug/session_pools")

if settings.enable_web_player:
    app.include_router(web_router, prefix="/web")  # Web player static files
    logger.debug("✅ Web player routes: /web/*")
else:
    logger.debug("⚠️  Web player routes disabled")

logger.info("🚀 All routes configured successfully")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("🏥 Health check requested")
    return {"status": "healthy", "service": "kokoro-fastapi"}


@app.get("/v1/test")
async def test_endpoint():
    """Test endpoint to verify routing"""
    logger.debug("🧪 Test endpoint called")
    return {"status": "ok", "message": "API is working correctly"}


@app.get("/debug/gpu")
async def gpu_stats():
    """Get current GPU statistics"""
    try:
        gpu_monitor = get_gpu_monitor()
        gpu_info = gpu_monitor.get_gpu_info(use_cache=False)  # Force fresh data
        
        if not gpu_info:
            return {"message": "No GPU information available", "gpus": []}
        
        # Convert to dict format for JSON response
        gpu_data = []
        for gpu in gpu_info:
            gpu_dict = {
                "id": gpu.id,
                "name": gpu.name,
                "utilization_percent": round(gpu.load * 100, 1),
                "memory": {
                    "used_mb": round(gpu.memory_used, 1),
                    "total_mb": round(gpu.memory_total, 1),
                    "percent": round(gpu.memory_percent, 1)
                }
            }
            
            if gpu.temperature is not None:
                gpu_dict["temperature_celsius"] = gpu.temperature
            if gpu.power_draw is not None:
                gpu_dict["power_watts"] = round(gpu.power_draw, 1)
            if gpu.power_limit is not None:
                gpu_dict["power_limit_watts"] = round(gpu.power_limit, 1)
                
            gpu_data.append(gpu_dict)
        
        # Also log the stats
        gpu_monitor.log_gpu_stats(level="info")
        
        return {
            "timestamp": time.time(),
            "gpu_count": len(gpu_data),
            "gpus": gpu_data
        }
        
    except Exception as e:
        logger.error(f"🖥️ Failed to get GPU stats: {e}")
        return {"error": str(e), "gpus": []}


if __name__ == "__main__":
    uvicorn.run("api.src.main:app", host=settings.host, port=settings.port, reload=True)
