import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
import os from 'os';
// Load .cresus/.env file
function loadEnvFile() {
    var envPath = path.join(os.homedir(), '.cresus', '.env');
    var env = {};
    try {
        if (fs.existsSync(envPath)) {
            var content = fs.readFileSync(envPath, 'utf-8');
            content.split('\n').forEach(function (line) {
                line = line.trim();
                if (!line || line.startsWith('#'))
                    return;
                var _a = line.split('='), key = _a[0], value = _a[1];
                if (key && value) {
                    env[key.trim()] = value.trim();
                }
            });
        }
        else {
            console.warn("\u26A0\uFE0F  Config file not found: ".concat(envPath));
        }
    }
    catch (err) {
        console.error("\u274C Error reading config: ".concat(err));
    }
    return env;
}
var envConfig = loadEnvFile();
// Priority: shell env vars (set by bin/front) > file config > defaults
var API_HOST = process.env.API_HOST || envConfig.API_HOST || 'localhost';
var API_PORT = process.env.API_PORT || envConfig.API_PORT || '8000';
var FRONT_PORT = parseInt(process.env.FRONT_PORT || envConfig.FRONT_PORT || '5173');
// Set environment variables so import.meta.env can access them
process.env.VITE_API_HOST = API_HOST;
process.env.VITE_API_PORT = API_PORT;
// Log configuration on startup
console.log('');
console.log('╔════════════════════════════════════════╗');
console.log('║     Cresus Frontend Configuration      ║');
console.log('╠════════════════════════════════════════╣');
console.log("\u2551 Frontend: http://0.0.0.0:".concat(FRONT_PORT));
console.log("\u2551 API Host: ".concat(API_HOST));
console.log("\u2551 API Port: ".concat(API_PORT));
console.log("\u2551 API URL:  http://".concat(API_HOST, ":").concat(API_PORT));
console.log('╚════════════════════════════════════════╝');
console.log("Config source: ".concat(Object.keys(envConfig).length > 0 ? 'From ~/.cresus/.env' : 'Using defaults'));
console.log('');
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { '@': path.resolve(__dirname, './src') },
    },
    define: {
        'import.meta.env.VITE_API_HOST': JSON.stringify(API_HOST),
        'import.meta.env.VITE_API_PORT': JSON.stringify(API_PORT),
    },
    server: {
        port: FRONT_PORT,
        host: '0.0.0.0',
        proxy: {
            '/api': {
                target: "http://".concat(API_HOST, ":").concat(API_PORT),
                changeOrigin: true,
            },
        },
    },
});
