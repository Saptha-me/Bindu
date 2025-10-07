// Utility functions (using common.js and api.js utilities)

// State management
let contextId = null;
let currentTaskId = null;

// Event handlers
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (!message) return;

    input.value = '';
    const sendButton = document.getElementById('send-btn');
    sendButton.disabled = true;

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
            // Still processing, add processing message back and poll again
            addProcessingMessage();
            setTimeout(pollTaskStatus, 1000);
        }

    } catch (error) {
        console.error('Error polling task status:', error);
        removeProcessingMessage();
        utils.showToast('Error getting task status: ' + error.message, 'error');
        addMessage('Error getting task status: ' + error.message, 'status');
        currentTaskId = null;
    }
}

// Message rendering
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
        const messageId = generateId();
        messageDiv.innerHTML = `
            <div class="group max-w-2xl px-4 py-3 text-gray-900 ${taskId ? 'cursor-help' : ''}" ${taskId ? `data-task-id="${taskId}"` : ''}>
              <div class="text-lg prose max-w-none message-content" data-message-id="${messageId}">${parsedContent}</div>
              <div class="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 message-actions" data-message-id="${messageId}">
                <button class="copy-btn p-2 rounded-md hover:bg-gray-200 transition-colors duration-200 transform hover:scale-110" title="Copy message" data-message-id="${messageId}">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                  </svg>
                </button>
                <button class="like-btn p-2 rounded-md hover:bg-green-100 transition-all duration-200 transform hover:scale-110" title="Like" data-message-id="${messageId}">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path>
                  </svg>
                </button>
                <button class="dislike-btn p-2 rounded-md hover:bg-red-100 transition-all duration-200 transform hover:scale-110" title="Dislike" data-message-id="${messageId}">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.737 3h4.017c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m6-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path>
                  </svg>
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

function addProcessingMessage() {
    removeProcessingMessage();
    
    const messagesDiv = document.getElementById('messages');
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

function removeProcessingMessage() {
    const processingMessage = document.getElementById('processing-message');
    if (processingMessage) {
        processingMessage.remove();
    }
}

// Message actions
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

function showCopyFeedback(messageId) {
    const copyBtn = document.querySelector(`.copy-btn[data-message-id="${messageId}"]`);
    if (copyBtn) {
        const originalIcon = copyBtn.innerHTML;
        copyBtn.innerHTML = `
            <svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
        `;
        copyBtn.classList.add('animate-pulse');
        setTimeout(() => {
            copyBtn.innerHTML = originalIcon;
            copyBtn.classList.remove('animate-pulse');
        }, 1000);
    }
}

function likeMessage(messageId) {
    const likeBtn = document.querySelector(`.like-btn[data-message-id="${messageId}"]`);
    const dislikeBtn = document.querySelector(`.dislike-btn[data-message-id="${messageId}"]`);
    
    if (likeBtn && dislikeBtn) {
        if (likeBtn.classList.contains('liked')) {
            // Unlike
            likeBtn.classList.remove('liked', 'text-green-500');
            likeBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path>
                </svg>
            `;
        } else {
            // Like
            likeBtn.classList.add('liked', 'text-green-500');
            likeBtn.innerHTML = `
                <svg class="w-4 h-4 text-green-500" fill="currentColor" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path>
                </svg>
            `;
            // Remove dislike if present
            dislikeBtn.classList.remove('disliked', 'text-red-500');
            dislikeBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.737 3h4.017c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m6-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path>
                </svg>
            `;
        }
    }
}

function dislikeMessage(messageId) {
    const dislikeBtn = document.querySelector(`.dislike-btn[data-message-id="${messageId}"]`);
    const likeBtn = document.querySelector(`.like-btn[data-message-id="${messageId}"]`);
    
    if (dislikeBtn && likeBtn) {
        if (dislikeBtn.classList.contains('disliked')) {
            // Undislike
            dislikeBtn.classList.remove('disliked', 'text-red-500');
            dislikeBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.737 3h4.017c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m6-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path>
                </svg>
            `;
        } else {
            // Dislike
            dislikeBtn.classList.add('disliked', 'text-red-500');
            dislikeBtn.innerHTML = `
                <svg class="w-4 h-4 text-red-500" fill="currentColor" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.737 3h4.017c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m6-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path>
                </svg>
            `;
            // Remove like if present
            likeBtn.classList.remove('liked', 'text-green-500');
            likeBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path>
                </svg>
            `;
        }
    }
}

// UI functions
function clearChat() {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = '';
    addMessage('Chat cleared. Start a new conversation!', 'status');
}

function newContext() {
    contextId = api.generateId();
    addMessage('New context started', 'status');
    renderContexts();
}

function renderContexts() {
    const contextsList = document.getElementById('contexts-list');
    contextsList.innerHTML = `
        <div class="w-full text-left p-3 rounded-lg border bg-primary-green text-white border-primary-green">
            <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-white"></div>
                <span class="text-sm font-medium">Context: ${contextId.substring(0, 8)}...</span>
            </div>
        </div>
    `;
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleIcon = document.getElementById('toggle-icon');
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

// Icon mappings (extending common icons)
const CHAT_ICON_MAP = {
    'chevron-right': 'heroicons:chevron-right-20-solid',
    'chevron-left': 'heroicons:chevron-left-20-solid',
    'plus': 'heroicons:plus-20-solid',
    'trash': 'heroicons:trash-20-solid',
    'cog': 'heroicons:cog-6-tooth-20-solid',
    'paper-airplane': 'heroicons:paper-airplane-20-solid'
};

function createChatIcon(iconName, className = 'w-4 h-4') {
    const iconId = CHAT_ICON_MAP[iconName] || CHAT_ICON_MAP['plus'];
    return `<iconify-icon icon="${iconId}" class="${className}"></iconify-icon>`;
}

function initializeIcons() {
    // Initialize sidebar icons
    document.getElementById('toggle-icon').innerHTML = createChatIcon('chevron-right', 'w-4 h-4');
    document.getElementById('new-context-icon').innerHTML = createChatIcon('plus', 'w-4 h-4');
    document.getElementById('clear-icon').innerHTML = createChatIcon('trash', 'w-4 h-4');
    document.getElementById('settings-icon').innerHTML = createChatIcon('cog', 'w-4 h-4');
    document.getElementById('send-icon').innerHTML = createChatIcon('paper-airplane', 'w-4 h-4');
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Initialize context ID
    contextId = utils.generateUUID();
    
    // Initialize UI
    initializeIcons();
    renderContexts();
    
    // Set up event listeners
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    document.getElementById('message-input').addEventListener('keypress', handleKeyPress);
    document.getElementById('clear-chat').addEventListener('click', clearChat);
    document.getElementById('new-context').addEventListener('click', newContext);
    document.getElementById('toggle-sidebar').addEventListener('click', toggleSidebar);
    
    // Event delegation for message action buttons
    document.getElementById('messages').addEventListener('click', function(event) {
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
