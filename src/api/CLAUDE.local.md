# Server API

Python REST API for managing trading environment. 

## Commands
- start or stop: `cresus service <start|stop|restart> gateway -d `
- status: `cresus service status`
- Test: `pytest tests/api`


## Architecture 
- code in src/api/

# Off-limits
- Never use yfinance or financedatabase, use src/tools/data instead
