/**
 * Bindu AG-UI Bridge
 * Translates AG-UI protocol events ↔ Bindu A2A JSON-RPC
 *
 * @version 1.0.0
 * @stack Bun + Hono
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';

import config from './config';
import { BinduClient } from './clients/bindu';
import { createAGUIRoutes } from './routes/agui';
import { createHealthRoutes } from './routes/health';

// Initialize Bindu client
const binduClient = new BinduClient(config);

// Create Hono app
const app = new Hono();

// Middleware
app.use('/*', cors({
  origin: '*',  // Or specific inspector UI origin
  allowMethods: ['GET', 'POST', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
  exposeHeaders: ['X-Request-Id'],
}));

app.use('/*', logger());

// Root endpoint
app.get('/', (c) => {
  return c.json({
    name: 'Bindu AG-UI Bridge',
    version: '1.0.0',
    description: 'Translates AG-UI protocol events ↔ Bindu A2A JSON-RPC',
    endpoints: {
      health: '/health',
      run: '/agui/run',
      runs: '/agui/runs',
    },
  });
});

// Mount routes
app.route('/health', createHealthRoutes(config, binduClient));
app.route('/agui', createAGUIRoutes(config, binduClient));

// Startup message
console.log(`
╔═══════════════════════════════════════════════════════════╗
║           Bindu AG-UI Bridge v1.0.0                       ║
╠═══════════════════════════════════════════════════════════╣
║  Port:          ${config.port.toString().padEnd(40)}║
║  Bindu URL:     ${config.binduUrl.padEnd(40)}║
║  Poll Interval: ${(config.pollIntervalMs + 'ms').padEnd(40)}║
║  Max Attempts:  ${config.maxPollAttempts.toString().padEnd(40)}║
╚═══════════════════════════════════════════════════════════╝
`);

export default {
  port: config.port,
  fetch: app.fetch,
};
