/**
 * Chat page logic
 * Handles chat interface, messaging, and task polling
 * @module chat
 */

// State management
let contextId = null;
let currentTaskId = null;
let pollingInterval = 1000; // Start with 1 second
const MAX_POLLING_INTERVAL = 5000; // Max 5 seconds

// DOM element cache
let cachedElements = {};

function getCachedElement(id) {
    if (!cachedElements[id]) {
        cachedElements[id] = document.getElementById(id);
    }
    return cachedElements[id];
}

/**
 * Create a message action icon using common icon utilities
 * @param {string} iconName - Icon name (copy, check, like, dislike)
 * @param {string} [className='w-4 h-4'] - CSS classes for the icon
 * @returns {string} HTML string for the icon
 */
function createMessageIcon(iconName, className = 'w-4 h-4') {
    const iconMap = {
        copy: 'clipboard',
        copySuccess: 'check',
        like: 'thumb-up',
        dislike: 'thumb-down'
    };
    return utils.createIcon(iconMap[iconName] || iconName, className);
}

/**
 * Handle key press events in the message input
 * Debounced to prevent multiple rapid submissions
 */
const handleKeyPress = utils.debounce(function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}, 300);

/**
 * Send a message to the agent
 * Handles message creation, API call, and UI updates
 * @async
 */
async function sendMessage() {
    const input = getCachedElement('message-input');
    const message = input.value.trim();

    if (!message) return;

    input.value = '';
    const sendButton = getCachedElement('send-btn');
    sendButton.disabled = true;
    
    // Reset polling interval for new message
    pollingInterval = 1000;

    try {
        const messageId = api.generateId();
        const taskId = api.generateId();
        if (!contextId) {
            contextId = api.generateId();
        }

        // Use API method to send chat message
        const result = await api.sendChatMessage(contextId, message, messageId, taskId);
        console.log('Backend response:', result);

        // Store task ID from the result
        currentTaskId = result.task_id;

        if (result.context_id) {
            contextId = result.context_id;
        }

        addMessage(message, 'user', currentTaskId);

        // Try to display agent message from possible fields
        if (result) {
            if (result.reply) {
                addMessage(result.reply, 'agent', currentTaskId);
                currentTaskId = null;
            } else if (result.content) {
                addMessage(result.content, 'agent', currentTaskId);
                currentTaskId = null;
            } else if (result.messages && result.messages.length > 0) {
                const agentMsg = result.messages.find(m => m.role === 'assistant' || m.role === 'agent');
                if (agentMsg && agentMsg.content) {
                    addMessage(agentMsg.content, 'agent', currentTaskId);
                    currentTaskId = null;
                }
            }
        }
        if (currentTaskId) {
            // Add processing indicator and start polling for task completion
            addProcessingMessage();
            pollTaskStatus();
        }

    } catch (error) {
        console.error('Error sending message:', error);
        utils.showToast('Error: ' + error.message, 'error');
        addMessage('Error: ' + error.message, 'status');
    } finally {
        sendButton.disabled = false;
    }
}

/**
 * Poll task status until completion
 * Uses exponential backoff for polling interval
 * @async
 */
async function pollTaskStatus() {
    if (!currentTaskId) return;

    try {
        // Use API method to get task status
        const task = await api.getTaskStatus(currentTaskId);

        // Remove processing message
        removeProcessingMessage();

        if (task.status.state === 'completed') {
            // Extract the agent's response from the latest message in history
            if (task.history && task.history.length > 0) {
                // Find the last message with role 'agent' or 'assistant'
                const lastAgentMessage = [...task.history].reverse().find(msg => msg.role === 'agent' || msg.role === 'assistant');
                if (lastAgentMessage && lastAgentMessage.parts && lastAgentMessage.parts.length > 0) {
                    const textPart = lastAgentMessage.parts.find(part => part.kind === 'text');
                    if (textPart) {
                        addMessage(textPart.text, 'agent', task.task_id);
                    }
                }
            }
            currentTaskId = null;
        } else if (task.status.state === 'failed') {
            addMessage('Task failed: ' + (task.status.error || 'Unknown error'), 'status');
            currentTaskId = null;
        } else if (task.status.state === 'canceled') {
            addMessage('Task was canceled', 'status');
            currentTaskId = null;
        } else {
            // Still processing, add processing message back and poll again with backoff
            addProcessingMessage();
            pollingInterval = Math.min(pollingInterval * 1.5, MAX_POLLING_INTERVAL);
            setTimeout(pollTaskStatus, pollingInterval);
        }

    } catch (error) {
        console.error('Error polling task status:', error);
        removeProcessingMessage();
        utils.showToast('Error getting task status: ' + error.message, 'error');
        addMessage('Error getting task status: ' + error.message, 'status');
        currentTaskId = null;
    }
}

/**
 * Add a message to the chat interface
 * @param {string} content - Message content
 * @param {string} sender - Message sender ('user', 'agent', or 'status')
 * @param {string|null} [taskId=null] - Optional task ID for the message
 */
function addMessage(content, sender, taskId = null) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    
    if (sender === 'user') {
        messageDiv.className = 'flex justify-end';
        messageDiv.innerHTML = `
          <div class="max-w-2xl px-4 py-2 bg-primary-green text-white rounded-full ${taskId ? 'cursor-help' : ''}" ${taskId ? `data-task-id="${taskId}"` : ''}>
            <div class="flex items-center">
              <p class="text-lg m-0">${utils.escapeHtml(content)}</p>
            </div>
          </div>
        `;
    } else if (sender === 'agent') {
        messageDiv.className = 'flex justify-start';
        const parsedContent = marked.parse(content);
        const messageId = api.generateId();
        messageDiv.innerHTML = `
            <div class="group max-w-2xl px-4 py-3 text-gray-900 ${taskId ? 'cursor-help' : ''}" ${taskId ? `data-task-id="${taskId}"` : ''}>
              <div class="text-lg prose max-w-none message-content" data-message-id="${messageId}">${parsedContent}</div>
              <div class="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 message-actions" data-message-id="${messageId}">
                <button class="copy-btn p-2 rounded-md hover:bg-gray-200 transition-colors duration-200 transform hover:scale-110" title="Copy message" data-message-id="${messageId}">
                  ${createMessageIcon('copy')}
                </button>
                <button class="like-btn p-2 rounded-md hover:bg-green-100 transition-all duration-200 transform hover:scale-110" title="Like" data-message-id="${messageId}">
                  ${createMessageIcon('like')}
                </button>
                <button class="dislike-btn p-2 rounded-md hover:bg-red-100 transition-all duration-200 transform hover:scale-110" title="Dislike" data-message-id="${messageId}">
                  ${createMessageIcon('dislike')}
                </button>
              </div>
            </div>
          `;
    } else if (sender === 'status') {
        messageDiv.className = 'flex justify-center';
        messageDiv.innerHTML = `
          <div class="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 max-w-md text-center">
            <p class="text-base text-yellow-800 italic">${utils.escapeHtml(content)}</p>
          </div>
        `;
    }

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * Add a processing indicator message
 */
function addProcessingMessage() {
    removeProcessingMessage();
    
    const messagesDiv = getCachedElement('messages');
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
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
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
        copyBtn.innerHTML = createMessageIcon('copySuccess', 'w-4 h-4 text-green-500');
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
    const likeBtn = document.querySelector(`.like-btn[data-message-id="${messageId}"]`);
    const dislikeBtn = document.querySelector(`.dislike-btn[data-message-id="${messageId}"]`);
    
    if (likeBtn && dislikeBtn) {
        if (likeBtn.classList.contains('liked')) {
            // Unlike
            likeBtn.classList.remove('liked', 'text-green-500');
            likeBtn.innerHTML = createMessageIcon('like');
        } else {
            // Like
            likeBtn.classList.add('liked', 'text-green-500');
            likeBtn.innerHTML = createMessageIcon('like', 'w-4 h-4 text-green-500');
            // Remove dislike if present
            dislikeBtn.classList.remove('disliked', 'text-red-500');
            dislikeBtn.innerHTML = createMessageIcon('dislike');
        }
    }
}

/**
 * Toggle dislike status for a message
 * @param {string} messageId - ID of the message to dislike
 */
function dislikeMessage(messageId) {
    const dislikeBtn = document.querySelector(`.dislike-btn[data-message-id="${messageId}"]`);
    const likeBtn = document.querySelector(`.like-btn[data-message-id="${messageId}"]`);
    
    if (dislikeBtn && likeBtn) {
        if (dislikeBtn.classList.contains('disliked')) {
            // Undislike
            dislikeBtn.classList.remove('disliked', 'text-red-500');
            dislikeBtn.innerHTML = createMessageIcon('dislike');
        } else {
            // Dislike
            dislikeBtn.classList.add('disliked', 'text-red-500');
            dislikeBtn.innerHTML = createMessageIcon('dislike', 'w-4 h-4 text-red-500');
            // Remove like if present
            likeBtn.classList.remove('liked', 'text-green-500');
            likeBtn.innerHTML = createMessageIcon('like');
        }
    }
}

/**
 * Clear all messages from the chat
 */
function clearChat() {
    const messagesDiv = getCachedElement('messages');
    messagesDiv.innerHTML = '';
    addMessage('Chat cleared. Start a new conversation!', 'status');
}

/**
 * Create a new conversation context
 */
function newContext() {
    contextId = api.generateId();
    addMessage('New context started', 'status');
    renderContexts();
}

/**
 * Render the current context in the sidebar
 */
function renderContexts() {
    const contextsList = getCachedElement('contexts-list');
    contextsList.innerHTML = `
        <div class="w-full text-left p-3 rounded-lg border bg-primary-green text-white border-primary-green">
            <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-white"></div>
                <span class="text-sm font-medium">Context: ${contextId.substring(0, 8)}...</span>
            </div>
        </div>
    `;
}

/**
 * Toggle the sidebar collapsed/expanded state
 */
function toggleSidebar() {
    const sidebar = getCachedElement('sidebar');
    const toggleIcon = getCachedElement('toggle-icon');
    const isCollapsed = sidebar.classList.contains('collapsed');
    
    if (isCollapsed) {
        sidebar.classList.remove('collapsed');
        sidebar.style.width = '320px';
        // Change to right-pointing chevron (expand)
        toggleIcon.innerHTML = createChatIcon('chevron-right', 'w-4 h-4');
    } else {
        sidebar.classList.add('collapsed');
        sidebar.style.width = '64px';
        // Change to left-pointing chevron (collapse)
        toggleIcon.innerHTML = createChatIcon('chevron-left', 'w-4 h-4');
    }
}

/**
 * Create a chat UI icon using common utilities
 * @param {string} iconName - Icon name from common ICON_MAP
 * @param {string} [className='w-4 h-4'] - CSS classes for the icon
 * @returns {string} HTML string for the icon
 */
function createChatIcon(iconName, className = 'w-4 h-4') {
    return utils.createIcon(iconName, className);
}

/**
 * Initialize all icons in the chat interface
 */
function initializeIcons() {
    // Initialize sidebar icons
    getCachedElement('toggle-icon').innerHTML = createChatIcon('chevron-right', 'w-4 h-4');
    getCachedElement('new-context-icon').innerHTML = createChatIcon('plus', 'w-4 h-4');
    getCachedElement('clear-icon').innerHTML = createChatIcon('trash', 'w-4 h-4');
    getCachedElement('settings-icon').innerHTML = createChatIcon('cog', 'w-4 h-4');
    getCachedElement('send-icon').innerHTML = createChatIcon('paper-airplane', 'w-4 h-4');
}

/**
 * Initialize the chat page on DOM ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize context ID
    contextId = utils.generateUUID();
    
    // Initialize UI
    initializeIcons();
    renderContexts();
    
    // Set up event listeners
    getCachedElement('send-btn').addEventListener('click', sendMessage);
    getCachedElement('message-input').addEventListener('keypress', handleKeyPress);
    getCachedElement('clear-chat').addEventListener('click', clearChat);
    getCachedElement('new-context').addEventListener('click', newContext);
    getCachedElement('toggle-sidebar').addEventListener('click', toggleSidebar);
    
    // Event delegation for message action buttons
    getCachedElement('messages').addEventListener('click', function(event) {
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
