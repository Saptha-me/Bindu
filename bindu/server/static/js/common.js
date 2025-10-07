// Common utilities for Bindu Agent UI
// Shared functions used across multiple pages

// Constants
const BADGE_CLASSES = {
    success: 'bg-green-50 text-green-700 border-green-200',
    error: 'bg-red-50 text-red-700 border-red-200',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
    neutral: 'bg-gray-100 text-gray-700 border-gray-200'
};

const TOAST_CLASSES = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
};

// Helper functions
function getBadgeClass(type) {
    return BADGE_CLASSES[type] || BADGE_CLASSES.neutral;
}

function getToastClass(type) {
    return TOAST_CLASSES[type] || TOAST_CLASSES.info;
}

// Format timestamp to readable string
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Format relative time (e.g., "2 minutes ago")
function formatRelativeTime(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'Just now';
}

// Truncate text with ellipsis
function truncateText(text, maxLength = 50) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Copy text to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    // Get or create toast container
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed bottom-4 right-4 z-50 space-y-2';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `px-6 py-3 rounded-lg shadow-lg text-white transition-all duration-300 ${getToastClass(type)}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            toast.remove();
            // Remove container if empty
            if (toastContainer.children.length === 0) {
                toastContainer.remove();
            }
        }, 300);
    }, 3000);
}

// Toggle dropdown
function toggleDropdown(dropdownId) {
    const content = document.getElementById(dropdownId);
    const header = content.previousElementSibling;
    const icon = header.querySelector('.dropdown-icon');
    
    if (content.classList.contains('expanded')) {
        content.classList.remove('expanded');
        icon.classList.remove('expanded');
    } else {
        content.classList.add('expanded');
        icon.classList.add('expanded');
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Parse markdown to HTML (basic implementation)
function parseMarkdown(text) {
    if (!text) return '';
    
    // Use marked.js if available, otherwise basic parsing
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    
    // Basic markdown parsing
    let html = escapeHtml(text);
    
    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>');
    
    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank">$1</a>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Theme management (if needed in future)
function initTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.classList.toggle('dark', theme === 'dark');
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    const newTheme = isDark ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
    localStorage.setItem('theme', newTheme);
}

// Generic component loader with error handling
async function loadComponent(componentName, targetId) {
    const container = document.getElementById(targetId);
    if (!container) {
        console.warn(`Container ${targetId} not found`);
        return;
    }
    
    try {
        const response = await fetch(`/components/${componentName}.html`);
        if (!response.ok) {
            throw new Error(`Failed to load ${componentName}: ${response.statusText}`);
        }
        
        container.innerHTML = await response.text();
        
        // Special handling for header
        if (componentName === 'header') {
            highlightActivePage();
        }
    } catch (error) {
        console.error(`Error loading ${componentName}:`, error);
        container.innerHTML = `<div class="text-red-500 text-sm">Failed to load ${componentName}</div>`;
    }
}

// Load common head content
async function loadCommonHead() {
    try {
        const response = await fetch('/components/head.html');
        if (!response.ok) {
            throw new Error(`Failed to load head: ${response.statusText}`);
        }
        
        const headContent = await response.text();
        
        // Create a temporary div to parse the HTML
        const temp = document.createElement('div');
        temp.innerHTML = headContent;
        
        // Append all elements to document head
        Array.from(temp.children).forEach(element => {
            document.head.appendChild(element);
        });
    } catch (error) {
        console.error('Error loading common head:', error);
    }
}

// Build header HTML
function buildHeader() {
    return `
        <header class="border-b border-gray-200 bg-white">
            <div class="flex items-center justify-between p-4">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
                        <img src="https://orvsccdc47.ufs.sh/f/Slhdc2MbjygMbusHsQBGIu7ZmbJta6NLkf1hT4cjBFQSEOnl" alt="Logo" class="w-8 h-8 object-cover" />
                    </div>
                    <div>
                        <h1 id="header-agent-name" class="text-lg font-semibold text-gray-900">Loading Agent...</h1>
                        <p id="header-agent-subtitle" class="text-sm text-gray-500">Loading...</p>
                    </div>
                </div>
                <div class="flex-1 flex items-center justify-center">
                    <nav class="flex bg-gray-100 rounded-lg p-1">
                        <a href="chat.html" class="px-4 py-2 text-gray-600 hover:text-gray-900 rounded-md text-sm font-medium transition-colors" data-page="chat">Chat</a>
                        <a href="agent.html" class="px-4 py-2 text-gray-600 hover:text-gray-900 rounded-md text-sm font-medium transition-colors" data-page="agent">Agent Info</a>
                        <a href="storage.html" class="px-4 py-2 text-gray-600 hover:text-gray-900 rounded-md text-sm font-medium transition-colors" data-page="storage">Storage</a>
                    </nav>
                </div>
                <div class="flex items-center gap-4">
                    <div class="px-3 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full text-sm font-medium">
                        Online
                    </div>
                    <a href="https://github.com/bindu-ai/pebble/" target="_blank" rel="noopener noreferrer">
                        <svg class="w-6 h-6 text-gray-700 hover:text-gray-900 transition-colors" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M12 2C6.477 2 2 6.484 2 12.021c0 4.428 2.865 8.186 6.839 9.525.5.092.682-.217.682-.482 0-.237-.009-.868-.013-1.703-2.782.605-3.369-1.342-3.369-1.342-.454-1.157-1.11-1.465-1.11-1.465-.908-.62.069-.608.069-.608 1.004.07 1.532 1.032 1.532 1.032.892 1.53 2.341 1.088 2.91.833.091-.647.35-1.088.636-1.339-2.221-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.025A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.295 2.748-1.025 2.748-1.025.546 1.378.202 2.397.1 2.65.64.7 1.028 1.595 1.028 2.688 0 3.847-2.337 4.695-4.566 4.944.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .267.18.578.688.48C19.138 20.204 22 16.447 22 12.021 22 6.484 17.523 2 12 2z"/>
                        </svg>
                    </a>
                </div>
            </div>
        </header>
    `;
}

// Load header component
async function loadHeader() {
    const container = document.getElementById('header-placeholder');
    if (!container) {
        console.warn('Header placeholder not found');
        return;
    }
    
    // Inject header HTML
    container.innerHTML = buildHeader();
    
    // Highlight active page
    highlightActivePage();
}

// Highlight active page in navigation
function highlightActivePage() {
    const currentPage = window.location.pathname.split('/').pop().replace('.html', '') || 'chat';
    const navLinks = document.querySelectorAll('nav a[data-page]');
    
    navLinks.forEach(link => {
        const page = link.getAttribute('data-page');
        if (page === currentPage) {
            link.classList.remove('text-gray-600', 'hover:text-gray-900');
            link.classList.add('bg-yellow-500', 'text-white');
        }
    });
}

// Build footer HTML
function buildFooter() {
    return `
        <footer class="bg-white border-t border-gray-200 mt-auto">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div class="text-center">
                    <div class="flex items-center justify-center space-x-2 mb-4">
                        <span class="text-2xl">🌻</span>
                        <h3 class="text-lg font-semibold text-gray-900">Bindu Protocol</h3>
                    </div>
                    <p class="text-gray-600 max-w-3xl mx-auto mb-4">
                        Bindu is a decentralized agent-to-agent communication protocol. 
                        <strong>Hibiscus</strong> is our registry and <strong>Imagine</strong> is the multi-orchestrator platform 
                        where you can bindufy your agent and be part of the agent economy.
                    </p>
                    <p class="text-sm text-gray-500 mb-6">
                        This is the local version. For production deployment, please follow the 
                        <a href="https://docs.bindu.ai" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="text-yellow-600 hover:text-yellow-700 underline transition-colors">
                            documentation
                        </a>.
                    </p>
                    <div class="mt-6 pt-6 border-t border-gray-200">
                        <p class="text-sm text-gray-500">
                            © 2025 Bindu AI. Built with ❤️ from Amsterdam.
                        </p>
                    </div>
                </div>
            </div>
        </footer>
    `;
}

// Load footer component
async function loadFooter() {
    const container = document.getElementById('footer-placeholder');
    if (!container) {
        console.warn('Footer placeholder not found');
        return;
    }
    
    // Inject footer HTML
    container.innerHTML = buildFooter();
}

// Create icon using Iconify
function createIcon(iconName, className = 'w-5 h-5') {
    // Map icon names to Iconify icon identifiers
    const iconMap = {
        'chart-bar': 'heroicons:chart-bar-20-solid',
        'computer-desktop': 'heroicons:computer-desktop-20-solid',
        'shield-check': 'heroicons:shield-check-20-solid',
        'puzzle-piece': 'heroicons:puzzle-piece-20-solid',
        'tag': 'heroicons:tag-20-solid',
        'globe-alt': 'heroicons:globe-alt-20-solid',
        'clock': 'heroicons:clock-20-solid',
        'chevron-down': 'heroicons:chevron-down-20-solid',
        'archive-box': 'heroicons:archive-box-20-solid',
        'document-text': 'heroicons:document-text-20-solid',
        'arrow-path': 'heroicons:arrow-path-20-solid',
        'trash': 'heroicons:trash-20-solid'
    };
    
    const iconId = iconMap[iconName] || iconMap['chart-bar'];
    return `<iconify-icon icon="${iconId}" class="${className}"></iconify-icon>`;
}

// Create page structure helper
function createPageStructure(config) {
    const { title, description } = config;
    
    // Update title and description if provided
    if (title) {
        document.title = title;
    }
    if (description) {
        const metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) {
            metaDesc.content = description;
        }
    }
}

// Generate UUID v4
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Status color mapping for task states
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

// Status icon mapping for task states
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

// Helper for yes/no display
function yesNo(value) {
    return value ? 'Yes' : 'No';
}

// Create empty state component
function createEmptyState(message, iconName = 'puzzle-piece', iconSize = 'w-12 h-12') {
    return `
        <div class="text-center py-8 text-gray-500">
            ${createIcon(iconName, `${iconSize} mx-auto mb-3 text-gray-300`)}
            <div class="text-sm">${message}</div>
        </div>
    `;
}

// Create error state component
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

// Create stat card component
function createStatCard(icon, label, value) {
    return `
        <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div class="flex items-center gap-2 mb-2">
                ${createIcon(icon, 'w-4 h-4 text-gray-500')}
                <span class="text-sm font-medium text-gray-500">${label}</span>
            </div>
            <div class="font-mono text-lg font-semibold text-gray-900">${value}</div>
        </div>
    `;
}

// Create stat row component
function createStatRow(label, value, colorClass = 'text-gray-900') {
    return `
        <div class="flex justify-between items-center py-2 border-b border-gray-200">
            <span class="text-sm font-medium text-gray-600">${label}</span>
            <span class="text-sm font-semibold ${colorClass}">${value}</span>
        </div>
    `;
}

// Create setting row component
function createSettingRow(label, value, isEnabled = null) {
    const badgeType = isEnabled === null ? 'neutral' : (isEnabled ? 'success' : 'error');
    const badgeClass = getBadgeClass(badgeType);
    
    return `
        <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
            <span class="font-medium text-gray-900">${label}</span>
            <div class="px-3 py-1 ${badgeClass} border rounded-full text-sm font-medium">
                ${value}
            </div>
        </div>
    `;
}

// Create dropdown component
function createDropdown(id, title, isAvailable, content) {
    const badgeType = isAvailable ? 'success' : 'error';
    const statusBadge = getBadgeClass(badgeType);
    const statusText = isAvailable ? 'Available' : 'Not available';
    
    return `
        <div class="border border-gray-200 rounded-lg overflow-hidden">
            <div class="p-3 bg-gray-50 cursor-pointer flex items-center justify-between hover:bg-gray-100 transition-colors" onclick="utils.toggleDropdown('${id}')">
                <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-700">${title}</span>
                    <div class="px-2 py-1 ${statusBadge} border rounded text-xs">
                        ${statusText}
                    </div>
                </div>
                ${createIcon('chevron-down', 'dropdown-icon w-4 h-4 text-gray-400')}
            </div>
            <div id="${id}" class="dropdown-content bg-white">
                ${content}
            </div>
        </div>
    `;
}

// Make functions globally available
window.utils = {
    formatTimestamp,
    formatRelativeTime,
    truncateText,
    copyToClipboard,
    showToast,
    toggleDropdown,
    escapeHtml,
    parseMarkdown,
    debounce,
    initTheme,
    toggleTheme,
    loadComponent,
    loadHeader,
    loadFooter,
    createIcon,
    getBadgeClass,
    getToastClass,
    createPageStructure,
    generateUUID,
    getStatusColor,
    getStatusIcon,
    yesNo,
    createEmptyState,
    createErrorState,
    createStatCard,
    createStatRow,
    createSettingRow,
    createDropdown
};

// Load common scripts dynamically
function loadCommonScripts() {
    // Only load if not already loaded
    if (!document.getElementById('common-api-script')) {
        const apiScript = document.createElement('script');
        apiScript.id = 'common-api-script';
        apiScript.src = 'js/api.js';
        document.body.appendChild(apiScript);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Theme initialization disabled for now (white background only)
    // initTheme();
    
    // Load common scripts
    loadCommonScripts();
    
    // Load components if placeholders exist
    if (document.getElementById('footer-placeholder')) {
        loadFooter();
    }
    if (document.getElementById('header-placeholder')) {
        loadHeader();
    }
});
