# Cresus Service Management

All Cresus services (Gateway, Frontend, MCP) are managed via a unified CLI interface.

## Service Status

```bash
cresus service status
```

Displays:
```
      Service Status       
┏━━━━━━━━━┳━━━━━━━━━┳━━━━━┓
┃ Service ┃ Status  ┃ PID ┃
┡━━━━━━━━━╇━━━━━━━━━╇━━━━━┩
│ gateway │ stopped │ -   │
│ front   │ stopped │ -   │
│ mcp     │ stopped │ -   │
└─────────┴─────────┴─────┘
```

## Services

### Gateway (API + Cron)
- **Port**: 8000
- **Script**: `bin/gateway`
- **Purpose**: REST API, scheduled tasks, background jobs
- **Start**: `cresus service start gateway`
- **Stop**: `cresus service stop gateway`
- **Restart**: `cresus service restart gateway`

### Frontend
- **Port**: 5173
- **Script**: `bin/front`
- **Purpose**: Web UI (React/Vite)
- **Start**: `cresus service start front`
- **Stop**: `cresus service stop front`
- **Restart**: `cresus service restart front`

### MCP Server
- **Port**: None (Stdio - managed by Hermes)
- **Script**: `bin/mcp`
- **Purpose**: Portfolio management tools (16 functions)
- **Status**: Hermes-managed (auto-start when Hermes initializes)
- **Check**: `hermes mcp test cresus`
- **Tools**: `hermes mcp list`

## Management Commands

### Start a Service
```bash
cresus service start <service>    # Foreground (development)
cresus service start <service> -d # Daemon (production)
```

### Stop a Service
```bash
cresus service stop <service>
```

### Restart a Service
```bash
cresus service restart <service>  # Daemon mode
```

### View Service Logs
```bash
cresus service logs <service>     # Last 20 lines
cresus service logs <service> -n 50  # Last 50 lines
```

## MCP Service Details

The MCP service is **Hermes-managed** and uses **Stdio transport**:

- **Auto-start**: Enabled when Hermes initializes
- **Transport**: Stdio (subprocess)
- **Management**: Automatic via Hermes configuration
- **Configuration**: `~/.hermes/config.yaml`

### MCP Status Check
```bash
# Service status
cresus service status mcp

# Hermes MCP status
hermes mcp list
hermes mcp test cresus

# Check connection
curl http://192.168.0.130:6501/api/v1/health
```

### MCP Logs
```bash
# View MCP logs
cresus service logs mcp
tail -f logs/mcp.log

# Debug mode
CRESUS_LOG_LEVEL=DEBUG cresus service start mcp
```

## Development Workflow

### Start All Services (Foreground)
```bash
# Terminal 1: Gateway
cresus service start gateway

# Terminal 2: Frontend  
cresus service start front

# Terminal 3: Hermes (manages MCP automatically)
hermes chat
```

### Production Deployment

```bash
# Start as daemons
cresus service start gateway -d
cresus service start front -d

# Check all services
cresus service status

# Monitor logs
cresus service logs gateway
cresus service logs front
cresus service logs mcp
```

## Configuration

### Hermes MCP Configuration
Location: `~/.hermes/config.yaml`

```yaml
mcp_servers:
  cresus:
    name: Cresus Portfolio API
    type: stdio
    command: /Volumes/Data/dev/cresus/venv/bin/python
    args:
      - -m
      - cresus_mcp.main
    cwd: /Volumes/Data/dev/cresus
    env:
      CRESUS_API_URL: http://192.168.0.130:6501/api/v1
      CRESUS_LOG_LEVEL: INFO
    enabled: true
    auto_start: true
```

### Environment Variables
- `CRESUS_API_URL` - Backend API URL
- `CRESUS_LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR)
- `CRESUS_PROJECT_ROOT` - Project root directory

## Service Information

### Port Usage
| Service | Port  | Purpose |
|---------|-------|---------|
| Gateway | 8000  | REST API |
| Frontend | 5173 | Web UI |
| MCP | stdio | Hermes integration |

### Log Files
| Service | Log File |
|---------|----------|
| Gateway | `logs/gateway.log` |
| Frontend | `logs/front.log` |
| MCP | `logs/mcp.log` |

### PID Storage
All service PIDs stored in: `.pids/` directory

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
lsof -i :<port>

# Check logs
cresus service logs <service>

# Try daemon mode for visibility
CRESUS_LOG_LEVEL=DEBUG cresus service start <service>
```

### Hermes MCP not found
```bash
# Reinitialize Hermes
hermes postinstall

# Check configuration
hermes mcp list

# Test connection
hermes mcp test cresus
```

### High CPU/Memory
```bash
# Check process
ps aux | grep cresus
ps aux | grep -E "gateway|front"

# Restart service
cresus service restart <service>

# Check logs for errors
tail -100 logs/<service>.log
```

## Related

- [MCP Service Details](MCP_SERVICE.md)
- [REST API](API.md)
- [Portfolio Management](PORTFOLIO.md)
