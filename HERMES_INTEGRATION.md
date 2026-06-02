# Hermes Agent Integration with Cresus MCP

## Overview

This document describes the integration of Hermes AI Agent with Cresus portfolio management system via the MCP (Model Context Protocol) interface.

**What You Get:**
- Autonomous AI agent for portfolio management
- Natural language interface for all Cresus operations
- 50+ tools accessible through MCP
- Smart portfolio analysis and recommendations
- Automated performance tracking

## Quick Start

### 1. Initialize Hermes

```bash
cresus init --hermes
```

This command:
- Creates `~/.hermes/` directory structure
- Copies 3 core skills (portfolio_manager, screener_analyzer, performance_analyzer)
- Configures MCP connection to Cresus API
- Sets up Hermes agent with Cresus system prompt

### 2. Start Services

```bash
# Terminal 1: Start Cresus API
cresus service start api

# Terminal 2: Launch Hermes Agent
hermes run
```

### 3. Interact with Hermes

```
Human: "Create a portfolio called 'Growth' with 50000€"
Hermes: Creates portfolio, confirms with details