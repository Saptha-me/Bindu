// Storage page logic
// Handles displaying contexts and tasks from storage

// Constants
const CONFIG = {
    MAX_ITEMS: 100,
    TRUNCATE_LENGTH: 100,
    REFRESH_DELAY: 100
};

let tasks = [];
let contexts = [];
let currentView = 'contexts';

// Helper functions specific to storage page

function createTaskCard(task, isCompact = false) {
    const statusColor = utils.getStatusColor(task.status?.state);
    const statusIcon = utils.getStatusIcon(task.status?.state);
    const latestMessage = task.history?.[task.history.length - 1]?.parts?.[0]?.text || 'No content';
    const truncatedMessage = utils.truncateText(latestMessage, CONFIG.TRUNCATE_LENGTH);
    
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
                    <button data-action="view-task" data-task-id="${task.task_id}" 
                            class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        ${isCompact ? 'View' : 'View Details'}
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
                        <button data-action="toggle-context" data-context-id="${contextId}" 
                                class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                            <span id="toggle-${contextId}">Show Tasks</span>
                        </button>
                        <button data-action="clear-context" data-context-id="${contextId}" 
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
        const rawData = await api.listTasks(null, CONFIG.MAX_ITEMS);
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
            taskList.innerHTML = utils.createErrorState(error.message, 'loadTasks()');
        }
    }
}

async function loadContexts() {
    try {
        const rawData = await api.listContexts(CONFIG.MAX_ITEMS);
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
            contextsList.innerHTML = utils.createErrorState(error.message, 'loadContexts()');
        }
    }
}

// Display functions
function updateStats() {
    const totalContexts = contexts.length;
    const totalTasks = tasks.length;
    
    // Single pass through tasks array for better performance
    const stats = tasks.reduce((acc, task) => {
        const state = task.status?.state;
        if (state === 'running' || state === 'pending') acc.active++;
        else if (state === 'completed') acc.completed++;
        else if (state === 'failed') acc.failed++;
        else if (state === 'canceled') acc.canceled++;
        return acc;
    }, { active: 0, completed: 0, failed: 0, canceled: 0 });
    
    const storageStats = document.getElementById('storage-stats');
    if (storageStats) {
        storageStats.innerHTML = `
            <div class="space-y-3">
                ${utils.createStatRow('Total Contexts', totalContexts)}
                ${utils.createStatRow('Total Tasks', totalTasks)}
                ${utils.createStatRow('Active Tasks', stats.active, 'text-blue-600')}
                ${utils.createStatRow('Completed', stats.completed, 'text-green-600')}
                ${utils.createStatRow('Failed', stats.failed, 'text-red-600')}
                ${utils.createStatRow('Canceled', stats.canceled, 'text-gray-600')}
            </div>
        `;
    }
}

function displayTasks() {
    const taskList = document.getElementById('task-list');
    
    if (tasks.length === 0) {
        taskList.innerHTML = utils.createEmptyState('Start a conversation in the chat to see task history here', 'document-text', 'w-16 h-16');
        return;
    }

    taskList.innerHTML = tasks.map(task => createTaskCard(task)).join('');
}

function displayContexts() {
    const contextsList = document.getElementById('contexts-list');
    
    if (contexts.length === 0) {
        contextsList.innerHTML = utils.createEmptyState('Start a conversation to create contexts with tasks', 'archive-box', 'w-16 h-16');
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
            // Reuse createTaskCard with compact mode
            tasksDiv.innerHTML = contextTasks.map(task => 
                `<div class="border-b border-gray-100 last:border-b-0">${createTaskCard(task, true)}</div>`
            ).join('');
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
        await api.clearAllStorage();

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

async function clearContextById(contextId) {
    if (!confirm('Are you sure you want to clear this context and all its tasks?')) {
        return;
    }

    try {
        await api.clearContext(contextId);
        utils.showToast('Context cleared successfully', 'success');
        refreshData();
    } catch (error) {
        console.error('Error clearing context:', error);
        utils.showToast('Failed to clear context: ' + error.message, 'error');
    }
}

function viewTask(taskId) {
    const task = tasks.find(t => t.task_id === taskId);
    if (!task) return;
    
    // TODO: Replace with proper modal component
    const details = [
        `ID: ${task.task_id}`,
        `Status: ${task.status?.state || 'unknown'}`,
        `Context: ${task.context_id}`,
        `History: ${task.history?.length || 0} messages`
    ].join('\n');
    
    alert(`Task Details:\n\n${details}`);
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
    }, CONFIG.REFRESH_DELAY);
    
    // Event delegation for better performance
    document.addEventListener('click', handleGlobalClick);
});

// Event delegation handler
function handleGlobalClick(e) {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    
    const action = target.dataset.action;
    const taskId = target.dataset.taskId;
    const contextId = target.dataset.contextId;
    
    switch(action) {
        case 'view-task':
            if (taskId) viewTask(taskId);
            break;
        case 'toggle-context':
            if (contextId) toggleContext(contextId);
            break;
        case 'clear-context':
            if (contextId) clearContextById(contextId);
            break;
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    document.removeEventListener('click', handleGlobalClick);
});
