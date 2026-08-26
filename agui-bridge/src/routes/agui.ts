/**
 * AG-UI Routes
 * /agui/* endpoint handlers
 */

import { Hono } from 'hono';
import { BridgeConfig } from '../config';
import { BinduClient } from '../clients/bindu';
import { createRunHandler } from '../handlers/run';

export function createAGUIRoutes(config: BridgeConfig, binduClient: BinduClient): Hono {
  const app = new Hono();

  // POST /agui/run - Main run endpoint
  const runHandler = createRunHandler(binduClient, config);
  app.post('/run', runHandler);

  // GET /agui/runs - List recent runs (optional v1.1 feature)
  app.get('/runs', async (c) => {
    try {
      const threadId = c.req.query('thread_id');
      const limit = parseInt(c.req.query('limit') || '10', 10);

      // Note: Bindu's tasks/list may not support filtering by contextId yet
      const tasks = await binduClient.listTasks(limit);

      // Filter by thread_id if provided
      const filteredTasks = threadId
        ? tasks.filter(t => t.contextId === threadId)
        : tasks;

      const runs = filteredTasks.map(task => ({
        run_id: task.id,
        thread_id: task.contextId,
        state: task.status.state,
        created_at: task.status.timestamp,
        completed_at: ['completed', 'failed', 'canceled'].includes(task.status.state)
          ? task.status.timestamp
          : undefined,
      }));

      return c.json({ runs });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to list runs';
      return c.json({ error: message }, 500);
    }
  });

  return app;
}
