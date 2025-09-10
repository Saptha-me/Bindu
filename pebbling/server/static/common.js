// Essential JavaScript functions for Pebbling UI

// Generate UUID v4
function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Theme management
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

// Format timestamp
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

// API request function
async function makeApiRequest(method, params) {
    const response = await fetch('/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: method,
            params: params,
            id: generateId()
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.error) {
        throw new Error(result.error.message || 'Unknown API error');
    }

    return result.result;
}

// Load agent card
async function loadAgentCard() {
    try {
        const response = await fetch('/.well-known/agent.json');
        if (!response.ok) throw new Error('Failed to load agent card');
        return await response.json();
    } catch (error) {
        console.error('Error loading agent card:', error);
        throw error;
    }
}

// Make functions globally available
window.toggleTheme = toggleTheme;
window.initTheme = initTheme;

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
});
