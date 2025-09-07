// Common JavaScript functions for all Pebbling pages

// Generate a proper UUID v4
function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Theme management for Tailwind CSS
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let theme = 'light';
    if (savedTheme) {
        theme = savedTheme;
    } else if (systemPrefersDark) {
        theme = 'dark';
    }
    
    // Apply theme to HTML element for Tailwind dark mode
    if (theme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    
    updateThemeToggleIcon();
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    const newTheme = isDark ? 'light' : 'dark';
    
    if (newTheme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    
    localStorage.setItem('theme', newTheme);
    updateThemeToggleIcon();
}

function updateThemeToggleIcon() {
    const themeToggle = document.getElementById('theme-toggle');
    const isDark = document.documentElement.classList.contains('dark');
    
    if (themeToggle) {
        if (isDark) {
            themeToggle.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="5"/>
                    <line x1="12" y1="1" x2="12" y2="3"/>
                    <line x1="12" y1="21" x2="12" y2="23"/>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                    <line x1="1" y1="12" x2="3" y2="12"/>
                    <line x1="21" y1="12" x2="23" y2="12"/>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
            `;
            themeToggle.title = 'Switch to light mode';
        } else {
            themeToggle.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
            `;
            themeToggle.title = 'Switch to dark mode';
        }
    }
}

// Show error message
function showError(message, containerId = 'error-container') {
    const errorDiv = document.getElementById(containerId);
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

// Set active navigation item
function setActiveNav(currentPage) {
    const navLinks = document.querySelectorAll('.nav a');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
}

// Format timestamp
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

// Common API request function
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

// Load agent card information
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

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
});
