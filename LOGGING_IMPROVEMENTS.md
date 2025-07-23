# Kokoro-FastAPI Enhanced Request Logging

This document demonstrates the enhanced request logging features added to the Kokoro-FastAPI application.

## Features Added

### 1. Request Logging Middleware
- **What it does**: Logs all incoming HTTP requests and their responses
- **Information logged**:
  - HTTP method and full URL
  - Client IP address
  - User-Agent (truncated to 50 characters)
  - Response status code
  - Processing time
  - Request body (for specific endpoints, with size limits)

### 2. Configuration Options
New settings in `core/config.py`:

```python
# Logging Settings
log_requests: bool = True          # Whether to log incoming requests
log_request_bodies: bool = True    # Whether to log request bodies (debug level)
log_user_agents: bool = True       # Whether to log user agents
```

### 3. Enhanced Startup Logging
- Route registration logging with endpoint details
- Configuration status for web player and other features

## Log Output Examples

### Successful Request
```
02:45:12 PM | INFO     | main:43 | 🔄 GET http://localhost:8880/health | IP: 127.0.0.1 | User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...
02:45:12 PM | DEBUG    | main:235 | 🏥 Health check requested
02:45:12 PM | INFO     | main:81 | ✅ GET http://localhost:8880/health | Status: 200 | Time: 0.003s
```

### TTS Request with Body Logging
```
02:46:15 PM | INFO     | main:43 | 🔄 POST http://localhost:8880/v1/audio/speech | IP: 127.0.0.1 | User-Agent: curl/7.87.0
02:46:15 PM | DEBUG    | main:60 | 📝 Request body: {
  "model": "kokoro",
  "input": "Hello, this is a test of the TTS system...",
  "voice": "af_heart",
  "response_format": "mp3"
}
02:46:15 PM | INFO     | main:81 | ✅ POST http://localhost:8880/v1/audio/speech | Status: 200 | Time: 1.245s
```

### Error Request
```
02:47:30 PM | INFO     | main:43 | 🔄 GET http://localhost:8880/invalid-endpoint | IP: 127.0.0.1 | User-Agent: curl/7.87.0
02:47:30 PM | INFO     | main:81 | ❌ GET http://localhost:8880/invalid-endpoint | Status: 404 | Time: 0.001s
```

### Startup Logging
```
02:45:00 PM | INFO     | main:108 | 🔧 Request logging enabled (including request bodies, user agents)
02:45:00 PM | INFO     | main:213 | 🛣️  Setting up API routes...
02:45:00 PM | DEBUG    | main:215 | ✅ OpenAI-compatible routes: /v1/audio/speech, /v1/models, /v1/audio/voices
02:45:00 PM | DEBUG    | main:218 | ✅ Development routes: /dev/phonemize, /dev/generate_from_phonemes, /dev/captioned_speech
02:45:00 PM | DEBUG    | main:221 | ✅ Debug routes: /debug/threads, /debug/storage, /debug/system, /debug/session_pools
02:45:00 PM | DEBUG    | main:224 | ✅ Web player routes: /web/*
02:45:00 PM | INFO     | main:229 | 🚀 All routes configured successfully
```

## Security & Privacy Considerations

1. **Request Body Logging**: Only logs small payloads (<1000 bytes) and truncates text input to 100 characters to prevent logging sensitive data
2. **User-Agent Truncation**: User agents are truncated to 50 characters to keep logs readable
3. **IP Logging**: Client IP addresses are logged for security monitoring
4. **Configurable**: All logging features can be disabled via environment variables

## Environment Variables

You can control logging behavior using these environment variables:

```bash
# Disable request logging entirely
LOG_REQUESTS=false

# Disable request body logging (but keep basic request info)
LOG_REQUEST_BODIES=false

# Disable user agent logging
LOG_USER_AGENTS=false
```

## Benefits

1. **Better Observability**: See exactly what requests are coming into your API
2. **Performance Monitoring**: Track response times for all endpoints
3. **Security Monitoring**: Monitor client IPs and user agents
4. **Debugging**: See request bodies for troubleshooting
5. **Configurable**: Turn on/off different logging levels as needed
