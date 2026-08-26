/**
 * Health Check Route
 */

import { Hono } from 'hono';
import { BridgeConfig } from '../config';
import { BinduClient } from '../clients/bindu';

export function createHealthRoutes(config: BridgeConfig, binduClient: BinduClient): Hono {
  const app = new Hono();

  app.get('/', async (c) => {
    const binduReachable = await binduClient.healthCheck();

    return c.json({
      status: binduReachable ? 'ok' : 'degraded',
      bindu_url: config.binduUrl,
      bindu_reachable: binduReachable,
      timestamp: new Date().toISOString(),
    });
  });

  return app;
}
