/**
 * Full-Stack Production Server & Reverse Proxy for AICTE FDR Management Portal
 * Serves the compiled Vite production bundle from dist/ (or preview.html fallback)
 * and proxies all /api/* requests to Flask on port 5000.
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = 5000;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

const server = http.createServer((req, res) => {
  // 1. API Reverse Proxy to Flask Backend
  if (req.url.startsWith('/api')) {
    const options = {
      hostname: BACKEND_HOST,
      port: BACKEND_PORT,
      path: req.url,
      method: req.method,
      headers: {
        ...req.headers,
        host: `${BACKEND_HOST}:${BACKEND_PORT}`,
      },
    };

    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (err) => {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        error: 'Bad Gateway',
        message: 'Could not connect to Flask backend at http://127.0.0.1:5000',
        details: err.message,
      }));
    });

    req.pipe(proxyReq, { end: true });
    return;
  }

  // 2. Static File Serving from dist/ or fallback
  let cleanUrl = req.url.split('?')[0];
  let distPath = path.join(__dirname, 'dist', cleanUrl === '/' ? 'index.html' : cleanUrl);

  if (fs.existsSync(distPath) && fs.statSync(distPath).isFile()) {
    const ext = path.extname(distPath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
    fs.createReadStream(distPath).pipe(res);
    return;
  }

  // SPA fallback to dist/index.html
  const distIndex = path.join(__dirname, 'dist', 'index.html');
  if (fs.existsSync(distIndex)) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    fs.createReadStream(distIndex).pipe(res);
    return;
  }

  // Standalone fallback to preview.html
  const previewPath = path.join(__dirname, 'preview.html');
  fs.readFile(previewPath, (err, content) => {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Error loading portal frontend.');
      return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(content);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[Frontend] AICTE FDR Portal is running on http://127.0.0.1:${PORT}`);
  console.log(`[Proxy] API requests (/api/*) are proxied to http://${BACKEND_HOST}:${BACKEND_PORT}`);
});
