// API module for Bindu Agent
// Handles all API communication and JSON-RPC calls

// Generate UUID v4 (use utils.generateUUID when available)
function generateId() {
    if (typeof utils !== 'undefined' && utils.generateUUID) {
        return utils.generateUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Make JSON-RPC API request
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

// Load agent card from well-known endpoint
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

// Send a message
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

// Create a new context
async function createContext() {
    return await makeApiRequest('contexts/create', {});
}

// List all contexts
async function listContexts(length = 100) {
    return await makeApiRequest('contexts/list', { length });
}

// Get context by ID
async function getContext(contextId) {
    return await makeApiRequest('contexts/get', {
        context_id: contextId
    });
}

// Clear a context or all contexts
async function clearContext(contextId = null) {
    const params = contextId ? { context_id: contextId } : {};
    return await makeApiRequest('contexts/clear', params);
}

// List tasks
async function listTasks(contextId = null, length = 100) {
    const params = { length };
    if (contextId) {
        params.context_id = contextId;
    }
    return await makeApiRequest('tasks/list', params);
}

// Get task by ID
async function getTask(taskId) {
    return await makeApiRequest('tasks/get', {
        task_id: taskId
    });
}

// Cancel a task
async function cancelTask(taskId) {
    return await makeApiRequest('tasks/cancel', {
        task_id: taskId
    });
}

// Clear all storage (contexts and tasks)
async function clearAllStorage() {
    return await clearContext(null);
}

// Send chat message with full configuration (for chat interface)
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

// Get task status (for polling)
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

// Make functions globally available
window.api = {
    generateId,
    makeApiRequest,
    loadAgentCard,
    sendMessage,
    sendChatMessage,
    createContext,
    listContexts,
    getContext,
    clearContext,
    clearAllStorage,
    listTasks,
    getTask,
    getTaskStatus,
    cancelTask
};
