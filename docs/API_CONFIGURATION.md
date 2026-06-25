# API Configuration

## Overview
The frontend automatically detects the API server location based on the frontend host.

## How It Works

### Default Behavior (No Configuration Needed)
- Frontend: `http://192.168.0.160:5173`
- API: `http://192.168.0.160:8000`

The frontend uses `window.location.hostname` and appends `:8000` to find the API server.

### Environment Variable Override
If you need to use a different API server, set `VITE_API_URL`:

```bash
# In front/.env.local
VITE_API_URL=http://api.example.com:8000

# Or at build time
VITE_API_URL=http://192.168.1.100:8000 npm run build
```

## Configuration Files

### Root .env
Contains server configuration:
```
API_HOST=0.0.0.0
API_PORT=8000
FRONT_PORT=5173
```

### front/.env.local (Optional)
Used to override API URL for frontend:
```
VITE_API_URL=http://192.168.0.160:8000
```

## Troubleshooting

### Still seeing localhost:8000?
1. Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
2. Hard reload (Ctrl+Shift+R or Cmd+Shift+R)
3. Check Network tab in DevTools to see actual API requests
4. Verify `getApiBaseUrl()` is being called: Open DevTools Console and run:
   ```javascript
   import { getApiBaseUrl } from '@/services/api'
   console.log(getApiBaseUrl())
   ```

### API Returns localhost:8000?
The fallback in `getApiBaseUrl()` only runs if `window` is undefined (SSR context).
This should not happen in the browser.

Check:
1. Browser console for any errors
2. Network tab to see actual API request URLs
3. `window.location.hostname` value in console

## Code Location

The API URL logic is in: `front/src/services/api.ts`

```typescript
export function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    return `http://${hostname}:8000`
  }
  return 'http://localhost:8000'
}
```

## Examples

| Frontend URL | API URL |
|---|---|
| http://localhost:5173 | http://localhost:8000 |
| http://192.168.0.160:5173 | http://192.168.0.160:8000 |
| http://example.com:5173 | http://example.com:8000 |
| http://staging.example.com | http://staging.example.com:8000 |
