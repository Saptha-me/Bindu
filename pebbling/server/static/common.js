// Common JavaScript functions for all Pebbling pages

// Generate a proper UUID v4
function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
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
