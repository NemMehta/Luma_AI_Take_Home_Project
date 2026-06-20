// Tiny zero-dependency static file server for the demo app (./sut).
// Used by Playwright's `webServer` config so `npm run traces` starts it
// automatically. Not the product — just enough to serve three static files.

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('./sut/', import.meta.url));
const PORT = Number(process.env.PORT ?? 5173);

const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
};

const server = createServer(async (req, res) => {
  const { pathname } = new URL(req.url ?? '/', 'http://localhost');
  // Strip leading slashes / parent-dir segments so requests can't escape ROOT.
  const relative = pathname === '/' ? 'index.html' : normalize(pathname).replace(/^([/\\]|\.\.)+/, '');
  try {
    const body = await readFile(join(ROOT, relative));
    res.writeHead(200, { 'content-type': CONTENT_TYPES[extname(relative)] ?? 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Not found');
  }
});

server.listen(PORT, () => console.log(`SUT static server on http://127.0.0.1:${PORT}`));
