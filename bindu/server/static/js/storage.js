/**
 * Storage page logic
 * Handles displaying contexts and tasks from storage
 * @module storage
 */

/**
 * Configuration constants for storage page
 * @const
 */
const CONFIG = {
    MAX_ITEMS: 100,
    TRUNCATE_LENGTH: 100,
    REFRESH_DELAY: 100
};

/**
 * State management
 */
let tasks = [];
let contexts = [];
let currentView = 'contexts';

/**
 * Load tasks from API and update UI
 * Uses centralized API method for data processing
 * @async
 */
async function loadTasks() {
    try {
        tasks = await api.getTasksGrouped(null, CONFIG.MAX_ITEMS);
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

/**
 * Load contexts from API and update UI
 * Uses centralized API method for data processing
 * @async
 */
async function loadContexts() {
    try {
        contexts = await api.getContextsGrouped(CONFIG.MAX_ITEMS);
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

/**
 * Display functions
 */

/**
 * Update statistics display with current task and context counts
 * Calculates stats in a single pass for optimal performance
 */
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

/**
 * Display tasks in the task list
 * Uses centralized task card component from utils
 */
function displayTasks() {
    const taskList = document.getElementById('task-list');
    
    if (tasks.length === 0) {
        taskList.innerHTML = utils.createEmptyState('Start a conversation in the chat to see task history here', 'document-text', 'w-16 h-16');
        return;
    }

    taskList.innerHTML = tasks.map(task => utils.createTaskCard(task, false, CONFIG.TRUNCATE_LENGTH)).join('');
}

/**
 * Display contexts in the contexts list
 * Uses centralized context card component from utils
 */
function displayContexts() {
    const contextsList = document.getElementById('contexts-list');
    
    if (contexts.length === 0) {
        contextsList.innerHTML = utils.createEmptyState('Start a conversation to create contexts with tasks', 'archive-box', 'w-16 h-16');
        return;
    }

    contextsList.innerHTML = contexts.map(context => utils.createContextCard(context)).join('');
}

/**
 * View management functions
 */

/**
 * Switch between contexts and tasks view
 * @param {string} view - View to switch to ('contexts' or 'tasks')
 */
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

/**
 * Toggle context tasks visibility
 * Loads and displays tasks for a specific context
 * @param {string} contextId - Context ID to toggle
 */
function toggleContext(contextId) {
    const tasksDiv = document.getElementById(`context-tasks-${contextId}`);
    const toggleSpan = document.getElementById(`toggle-${contextId}`);
    
    if (tasksDiv.classList.contains('hidden')) {
        // Load and display tasks for this context
        const contextTasks = tasks.filter(t => t.context_id === contextId);
        if (contextTasks.length > 0) {
            // Use centralized task card component with compact mode
            tasksDiv.innerHTML = contextTasks.map(task => 
                `<div class="border-b border-gray-100 last:border-b-0">${utils.createTaskCard(task, true, CONFIG.TRUNCATE_LENGTH)}</div>`
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
