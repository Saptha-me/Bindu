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
 * Icon configuration for UI elements
 * @const
 */
const ICON_CONFIG = {
    buttons: [
        { id: 'contexts-icon', icon: 'archive-box', size: 'w-4 h-4' },
        { id: 'tasks-icon', icon: 'document-text', size: 'w-4 h-4' },
        { id: 'refresh-icon', icon: 'arrow-path', size: 'w-4 h-4' },
        { id: 'clear-icon', icon: 'trash', size: 'w-4 h-4' }
    ],
    headers: [
        { id: 'contexts-header', icon: 'archive-box', size: 'w-5 h-5 text-yellow-600' },
        { id: 'tasks-header', icon: 'document-text', size: 'w-5 h-5 text-yellow-600' },
        { id: 'stats-header', icon: 'chart-bar', size: 'w-5 h-5 text-yellow-600' }
    ]
};

/**
 * DOM element cache for performance optimization
 * @type {Object}
 */
const elements = {};

/**
 * Get cached DOM element
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} Cached element or null
 */
function getElement(id) {
    if (!elements[id]) {
        elements[id] = document.getElementById(id);
    }
    return elements[id];
}

/**
 * State management
 */
let tasks = [];
let contexts = [];
let currentView = 'contexts';

/**
 * Handle API errors with consistent error display
 * @param {Error} error - Error object
 * @param {string} elementId - Element ID to display error in
 * @param {string} context - Context for error logging
 */
function handleError(error, elementId, context) {
    console.error(`Error ${context}:`, error);
    const element = getElement(elementId);
    if (element) {
        element.innerHTML = utils.createErrorState(error.message, context);
    }
}

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
        handleError(error, 'task-list', 'loading tasks');
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
        handleError(error, 'contexts-list', 'loading contexts');
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

    const storageStats = getElement('storage-stats');
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
 * Render content to a container element
 * @param {string} elementId - Element ID to render into
 * @param {Array} items - Items to render
 * @param {Function} renderFn - Function to render each item
 * @param {string} emptyMessage - Message to show when no items
 * @param {string} emptyIcon - Icon to show when no items
 */
function renderList(elementId, items, renderFn, emptyMessage, emptyIcon) {
    const element = getElement(elementId);
    if (!element) return;

    if (items.length === 0) {
        element.innerHTML = utils.createEmptyState(emptyMessage, emptyIcon, 'w-16 h-16');
        return;
    }

    element.innerHTML = items.map(renderFn).join('');
}

/**
 * Display tasks in the task list
 * Uses centralized task card component from utils
 */
function displayTasks() {
    renderList(
        'task-list',
        tasks,
        task => utils.createTaskCard(task, false, CONFIG.TRUNCATE_LENGTH),
        'Start a conversation in the chat to see task history here',
        'document-text'
    );
}

/**
 * Display contexts in the contexts list
 * Uses centralized context card component from utils
 */
function displayContexts() {
    renderList(
        'contexts-list',
        contexts,
        context => utils.createContextCard(context),
        'Start a conversation to create contexts with tasks',
        'archive-box'
    );
}

/**
 * View management functions
 */

/**
 * Toggle button active state
 * @param {HTMLElement} activeBtn - Button to activate
 * @param {HTMLElement} inactiveBtn - Button to deactivate
 */
function toggleButtonState(activeBtn, inactiveBtn) {
    activeBtn.classList.add('bg-yellow-500', 'text-white');
    activeBtn.classList.remove('text-gray-600');
    inactiveBtn.classList.remove('bg-yellow-500', 'text-white');
    inactiveBtn.classList.add('text-gray-600');
}

/**
 * Switch between contexts and tasks view
 * @param {string} view - View to switch to ('contexts' or 'tasks')
 */
function switchView(view) {
    currentView = view;
    const contextsContainer = getElement('contexts-container');
    const tasksContainer = getElement('tasks-container');
    const contextsBtn = getElement('contexts-view-btn');
    const tasksBtn = getElement('tasks-view-btn');

    const isContextsView = view === 'contexts';

    // Toggle container visibility
    contextsContainer.classList.toggle('hidden', !isContextsView);
    tasksContainer.classList.toggle('hidden', isContextsView);

    // Toggle button states
    toggleButtonState(
        isContextsView ? contextsBtn : tasksBtn,
        isContextsView ? tasksBtn : contextsBtn
    );

    // Display appropriate content
    isContextsView ? displayContexts() : displayTasks();
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

/**
 * Action functions
 */

/**
 * Clear all storage (tasks and contexts)
 * Prompts user for confirmation before clearing
 * @async
 */
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

/**
 * Clear a specific context by ID
 * Prompts user for confirmation before clearing
 * @param {string} contextId - Context ID to clear
 * @async
 */
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

/**
 * View task details
 * TODO: Replace with proper modal component
 * @param {string} taskId - Task ID to view
 */
function viewTask(taskId) {
    const task = tasks.find(t => t.task_id === taskId);
    if (!task) return;

    const details = [
        `ID: ${task.task_id}`,
        `Status: ${task.status?.state || 'unknown'}`,
        `Context: ${task.context_id}`,
        `History: ${task.history?.length || 0} messages`
    ].join('\n');

    alert(`Task Details:\n\n${details}`);
}

/**
 * Refresh all data from API
 * Reloads both tasks and contexts
 */
function refreshData() {
    loadTasks();
    loadContexts();
}

/**
 * UI initialization functions
 */

/**
 * Initialize icons in headers and buttons
 * Uses centralized icon creation from utils and configuration
 */
function initializeIcons() {
    // Initialize button icons
    ICON_CONFIG.buttons.forEach(({ id, icon, size }) => {
        const element = getElement(id);
        if (element) {
            element.innerHTML = utils.createIcon(icon, size);
        }
    });

    // Initialize header icons
    ICON_CONFIG.headers.forEach(({ id, icon, size }) => {
        const element = getElement(id);
        if (element) {
            element.insertAdjacentHTML('afterbegin', utils.createIcon(icon, size));
        }
    });
}

/**
 * Event delegation handler for global click events
 * Handles all button actions using data attributes
 * @param {Event} e - Click event
 */
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

/**
 * Initialize the storage page on DOM ready
 * Sets up icons, loads data, and attaches event listeners
 */
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

/**
 * Cleanup on page unload
 * Removes event listeners to prevent memory leaks
 */
window.addEventListener('beforeunload', () => {
    document.removeEventListener('click', handleGlobalClick);
});
