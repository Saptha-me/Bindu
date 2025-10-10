// Common utilities for Bindu Agent UI
// Shared functions used across multiple pages

// Constants
// Consolidated style mappings
const STYLE_MAPS = {
    badge: {
        success: 'bg-green-50 text-green-700 border-green-200',
        error: 'bg-red-50 text-red-700 border-red-200',
        warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        info: 'bg-blue-50 text-blue-700 border-blue-200',
        neutral: 'bg-gray-100 text-gray-700 border-gray-200'
    },
    toast: {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500'
    },
    status: {
        completed: 'bg-green-100 text-green-800',
        failed: 'bg-red-100 text-red-800',
        running: 'bg-blue-100 text-blue-800',
        pending: 'bg-yellow-100 text-yellow-800',
        canceled: 'bg-gray-100 text-gray-800',
        working: 'bg-purple-100 text-purple-800'
    },
    statusIcon: {
        completed: '✅',
        failed: '❌',
        running: '⚡',
        pending: '⏳',
        canceled: '🚫',
        working: '🔄'
    },
    trust: {
        low: { label: 'Low Trust', type: 'error' },
        medium: { label: 'Medium Trust', type: 'warning' },
        high: { label: 'High Trust', type: 'success' }
    }
};

// Legacy constants for backward compatibility
const BADGE_CLASSES = STYLE_MAPS.badge;
const TOAST_CLASSES = STYLE_MAPS.toast;
const TRUST_LABELS = {
    low: STYLE_MAPS.trust.low.label,
    medium: STYLE_MAPS.trust.medium.label,
    high: STYLE_MAPS.trust.high.label
};
const TRUST_BADGE_TYPES = {
    low: STYLE_MAPS.trust.low.type,
    medium: STYLE_MAPS.trust.medium.type,
    high: STYLE_MAPS.trust.high.type
};

// Helper functions

/**
 * Generic style mapper - DRY utility for all style lookups
 * @param {string} category - Style category (badge, toast, status, etc.)
 * @param {string} key - Lookup key
 * @param {string} defaultKey - Default fallback key
 * @returns {string} CSS classes or value
 */
function getStyleClass(category, key, defaultKey = null) {
    const map = STYLE_MAPS[category];
    if (!map) return '';
    return map[key] || (defaultKey ? map[defaultKey] : '');
}

/**
 * Get badge CSS classes based on type
 * @param {string} type - Badge type (success, error, warning, info, neutral)
 * @returns {string} CSS classes for the badge
 */
function getBadgeClass(type) {
    return getStyleClass('badge', type, 'neutral');
}

/**
 * Get trust badge type from trust level
 * @param {string} trustLevel - Trust level (low, medium, high)
 * @returns {string} Badge type for the trust level
 */
function getTrustBadgeType(trustLevel) {
    return STYLE_MAPS.trust[trustLevel]?.type || 'neutral';
}

/**
 * Get trust label from trust level
 * @param {string} trustLevel - Trust level (low, medium, high)
 * @returns {string} Human-readable trust label
 */
function getTrustLabel(trustLevel) {
    return STYLE_MAPS.trust[trustLevel]?.label || 'Unknown';
}

/**
 * Get toast CSS classes
 * @param {string} type - Toast type
 * @returns {string} CSS classes
 */
function getToastClass(type) {
    return getStyleClass('toast', type, 'info');
}

// Format timestamp to readable string (memoized)
const formatTimestamp = memoize(function(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
}, 100);

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

// Truncate text with ellipsis (memoized)
const truncateText = memoize(function(text, maxLength = 50) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}, 200);

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

// Show toast notification (optimized with proper cleanup)
function showToast(message, type = 'info') {
    // Get or create toast container using stored reference
    const toastContainer = domRefs.getToastContainer();

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `px-6 py-3 rounded-lg shadow-lg text-white transition-all duration-300 ${getToastClass(type)}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    // Track timers for cleanup
    let fadeTimer = null;
    let removeTimer = null;

    // Auto-remove after 3 seconds
    const removeToast = () => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';

        removeTimer = setTimeout(() => {
            toast.remove();
            // Clean up timer references
            if (fadeTimer) cleanupRegistry.clearTimeout(fadeTimer);
            if (removeTimer) cleanupRegistry.clearTimeout(removeTimer);

            // Remove container if empty and clear reference
            if (toastContainer.children.length === 0) {
                toastContainer.remove();
                domRefs.clearToastContainer();
            }
        }, 300);
        cleanupRegistry.registerTimeout(removeTimer);
    };

    fadeTimer = setTimeout(removeToast, 3000);
    cleanupRegistry.registerTimeout(fadeTimer);

    // Return cleanup function
    return () => {
        if (fadeTimer) {
            cleanupRegistry.clearTimeout(fadeTimer);
            fadeTimer = null;
        }
        if (removeTimer) {
            cleanupRegistry.clearTimeout(removeTimer);
            removeTimer = null;
        }
        toast.remove();
    };
}

// Toggle dropdown (optimized with DOM caching)
function toggleDropdown(dropdownId) {
    const content = domCache.get(dropdownId);
    if (!content) return;

    const isExpanded = content.classList.contains('expanded');
    content.classList.toggle('expanded', !isExpanded);

    // Cache icon query
    const iconCacheKey = `dropdown-icon-${dropdownId}`;
    let icon = domCache.query(iconCacheKey);
    if (!icon) {
        const header = content.previousElementSibling;
        icon = header?.querySelector('.dropdown-icon');
        if (icon) domCache.query(iconCacheKey); // Store for next time
    }
    icon?.classList.toggle('expanded', !isExpanded);
}

// Escape HTML to prevent XSS (memoized for performance)
const escapeHtml = memoize(function(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}, 500); // Cache up to 500 escaped strings

// Parse markdown to HTML (memoized for performance)
const parseMarkdownMemo = createMemoized(function(text) {
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
}, 200); // Cache up to 200 parsed markdown strings

// Export the memoized function
const parseMarkdown = parseMarkdownMemo.fn;

// Debounce function (with cleanup support)
function debounce(func, wait) {
    let timeout;

    const debounced = function executedFunction(...args) {
        const later = () => {
            if (timeout) cleanupRegistry.clearTimeout(timeout);
            timeout = null;
            func(...args);
        };

        if (timeout) cleanupRegistry.clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        cleanupRegistry.registerTimeout(timeout);
    };

    // Add cancel method for manual cleanup
    debounced.cancel = () => {
        if (timeout) {
            cleanupRegistry.clearTimeout(timeout);
            timeout = null;
        }
    };

    return debounced;
}

/**
 * Memoization utility with LRU cache
 * Caches function results to avoid expensive recomputation
 * @param {Function} fn - Function to memoize
 * @param {number} maxSize - Maximum cache size (default: 100)
 * @returns {Function} Memoized function
 */
function memoize(fn, maxSize = 100) {
    const cache = new Map();

    return function memoized(...args) {
        // Create cache key from arguments
        const key = JSON.stringify(args);

        // Return cached result if exists
        if (cache.has(key)) {
            return cache.get(key);
        }

        // Compute result
        const result = fn.apply(this, args);

        // Store in cache
        cache.set(key, result);

        // Implement LRU: remove oldest entry if cache is full
        if (cache.size > maxSize) {
            const firstKey = cache.keys().next().value;
            cache.delete(firstKey);
        }

        return result;
    };
}

/**
 * Create a memoized function with manual cache control
 * @param {Function} fn - Function to memoize
 * @param {number} maxSize - Maximum cache size
 * @returns {Object} Object with memoized function and cache control methods
 */
function createMemoized(fn, maxSize = 100) {
    const cache = new Map();

    const memoized = function(...args) {
        const key = JSON.stringify(args);

        if (cache.has(key)) {
            return cache.get(key);
        }

        const result = fn.apply(this, args);
        cache.set(key, result);

        if (cache.size > maxSize) {
            const firstKey = cache.keys().next().value;
            cache.delete(firstKey);
        }

        return result;
    };

    return {
        fn: memoized,
        clear: () => cache.clear(),
        size: () => cache.size,
        has: (key) => cache.has(JSON.stringify([key]))
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

// Generic component loader with error handling, cleanup, and deduplication
async function loadComponent(componentName, targetId) {
    const container = domCache.get(targetId);
    if (!container) {
        console.warn(`Container ${targetId} not found`);
        return;
    }

    // Create unique key for deduplication
    const requestKey = `component:${componentName}:${targetId}`;

    // Use request deduplication
    return requestDeduplicator.dedupe(requestKey, async () => {
        // Create abort controller for request cleanup
        const abortController = new AbortController();

        try {
            const response = await fetch(`/components/${componentName}.html`, {
                signal: abortController.signal
            });

            if (!response.ok) {
                throw new Error(`Failed to load ${componentName}: ${response.statusText}`);
            }

            const content = await response.text();

            // Only update DOM if container still exists
            if (document.body.contains(container)) {
                container.innerHTML = content;

                // Invalidate cache after DOM change
                domCache.clear();

                // Special handling for header
                if (componentName === 'header') {
                    highlightActivePage();
                }
            }

            return content;
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log(`Component load aborted: ${componentName}`);
            } else {
                console.error(`Error loading ${componentName}:`, error);
                if (document.body.contains(container)) {
                    container.innerHTML = `<div class="text-red-500 text-sm">Failed to load ${componentName}</div>`;
                }
            }
            throw error; // Re-throw to propagate to deduplicator
        } finally {
            // Cleanup function for abort controller
            abortController.abort();
        }
    });
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
                    <a href="https://github.com/Saptha-me/Bindu" target="_blank" rel="noopener noreferrer" class="text-gray-700 hover:text-gray-900 transition-colors">
                        ${createIcon('github', 'w-6 h-6')}
                    </a>
                </div>
            </div>
        </header>
    `;
}

// Load header component (optimized with stored references and deduplication)
async function loadHeader() {
    const container = domRefs.headerPlaceholder || domCache.get('header-placeholder');
    if (!container) {
        console.warn('Header placeholder not found');
        return;
    }

    // Use request deduplication for header loading
    const requestKey = 'header:load';

    return requestDeduplicator.dedupe(requestKey, async () => {
        // Inject header HTML
        container.innerHTML = buildHeader();

        // Refresh header-specific references
        domRefs.refreshHeader();

        // Invalidate nav-related cache after DOM change
        domCache.clear();

        // Highlight active page
        highlightActivePage();

        return true;
    });
}

// Highlight active page in navigation (optimized with early exit)
function highlightActivePage() {
    const currentPage = window.location.pathname.split('/').pop().replace('.html', '') || 'chat';
    const navLinks = domCache.queryAll('nav a[data-page]');

    for (const link of navLinks) {
        if (link.getAttribute('data-page') === currentPage) {
            link.classList.remove('text-gray-600', 'hover:text-gray-900');
            link.classList.add('bg-yellow-500', 'text-white');
            break; // Early exit once found
        }
    }
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

// Load footer component (optimized with stored references and deduplication)
async function loadFooter() {
    const container = domRefs.footerPlaceholder || domCache.get('footer-placeholder');
    if (!container) {
        console.warn('Footer placeholder not found');
        return;
    }

    // Use request deduplication for footer loading
    const requestKey = 'footer:load';

    return requestDeduplicator.dedupe(requestKey, async () => {
        // Inject footer HTML
        container.innerHTML = buildFooter();

        return true;
    });
}

/**
 * Consolidated icon mapping for Iconify icons
 * Centralized icon definitions used across all pages
 */
const ICON_MAP = {
    // Common icons
    'chart-bar': 'heroicons:chart-bar-20-solid',
    'computer-desktop': 'heroicons:computer-desktop-20-solid',
    'shield-check': 'heroicons:shield-check-20-solid',
    'puzzle-piece': 'heroicons:puzzle-piece-20-solid',
    'tag': 'heroicons:tag-20-solid',
    'globe-alt': 'heroicons:globe-alt-20-solid',
    'clock': 'heroicons:clock-20-solid',
    'chevron-down': 'heroicons:chevron-down-20-solid',
    'chevron-right': 'heroicons:chevron-right-20-solid',
    'chevron-left': 'heroicons:chevron-left-20-solid',
    'archive-box': 'heroicons:archive-box-20-solid',
    'document-text': 'heroicons:document-text-20-solid',
    'arrow-path': 'heroicons:arrow-path-20-solid',
    'trash': 'heroicons:trash-20-solid',
    'plus': 'heroicons:plus-20-solid',
    'cog': 'heroicons:cog-6-tooth-20-solid',
    'paper-airplane': 'heroicons:paper-airplane-20-solid',
    // Message action icons (consolidated from MESSAGE_ICON_MAP)
    'clipboard': 'heroicons:clipboard-document-20-solid',
    'check': 'heroicons:check-20-solid',
    'thumb-up': 'heroicons:hand-thumb-up-20-solid',
    'thumb-down': 'heroicons:hand-thumb-down-20-solid',
    // Aliases for message actions
    'copy': 'heroicons:clipboard-document-20-solid',
    'copySuccess': 'heroicons:check-20-solid',
    'like': 'heroicons:hand-thumb-up-20-solid',
    'dislike': 'heroicons:hand-thumb-down-20-solid',
    // Brand icons
    'github': 'mdi:github',
    // State icons
    'exclamation-triangle': 'heroicons:exclamation-triangle-20-solid'
};

/**
 * Create an Iconify icon element (memoized)
 * @param {string} iconName - Name of the icon from ICON_MAP
 * @param {string} className - CSS classes to apply to the icon
 * @returns {string} HTML string for the icon element
 */
const createIcon = memoize(function(iconName, className = 'w-5 h-5') {
    const iconId = ICON_MAP[iconName] || ICON_MAP['chart-bar'];
    return `<iconify-icon icon="${iconId}" class="${className}"></iconify-icon>`;
}, 150);

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

/**
 * Generate UUID v4 (not memoized - must be unique each time)
 * Optimized version without regex for better performance
 * @returns {string} UUID v4 string
 */
function generateUUID() {
    const hex = '0123456789abcdef';
    let uuid = '';
    for (let i = 0; i < 36; i++) {
        if (i === 8 || i === 13 || i === 18 || i === 23) {
            uuid += '-';
        } else if (i === 14) {
            uuid += '4';
        } else if (i === 19) {
            uuid += hex[(Math.random() * 4 | 0) + 8];
        } else {
            uuid += hex[Math.random() * 16 | 0];
        }
    }
    return uuid;
}

// Status color mapping for task states (memoized, using consolidated map)
const getStatusColor = memoize(function(state) {
    return getStyleClass('status', state, 'canceled');
}, 10);

// Status icon mapping for task states (memoized, using consolidated map)
const getStatusIcon = memoize(function(state) {
    return STYLE_MAPS.statusIcon[state] || '❓';
}, 10);

// Helper for yes/no display
function yesNo(value) {
    return value ? 'Yes' : 'No';
}

/**
 * DOM element caching utility
 * Improves performance by caching DOM queries
 * @returns {Object} Cache manager with get, query, queryAll, and clear methods
 */
function createDOMCache() {
    const cache = {};
    const queryCache = {};

    return {
        get: (id) => {
            if (!cache[id]) {
                cache[id] = document.getElementById(id);
            }
            return cache[id];
        },
        query: (selector) => {
            if (!queryCache[selector]) {
                queryCache[selector] = document.querySelector(selector);
            }
            return queryCache[selector];
        },
        queryAll: (selector) => {
            // Don't cache queryAll as it returns a live NodeList
            return document.querySelectorAll(selector);
        },
        invalidate: (key) => {
            if (key) {
                delete cache[key];
                delete queryCache[key];
            }
        },
        clear: () => {
            Object.keys(cache).forEach(key => delete cache[key]);
            Object.keys(queryCache).forEach(key => delete queryCache[key]);
        }
    };
}

// Global DOM cache instance
const domCache = createDOMCache();

/**
 * Request deduplication manager for component loading
 * Prevents multiple simultaneous requests for the same resource
 */
const requestDeduplicator = {
    pendingRequests: new Map(),

    /**
     * Get or create a request for a resource
     * @param {string} key - Unique key for the request
     * @param {Function} requestFn - Function that returns a Promise
     * @returns {Promise} The pending or new request
     */
    async dedupe(key, requestFn) {
        // Return existing pending request if available
        if (this.pendingRequests.has(key)) {
            return this.pendingRequests.get(key);
        }

        // Create new request
        const promise = requestFn()
            .finally(() => {
                // Clean up after request completes (success or failure)
                this.pendingRequests.delete(key);
            });

        // Store pending request
        this.pendingRequests.set(key, promise);

        return promise;
    },

    /**
     * Cancel a pending request
     * @param {string} key - Request key to cancel
     */
    cancel(key) {
        this.pendingRequests.delete(key);
    },

    /**
     * Cancel all pending requests
     */
    cancelAll() {
        this.pendingRequests.clear();
    },

    /**
     * Check if a request is pending
     * @param {string} key - Request key
     * @returns {boolean}
     */
    isPending(key) {
        return this.pendingRequests.has(key);
    }
};

/**
 * Global cleanup registry for memory leak prevention
 * Tracks timers, event listeners, and other resources that need cleanup
 */
const cleanupRegistry = {
    timers: new Set(),
    intervals: new Set(),
    eventListeners: new Map(),

    /**
     * Register a timeout for cleanup
     */
    registerTimeout(id) {
        this.timers.add(id);
        return id;
    },

    /**
     * Register an interval for cleanup
     */
    registerInterval(id) {
        this.intervals.add(id);
        return id;
    },

    /**
     * Register an event listener for cleanup
     */
    registerEventListener(element, event, handler, options) {
        const key = `${element.tagName || 'window'}_${event}`;
        if (!this.eventListeners.has(key)) {
            this.eventListeners.set(key, []);
        }
        this.eventListeners.get(key).push({ element, event, handler, options });
    },

    /**
     * Clear a specific timeout
     */
    clearTimeout(id) {
        clearTimeout(id);
        this.timers.delete(id);
    },

    /**
     * Clear a specific interval
     */
    clearInterval(id) {
        clearInterval(id);
        this.intervals.delete(id);
    },

    /**
     * Clear all registered resources
     */
    clearAll() {
        // Clear all timers
        this.timers.forEach(id => clearTimeout(id));
        this.timers.clear();

        // Clear all intervals
        this.intervals.forEach(id => clearInterval(id));
        this.intervals.clear();

        // Remove all event listeners
        this.eventListeners.forEach(listeners => {
            listeners.forEach(({ element, event, handler, options }) => {
                element?.removeEventListener(event, handler, options);
            });
        });
        this.eventListeners.clear();
    }
};

/**
 * Global DOM references for frequently accessed elements
 * Stores direct references to avoid repeated queries
 */
const domRefs = {
    body: null,
    toastContainer: null,
    headerPlaceholder: null,
    footerPlaceholder: null,
    headerAgentName: null,
    headerAgentSubtitle: null,

    /**
     * Initialize DOM references
     * Call this after DOM is ready or after dynamic content loads
     */
    init() {
        this.body = document.body;
        this.headerPlaceholder = document.getElementById('header-placeholder');
        this.footerPlaceholder = document.getElementById('footer-placeholder');
    },

    /**
     * Refresh header-specific references
     * Call after header is loaded
     */
    refreshHeader() {
        this.headerAgentName = document.getElementById('header-agent-name');
        this.headerAgentSubtitle = document.getElementById('header-agent-subtitle');
    },

    /**
     * Get or create toast container with reference caching
     */
    getToastContainer() {
        if (!this.toastContainer || !document.body.contains(this.toastContainer)) {
            this.toastContainer = document.getElementById('toast-container');
            if (!this.toastContainer) {
                this.toastContainer = document.createElement('div');
                this.toastContainer.id = 'toast-container';
                this.toastContainer.className = 'fixed bottom-4 right-4 z-50 space-y-2';
                this.body.appendChild(this.toastContainer);
            }
        }
        return this.toastContainer;
    },

    /**
     * Clear toast container reference
     */
    clearToastContainer() {
        this.toastContainer = null;
    },

    /**
     * Clear all DOM references
     */
    clearAll() {
        this.body = null;
        this.toastContainer = null;
        this.headerPlaceholder = null;
        this.footerPlaceholder = null;
        this.headerAgentName = null;
        this.headerAgentSubtitle = null;
    }
};

/**
 * Create a message action icon (memoized)
 * Now uses consolidated ICON_MAP directly
 * @param {string} iconName - Icon name (copy, copySuccess, like, dislike)
 * @param {string} [className='w-4 h-4'] - CSS classes for the icon
 * @returns {string} HTML string for the icon
 */
const createMessageIcon = memoize(function(iconName, className = 'w-4 h-4') {
    return createIcon(iconName, className);
}, 50);

/**
 * Extract agent response content from API result
 * Handles multiple possible response formats
 * @param {Object} result - API response result
 * @returns {string|null} Extracted content or null if not found
 */
function extractAgentResponse(result) {
    if (!result) return null;

    // Try different response formats (ordered by most common)
    if (result.reply) return result.reply;
    if (result.content) return result.content;

    // Check messages array (use findLast for better performance - get latest message)
    if (result.messages?.length > 0) {
        // Use reverse iteration for better performance (latest message first)
        for (let i = result.messages.length - 1; i >= 0; i--) {
            const m = result.messages[i];
            if ((m.role === 'assistant' || m.role === 'agent') && m.content) {
                return m.content;
            }
        }
    }

    return null;
}

/**
 * Extract text from task history
 * Finds the last agent message in task history
 * @param {Object} task - Task object with history
 * @returns {string|null} Extracted text or null
 */
function extractTaskResponse(task) {
    if (!task?.history?.length) return null;

    // Reverse iterate without creating new array (more efficient)
    for (let i = task.history.length - 1; i >= 0; i--) {
        const msg = task.history[i];
        if (msg.role === 'agent' || msg.role === 'assistant') {
            if (msg.parts?.length > 0) {
                const textPart = msg.parts.find(part => part.kind === 'text');
                if (textPart?.text) return textPart.text;
            }
        }
    }

    return null;
}

/**
 * Scroll element to bottom
 * @param {HTMLElement} element - Element to scroll
 */
function scrollToBottom(element) {
    if (element) {
        element.scrollTop = element.scrollHeight;
    }
}

/**
 * Toggle button reaction state (like/dislike)
 * Optimized with cached selectors
 * @param {string} messageId - Message ID
 * @param {string} type - 'like' or 'dislike'
 */
function toggleReaction(messageId, type) {
    const isLike = type === 'like';
    const primaryBtn = domCache.query(`.${type}-btn[data-message-id="${messageId}"]`);
    const oppositeBtn = domCache.query(`.${isLike ? 'dislike' : 'like'}-btn[data-message-id="${messageId}"]`);

    if (!primaryBtn || !oppositeBtn) return;

    const activeClass = `${type}d`;
    const colorClass = isLike ? 'text-green-500' : 'text-red-500';

    if (primaryBtn.classList.contains(activeClass)) {
        // Remove reaction
        primaryBtn.classList.remove(activeClass, colorClass);
        primaryBtn.innerHTML = createMessageIcon(type);
    } else {
        // Add reaction
        primaryBtn.classList.add(activeClass, colorClass);
        primaryBtn.innerHTML = createMessageIcon(type, `w-4 h-4 ${colorClass}`);
        // Remove opposite reaction
        const oppositeActiveClass = isLike ? 'disliked' : 'liked';
        const oppositeColorClass = isLike ? 'text-red-500' : 'text-green-500';
        oppositeBtn.classList.remove(oppositeActiveClass, oppositeColorClass);
        oppositeBtn.innerHTML = createMessageIcon(isLike ? 'dislike' : 'like');
    }
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
                ${createIcon('exclamation-triangle', 'w-16 h-16 mx-auto')}
            </div>
            <p class="text-gray-600 text-lg font-medium">Error Loading Data</p>
            <p class="text-gray-500 mt-1">${message}</p>
            <button onclick="${onRetry}" class="mt-4 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors">
                Retry
            </button>
        </div>
    `;
}

/**
 * Generic info row creator - DRY utility for stat/setting rows
 * @param {Object} config - Configuration object
 * @returns {string} HTML string
 */
function createInfoRow(config) {
    const {
        label,
        value,
        type = 'stat', // 'stat', 'setting', 'card'
        icon = null,
        colorClass = 'text-gray-900',
        badgeType = 'neutral'
    } = config;

    if (type === 'card') {
        return `
            <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
                <div class="flex items-center gap-2 mb-2">
                    ${icon ? createIcon(icon, 'w-4 h-4 text-gray-500') : ''}
                    <span class="text-sm font-medium text-gray-500">${label}</span>
                </div>
                <div class="font-mono text-lg font-semibold text-gray-900">${value}</div>
            </div>
        `;
    }

    if (type === 'setting') {
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

    // Default: stat row
    return `
        <div class="flex justify-between items-center py-2 border-b border-gray-200">
            <span class="text-sm font-medium text-gray-600">${label}</span>
            <span class="text-sm font-semibold ${colorClass}">${value}</span>
        </div>
    `;
}

// Backward compatibility wrappers
function createStatCard(icon, label, value) {
    return createInfoRow({ type: 'card', icon, label, value });
}

function createStatRow(label, value, colorClass = 'text-gray-900') {
    return createInfoRow({ type: 'stat', label, value, colorClass });
}

function createSettingRow(label, value, isEnabled = null) {
    const badgeType = isEnabled === null ? 'neutral' : (isEnabled ? 'success' : 'error');
    return createInfoRow({ type: 'setting', label, value, badgeType });
}

/**
 * Create a collapsible dropdown component
 * @param {string} id - Unique ID for the dropdown
 * @param {string} title - Title text for the dropdown header
 * @param {boolean} isAvailable - Whether the content is available
 * @param {string} content - HTML content to display when expanded
 * @returns {string} HTML string for the dropdown component
 */
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

/**
 * Create a skill card component
 * @param {Object} skill - Skill object with name and description
 * @param {string} skill.name - Name of the skill
 * @param {string} [skill.description] - Description of the skill
 * @returns {string} HTML string for the skill card
 */
function createSkillCard(skill) {
    return `
        <div class="p-4 border border-yellow-200 bg-yellow-50 rounded-lg">
            <div class="flex items-start gap-3">
                <div class="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
                <div>
                    <div class="font-semibold text-yellow-700 mb-1">${skill.name}</div>
                    <div class="text-sm text-gray-600">${skill.description || 'Ability to answer basic questions'}</div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Create a technical detail row component
 * @param {string} label - Label for the detail
 * @param {string} value - Value to display
 * @param {boolean} [isMonospace=false] - Whether to use monospace font
 * @returns {string} HTML string for the technical detail row
 */
function createTechnicalDetail(label, value, isMonospace = false) {
    const valueClass = isMonospace ? 'font-mono text-sm' : 'font-mono text-xs';
    const extraClass = isMonospace ? '' : ' break-all text-gray-600';

    return `
        <div>
            <div class="text-sm font-medium text-gray-500 mb-2">${label}</div>
            <div class="bg-gray-50 rounded-lg px-3 py-2 border border-gray-200${extraClass}">
                <div class="${valueClass}">${value}</div>
            </div>
        </div>
    `;
}

/**
 * Create a task card component for displaying task information
 * @param {Object} task - Task object with status, history, and metadata
 * @param {string} task.task_id - Unique task identifier
 * @param {string} task.context_id - Context identifier
 * @param {Object} task.status - Task status object with state
 * @param {Array} task.history - Array of message objects
 * @param {boolean} [isCompact=false] - Whether to use compact layout
 * @param {number} [truncateLength=100] - Maximum length for message text
 * @returns {string} HTML string for the task card
 */
function createTaskCard(task, isCompact = false, truncateLength = 100) {
    const statusColor = getStatusColor(task.status?.state);
    const statusIcon = getStatusIcon(task.status?.state);
    const latestMessage = task.history?.[task.history.length - 1]?.parts?.[0]?.text || 'No content';
    const truncatedMessage = truncateText(latestMessage, truncateLength);

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

/**
 * Create a context card component for displaying context information
 * @param {Object} contextData - Context object with metadata
 * @param {string} contextData.context_id - Unique context identifier
 * @param {number} [contextData.task_count=0] - Number of tasks in context
 * @returns {string} HTML string for the context card
 */
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

// Make functions globally available
window.utils = {
    // Formatting utilities
    formatTimestamp,
    formatRelativeTime,
    truncateText,
    escapeHtml,
    parseMarkdown,
    parseMarkdownMemo, // Expose memoized version with cache control

    // Interaction utilities
    copyToClipboard,
    showToast,
    toggleDropdown,
    debounce,
    memoize,
    createMemoized,

    // Theme utilities
    initTheme,
    toggleTheme,

    // Component loaders
    loadComponent,
    loadHeader,
    loadFooter,

    // UI component creators
    createIcon,
    createMessageIcon,
    createEmptyState,
    createErrorState,
    createStatCard,
    createStatRow,
    createSettingRow,
    createDropdown,
    createSkillCard,
    createTechnicalDetail,
    createTaskCard,
    createContextCard,

    // Badge and status utilities
    getStyleClass, // Generic style mapper
    getBadgeClass,
    getToastClass,
    getTrustBadgeType,
    getTrustLabel,
    getStatusColor,
    getStatusIcon,

    // Helper utilities
    createPageStructure,
    generateUUID, // Used by api.js generateId() as fallback
    yesNo,
    createDOMCache,
    domCache, // Expose global cache instance
    domRefs, // Expose global DOM references
    cleanupRegistry, // Expose cleanup registry
    requestDeduplicator, // Expose request deduplicator
    extractAgentResponse,
    extractTaskResponse,
    scrollToBottom,
    toggleReaction,

    // Constants (exposed for reference)
    STYLE_MAPS, // Consolidated style mappings
    ICON_MAP,
    TRUST_LABELS,
    TRUST_BADGE_TYPES,
    // Legacy constants
    BADGE_CLASSES,
    TOAST_CLASSES
};

// Load common scripts dynamically (with cleanup)
function loadCommonScripts() {
    // Only load if not already loaded
    if (!document.getElementById('common-api-script')) {
        const apiScript = document.createElement('script');
        apiScript.id = 'common-api-script';
        apiScript.src = 'js/api.js';

        // Add error handler to prevent memory leaks
        const errorHandler = (e) => {
            console.error('Failed to load api.js:', e);
            apiScript.remove();
        };

        apiScript.addEventListener('error', errorHandler, { once: true });
        document.body.appendChild(apiScript);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM references
    domRefs.init();

    // Theme initialization disabled for now (white background only)
    // initTheme();

    // Load common scripts
    loadCommonScripts();

    // Load components if placeholders exist (using stored references)
    if (domRefs.footerPlaceholder) {
        loadFooter();
    }
    if (domRefs.headerPlaceholder) {
        loadHeader();
    }
});

// Cleanup on page unload to prevent memory leaks
window.addEventListener('beforeunload', () => {
    cleanupRegistry.clearAll();
    domCache.clear();
    domRefs.clearAll();
    requestDeduplicator.cancelAll();
});

// Cleanup on page hide (for back/forward cache)
window.addEventListener('pagehide', () => {
    cleanupRegistry.clearAll();
    requestDeduplicator.cancelAll();
});

// Expose cache clearing utilities for debugging
window.clearMemoCache = () => {
    parseMarkdownMemo.clear();
    console.log('Memoization caches cleared');
};

window.clearAllCaches = () => {
    parseMarkdownMemo.clear();
    domCache.clear();
    cleanupRegistry.clearAll();
    requestDeduplicator.cancelAll();
    console.log('All caches and resources cleared');
};

// Debug utility to check pending requests
window.getPendingRequests = () => {
    return Array.from(requestDeduplicator.pendingRequests.keys());
};
