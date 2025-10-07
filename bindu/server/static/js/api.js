/**
 * API module for Bindu Agent
 * Handles all API communication and JSON-RPC calls
 * @module api
 */

/**
 * Generate a UUID v4 identifier
 * Uses utils.generateUUID when available, otherwise falls back to local implementation
 * @returns {string} UUID v4 string
 */
function generateId() {
    if (typeof utils !== 'undefined' && utils.generateUUID) {
        return utils.generateUUID();
    }
    // Optimized UUID v4 generation without regex
    const hex = '0123456789abcdef';
    let uuid = '';
    for (let i = 0; i < 36; i++) {
        if (i === 8 || i === 13 || i === 18 || i === 23) {
            uuid += '-';
        } else if (i === 14) {
            uuid += '4';
        } else if (i === 19) {
            uuid += hex[(Math.random() * 4 | 0) + 8];
        } else {
            uuid += hex[Math.random() * 16 | 0];
        }
    }
    return uuid;
}

/**
 * Shared headers object for all requests
 * @const
 * @private
 */
const JSON_HEADERS = {
    'Content-Type': 'application/json'
};

/**
 * Make a JSON-RPC 2.0 API request to the agent server
 * @param {string} method - JSON-RPC method name (e.g., 'message/send', 'tasks/get')
 * @param {Object} params - Parameters for the method
 * @returns {Promise<any>} The result from the API response
 * @throws {Error} If the request fails or returns an error
 */
async function makeApiRequest(method, params) {
    const response = await fetch('/', {
        method: 'POST',
        headers: JSON_HEADERS,
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: generateId()
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.error) {
        throw new Error(result.error.message || 'Unknown API error');
    }

    return result.result;
}

/**
 * Agent card cache
 * @private
 */
let agentCardCache = null;

/**
 * Load agent card information from the well-known endpoint
 * Uses caching to avoid repeated requests
 * @param {boolean} [forceRefresh=false] - Force refresh the cache
 * @returns {Promise<Object>} Agent card data including name, version, capabilities, etc.
 * @throws {Error} If the agent card cannot be loaded
 */
async function loadAgentCard(forceRefresh = false) {
    if (agentCardCache && !forceRefresh) {
        return agentCardCache;
    }
    
    try {
        const response = await fetch('/.well-known/agent.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        agentCardCache = await response.json();
        return agentCardCache;
    } catch (error) {
        console.error('Error loading agent card:', error);
        throw error;
    }
}

/**
 * Send a simple message to the agent
 * @param {string} contextId - Context ID for the conversation
 * @param {string} content - Message content text
 * @param {string} [role='user'] - Role of the message sender
 * @returns {Promise<Object>} Response from the agent
 */
async function sendMessage(contextId, content, role = 'user') {
    return makeApiRequest('message/send', {
        context_id: contextId,
        message: {
            role: role,
            parts: [{
                kind: 'text',
                text: content
            }]
        }
    });
}

/**
 * Create a new conversation context
 * @returns {Promise<Object>} Created context object with context_id
 */
async function createContext() {
    return makeApiRequest('contexts/create', {});
}

/**
 * List all conversation contexts
 * @param {number} [length=100] - Maximum number of contexts to retrieve
 * @returns {Promise<Array>} Array of context objects
 */
async function listContexts(length = 100) {
    return makeApiRequest('contexts/list', { length });
}

/**
 * Get a specific context by ID
 * @param {string} contextId - Context ID to retrieve
 * @returns {Promise<Object>} Context object with tasks and messages
 */
async function getContext(contextId) {
    return makeApiRequest('contexts/get', {
        context_id: contextId
    });
}

/**
 * Clear a specific context or all contexts
 * @param {string|null} [contextId=null] - Context ID to clear, or null to clear all
 * @returns {Promise<Object>} Response confirming the clear operation
 */
async function clearContext(contextId = null) {
    const params = contextId ? { context_id: contextId } : {};
    return makeApiRequest('contexts/clear', params);
}

/**
 * List tasks, optionally filtered by context
 * @param {string|null} [contextId=null] - Context ID to filter tasks, or null for all tasks
 * @param {number} [length=100] - Maximum number of tasks to retrieve
 * @returns {Promise<Array>} Array of task objects
 */
async function listTasks(contextId = null, length = 100) {
    const params = { length };
    if (contextId) {
        params.context_id = contextId;
    }
    return makeApiRequest('tasks/list', params);
}

/**
 * Get a specific task by ID
 * @param {string} taskId - Task ID to retrieve
 * @returns {Promise<Object>} Task object with status, history, and artifacts
 */
async function getTask(taskId) {
    return makeApiRequest('tasks/get', {
        task_id: taskId
    });
}

/**
 * Cancel a running task
 * @param {string} taskId - Task ID to cancel
 * @returns {Promise<Object>} Response confirming the cancellation
 */
async function cancelTask(taskId) {
    return makeApiRequest('tasks/cancel', {
        task_id: taskId
    });
}

/**
 * Clear all storage including contexts and tasks
 * @returns {Promise<Object>} Response confirming the clear operation
 */
async function clearAllStorage() {
    return clearContext(null);
}

/**
 * Get tasks grouped by task_id with full history
 * Processes raw task data into structured task objects
 * @param {string|null} [contextId=null] - Context ID to filter tasks, or null for all tasks
 * @param {number} [length=100] - Maximum number of tasks to retrieve
 * @returns {Promise<Array>} Array of task objects with grouped history
 */
async function getTasksGrouped(contextId = null, length = 100) {
    const rawData = await listTasks(contextId, length);
    const taskGroups = {};
    
    // Single pass through all messages
    for (const messageArray of rawData) {
        if (!Array.isArray(messageArray) || messageArray.length === 0) continue;
        
        for (const msg of messageArray) {
            const taskId = msg.task_id;
            if (!taskGroups[taskId]) {
                taskGroups[taskId] = {
                    task_id: taskId,
                    context_id: msg.context_id,
                    history: [],
                    status: { state: 'completed' }
                };
            }
            taskGroups[taskId].history.push(msg);
        }
    }
    
    return Object.values(taskGroups);
}

/**
 * Get contexts with task counts
 * Processes raw context data and calculates task counts per context
 * @param {number} [length=100] - Maximum number of contexts to retrieve
 * @returns {Promise<Array>} Array of context objects with task counts
 */
async function getContextsGrouped(length = 100) {
    const rawData = await listContexts(length);
    const contextMap = {};
    
    // Single pass through all messages
    for (const messageArray of rawData) {
        if (!Array.isArray(messageArray) || messageArray.length === 0) continue;
        
        for (const msg of messageArray) {
            const contextId = msg.context_id;
            if (!contextMap[contextId]) {
                contextMap[contextId] = {
                    context_id: contextId,
                    id: contextId,
                    task_ids: new Set()
                };
            }
            contextMap[contextId].task_ids.add(msg.task_id);
        }
    }
    
    // Convert to array with task counts (avoid object spread)
    const contexts = [];
    for (const contextId in contextMap) {
        const context = contextMap[contextId];
        contexts.push({
            context_id: context.context_id,
            id: context.id,
            task_count: context.task_ids.size
        });
    }
    return contexts;
}

/**
 * Send a chat message with full configuration
 * Used by the chat interface for complete message handling
 * @param {string} contextId - Context ID for the conversation
 * @param {string} message - Message text content
 * @param {string|null} [messageId=null] - Optional message ID, auto-generated if not provided
 * @param {string|null} [taskId=null] - Optional task ID, auto-generated if not provided
 * @returns {Promise<Object>} Response with task_id, context_id, and optional reply
 */
async function sendChatMessage(contextId, message, messageId = null, taskId = null) {
    return makeApiRequest('message/send', {
        message: {
            role: 'user',
            parts: [{
                kind: 'text',
                text: message
            }],
            kind: 'message',
            messageId: messageId || generateId(),
            contextId: contextId,
            taskId: taskId || generateId()
        },
        configuration: {
            acceptedOutputModes: ['application/json']
        }
    });
}

/**
 * Get task status for polling
 * Used to check task completion and retrieve results
 * @param {string} taskId - Task ID to check status for
 * @returns {Promise<Object>} Task object with current status and history
 */
async function getTaskStatus(taskId) {
    return makeApiRequest('tasks/get', {
        taskId: taskId
    });
}

/**
 * Task polling configuration
 * @const
 */
const POLLING_CONFIG = {
    INITIAL_INTERVAL: 1000,  // 1 second
    MAX_INTERVAL: 5000,      // 5 seconds
    BACKOFF_MULTIPLIER: 1.5
};

/**
 * Terminal task states (cached to avoid array allocation)
 * @const
 * @private
 */
const TERMINAL_STATES = ['completed', 'failed', 'canceled'];

/**
 * Poll task status with exponential backoff
 * Automatically handles polling until task reaches terminal state
 * @param {string} taskId - Task ID to poll
 * @param {Function} onUpdate - Callback for status updates (task, isComplete)
 * @param {Function} onError - Callback for errors
 * @returns {Object} Object with cancel() method to stop polling
 */
function pollTaskWithBackoff(taskId, onUpdate, onError) {
    let timeoutId = null;
    let cancelled = false;
    
    async function poll(interval = POLLING_CONFIG.INITIAL_INTERVAL) {
        if (cancelled) return;
        
        try {
            const task = await getTaskStatus(taskId);
            const state = task.status?.state;
            
            // Check if task is in terminal state
            const isTerminal = TERMINAL_STATES.includes(state);
            
            // Call update callback
            onUpdate(task, isTerminal);
            
            // Continue polling if not terminal and not cancelled
            if (!isTerminal && !cancelled) {
                const nextInterval = Math.min(
                    interval * POLLING_CONFIG.BACKOFF_MULTIPLIER,
                    POLLING_CONFIG.MAX_INTERVAL
                );
                timeoutId = setTimeout(() => poll(nextInterval), interval);
            }
        } catch (error) {
            if (!cancelled) {
                onError(error);
            }
        }
    }
    
    // Start polling
    poll();
    
    // Return cancellation control
    return {
        cancel: () => {
            cancelled = true;
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
        }
    };
}

/**
 * Global API namespace
 * All API functions are exposed through window.api
 * @namespace api
 */
window.api = {
    // Core utilities
    generateId,
    makeApiRequest,
    
    // Agent information
    loadAgentCard,
    
    // Messaging
    sendMessage,
    sendChatMessage,
    
    // Context management
    createContext,
    listContexts,
    getContext,
    clearContext,
    clearAllStorage,
    getContextsGrouped,
    
    // Task management
    listTasks,
    getTask,
    getTaskStatus,
    cancelTask,
    getTasksGrouped,
    pollTaskWithBackoff,
    
    // Constants
    POLLING_CONFIG
};
