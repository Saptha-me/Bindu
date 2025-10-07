// Storage page logic
// Handles displaying contexts and tasks from storage

let tasks = [];
let contexts = [];
let currentView = 'contexts';

// Helper functions
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function getStatusColor(state) {
    const colors = {
        completed: 'bg-green-100 text-green-800',
        failed: 'bg-red-100 text-red-800',
        running: 'bg-blue-100 text-blue-800',
        pending: 'bg-yellow-100 text-yellow-800',
        canceled: 'bg-gray-100 text-gray-800',
        working: 'bg-purple-100 text-purple-800'
    };
    return colors[state] || 'bg-gray-100 text-gray-800';
}

function getStatusIcon(state) {
    const icons = {
        completed: '✅',
        failed: '❌',
        running: '⚡',
        pending: '⏳',
        canceled: '🚫',
        working: '🔄'
    };
    return icons[state] || '❓';
}

// Component helper functions
function createEmptyState(icon, title, subtitle) {
    return `
        <div class="text-center py-12">
            <div class="text-gray-400 mb-4">
                <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${icon}
                </svg>
            </div>
            <p class="text-gray-600 text-lg font-medium">${title}</p>
            <p class="text-gray-500 mt-1">${subtitle}</p>
        </div>
    `;
}

function createErrorState(message, onRetry) {
    return `
        <div class="text-center py-12">
            <div class="text-gray-400 mb-4">
                <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
            </div>
            <p class="text-gray-600 text-lg font-medium">Error Loading Data</p>
            <p class="text-gray-500 mt-1">${message}</p>
            <button onclick="${onRetry}" class="mt-4 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors">
                Retry
            </button>
        </div>
    `;
}

function createStatRow(label, value, colorClass = 'text-gray-900') {
    return `
        <div class="flex justify-between items-center py-2 border-b border-gray-200">
            <span class="text-sm font-medium text-gray-600">${label}</span>
            <span class="text-sm font-semibold ${colorClass}">${value}</span>
        </div>
    `;
}

function createTaskCard(task) {
    const statusColor = getStatusColor(task.status?.state);
    const statusIcon = getStatusIcon(task.status?.state);
    const latestMessage = task.history?.[task.history.length - 1]?.parts?.[0]?.text || 'No content';
    const truncatedMessage = latestMessage.substring(0, 100) + (latestMessage.length > 100 ? '...' : '');
    
    return `
        <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors duration-200">
            <div class="flex items-start justify-between">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-2">
                        <span class="text-lg">${statusIcon}</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor}">
                            ${task.status?.state || 'unknown'}
                        </span>
                        <span class="text-xs text-gray-500 font-mono">
                            ${task.task_id?.substring(0, 8)}...
                        </span>
                    </div>
                    
                    <div class="text-sm text-gray-600 mb-2">
                        <strong>Context:</strong> ${task.context_id?.substring(0, 8)}...
                    </div>
                    
                    ${task.history?.length > 0 ? `
                        <div class="text-sm text-gray-900">
                            <strong>Latest Message:</strong> ${truncatedMessage}
                        </div>
                    ` : ''}
                </div>
                
                <div class="flex-shrink-0 ml-4">
                    <button onclick="viewTask('${task.task_id}')" 
                            class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        View Details
                    </button>
                </div>
            </div>
            
            ${task.status?.error ? `
                <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p class="text-sm text-red-800">
                        <strong>Error:</strong> ${task.status.error}
                    </p>
                </div>
            ` : ''}
        </div>
    `;
}

function createContextCard(contextData) {
    const contextId = contextData.context_id;
    const taskCount = contextData.task_count || 0;
    
    return `
        <div class="border border-gray-200 rounded-lg overflow-hidden">
            <div class="bg-gray-50 p-4 border-b border-gray-200">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <span class="text-lg">🗂️</span>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">
                                Context ${contextId?.substring(0, 8)}...
                            </h3>
                            <p class="text-sm text-gray-500">
                                ${taskCount} task${taskCount !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="toggleContext('${contextId}')" 
                                class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                            <span id="toggle-${contextId}">Show Tasks</span>
                        </button>
                        <button onclick="clearContext('${contextId}')" 
                                class="text-red-600 hover:text-red-800 text-sm font-medium">
                            Clear
                        </button>
                    </div>
                </div>
            </div>
            
            <div id="context-tasks-${contextId}" class="hidden">
                <div class="p-4 text-center text-gray-500">
                    Loading tasks...
                </div>
            </div>
        </div>
    `;
}

// API functions
async function loadTasks() {
    try {
        const payload = {
            jsonrpc: "2.0",
            method: "tasks/list",
            params: { length: 100 },
            id: generateUUID()
        };

        const response = await fetch('/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error.message || 'Unknown error');
        }
        
        // Parse the message arrays into task objects
        const rawData = result.result || [];
        tasks = [];
        
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
        
        updateStats();
        if (currentView === 'tasks') {
            displayTasks();
        }
        
    } catch (error) {
        console.error('Error loading tasks:', error);
        const taskList = document.getElementById('task-list');
        if (taskList) {
            taskList.innerHTML = createErrorState(error.message, 'loadTasks()');
        }
    }
}

async function loadContexts() {
    try {
        const payload = {
            jsonrpc: "2.0",
            method: "contexts/list",
            params: { length: 100 },
            id: generateUUID()
        };

        const response = await fetch('/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error.message || 'Unknown error');
        }
        
        // Parse the message arrays to extract unique contexts
        const rawData = result.result || [];
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
        contexts = Object.values(contextMap).map(context => ({
            ...context,
            task_count: context.task_ids.size,
            task_ids: undefined
        }));
        
        updateStats();
        if (currentView === 'contexts') {
            displayContexts();
        }
        
    } catch (error) {
        console.error('Error loading contexts:', error);
        const contextsList = document.getElementById('contexts-list');
        if (contextsList) {
            contextsList.innerHTML = createErrorState(error.message, 'loadContexts()');
        }
    }
}

// Display functions
function updateStats() {
    const totalContexts = contexts.length;
    const totalTasks = tasks.length;
    const activeTasks = tasks.filter(t => t.status?.state === 'running' || t.status?.state === 'pending').length;
    const completedTasks = tasks.filter(t => t.status?.state === 'completed').length;
    const failedTasks = tasks.filter(t => t.status?.state === 'failed').length;
    const canceledTasks = tasks.filter(t => t.status?.state === 'canceled').length;
    
    const storageStats = document.getElementById('storage-stats');
    if (storageStats) {
        storageStats.innerHTML = `
            <div class="space-y-3">
                ${createStatRow('Total Contexts', totalContexts)}
                ${createStatRow('Total Tasks', totalTasks)}
                ${createStatRow('Active Tasks', activeTasks, 'text-blue-600')}
                ${createStatRow('Completed', completedTasks, 'text-green-600')}
                ${createStatRow('Failed', failedTasks, 'text-red-600')}
                <div class="flex justify-between items-center py-2">
                    <span class="text-sm font-medium text-gray-600">Canceled</span>
                    <span class="text-sm font-semibold text-gray-600">${canceledTasks}</span>
                </div>
            </div>
        `;
    }
}

function displayTasks() {
    const taskList = document.getElementById('task-list');
    
    if (tasks.length === 0) {
        const emptyIcon = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>';
        taskList.innerHTML = createEmptyState(emptyIcon, 'No tasks found', 'Start a conversation in the chat to see task history here');
        return;
    }

    taskList.innerHTML = tasks.map(task => createTaskCard(task)).join('');
}

function displayContexts() {
    const contextsList = document.getElementById('contexts-list');
    
    if (contexts.length === 0) {
        const emptyIcon = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>';
        contextsList.innerHTML = createEmptyState(emptyIcon, 'No contexts found', 'Start a conversation to create contexts with tasks');
        return;
    }

    contextsList.innerHTML = contexts.map(context => createContextCard(context)).join('');
}

// View management
function switchView(view) {
    currentView = view;
    const contextsContainer = document.getElementById('contexts-container');
    const tasksContainer = document.getElementById('tasks-container');
    const contextsBtn = document.getElementById('contexts-view-btn');
    const tasksBtn = document.getElementById('tasks-view-btn');

    if (view === 'contexts') {
        contextsContainer.classList.remove('hidden');
        tasksContainer.classList.add('hidden');
        contextsBtn.classList.add('bg-yellow-500', 'text-white');
        contextsBtn.classList.remove('text-gray-600');
        tasksBtn.classList.remove('bg-yellow-500', 'text-white');
        tasksBtn.classList.add('text-gray-600');
        displayContexts();
    } else {
        contextsContainer.classList.add('hidden');
        tasksContainer.classList.remove('hidden');
        tasksBtn.classList.add('bg-yellow-500', 'text-white');
        tasksBtn.classList.remove('text-gray-600');
        contextsBtn.classList.remove('bg-yellow-500', 'text-white');
        contextsBtn.classList.add('text-gray-600');
        displayTasks();
    }
}

function toggleContext(contextId) {
    const tasksDiv = document.getElementById(`context-tasks-${contextId}`);
    const toggleSpan = document.getElementById(`toggle-${contextId}`);
    
    if (tasksDiv.classList.contains('hidden')) {
        // Load and display tasks for this context
        const contextTasks = tasks.filter(t => t.context_id === contextId);
        if (contextTasks.length > 0) {
            tasksDiv.innerHTML = contextTasks.map(task => {
                const statusColor = getStatusColor(task.status?.state);
                const statusIcon = getStatusIcon(task.status?.state);
                const latestMessage = task.history?.[task.history.length - 1]?.parts?.[0]?.text || 'No content';
                const truncatedMessage = latestMessage.substring(0, 100) + (latestMessage.length > 100 ? '...' : '');
                
                return `
                    <div class="p-4 border-b border-gray-100 last:border-b-0">
                        <div class="flex items-start justify-between">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-3 mb-2">
                                    <span class="text-lg">${statusIcon}</span>
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor}">
                                        ${task.status?.state || 'unknown'}
                                    </span>
                                    <span class="text-xs text-gray-500 font-mono">
                                        ${task.task_id?.substring(0, 8)}...
                                    </span>
                                </div>
                                
                                ${task.history?.length > 0 ? `
                                    <div class="text-sm text-gray-900">
                                        <strong>Messages (${task.history.length}):</strong> ${truncatedMessage}
                                    </div>
                                ` : ''}
                            </div>
                            
                            <div class="flex-shrink-0 ml-4">
                                <button onclick="viewTask('${task.task_id}')" 
                                        class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                                    View
                                </button>
                            </div>
                        </div>
                        
                        ${task.status?.error ? `
                            <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                                <p class="text-sm text-red-800">
                                    <strong>Error:</strong> ${task.status.error}
                                </p>
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
        } else {
            tasksDiv.innerHTML = '<div class="p-4 text-center text-gray-500">No tasks in this context</div>';
        }
        
        tasksDiv.classList.remove('hidden');
        toggleSpan.textContent = 'Hide Tasks';
    } else {
        tasksDiv.classList.add('hidden');
        toggleSpan.textContent = 'Show Tasks';
    }
}

// Action functions
async function clearStorage() {
    if (!confirm('Are you sure you want to clear all task history? This action cannot be undone.')) {
        return;
    }

    try {
        const payload = {
            jsonrpc: "2.0",
            method: "contexts/clear",
            params: {},
            id: generateUUID()
        };

        const response = await fetch('/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error.message || 'Unknown error');
        }

        tasks = [];
        contexts = [];
        updateStats();
        if (currentView === 'contexts') {
            displayContexts();
        } else {
            displayTasks();
        }
        
        utils.showToast('All tasks and contexts cleared successfully', 'success');
    } catch (error) {
        console.error('Error clearing storage:', error);
        utils.showToast('Failed to clear storage: ' + error.message, 'error');
    }
}

async function clearContext(contextId) {
    if (!confirm('Are you sure you want to clear this context and all its tasks?')) {
        return;
    }

    try {
        const payload = {
            jsonrpc: "2.0",
            method: "contexts/clear",
            params: { context_id: contextId },
            id: generateUUID()
        };

        const response = await fetch('/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error.message || 'Unknown error');
        }

        utils.showToast('Context cleared successfully', 'success');
        refreshData();
        
    } catch (error) {
        console.error('Error clearing context:', error);
        utils.showToast('Failed to clear context: ' + error.message, 'error');
    }
}

function viewTask(taskId) {
    const task = tasks.find(t => t.task_id === taskId);
    if (task) {
        alert(`Task Details:\n\nID: ${task.task_id}\nStatus: ${task.status?.state}\nContext: ${task.context_id}\n\nHistory: ${task.history?.length || 0} messages`);
    }
}

function refreshData() {
    loadTasks();
    loadContexts();
}

// Add icons to headers and buttons
function initializeIcons() {
    // Button icons
    const contextsIcon = document.getElementById('contexts-icon');
    if (contextsIcon) {
        contextsIcon.innerHTML = utils.createIcon('archive-box', 'w-4 h-4');
    }
    
    const tasksIcon = document.getElementById('tasks-icon');
    if (tasksIcon) {
        tasksIcon.innerHTML = utils.createIcon('document-text', 'w-4 h-4');
    }
    
    const refreshIcon = document.getElementById('refresh-icon');
    if (refreshIcon) {
        refreshIcon.innerHTML = utils.createIcon('arrow-path', 'w-4 h-4');
    }
    
    const clearIcon = document.getElementById('clear-icon');
    if (clearIcon) {
        clearIcon.innerHTML = utils.createIcon('trash', 'w-4 h-4');
    }
    
    // Section header icons
    const contextsHeader = document.getElementById('contexts-header');
    if (contextsHeader) {
        contextsHeader.insertAdjacentHTML('afterbegin', utils.createIcon('archive-box', 'w-5 h-5 text-yellow-600'));
    }
    
    const tasksHeader = document.getElementById('tasks-header');
    if (tasksHeader) {
        tasksHeader.insertAdjacentHTML('afterbegin', utils.createIcon('document-text', 'w-5 h-5 text-yellow-600'));
    }
    
    const statsHeader = document.getElementById('stats-header');
    if (statsHeader) {
        statsHeader.insertAdjacentHTML('afterbegin', utils.createIcon('chart-bar', 'w-5 h-5 text-yellow-600'));
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeIcons();
    loadTasks();
    loadContexts();
    setTimeout(() => {
        switchView('contexts');
    }, 100);
});
