/**
 * Chat page logic
 * Handles chat interface, messaging, and task polling
 * @module chat
 */

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Message sender types
 * @const
 */
const SENDER = {
    USER: 'user',
    AGENT: 'agent',
    STATUS: 'status'
};

/**
 * Task state constants
 * @const
 */
const TASK_STATE = {
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELED: 'canceled'
};

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

/**
 * Chat state
 * @type {Object}
 */
const chatState = {
    contextId: null,
    currentTaskId: null,
    pollingController: null  // Stores polling cancellation controller
};

/**
 * DOM element cache for performance optimization
 * Uses centralized caching utility from common.js
 */
const domCache = utils.createDOMCache();

// ============================================================================
// EVENT HANDLERS
// ============================================================================

/**
 * Handle key press events in the message input
 * Debounced to prevent multiple rapid submissions
 * @param {KeyboardEvent} event - Keyboard event
 */
const handleKeyPress = utils.debounce(function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}, 300);

// ============================================================================
// MESSAGING FUNCTIONS
// ============================================================================

/**
 * Send a message to the agent
 * Handles message creation, API call, and UI updates
 * @async
 */
async function sendMessage() {
    const input = domCache.get('message-input');
    const message = input.value.trim();

    if (!message) return;

    input.value = '';
    const sendButton = domCache.get('send-btn');
    sendButton.disabled = true;

    try {
        const messageId = api.generateId();
        const taskId = api.generateId();
        
        // Initialize context if needed
        if (!chatState.contextId) {
            chatState.contextId = api.generateId();
        }

        // Send message via API
        const result = await api.sendChatMessage(chatState.contextId, message, messageId, taskId);
        console.log('Backend response:', result);

        // Update state with response
        chatState.currentTaskId = result.task_id;
        if (result.context_id) {
            chatState.contextId = result.context_id;
        }

        // Display user message
        addMessage(message, SENDER.USER, chatState.currentTaskId);

        // Try to extract and display agent response
        const agentResponse = utils.extractAgentResponse(result);
        if (agentResponse) {
            addMessage(agentResponse, SENDER.AGENT, chatState.currentTaskId);
            chatState.currentTaskId = null;
        }
        
        // Start polling if task is still active
        if (chatState.currentTaskId) {
            addProcessingMessage();
            startTaskPolling();
        }

    } catch (error) {
        console.error('Error sending message:', error);
        utils.showToast('Error: ' + error.message, 'error');
        addMessage('Error: ' + error.message, SENDER.STATUS);
    }
}

/**
 * Start polling for task status updates
 * Uses centralized polling utility from api.js
 * @async
 */
function startTaskPolling() {
    if (!chatState.currentTaskId) return;
    
    // Cancel any existing polling
    if (chatState.pollingController) {
        chatState.pollingController.cancel();
    }

    // Start new polling with cancellation control
    chatState.pollingController = api.pollTaskWithBackoff(
        chatState.currentTaskId,
        handleTaskUpdate,
        handleTaskError
    );
}

/**
 * Handle task status updates during polling
 * @param {Object} task - Task object with status and history
 * @param {boolean} isTerminal - Whether task is in terminal state
 */
function handleTaskUpdate(task, isTerminal) {
    removeProcessingMessage();

    const state = task.status.state;
    
    if (state === TASK_STATE.COMPLETED) {
        // Extract and display agent response
        const responseText = utils.extractTaskResponse(task);
        if (responseText) {
            addMessage(responseText, SENDER.AGENT, task.task_id);
        }
        chatState.currentTaskId = null;
        chatState.pollingController = null;
        
    } else if (state === TASK_STATE.FAILED) {
        addMessage('Task failed: ' + (task.status.error || 'Unknown error'), SENDER.STATUS);
        chatState.currentTaskId = null;
        chatState.pollingController = null;
        
    } else if (state === TASK_STATE.CANCELED) {
        addMessage('Task was canceled', SENDER.STATUS);
        chatState.currentTaskId = null;
        chatState.pollingController = null;
        
    } else {
        // Still processing, show indicator
        addProcessingMessage();
    }
}

/**
 * Handle task polling errors
 * @param {Error} error - Error object
 */
function handleTaskError(error) {
    console.error('Error polling task status:', error);
    removeProcessingMessage();
    utils.showToast('Error getting task status: ' + error.message, 'error');
    addMessage('Error getting task status: ' + error.message, SENDER.STATUS);
    chatState.currentTaskId = null;
}

// ============================================================================
// UI RENDERING FUNCTIONS
// ============================================================================

/**
 * Add a message to the chat interface
 * @param {string} content - Message content
 * @param {string} sender - Message sender ('user', 'agent', or 'status')
 * @param {string|null} [taskId=null] - Optional task ID for the message
 */
function addMessage(content, sender, taskId = null) {
    const messagesDiv = domCache.get('messages');
    const messageDiv = document.createElement('div');
    
    if (sender === SENDER.USER) {
        messageDiv.className = 'flex justify-end';
        messageDiv.innerHTML = `
          <div class="max-w-2xl px-4 py-2 bg-primary-green text-white rounded-full ${taskId ? 'cursor-help' : ''}" ${taskId ? `data-task-id="${taskId}"` : ''}>
            <div class="flex items-center">
              <p class="text-lg m-0">${utils.escapeHtml(content)}</p>
            </div>
          </div>
        `;
    } else if (sender === SENDER.AGENT) {
        messageDiv.className = 'flex justify-start';
        const parsedContent = marked.parse(content);
        const messageId = api.generateId();
        messageDiv.innerHTML = `
            <div class="group max-w-2xl px-4 py-3 text-gray-900 ${taskId ? 'cursor-help' : ''}" ${taskId ? `data-task-id="${taskId}"` : ''}>
              <div class="text-lg prose max-w-none message-content" data-message-id="${messageId}">${parsedContent}</div>
              <div class="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 message-actions" data-message-id="${messageId}">
                <button class="copy-btn p-2 rounded-md hover:bg-gray-200 transition-colors duration-200 transform hover:scale-110" title="Copy message" data-message-id="${messageId}">
                  ${utils.createMessageIcon('copy')}
                </button>
                <button class="like-btn p-2 rounded-md hover:bg-green-100 transition-all duration-200 transform hover:scale-110" title="Like" data-message-id="${messageId}">
                  ${utils.createMessageIcon('like')}
                </button>
                <button class="dislike-btn p-2 rounded-md hover:bg-red-100 transition-all duration-200 transform hover:scale-110" title="Dislike" data-message-id="${messageId}">
                  ${utils.createMessageIcon('dislike')}
                </button>
              </div>
            </div>
          `;
    } else if (sender === SENDER.STATUS) {
        messageDiv.className = 'flex justify-center';
        messageDiv.innerHTML = `
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 max-w-md text-center">
            <p class="text-base text-yellow-800 italic">${utils.escapeHtml(content)}</p>
          </div>
        `;
    }

    messagesDiv.appendChild(messageDiv);
    utils.scrollToBottom(messagesDiv);
}

/**
 * Add a processing indicator message
 * Shows visual feedback while agent is processing
 */
function addProcessingMessage() {
    removeProcessingMessage();
    
    const messagesDiv = domCache.get('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex justify-start';
    messageDiv.id = 'processing-message';
    messageDiv.innerHTML = `
        <div class="max-w-2xl px-3 py-2 bg-gray-100 text-gray-900 rounded-full border border-gray-200 inline-flex items-center gap-3" role="status" aria-live="polite">
          <div class="flex items-center">
            <span class="text-sm text-gray-600">Agent is thinking...</span>
          </div>
        </div>
      `;
    
    messagesDiv.appendChild(messageDiv);
    utils.scrollToBottom(messagesDiv);
}

/**
 * Remove the processing indicator message
 */
function removeProcessingMessage() {
    const processingMessage = document.getElementById('processing-message');
    if (processingMessage) {
        processingMessage.remove();
    }
}

// ============================================================================
// MESSAGE ACTION HANDLERS
// ============================================================================

/**
 * Copy a message to clipboard
 * @param {string} messageId - ID of the message to copy
 * @async
 */
async function copyMessage(messageId) {
    const messageContent = document.querySelector(`.message-content[data-message-id="${messageId}"]`);
    if (messageContent) {
        const text = messageContent.textContent || messageContent.innerText;
        const success = await utils.copyToClipboard(text);
        if (success) {
            showCopyFeedback(messageId);
            utils.showToast('Message copied to clipboard', 'success');
        } else {
            utils.showToast('Failed to copy message', 'error');
        }
    }
}

/**
 * Show visual feedback when a message is copied
 * @param {string} messageId - ID of the copied message
 */
function showCopyFeedback(messageId) {
    const copyBtn = document.querySelector(`.copy-btn[data-message-id="${messageId}"]`);
    if (copyBtn) {
        const originalIcon = copyBtn.innerHTML;
        copyBtn.innerHTML = utils.createMessageIcon('copySuccess', 'w-4 h-4 text-green-500');
        copyBtn.classList.add('animate-pulse');
        setTimeout(() => {
            copyBtn.innerHTML = originalIcon;
            copyBtn.classList.remove('animate-pulse');
        }, 1000);
    }
}

/**
 * Toggle like status for a message
 * @param {string} messageId - ID of the message to like
 */
function likeMessage(messageId) {
    utils.toggleReaction(messageId, 'like');
}

/**
 * Toggle dislike status for a message
 * @param {string} messageId - ID of the message to dislike
 */
function dislikeMessage(messageId) {
    utils.toggleReaction(messageId, 'dislike');
}

// ============================================================================
// CONTEXT & CHAT MANAGEMENT
// ============================================================================

/**
 * Clear all messages from the chat
 */
function clearChat() {
    const messagesDiv = domCache.get('messages');
    messagesDiv.innerHTML = '';
    addMessage('Chat cleared. Start a new conversation!', SENDER.STATUS);
}

/**
 * Create a new conversation context
 */
function newContext() {
    chatState.contextId = api.generateId();
    addMessage('New context started', SENDER.STATUS);
    renderContexts();
}

/**
 * Render the current context in the sidebar
 */
function renderContexts() {
    const contextsList = domCache.get('contexts-list');
    contextsList.innerHTML = `
        <div class="w-full text-left p-3 rounded-lg border bg-primary-green text-white border-primary-green">
            <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-white"></div>
                <span class="text-sm font-medium">Context: ${chatState.contextId.substring(0, 8)}...</span>
            </div>
        </div>
    `;
}

// ============================================================================
// UI INTERACTION HANDLERS
// ============================================================================

/**
 * Toggle the sidebar collapsed/expanded state
 */
function toggleSidebar() {
    const sidebar = domCache.get('sidebar');
    const toggleIcon = domCache.get('toggle-icon');
    const isCollapsed = sidebar.classList.contains('collapsed');
    
    if (isCollapsed) {
        sidebar.classList.remove('collapsed');
        sidebar.style.width = '320px';
        toggleIcon.innerHTML = utils.createIcon('chevron-right', 'w-4 h-4');
    } else {
        sidebar.classList.add('collapsed');
        sidebar.style.width = '64px';
        toggleIcon.innerHTML = utils.createIcon('chevron-left', 'w-4 h-4');
    }
}

/**
 * Initialize all icons in the chat interface
 * Uses centralized icon utilities from common.js
 */
function initializeIcons() {
    domCache.get('toggle-icon').innerHTML = utils.createIcon('chevron-right', 'w-4 h-4');
    domCache.get('new-context-icon').innerHTML = utils.createIcon('plus', 'w-4 h-4');
    domCache.get('clear-icon').innerHTML = utils.createIcon('trash', 'w-4 h-4');
    domCache.get('settings-icon').innerHTML = utils.createIcon('cog', 'w-4 h-4');
    domCache.get('send-icon').innerHTML = utils.createIcon('paper-airplane', 'w-4 h-4');
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize the chat page on DOM ready
 * Sets up state, UI, and event listeners
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize context ID using API's ID generator for consistency
    chatState.contextId = api.generateId();
    
    // Initialize UI
    initializeIcons();
    renderContexts();
    
    // Set up event listeners
    domCache.get('send-btn').addEventListener('click', sendMessage);
    domCache.get('message-input').addEventListener('keypress', handleKeyPress);
    domCache.get('clear-chat').addEventListener('click', clearChat);
    domCache.get('new-context').addEventListener('click', newContext);
    domCache.get('toggle-sidebar').addEventListener('click', toggleSidebar);
    
    // Event delegation for message action buttons
    domCache.get('messages').addEventListener('click', function(event) {
        const target = event.target.closest('button');
        if (!target) return;
        
        const messageId = target.getAttribute('data-message-id');
        if (!messageId) return;
        
        if (target.classList.contains('copy-btn')) {
            copyMessage(messageId);
        } else if (target.classList.contains('like-btn')) {
            likeMessage(messageId);
        } else if (target.classList.contains('dislike-btn')) {
            dislikeMessage(messageId);
        }
    });
});
