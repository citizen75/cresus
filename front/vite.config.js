import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
var API_HOST = process.env.API_HOST || 'localhost';
var API_PORT = process.env.API_PORT || '8000';
var FRONT_PORT = parseInt(process.env.FRONT_PORT || '5173');
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { '@': path.resolve(__dirname, './src') },
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
