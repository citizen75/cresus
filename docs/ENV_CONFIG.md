# Environment Configuration (.env)

All Cresus servers are now configured via `.env` file instead of `config/cresus.yml`. This provides:
- Easy setup for different environments (dev, staging, production)
- Secrets management without version control
- Simple host/port configuration
- Clear server separation

## Configuration

### Setup

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```bash
# API Server
API_HOST=0.0.0.0
API_PORT=8000

# MCP Server (Model Context Protocol)
MCP_HOST=localhost
MCP_PORT=3000

# Frontend Server
FRONT_HOST=localhost
FRONT_PORT=5173

# Gateway Settings
GATEWAY_CRON_ENABLED=false
GATEWAY_MCP_ENABLED=true
GATEWAY_CRON_CONFIG=config/cron.yml
```

## Variables

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server bind address |
| `API_PORT` | `8000` | API server port |
| `MCP_HOST` | `localhost` | MCP server bind address |
| `MCP_PORT` | `3000` | MCP server port |
| `FRONT_HOST` | `localhost` | Frontend dev server bind address |
| `FRONT_PORT` | `5173` | Frontend dev server port |

### Gateway Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_CRON_ENABLED` | `false` | Enable cron job scheduler |
| `GATEWAY_MCP_ENABLED` | `true` | Enable MCP server in gateway |
| `GATEWAY_CRON_CONFIG` | `config/cron.yml` | Path to cron jobs config |

## Environment Variable Loading

Environment variables are loaded in this order:
1. System environment (highest priority)
2. `.env` file (if exists)
3. Default values in code (lowest priority)

This means you can override any `.env` value by setting it in your shell:
```bash
API_PORT=9000 python src/gateway/main.py
```

## Per-Environment Setup

### Development
```bash
# .env
API_HOST=127.0.0.1
API_PORT=8000
FRONT_PORT=5173
GATEWAY_CRON_ENABLED=false
```

### Staging
```bash
# .env
API_HOST=0.0.0.0
API_PORT=8000
GATEWAY_CRON_ENABLED=true
GATEWAY_MCP_ENABLED=true
```

### Production
```bash
# .env
API_HOST=0.0.0.0
API_PORT=8000
FRONT_HOST=0.0.0.0
FRONT_PORT=5173
GATEWAY_CRON_ENABLED=true
GATEWAY_MCP_ENABLED=false
```

## Using Environment Variables in Code

### Python (Backend)

```python
from utils.env import (
    get_api_host,
    get_api_port,
    get_gateway_cron_enabled,
    env
)

# Get specific values
api_host = get_api_host()
api_port = get_api_port()

# Get generic value
log_level = env.get("CRESUS_LOG_LEVEL", "INFO")
cron_enabled = env.get_bool("GATEWAY_CRON_ENABLED", False)
timeout = env.get_int("API_TIMEOUT", 30)
```

### TypeScript/JavaScript (Frontend)

Environment variables are read by Vite at build time:

```typescript
// vite.config.ts
const API_PORT = process.env.API_PORT || '8000'
const FRONT_PORT = parseInt(process.env.FRONT_PORT || '5173')
```

The frontend automatically uses environment variables for:
- API proxy target
- Dev server port
- Dev server host

## Starting Services

With `.env` configured:

```bash
# Start gateway (API + MCP + Cron)
python src/gateway/main.py

# Or with custom port
API_PORT=9000 python src/gateway/main.py

# Start frontend (reads FRONT_PORT and API_HOST from .env)
cd front && npm run dev
```

## Troubleshooting

### Port already in use

Change the port in `.env`:
```bash
API_PORT=9000
```

### Environment variable not being read

1. Check `.env` file exists in project root
2. Verify variable format: `KEY=value` (no spaces around `=`)
3. Use `env.get()` helper instead of `os.environ` directly
4. Restart your application

### Frontend not connecting to API

Check that `API_HOST` and `API_PORT` in `.env` match where the API is actually running:
```bash
# If API is on different machine
API_HOST=192.168.1.100
API_PORT=8000
```

## Security

⚠️ **Important**: Never commit `.env` to version control!

1. Add `.env` to `.gitignore`
2. Share `.env.example` with default/public values
3. Keep actual credentials in `.env` (not in repo)
4. Use `.env` for local development only
5. Use environment variables or secrets management in production

```bash
# .gitignore
.env
.env.local
.env.*.local
```
