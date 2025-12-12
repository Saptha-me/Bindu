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

// Authentication State
let authToken = localStorage.getItem('bindu_auth_token') || null;

// Payment State
let paymentToken = null;
let pendingPaymentRequest = null;

// ============================================================================
// Payment Management
// ============================================================================

async function handlePaymentRequired(originalRequest) {
    try {
        addMessage('Time to pay the piper!', 'status');

        // Start payment session (no auth required - public endpoint)
        const sessionResponse = await fetch(`${BASE_URL}/api/start-payment-session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!sessionResponse.ok) {
            throw new Error('Failed to start payment session');
        }

        const sessionData = await sessionResponse.json();
        const { session_id, browser_url } = sessionData;

        addMessage(`🌐 Opening payment page...`, 'status');

        // Open payment page in new window
        const paymentWindow = window.open(browser_url, '_blank', 'width=600,height=800');

        if (!paymentWindow) {
            addMessage('❌ Please allow popups to complete payment', 'status');
            return false;
        }

        addMessage('Waiting for your wallet to wake up...', 'status');

        // Poll for payment completion
        const maxAttempts = 60; // 5 minutes (5 second intervals)
        let attempts = 0;

        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
            attempts++;

            const statusResponse = await fetch(`${BASE_URL}/api/payment-status/${session_id}`);

            if (!statusResponse.ok) continue;

            const statusData = await statusResponse.json();

            if (statusData.status === 'completed' && statusData.payment_token) {
                paymentToken = statusData.payment_token;
                addMessage('💰 Payment approved! Your agent is now caffeinated.', 'status');

                // Close payment window if still open
                if (paymentWindow && !paymentWindow.closed) {
                    paymentWindow.close();
                }

                return true;
            }

            if (statusData.status === 'failed') {
                addMessage('❌ Payment failed: ' + (statusData.error || 'Unknown error'), 'status');
                return false;
            }
        }

        addMessage('⏱️ Payment timeout. Please try again.', 'status');
        return false;

    } catch (error) {
        console.error('Payment error:', error);
        addMessage('❌ Payment error: ' + error.message, 'status');
        return false;
    }
}

function getPaymentHeaders() {
    if (!paymentToken) return {};

    // Ensure payment token is properly encoded
    const cleanToken = paymentToken.trim();

    // Check for non-ASCII characters
    if (!/^[\x00-\x7F]*$/.test(cleanToken)) {
        console.error('Payment token contains non-ASCII characters');
        paymentToken = null;
        return {};
    }

    return { 'X-PAYMENT': cleanToken };
}

// ============================================================================
// Authentication Management
// ============================================================================

function getAuthHeaders() {
    if (!authToken) return {};

    // Ensure token is properly encoded (trim and validate ASCII)
    const cleanToken = authToken.trim();

    // Check for non-ASCII characters that would cause ISO-8859-1 errors
    if (!/^[\x00-\x7F]*$/.test(cleanToken)) {
        console.error('Auth token contains non-ASCII characters');
        addMessage('⚠️ Invalid auth token format. Please re-enter your token.', 'status');
        authToken = null;
        localStorage.removeItem('bindu_auth_token');
        return {};
    }

    return { 'Authorization': `Bearer ${cleanToken}` };
}

function openAuthSettings() {
    const token = prompt('Enter JWT token (leave empty to clear):');
    if (token !== null) {
        authToken = token || null;
        if (authToken) {
            localStorage.setItem('bindu_auth_token', authToken);
            addMessage('✅ Token saved', 'status');
        } else {
            localStorage.removeItem('bindu_auth_token');
            addMessage('Token cleared', 'status');
        }
    }
}

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
// Collapsible Section Management
// ============================================================================

function toggleSection(sectionId) {
    const content = document.getElementById(`${sectionId}-content`);
    const header = content.previousElementSibling;
    const icon = header.querySelector('.toggle-icon');

    if (content.classList.contains('expanded')) {
        content.classList.remove('expanded');
        content.classList.add('collapsed');
        icon.style.transform = 'rotate(-90deg)';
    } else {
        content.classList.remove('collapsed');
        content.classList.add('expanded');
        icon.style.transform = 'rotate(0deg)';
    }
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

        // Load DID document
        let didDocument = null;
        try {
            // Extract DID from manifest capabilities - look for extension with uri starting with "did:"
            const didExtension = manifest.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));
            console.log('DID Extension found:', didExtension);

            if (didExtension && didExtension.uri) {
                console.log('Resolving DID:', didExtension.uri);
                const didResponse = await fetch(`${BASE_URL}/did/resolve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ did: didExtension.uri })
                });
                console.log('DID Response status:', didResponse.status);
                if (didResponse.ok) {
                    didDocument = await didResponse.json();
                    console.log('DID Document loaded:', didDocument);
                } else {
                    const errorText = await didResponse.text();
                    console.error('DID resolution failed:', errorText);
                }
            } else {
                console.warn('No DID found in manifest capabilities');
            }
        } catch (error) {
            console.error('Error loading DID document:', error);
        }

        agentInfo = { manifest, skills: skillsData.skills || [], didDocument };
        displayAgentInfo();
        displaySkills();
    } catch (error) {
        console.error('Error loading agent info:', error);
        document.getElementById('agent-card-content').innerHTML =
            '<div class="error" style="display:block;">Failed to load agent information</div>';
    }
}

function displayAgentInfo() {
    if (!agentInfo) return;

    const { manifest, didDocument } = agentInfo;

    // Update header with agent name and metadata
    const headerName = document.getElementById('agent-name-header');
    const headerSubtitle = document.getElementById('agent-subtitle');
    const headerMetadata = document.getElementById('agent-metadata');

    if (headerName) {
        headerName.textContent = manifest.name || 'Bindu Agent';
    }

    if (headerSubtitle) {
        headerSubtitle.textContent = manifest.description || 'A Bindu agent';
    }

    if (headerMetadata) {
        const didExtension = manifest.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));

        // Get full URL with port from manifest or current window location
        let urlWithPort = manifest.url || manifest.uri || window.location.origin;
        // Remove protocol but keep host:port
        urlWithPort = urlWithPort.replace(/^https?:\/\//, '');
        // Remove any trailing path
        urlWithPort = urlWithPort.split('/')[0];

        // Get Bindu version from manifest metadata or capabilities
        const binduVersion = manifest.bindu_version || manifest.metadata?.bindu_version || '0.1.0';

        // Check if agent has x402 payment requirements
        const hasPaywall = manifest.capabilities?.extensions?.some(ext =>
            ext.uri?.includes('x402') || ext.uri?.includes('payment')
        ) || manifest.execution_cost || manifest.paymentRequired;

        // Check if agent requires authentication
        const requiresAuth = manifest.auth?.enabled ||
            manifest.authentication_required ||
            manifest.capabilities?.authentication ||
            manifest.security?.authentication_required;

        headerMetadata.innerHTML = `
            <span class="metadata-badge">Bindu v${binduVersion}</span>
            <span class="metadata-badge">Protocol v${manifest.protocolVersion || '0.2.5'}</span>
            <span class="metadata-badge">${urlWithPort}</span>
        `;

        // Show badge if payment or auth is required
        const paywallBadge = document.getElementById('paywall-badge');
        if (paywallBadge && (hasPaywall || requiresAuth)) {
            let badgeText = '';
            if (hasPaywall && requiresAuth) {
                badgeText = '💰🔐 Paid + Auth';
            } else if (hasPaywall) {
                badgeText = '💰 Behind Paywall';
            } else if (requiresAuth) {
                badgeText = '🔐 Behind Auth';
            }
            paywallBadge.textContent = badgeText;
            paywallBadge.style.display = 'inline-block';
        }
    }

    // 1. Display Agent Overview (Left Column)
    const cardContainer = document.getElementById('agent-card-content');
    const didExtension = manifest.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));
    const author = didExtension?.params?.author || 'Unknown';

    let cardHtml = `
        <table class="info-table">
            <tr>
                <td>Author</td>
                <td>${author}</td>
            </tr>
            <tr>
                <td>Version</td>
                <td>${manifest.version || 'N/A'}</td>
            </tr>
            ${manifest.url ? `
                <tr>
                    <td>URL</td>
                    <td>${manifest.url}</td>
                </tr>
            ` : ''}
            ${manifest.protocolVersion ? `
                <tr>
                    <td>Protocol</td>
                    <td>${manifest.protocolVersion}</td>
                </tr>
            ` : ''}
            ${manifest.capabilities?.streaming ? `
                <tr>
                    <td>Streaming</td>
                    <td>✓ Supported</td>
                </tr>
            ` : ''}
        </table>
    `;

    cardContainer.innerHTML = cardHtml;

    // 2. Display DID Summary (Left Column, below agent card)
    const didContainer = document.getElementById('did-summary-content');
    if (didDocument) {
        const authKey = didDocument.authentication?.[0];

        let didHtml = `
            <table class="did-table">
                <tr>
                    <td>DID</td>
                    <td>
                        <div class="did-value-with-copy">
                            <div class="did-value">${didDocument.id || 'N/A'}</div>
                            <button class="copy-inline-btn" onclick="copyToClipboard('${didDocument.id}', this)" title="Copy DID">📋</button>
                        </div>
                    </td>
                </tr>
                ${authKey ? `
                    <tr>
                        <td>Public Key</td>
                        <td>
                            <div class="did-value-with-copy">
                                <div class="did-value">${authKey.publicKeyBase58 || 'N/A'}</div>
                                <button class="copy-inline-btn" onclick="copyToClipboard('${authKey.publicKeyBase58}', this)" title="Copy Public Key">📋</button>
                            </div>
                        </td>
                    </tr>
                ` : ''}
            </table>
        `;

        didContainer.innerHTML = didHtml;
    } else {
        didContainer.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 12px;">DID information not available</div>';
    }

    // 3. Display Agent Card JSON (Right Side)
    const agentJsonDisplay = document.getElementById('agent-json-display');
    const agentJsonString = JSON.stringify(manifest, null, 2);
    agentJsonDisplay.textContent = agentJsonString;
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

    const jsonString = JSON.stringify(agentInfo.manifest, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
        const btn = document.querySelector('.copy-json-btn');
        if (btn) {
            const originalText = btn.textContent;
            btn.textContent = '✓ Copied!';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function copyDIDJSON() {
    if (!agentInfo || !agentInfo.didDocument) return;

    const jsonString = JSON.stringify(agentInfo.didDocument, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
        const btns = document.querySelectorAll('.copy-json-btn');
        const btn = btns[1]; // Second button is DID Document
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = '✓';
        setTimeout(() => {
            button.textContent = originalText;
        }, 1500);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function displaySkills() {
    if (!agentInfo || !agentInfo.skills) return;

    const summaryContainer = document.getElementById('skills-summary-content');
    const { skills } = agentInfo;

    if (skills.length === 0) {
        summaryContainer.innerHTML = '<div style="color: #9ca3af; font-size: 11px;">No skills available</div>';
    } else {
        // Map skill names to icons
        const skillIcons = {
            'question-answering': '💬',
            'pdf-processing': '📄',
            'text-generation': '✍️',
            'image-generation': '🎨',
            'code-generation': '💻',
            'data-analysis': '📊',
            'translation': '🌐',
            'summarization': '📝'
        };

        let html = skills.map(skill => {
            const skillName = skill.name || skill.id || 'Unknown Skill';
            const icon = skillIcons[skillName] || skillIcons[skill.id] || '⚡';
            const description = skill.description || '';
            const truncatedDesc = description.length > 60 ? description.substring(0, 60) + '...' : description;

            return `
                <div class="skill-item" onclick="openSkillModal('${skill.id}')">
                    <div class="skill-header">
                        <span class="skill-icon">${icon}</span>
                        <span class="skill-name">${skillName}</span>
                    </div>
                    ${truncatedDesc ? `<div class="skill-description">${truncatedDesc}</div>` : ''}
                </div>
            `;
        }).join('');
        summaryContainer.innerHTML = html;
    }
}

async function openSkillModal(skillId) {
    const modal = document.getElementById('skill-modal');
    const modalBody = document.getElementById('skill-modal-body');
    const modalTitle = document.getElementById('skill-modal-title');

    modal.style.display = 'flex';
    modalBody.innerHTML = '<div class="loading">Loading skill details...</div>';
    modalTitle.textContent = 'Skill Details';

    try {
        const response = await fetch(`${BASE_URL}/agent/skills/${skillId}`);
        if (!response.ok) throw new Error('Failed to load skill details');

        const skillData = await response.json();
        displaySkillDetails(skillData);
    } catch (error) {
        console.error('Error loading skill details:', error);
        modalBody.innerHTML = '<div class="error" style="display:block;">Failed to load skill details</div>';
    }
}

function displaySkillDetails(skill) {
    const modalTitle = document.getElementById('skill-modal-title');
    const modalBody = document.getElementById('skill-modal-body');

    modalTitle.textContent = skill.name || skill.id;

    let html = `
        <div class="skill-detail-section">
            <h3>Description</h3>
            <p>${skill.description || 'No description available'}</p>
        </div>

        ${skill.tags && skill.tags.length > 0 ? `
            <div class="skill-detail-section">
                <h3>Tags</h3>
                <div class="skill-tags">
                    ${skill.tags.map(tag => `<span class="skill-tag">${tag}</span>`).join('')}
                </div>
            </div>
        ` : ''}

        ${skill.examples && skill.examples.length > 0 ? `
            <div class="skill-detail-section">
                <h3>Example Queries</h3>
                <ul class="skill-examples">
                    ${skill.examples.map(ex => `<li>"${ex}"</li>`).join('')}
                </ul>
            </div>
        ` : ''}

        ${skill.input_modes && skill.input_modes.length > 0 ? `
            <div class="skill-detail-section">
                <h3>Input Modes</h3>
                <p>${skill.input_modes.join(', ')}</p>
            </div>
        ` : ''}

        ${skill.output_modes && skill.output_modes.length > 0 ? `
            <div class="skill-detail-section">
                <h3>Output Modes</h3>
                <p>${skill.output_modes.join(', ')}</p>
            </div>
        ` : ''}

        ${skill.version ? `
            <div class="skill-detail-section">
                <h3>Version</h3>
                <p>${skill.version}</p>
            </div>
        ` : ''}

        ${skill.performance ? `
            <div class="skill-detail-section">
                <h3>Performance</h3>
                <p>Avg Processing Time: ${skill.performance.avg_processing_time_ms}ms</p>
                <p>Max Concurrent Requests: ${skill.performance.max_concurrent_requests}</p>
            </div>
        ` : ''}
    `;

    modalBody.innerHTML = html;
}

function closeSkillModal() {
    const modal = document.getElementById('skill-modal');
    modal.style.display = 'none';
}

// ============================================================================
// Context Management
// ============================================================================

async function loadContexts() {
    try {
        console.log('Loading contexts...');
        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                ...getPaymentHeaders()
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'contexts/list',
                params: { length: 50 },
                id: generateId()
            })
        });

        console.log('Contexts response status:', response.status);

        // Handle 401 Unauthorized
        if (response.status === 401) {
            console.warn('Authentication required for contexts');
            addMessage('🔒 Authentication required to load contexts. Please provide your JWT token.', 'status');
            return;
        }

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
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                ...getPaymentHeaders()
            },
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
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                ...getPaymentHeaders()
            },
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
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                ...getPaymentHeaders()
            },
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

        const requestBody = {
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
        };

        const response = await fetch(`${BASE_URL}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                ...getPaymentHeaders()
            },
            body: JSON.stringify(requestBody)
        });

        // Handle 401 Unauthorized (Auth Required)
        if (response.status === 401) {
            addMessage('🔒 Authentication required. Please provide your JWT token.', 'status');
            openAuthSettings();
            throw new Error('Authentication required');
        }

        // Handle 402 Payment Required
        if (response.status === 402) {
            const paymentSuccess = await handlePaymentRequired(requestBody);
            if (paymentSuccess) {
                // Retry the exact same request with payment token
                const retryResponse = await fetch(`${BASE_URL}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...getAuthHeaders(),
                        ...getPaymentHeaders()
                    },
                    body: JSON.stringify(requestBody)
                });

                if (!retryResponse.ok) throw new Error('Failed to send message after payment');

                const result = await retryResponse.json();
                if (result.error) throw new Error(result.error.message || 'Unknown error');

                const task = result.result;
                const taskContextId = task.context_id || task.contextId;

                console.log('Payment retry successful, received task:', {
                    taskId: task.id,
                    contextId: taskContextId
                });

                // Continue with normal flow
                // Keep payment token for this task (will be cleared when task reaches terminal state)
                currentTaskId = task.id;

                if (taskContextId) {
                    const isNewContext = !contextId;
                    contextId = taskContextId;
                    updateContextIndicator();

                    if (isNewContext) {
                        await loadContexts();
                    }
                }

                const displayMessage = replyToTaskId
                    ? `↩️ Replying to task ${replyToTaskId.substring(0, 8)}...\n\n${message}`
                    : message;
                addMessage(displayMessage, 'user', task.id);

                clearReply();
                addThinkingIndicator('thinking-indicator', task.id);
                pollTaskStatus(task.id);

                return;
            } else {
                throw new Error('Payment required but not completed');
            }
        }

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

        // Add thinking indicator immediately
        addThinkingIndicator('thinking-indicator', task.id);

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
    const thinkingId = 'thinking-indicator';

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
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                    ...getPaymentHeaders()
                },
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
                 console.log('Task status update:', task);
                if (state === 'completed') {
                    const responseText = extractResponse(task);
                    addMessage(responseText, 'agent', taskId, state);
                }
                else if (state === 'failed') {
                    const error =
                        task.metadata?.error ||
                        task.metadata?.error_message ||
                        task.status?.error ||
                        task.error ||
                        'Task failed';

                    addMessage(`❌ Task failed: ${error}`, 'status');
                    const responseText = extractResponse(task);
                    addMessage(responseText, 'agent', taskId, state)
                }

                else {
                    addMessage('⚠️ Task was canceled', 'status');
                }

                // Clear payment token when task reaches terminal state
                // Next message will create NEW task and require NEW payment
                if (paymentToken) {
                    console.log('Task completed - clearing payment token for next task');
                    paymentToken = null;
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
                ...getAuthHeaders(),
                ...getPaymentHeaders()
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
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                ...getPaymentHeaders()
            },
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
    const feedbackModal = document.getElementById('feedback-modal');
    const skillModal = document.getElementById('skill-modal');

    feedbackModal.addEventListener('click', (e) => {
        if (e.target === feedbackModal) {
            closeFeedbackModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && feedbackModal.style.display === 'flex') {
            closeFeedbackModal();
        }

        if (skillModal && skillModal.style.display === 'flex') {
            closeSkillModal();
        }
    });
});
