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
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

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
        headers: {
            'Content-Type': 'application/json',
        },
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
 * Load agent card information from the well-known endpoint
 * @returns {Promise<Object>} Agent card data including name, version, capabilities, etc.
 * @throws {Error} If the agent card cannot be loaded
 */
async function loadAgentCard() {
    try {
        const response = await fetch('/.well-known/agent.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
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
    return await makeApiRequest('message/send', {
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
    return await makeApiRequest('contexts/create', {});
}

/**
 * List all conversation contexts
 * @param {number} [length=100] - Maximum number of contexts to retrieve
 * @returns {Promise<Array>} Array of context objects
 */
async function listContexts(length = 100) {
    return await makeApiRequest('contexts/list', { length });
}

/**
 * Get a specific context by ID
 * @param {string} contextId - Context ID to retrieve
 * @returns {Promise<Object>} Context object with tasks and messages
 */
async function getContext(contextId) {
    return await makeApiRequest('contexts/get', {
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
    return await makeApiRequest('contexts/clear', params);
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
    return await makeApiRequest('tasks/list', params);
}

/**
 * Get a specific task by ID
 * @param {string} taskId - Task ID to retrieve
 * @returns {Promise<Object>} Task object with status, history, and artifacts
 */
async function getTask(taskId) {
    return await makeApiRequest('tasks/get', {
        task_id: taskId
    });
}

/**
 * Cancel a running task
 * @param {string} taskId - Task ID to cancel
 * @returns {Promise<Object>} Response confirming the cancellation
 */
async function cancelTask(taskId) {
    return await makeApiRequest('tasks/cancel', {
        task_id: taskId
    });
}

/**
 * Clear all storage including contexts and tasks
 * @returns {Promise<Object>} Response confirming the clear operation
 */
async function clearAllStorage() {
    return await clearContext(null);
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
    const tasks = [];
    
    rawData.forEach(messageArray => {
        if (Array.isArray(messageArray) && messageArray.length > 0) {
            const taskGroups = {};
            messageArray.forEach(msg => {
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
            });
            
            Object.values(taskGroups).forEach(task => tasks.push(task));
        }
    });
    
    return tasks;
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
    
    rawData.forEach(messageArray => {
        if (Array.isArray(messageArray) && messageArray.length > 0) {
            messageArray.forEach(msg => {
                const contextId = msg.context_id;
                if (!contextMap[contextId]) {
                    contextMap[contextId] = {
                        context_id: contextId,
                        id: contextId,
                        task_count: 0,
                        task_ids: new Set()
                    };
                }
                contextMap[contextId].task_ids.add(msg.task_id);
            });
        }
    });
    
    // Convert to array and calculate task counts
    return Object.values(contextMap).map(context => ({
        ...context,
        task_count: context.task_ids.size,
        task_ids: undefined
    }));
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
    messageId = messageId || generateId();
    taskId = taskId || generateId();
    
    const payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{
                    "kind": "text",
                    "text": message
                }],
                "kind": "message",
                "messageId": messageId,
                "contextId": contextId,
                "taskId": taskId
            },
            "configuration": {
                "acceptedOutputModes": ["application/json"]
            }
        },
        "id": generateId()
    };

    const response = await fetch('/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.error) {
        throw new Error(result.error.message || 'Unknown error');
    }

    return result.result;
}

/**
 * Get task status for polling
 * Used to check task completion and retrieve results
 * @param {string} taskId - Task ID to check status for
 * @returns {Promise<Object>} Task object with current status and history
 */
async function getTaskStatus(taskId) {
    const payload = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {
            "taskId": taskId
        },
        "id": generateId()
    };

    const response = await fetch('/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.error) {
        throw new Error(result.error.message || 'Unknown error');
    }

    return result.result;
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
    getTasksGrouped
};
