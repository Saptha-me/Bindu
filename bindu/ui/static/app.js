// Bindu Agent Chat Interface - Main Application Logic

// Global State
let agentInfo = null;

// Task Management (A2A Protocol Compliant)
// - currentTaskId: Last task ID
// - currentTaskState: State of current task (input-required, completed, etc.)
// - Non-terminal states (input-required, auth-required): REUSE same task ID
// - Terminal states (completed, failed, canceled): CREATE new task with referenceTaskIds
let currentTaskId = null;
let currentTaskState = null;  // Track if task is terminal or non-terminal
let contextId = null;
let replyToTaskId = null;  // Explicit reply target (set by clicking agent message)
let taskHistory = [];
let contexts = [];
const BASE_URL = window.location.origin;

// ============================================================================
// Tab Management
// ============================================================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
}

// ============================================================================
// Agent Info Management
// ============================================================================

async function loadAgentInfo() {
    try {
        const manifestResponse = await fetch(`${BASE_URL}/.well-known/agent.json`);
        const manifest = manifestResponse.ok ? await manifestResponse.json() : {};

        const skillsResponse = await fetch(`${BASE_URL}/agent/skills`);
        const skillsData = skillsResponse.ok ? await skillsResponse.json() : { skills: [] };

        agentInfo = { manifest, skills: skillsData.skills || [] };
        displayAgentInfo();
        displaySkills();
    } catch (error) {
        console.error('Error loading agent info:', error);
        document.getElementById('agent-info-content').innerHTML =
            '<div class="error" style="display:block;">Failed to load agent information</div>';
    }
}

function displayAgentInfo() {
    if (!agentInfo) return;

    const { manifest } = agentInfo;
    const container = document.getElementById('agent-info-content');
    
    // Format JSON with syntax highlighting
    const jsonString = JSON.stringify(manifest, null, 4);
    
    let html = `
        <div class="info-section">
            <h3>${manifest.name || 'Unknown Agent'}</h3>
            <p style="color: #666; font-size: 11px; margin-top: 8px;">${manifest.description || 'No description available'}</p>
        </div>
        
        <div class="info-section">
            <h3>Details</h3>
            <div class="info-grid">
                <div class="info-label">Author:</div>
                <div class="info-value">${manifest.capabilities?.extensions?.[0]?.params?.author || 'Unknown'}</div>
                
                <div class="info-label">Version:</div>
                <div class="info-value">${manifest.version || 'N/A'}</div>
                
                ${manifest.url ? `
                    <div class="info-label">URL:</div>
                    <div class="info-value">${manifest.url}</div>
                ` : ''}
            </div>
        </div>
        
        <div class="info-section">
            <h3>Complete Agent Card (JSON)</h3>
            <div class="json-viewer">
                <button class="copy-json-btn" onclick="copyAgentCardJSON()">📋 Copy JSON</button>
                <pre><code>${escapeHtml(jsonString)}</code></pre>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function copyAgentCardJSON() {
    if (!agentInfo || !agentInfo.manifest) return;
    
    const jsonString = JSON.stringify(agentInfo.manifest, null, 4);
    navigator.clipboard.writeText(jsonString).then(() => {
        const btn = document.querySelector('.copy-json-btn');
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function displaySkills() {
    if (!agentInfo || !agentInfo.skills) return;

    const container = document.getElementById('skills-content');
    const { skills } = agentInfo;

    if (skills.length === 0) {
        container.innerHTML = '<div class="loading">No skills available</div>';
        return;
    }

    let html = skills.map(skill => `
        <div class="skill-item">
            <div class="skill-name">${skill.name || skill.id || 'Unknown Skill'}</div>
            ${skill.description ? `<div class="skill-description">${skill.description}</div>` : ''}
        </div>
    `).join('');

    container.innerHTML = html;
}

// ============================================================================
// Context Management
// ============================================================================

async function loadContexts() {
    try {
        console.log('Loading contexts...');
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'contexts/list',
                params: { length: 50 },
                id: generateId()
            })
        });

        console.log('Contexts response status:', response.status);

        if (!response.ok) throw new Error('Failed to load contexts');

        const result = await response.json();
        console.log('Contexts result:', result);
        
        if (result.error) {
            console.error('Contexts error:', result.error);
            throw new Error(result.error.message || 'Unknown error');
        }

        const serverContexts = result.result || [];
        console.log('Server contexts:', serverContexts);
        
        // Transform server contexts to UI format
        contexts = serverContexts.map(ctx => ({
            id: ctx.context_id,
            taskCount: ctx.task_count || 0,
            taskIds: ctx.task_ids || [],
            timestamp: Date.now(), // Will be updated when we load tasks
            firstMessage: 'Loading...'
        }));

        console.log('Transformed contexts:', contexts);

        // Load first message for each context
        for (const ctx of contexts) {
            if (ctx.taskIds.length > 0) {
                await loadContextPreview(ctx);
            }
        }

        updateContextList();
    } catch (error) {
        console.error('Error loading contexts:', error);
        // Show empty state if no contexts
        updateContextList();
    }
}

async function loadContextPreview(ctx) {
    try {
        // Get the first task to extract the first message
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'tasks/get',
                params: { taskId: ctx.taskIds[0] },
                id: generateId()
            })
        });

        if (!response.ok) return;

        const result = await response.json();
        if (result.error) return;

        const task = result.result;
        const history = task.history || [];
        
        // Find first user message
        for (const msg of history) {
            if (msg.role === 'user') {
                const parts = msg.parts || [];
                const textParts = parts
                    .filter(part => part.kind === 'text')
                    .map(part => part.text);
                if (textParts.length > 0) {
                    ctx.firstMessage = textParts[0].substring(0, 50);
                    break;
                }
            }
        }

        // Update timestamp from task
        if (task.status && task.status.timestamp) {
            ctx.timestamp = new Date(task.status.timestamp).getTime();
        }
    } catch (error) {
        console.error('Error loading context preview:', error);
    }
}

function createNewContext() {
    contextId = null;
    currentTaskId = null;
    currentTaskState = null;
    replyToTaskId = null;
    document.getElementById('chat-messages').innerHTML = '';
    clearReply();
    updateContextIndicator();
    updateContextList();
}

function updateContextIndicator() {
    const indicator = document.getElementById('context-indicator-text');
    if (contextId) {
        const shortId = contextId.substring(0, 8);
        indicator.textContent = `Active Context: ${shortId}`;
    } else {
        indicator.textContent = 'No active context - Start a new conversation';
    }
}

function updateContextList() {
    const container = document.getElementById('context-list');
    
    if (contexts.length === 0) {
        container.innerHTML = '<div class="loading">No contexts yet</div>';
        return;
    }

    // Sort contexts by timestamp (most recent first)
    const sortedContexts = [...contexts].sort((a, b) => b.timestamp - a.timestamp);

    let html = sortedContexts.map((ctx, index) => {
        const isActive = ctx.id === contextId;
        const time = formatTime(ctx.timestamp);
        const preview = ctx.firstMessage || 'New conversation';
        const taskCount = ctx.taskCount || 0;
        const contextShortId = ctx.id.substring(0, 8);
        const colorClass = getContextColor(index);
        
        return `
            <div class="context-item ${isActive ? 'active' : ''}" onclick="switchContext('${ctx.id}')">
                <div class="context-header">
                    <div class="context-badge ${colorClass}">${contextShortId}</div>
                    <div class="context-time">${time}</div>
                    <button class="context-clear-btn" onclick="event.stopPropagation(); confirmClearContext('${ctx.id}')" title="Clear context">×</button>
                </div>
                <div class="context-preview">${preview}</div>
                <div class="context-footer">
                    <span class="context-tasks">${taskCount} task${taskCount !== 1 ? 's' : ''}</span>
                    <span class="context-id-label">Context: ${contextShortId}</span>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function getContextColor(index) {
    const colors = ['color-blue', 'color-green', 'color-purple', 'color-orange', 'color-pink', 'color-teal'];
    return colors[index % colors.length];
}

async function switchContext(ctxId) {
    if (ctxId === contextId) return; // Already on this context

    try {
        // Clear current chat
        document.getElementById('chat-messages').innerHTML = '';
        contextId = ctxId;
        currentTaskId = null;
        currentTaskState = null;
        replyToTaskId = null;
        clearReply();

        // Find context
        const ctx = contexts.find(c => c.id === ctxId);
        if (!ctx) {
            showError('Context not found');
            return;
        }

        // Load all tasks for this context
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'tasks/list',
                params: { limit: 100, offset: 0 },
                id: generateId()
            })
        });

        if (!response.ok) throw new Error('Failed to load tasks');

        const result = await response.json();
        if (result.error) throw new Error(result.error.message || 'Unknown error');

        const allTasks = result.result || [];
        
        // Filter tasks for this context
        const contextTasks = allTasks.filter(task => task.context_id === ctxId);
        
        // Sort by timestamp
        contextTasks.sort((a, b) => {
            const timeA = new Date(a.status.timestamp).getTime();
            const timeB = new Date(b.status.timestamp).getTime();
            return timeA - timeB;
        });

        // Display all messages from tasks
        for (const task of contextTasks) {
            const history = task.history || [];
            for (const msg of history) {
                const parts = msg.parts || [];
                const textParts = parts
                    .filter(part => part.kind === 'text')
                    .map(part => part.text);
                
                if (textParts.length > 0) {
                    const text = textParts.join('\n');
                    const sender = msg.role === 'user' ? 'user' : 'agent';
                    const state = sender === 'agent' ? task.status.state : null;
                    addMessage(text, sender, task.id, state);
                }
            }
        }

        // Set current task to the last task
        if (contextTasks.length > 0) {
            const lastTask = contextTasks[contextTasks.length - 1];
            currentTaskId = lastTask.id;
            currentTaskState = lastTask.status.state;
        }

        updateContextIndicator();
        updateContextList();
    } catch (error) {
        console.error('Error switching context:', error);
        showError('Failed to load context: ' + error.message);
    }
}

function confirmClearContext(ctxId) {
    if (confirm('Are you sure you want to clear this context and all its tasks? This action cannot be undone.')) {
        clearContext(ctxId);
    }
}

async function clearContext(ctxId) {
    try {
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'contexts/clear',
                params: { contextId: ctxId },
                id: generateId()
            })
        });

        if (!response.ok) throw new Error('Failed to clear context');

        const result = await response.json();
        if (result.error) throw new Error(result.error.message || 'Unknown error');

        // Remove from local contexts
        contexts = contexts.filter(c => c.id !== ctxId);

        // If this was the active context, clear the chat
        if (contextId === ctxId) {
            createNewContext();
        } else {
            updateContextList();
        }

        addMessage('Context cleared successfully', 'status');
    } catch (error) {
        console.error('Error clearing context:', error);
        showError('Failed to clear context: ' + error.message);
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 24) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

// ============================================================================
// Chat Functions
// ============================================================================

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (!message) return;

    input.value = '';
    const sendButton = document.getElementById('send-button');
    sendButton.disabled = true;

    try {
        // Task ID logic based on A2A protocol:
        // - Non-terminal states (input-required, auth-required): REUSE task ID
        // - Terminal states (completed, failed, canceled): CREATE new task
        // - No current task: CREATE new task
        let taskId;
        const referenceTaskIds = [];
        
        const isNonTerminalState = currentTaskState && 
            (currentTaskState === 'input-required' || currentTaskState === 'auth-required');
        
        if (replyToTaskId) {
            // Explicit reply to a specific task - always create new task
            taskId = generateId();
            referenceTaskIds.push(replyToTaskId);
        } else if (isNonTerminalState && currentTaskId) {
            // Continue same task for non-terminal states
            taskId = currentTaskId;
        } else if (currentTaskId) {
            // Terminal state or no state - create new task, reference previous
            taskId = generateId();
            referenceTaskIds.push(currentTaskId);
        } else {
            // First message in conversation
            taskId = generateId();
        }
        
        const messageId = generateId();
        const newContextId = contextId || generateId();
        
        console.log('Sending message with:', {
            taskId,
            contextId: newContextId,
            existingContextId: contextId,
            isNewContext: !contextId
        });

        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'message/send',
                params: {
                    message: {
                        role: 'user',
                        parts: [{ kind: 'text', text: message }],
                        kind: 'message',
                        messageId: messageId,
                        contextId: newContextId,
                        taskId: taskId,
                        ...(referenceTaskIds.length > 0 && { referenceTaskIds })
                    },
                    configuration: {
                        acceptedOutputModes: ['application/json']
                    }
                },
                id: generateId()
            })
        });

        if (!response.ok) throw new Error('Failed to send message');

        const result = await response.json();
        if (result.error) throw new Error(result.error.message || 'Unknown error');

        const task = result.result;
        // Server uses snake_case (context_id), not camelCase (contextId)
        const taskContextId = task.context_id || task.contextId;
        
        console.log('Received task:', {
            taskId: task.id,
            contextId: taskContextId,
            context_id: task.context_id,
            previousContextId: contextId
        });
        
        // Update currentTaskId to the NEW task
        currentTaskId = task.id;
        
        // Check if this is a new context
        const isNewContext = taskContextId && !contextId;
        
        if (taskContextId) {
            contextId = taskContextId;
            updateContextIndicator();
        }
        
        console.log('After update:', {
            contextId,
            isNewContext
        });
        
        // Reload contexts if new context was created
        if (isNewContext) {
            await loadContexts();
        }

        const displayMessage = replyToTaskId 
            ? `↩️ Replying to task ${replyToTaskId.substring(0, 8)}...\n\n${message}`
            : message;
        addMessage(displayMessage, 'user', task.id);

        clearReply();
        pollTaskStatus(task.id);

    } catch (error) {
        console.error('Error sending message:', error);
        showError('Failed to send message: ' + error.message);
    } finally {
        sendButton.disabled = false;
    }
}

// ============================================================================
// Task Polling
// ============================================================================

let currentPollingTaskId = null;

async function pollTaskStatus(taskId) {
    let attempts = 0;
    const maxAttempts = 300;
    currentPollingTaskId = taskId;
    
    // Add thinking indicator with cancel button
    const thinkingId = 'thinking-indicator';
    addThinkingIndicator(thinkingId, taskId);

    const poll = async () => {
        if (attempts >= maxAttempts) {
            removeThinkingIndicator(thinkingId);
            addMessage('⏱️ Timeout: Task did not complete', 'status');
            currentTaskId = null;
            return;
        }

        attempts++;

        try {
            const response = await fetch(`${BASE_URL}/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'tasks/get',
                    params: { taskId: taskId },
                    id: generateId()
                })
            });

            if (!response.ok) throw new Error('Failed to get task status');

            const result = await response.json();
            if (result.error) throw new Error(result.error.message || 'Unknown error');

            const task = result.result;
            const state = task.status.state;

            // Terminal states - task is now IMMUTABLE
            if (state === 'completed' || state === 'failed' || state === 'canceled') {
                removeThinkingIndicator(thinkingId);
                currentPollingTaskId = null;
                // Keep currentTaskId and mark as terminal
                currentTaskId = taskId;
                currentTaskState = state;  // Terminal state
                if (!taskHistory.includes(taskId)) {
                    taskHistory.push(taskId);
                }

                if (state === 'completed') {
                    const responseText = extractResponse(task);
                    addMessage(responseText, 'agent', taskId, state);
                } else if (state === 'failed') {
                    const error = task.metadata?.error || 'Task failed';
                    addMessage(`❌ Task failed: ${error}`, 'status');
                } else {
                    addMessage('⚠️ Task was canceled', 'status');
                }
                
                // Reload contexts to update task counts
                await loadContexts();
            } 
            // Non-terminal states - task still MUTABLE, waiting for input
            else if (state === 'input-required' || state === 'auth-required') {
                removeThinkingIndicator(thinkingId);
                // Keep currentTaskId and mark as non-terminal
                currentTaskId = taskId;
                currentTaskState = state;  // Non-terminal state
                if (!taskHistory.includes(taskId)) {
                    taskHistory.push(taskId);
                }
                const responseText = extractResponse(task);
                addMessage(responseText, 'agent', taskId, state);
                
                // Reload contexts to update task counts
                await loadContexts();
            } 
            // Working states - continue polling
            else if (state === 'submitted' || state === 'working') {
                setTimeout(poll, 1000);
            }

        } catch (error) {
            console.error('Error polling task status:', error);
            removeThinkingIndicator(thinkingId);
            currentPollingTaskId = null;
            addMessage('Error getting task status: ' + error.message, 'status');
            currentTaskId = null;
        }
    };

    setTimeout(poll, 1000);
}

// ============================================================================
// Task Cancellation
// ============================================================================

async function cancelTask(taskId) {
    try {
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'tasks/cancel',
                params: {
                    taskId: taskId
                },
                id: taskId
            })
        });

        if (!response.ok) throw new Error('Failed to cancel task');

        const result = await response.json();
        if (result.error) {
            throw new Error(result.error.message || 'Unknown error');
        }

        // Stop polling
        currentPollingTaskId = null;
        removeThinkingIndicator('thinking-indicator');
        
        addMessage('⚠️ Task canceled successfully', 'status');
        
        // Reload contexts to update task counts
        await loadContexts();
        
        return result.result;
    } catch (error) {
        console.error('Error canceling task:', error);
        showError('Failed to cancel task: ' + error.message);
        throw error;
    }
}

function extractResponse(task) {
    const artifacts = task.artifacts || [];
    if (artifacts.length > 0) {
        const artifact = artifacts[artifacts.length - 1];
        const parts = artifact.parts || [];
        const textParts = parts
            .filter(part => part.kind === 'text')
            .map(part => part.text);
        if (textParts.length > 0) return textParts.join('\n');
    }

    const history = task.history || [];
    for (let i = history.length - 1; i >= 0; i--) {
        const msg = history[i];
        if (msg.role === 'assistant' || msg.role === 'agent') {
            const parts = msg.parts || [];
            const textParts = parts
                .filter(part => part.kind === 'text')
                .map(part => part.text);
            if (textParts.length > 0) return textParts.join('\n');
        }
    }

    return '✅ Task completed but no response found';
}

// ============================================================================
// Thinking Indicator
// ============================================================================

function addThinkingIndicator(id, taskId = null) {
    const messagesDiv = document.getElementById('chat-messages');
    
    // Remove any existing thinking indicator
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    
    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = id;
    thinkingDiv.className = 'message agent thinking';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const dotsDiv = document.createElement('div');
    dotsDiv.className = 'thinking-dots';
    dotsDiv.innerHTML = '<span>.</span><span>.</span><span>.</span>';
    contentDiv.appendChild(dotsDiv);
    
    // Add cancel button if taskId is provided
    if (taskId) {
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'cancel-task-btn';
        cancelBtn.innerHTML = '✕ Cancel';
        cancelBtn.onclick = async (e) => {
            e.stopPropagation();
            if (confirm('Are you sure you want to cancel this task?')) {
                await cancelTask(taskId);
            }
        };
        contentDiv.appendChild(cancelBtn);
    }
    
    thinkingDiv.appendChild(contentDiv);
    messagesDiv.appendChild(thinkingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function removeThinkingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

// ============================================================================
// Message Display
// ============================================================================

function addMessage(content, sender, taskId = null, state = null) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (sender === 'agent' && taskId) {
        messageDiv.style.cursor = 'pointer';
        messageDiv.onclick = () => setReplyTo(taskId);
    }

    if (sender === 'agent') {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    // Add feedback button inside content for completed agent tasks
    if (state && state.toLowerCase() === 'completed' && sender === 'agent' && taskId) {
        const feedbackBtn = document.createElement('button');
        feedbackBtn.className = 'feedback-btn-corner';
        feedbackBtn.innerHTML = '👍 Feedback';
        feedbackBtn.onclick = (e) => {
            e.stopPropagation();
            openFeedbackModal(taskId);
        };
        contentDiv.appendChild(feedbackBtn);
    }

    messageDiv.appendChild(contentDiv);

    if (taskId && state) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';
        metaDiv.innerHTML = `Task: ${taskId} <span class="task-badge ${state}">${state}</span>`;
        messageDiv.appendChild(metaDiv);
    }

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ============================================================================
// Reply Management
// ============================================================================

function setReplyTo(taskId) {
    replyToTaskId = taskId;
    const indicator = document.getElementById('reply-indicator');
    const text = document.getElementById('reply-text');
    text.textContent = `💬 Replying to task: ${taskId.substring(0, 8)}...`;
    indicator.classList.add('visible');
    document.getElementById('message-input').focus();
}

function clearReply() {
    replyToTaskId = null;
    document.getElementById('reply-indicator').classList.remove('visible');
}

// ============================================================================
// Feedback Management
// ============================================================================

function openFeedbackModal(taskId) {
    const modal = document.getElementById('feedback-modal');
    const taskIdSpan = document.getElementById('feedback-task-id');
    taskIdSpan.textContent = taskId;
    modal.dataset.taskId = taskId;
    modal.style.display = 'flex';
}

function closeFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    modal.style.display = 'none';
    document.getElementById('feedback-text').value = '';
    document.getElementById('feedback-rating').value = '5';
}

async function submitFeedback() {
    const modal = document.getElementById('feedback-modal');
    const taskId = modal.dataset.taskId;
    const feedback = document.getElementById('feedback-text').value.trim();
    const rating = parseInt(document.getElementById('feedback-rating').value);
    
    // Build params - always include feedback field (use default if empty)
    const params = {
        taskId: taskId,
        feedback: feedback || `Rating: ${rating}/5`,
        rating: rating,
        metadata: {
            source: 'web-ui',
            timestamp: new Date().toISOString()
        }
    };
    
    try {
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'tasks/feedback',
                params: params,
                id: generateId()
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(`Feedback error: ${data.error.message}`);
        } else {
            closeFeedbackModal();
            addMessage('Feedback submitted', 'status');
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        showError('Failed to submit feedback');
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

function showError(message) {
    const errorDiv = document.getElementById('chat-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    loadAgentInfo();
    loadContexts();
    
    // Modal event listeners
    const modal = document.getElementById('feedback-modal');
    
    // Close modal when clicking outside the modal content
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeFeedbackModal();
        }
    });
    
    // Close modal on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeFeedbackModal();
        }
    });
});
