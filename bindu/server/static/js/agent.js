// Agent page logic
// Handles displaying agent information and capabilities

let agentCard = null;

// Load and display agent information
async function loadAndDisplayAgent() {
    try {
        agentCard = await api.loadAgentCard();
        
        displayAgentCard();
        displayCapabilities();
        displaySkills();
        displayTechnicalDetails();
        displayIdentityTrust();
        displayExtensions();
    } catch (error) {
        console.error('Error loading agent card:', error);
        document.getElementById('header-agent-name').textContent = 'Unknown Agent';
        document.getElementById('header-agent-subtitle').textContent = 'Unable to load agent information';
        utils.showToast('Failed to load agent information: ' + error.message, 'error');
    }
}

// Display main agent card information
function displayAgentCard() {
    if (!agentCard) return;

    // Update header
    document.getElementById('header-agent-name').textContent = agentCard.name;
    document.getElementById('header-agent-subtitle').textContent = agentCard.description || 'AI Agent';

    // Display stats
    const statsDiv = document.getElementById('agent-stats');
    statsDiv.innerHTML = `
        <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div class="flex items-center gap-2 mb-2">
                ${utils.createIcon('tag', 'w-4 h-4 text-gray-500')}
                <span class="text-sm font-medium text-gray-500">Version</span>
            </div>
            <div class="font-mono text-lg font-semibold text-gray-900">${agentCard.version}</div>
        </div>
        <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div class="flex items-center gap-2 mb-2">
                ${utils.createIcon('globe-alt', 'w-4 h-4 text-gray-500')}
                <span class="text-sm font-medium text-gray-500">Protocol</span>
            </div>
            <div class="font-mono text-lg font-semibold text-gray-900">v${agentCard.protocolVersion}</div>
        </div>
        <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div class="flex items-center gap-2 mb-2">
                ${utils.createIcon('chart-bar', 'w-4 h-4 text-gray-500')}
                <span class="text-sm font-medium text-gray-500">Kind</span>
            </div>
            <div class="font-mono text-lg font-semibold text-gray-900">${agentCard.kind || 'Agent'}</div>
        </div>
        <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div class="flex items-center gap-2 mb-2">
                ${utils.createIcon('clock', 'w-4 h-4 text-gray-500')}
                <span class="text-sm font-medium text-gray-500">Sessions</span>
            </div>
            <div class="font-mono text-lg font-semibold text-gray-900">${agentCard.numHistorySessions || 0}</div>
        </div>
    `;

    // Display settings
    const settingsDiv = document.getElementById('agent-settings');
    settingsDiv.innerHTML = `
        <div class="space-y-3">
            <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                <span class="font-medium text-gray-900">Debug</span>
                <div class="px-3 py-1 bg-gray-100 text-gray-700 border border-gray-200 rounded-full text-sm font-medium">
                    ${agentCard.debugMode ? 'Level ' + agentCard.debugLevel : 'Disabled'}
                </div>
            </div>
            <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                <span class="font-medium text-gray-900">Monitoring</span>
                <div class="px-3 py-1 ${agentCard.monitoring ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded-full text-sm font-medium">
                    ${agentCard.monitoring ? 'Enabled' : 'Disabled'}
                </div>
            </div>
            <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                <span class="font-medium text-gray-900">Telemetry</span>
                <div class="px-3 py-1 ${agentCard.telemetry ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded-full text-sm font-medium">
                    ${agentCard.telemetry ? 'Enabled' : 'Disabled'}
                </div>
            </div>
        </div>
        <div class="space-y-3">
            <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                <span class="font-medium text-gray-900">Trust Level</span>
                <span class="text-gray-600 capitalize">${agentCard.agentTrust || 'Unknown'}</span>
            </div>
            <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                <span class="font-medium text-gray-900">Identity Provider</span>
                <span class="text-gray-600">Pebble Protocol</span>
            </div>
            <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                <span class="font-medium text-gray-900">Agent ID</span>
                <span class="text-gray-600 font-mono text-xs">${agentCard.id || 'Unknown'}</span>
            </div>
        </div>
    `;
}

// Display technical details
function displayTechnicalDetails() {
    if (!agentCard) return;

    const technicalDiv = document.getElementById('technical-details');
    technicalDiv.innerHTML = `
        <div>
            <div class="text-sm font-medium text-gray-500 mb-2">URL</div>
            <div class="font-mono text-sm bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
                ${agentCard.url}
            </div>
        </div>
        <div>
            <div class="text-sm font-medium text-gray-500 mb-2">DID</div>
            <div class="font-mono text-xs bg-gray-50 rounded-lg px-3 py-2 border border-gray-200 break-all text-gray-600">
                ${agentCard.identity?.did || 'did:pebble:c94a3e7aa41540a5b25ee342f0908ad'}
            </div>
        </div>
    `;
}

// Display capabilities
function displayCapabilities() {
    if (!agentCard || !agentCard.capabilities || Object.keys(agentCard.capabilities).length === 0) {
        document.getElementById('capabilities-section').style.display = 'none';
        return;
    }

    document.getElementById('capabilities-section').style.display = 'block';
    const capabilities = agentCard.capabilities;
    const capabilitiesDiv = document.getElementById('capabilities-list');

    capabilitiesDiv.innerHTML = `
        <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
            <span class="font-medium text-gray-900">Streaming</span>
            <div class="px-3 py-1 ${capabilities.streaming ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded-full text-sm font-medium">
                ${capabilities.streaming ? 'Yes' : 'No'}
            </div>
        </div>
        <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
            <span class="font-medium text-gray-900">Push Notifications</span>
            <div class="px-3 py-1 ${capabilities.pushNotifications ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded-full text-sm font-medium">
                ${capabilities.pushNotifications ? 'Yes' : 'No'}
            </div>
        </div>
        <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
            <span class="font-medium text-gray-900">State History</span>
            <div class="px-3 py-1 ${capabilities.stateTransitionHistory ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded-full text-sm font-medium">
                ${capabilities.stateTransitionHistory ? 'Yes' : 'No'}
            </div>
        </div>
    `;
}

// Display skills
function displaySkills() {
    if (!agentCard || !agentCard.skills || agentCard.skills.length === 0) {
        document.getElementById('skills-list').innerHTML = 
            '<div class="text-center py-4 text-gray-500 text-sm">No skills defined</div>';
        return;
    }

    const skillsDiv = document.getElementById('skills-list');
    skillsDiv.innerHTML = `
        <div class="p-4 border border-yellow-200 bg-yellow-50 rounded-lg">
            <div class="flex items-start gap-3">
                <div class="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
                <div>
                    <div class="font-semibold text-yellow-700 mb-1">${agentCard.skills[0].name}</div>
                    <div class="text-sm text-gray-600">${agentCard.skills[0].description || 'Ability to answer basic questions'}</div>
                </div>
            </div>
        </div>
    `;
}

// Display identity and trust information
function displayIdentityTrust() {
    const identityTrustDiv = document.getElementById('identity-trust-list');
    
    if (!agentCard || !agentCard.identity) {
        identityTrustDiv.innerHTML = 
            '<div class="text-center py-4 text-gray-500 text-sm">No identity information available</div>';
        return;
    }

    const identity = agentCard.identity;
    const agentTrust = agentCard.agentTrust || 'Unknown';
    
    // Get public key from DID document
    let publicKeyPem = null;
    if (identity.didDocument && identity.didDocument.verificationMethod && identity.didDocument.verificationMethod.length > 0) {
        publicKeyPem = identity.didDocument.verificationMethod[0].publicKeyPem;
    }

    identityTrustDiv.innerHTML = `
        <div class="space-y-3">
            <div class="border border-gray-200 rounded-lg overflow-hidden">
                <div class="p-3 bg-gray-50 cursor-pointer flex items-center justify-between hover:bg-gray-100 transition-colors" onclick="utils.toggleDropdown('public-key-dropdown')">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-medium text-gray-700">Public Key</span>
                        <div class="px-2 py-1 ${publicKeyPem ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded text-xs">
                            ${publicKeyPem ? 'Available' : 'Not available'}
                        </div>
                    </div>
                    <svg class="dropdown-icon w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                </div>
                <div id="public-key-dropdown" class="dropdown-content bg-white">
                    ${publicKeyPem ? `
                    <div class="space-y-2">
                        <div class="text-xs text-gray-500 font-medium">Full Public Key:</div>
                        <div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <div class="font-mono text-xs break-all text-gray-600 leading-relaxed">
                                ${publicKeyPem}
                            </div>
                        </div>
                    </div>
                    ` : '<div class="text-sm text-gray-500">No public key available</div>'}
                </div>
            </div>
            
            <div class="border border-gray-200 rounded-lg overflow-hidden">
                <div class="p-3 bg-gray-50 cursor-pointer flex items-center justify-between hover:bg-gray-100 transition-colors" onclick="utils.toggleDropdown('csr-dropdown')">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-medium text-gray-700">CSR Path</span>
                        <div class="px-2 py-1 ${identity.csr ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded text-xs">
                            ${identity.csr ? 'Available' : 'Not available'}
                        </div>
                    </div>
                    <svg class="dropdown-icon w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                </div>
                <div id="csr-dropdown" class="dropdown-content bg-white">
                    ${identity.csr ? `
                    <div class="space-y-2">
                        <div class="text-xs text-gray-500 font-medium">Certificate Signing Request Path:</div>
                        <div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <div class="font-mono text-sm text-gray-600 break-all">
                                ${identity.csr}
                            </div>
                        </div>
                    </div>
                    ` : '<div class="text-sm text-gray-500">No CSR path available</div>'}
                </div>
            </div>
            
            <div class="p-3 border border-gray-200 rounded-lg">
                <div class="text-sm font-medium text-gray-500 mb-1">Trust Level</div>
                <div class="flex items-center justify-between">
                    <span class="text-gray-600 capitalize">${agentTrust}</span>
                    <div class="px-2 py-1 ${agentTrust === 'high' ? 'bg-green-50 text-green-700 border-green-200' : agentTrust === 'medium' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' : 'bg-red-50 text-red-700 border-red-200'} border rounded text-xs">
                        ${agentTrust === 'low' ? 'Low Trust' : agentTrust === 'medium' ? 'Medium Trust' : agentTrust === 'high' ? 'High Trust' : 'Unknown'}
                    </div>
                </div>
            </div>

            <div class="p-3 border border-gray-200 rounded-lg">
                <div class="text-sm font-medium text-gray-500 mb-1">DID Document</div>
                <div class="text-xs text-gray-600">Present (${identity.didDocument?.verificationMethod?.length || 0} methods)</div>
            </div>
        </div>
    `;
}

// Display extensions
function displayExtensions() {
    const extensionsDiv = document.getElementById('extensions-list');
    
    extensionsDiv.innerHTML = `
        <div class="text-center py-8 text-gray-500">
            <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M17 14v6m-3-3h6M6 10h2a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2zm10 0h2a2 2 0 002-2V6a2 2 0 00-2-2h-2a2 2 0 00-2 2v2a2 2 0 002 2zM6 20h2a2 2 0 002-2v-2a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2z"></path>
            </svg>
            <div class="text-sm">No extensions available</div>
        </div>
    `;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAndDisplayAgent();
});
