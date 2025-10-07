// Agent page logic
// Handles displaying agent information and capabilities

let agentCard = null;

// Constants
const TRUST_LABELS = {
    low: 'Low Trust',
    medium: 'Medium Trust',
    high: 'High Trust'
};

const TRUST_BADGE_TYPES = {
    low: 'error',
    medium: 'warning',
    high: 'success'
};

// Helper functions
const yesNo = (value) => value ? 'Yes' : 'No';

// Component helper functions
function createStatCard(icon, label, value) {
    return `
        <div class="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div class="flex items-center gap-2 mb-2">
                ${utils.createIcon(icon, 'w-4 h-4 text-gray-500')}
                <span class="text-sm font-medium text-gray-500">${label}</span>
            </div>
            <div class="font-mono text-lg font-semibold text-gray-900">${value}</div>
        </div>
    `;
}

function createSettingRow(label, value, isEnabled = null) {
    const badgeType = isEnabled === null ? 'neutral' : (isEnabled ? 'success' : 'error');
    const badgeClass = utils.getBadgeClass(badgeType);
    
    return `
        <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
            <span class="font-medium text-gray-900">${label}</span>
            <div class="px-3 py-1 ${badgeClass} border rounded-full text-sm font-medium">
                ${value}
            </div>
        </div>
    `;
}

function createEmptyState(message, iconSize = 'w-12 h-12') {
    return `
        <div class="text-center py-8 text-gray-500">
            ${utils.createIcon('puzzle-piece', `${iconSize} mx-auto mb-3 text-gray-300`)}
            <div class="text-sm">${message}</div>
        </div>
    `;
}

function createDropdown(id, title, isAvailable, content) {
    const badgeType = isAvailable ? 'success' : 'error';
    const statusBadge = utils.getBadgeClass(badgeType);
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
                ${utils.createIcon('chevron-down', 'dropdown-icon w-4 h-4 text-gray-400')}
            </div>
            <div id="${id}" class="dropdown-content bg-white">
                ${content}
            </div>
        </div>
    `;
}

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
    statsDiv.innerHTML = [
        createStatCard('tag', 'Version', agentCard.version),
        createStatCard('globe-alt', 'Protocol', `v${agentCard.protocolVersion}`),
        createStatCard('chart-bar', 'Kind', agentCard.kind || 'Agent'),
        createStatCard('clock', 'Sessions', agentCard.numHistorySessions || 0)
    ].join('');

    // Display settings
    const settingsDiv = document.getElementById('agent-settings');
    const debugValue = agentCard.debugMode ? `Level ${agentCard.debugLevel}` : 'Disabled';
    const monitoringValue = agentCard.monitoring ? 'Enabled' : 'Disabled';
    const telemetryValue = agentCard.telemetry ? 'Enabled' : 'Disabled';
    
    settingsDiv.innerHTML = `
        <div class="space-y-3">
            ${createSettingRow('Debug', debugValue)}
            ${createSettingRow('Monitoring', monitoringValue, agentCard.monitoring)}
            ${createSettingRow('Telemetry', telemetryValue, agentCard.telemetry)}
        </div>
        <div class="space-y-3">
            ${createSettingRow('Trust Level', `<span class="capitalize">${agentCard.agentTrust || 'Unknown'}</span>`)}
            ${createSettingRow('Identity Provider', 'Pebble Protocol')}
            ${createSettingRow('Agent ID', `<span class="font-mono text-xs">${agentCard.id || 'Unknown'}</span>`)}
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

    capabilitiesDiv.innerHTML = [
        createSettingRow('Streaming', yesNo(capabilities.streaming), capabilities.streaming),
        createSettingRow('Push Notifications', yesNo(capabilities.pushNotifications), capabilities.pushNotifications),
        createSettingRow('State History', yesNo(capabilities.stateTransitionHistory), capabilities.stateTransitionHistory)
    ].join('');
}

// Display skills
function displaySkills() {
    if (!agentCard || !agentCard.skills || agentCard.skills.length === 0) {
        document.getElementById('skills-list').innerHTML = createEmptyState('No skills defined', 'w-8 h-8');
        return;
    }

    const skillsDiv = document.getElementById('skills-list');
    skillsDiv.innerHTML = agentCard.skills.map(skill => createSkillCard(skill)).join('');
}

// Display identity and trust information
function displayIdentityTrust() {
    const identityTrustDiv = document.getElementById('identity-trust-list');
    
    if (!agentCard || !agentCard.identity) {
        identityTrustDiv.innerHTML = createEmptyState('No identity information available', 'w-8 h-8');
        return;
    }

    const identity = agentCard.identity;
    const agentTrust = agentCard.agentTrust || 'Unknown';
    
    // Get public key from DID document
    let publicKeyPem = null;
    if (identity.didDocument && identity.didDocument.verificationMethod && identity.didDocument.verificationMethod.length > 0) {
        publicKeyPem = identity.didDocument.verificationMethod[0].publicKeyPem;
    }

    // Create dropdown content
    const publicKeyContent = publicKeyPem ? `
        <div class="space-y-2">
            <div class="text-xs text-gray-500 font-medium">Full Public Key:</div>
            <div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div class="font-mono text-xs break-all text-gray-600 leading-relaxed">
                    ${publicKeyPem}
                </div>
            </div>
        </div>
    ` : '<div class="text-sm text-gray-500">No public key available</div>';

    const csrContent = identity.csr ? `
        <div class="space-y-2">
            <div class="text-xs text-gray-500 font-medium">Certificate Signing Request Path:</div>
            <div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div class="font-mono text-sm text-gray-600 break-all">
                    ${identity.csr}
                </div>
            </div>
        </div>
    ` : '<div class="text-sm text-gray-500">No CSR path available</div>';

    // Trust level badge
    const trustBadgeType = TRUST_BADGE_TYPES[agentTrust] || 'neutral';
    const trustBadgeClass = utils.getBadgeClass(trustBadgeType);
    const trustLabel = TRUST_LABELS[agentTrust] || 'Unknown';

    identityTrustDiv.innerHTML = `
        <div class="space-y-3">
            ${createDropdown('public-key-dropdown', 'Public Key', !!publicKeyPem, publicKeyContent)}
            ${createDropdown('csr-dropdown', 'CSR Path', !!identity.csr, csrContent)}
            
            <div class="p-3 border border-gray-200 rounded-lg">
                <div class="text-sm font-medium text-gray-500 mb-1">Trust Level</div>
                <div class="flex items-center justify-between">
                    <span class="text-gray-600 capitalize">${agentTrust}</span>
                    <div class="px-2 py-1 ${trustBadgeClass} border rounded text-xs">
                        ${trustLabel}
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
    extensionsDiv.innerHTML = createEmptyState('No extensions available');
}

// Add icons to section headers
function initializeSectionIcons() {
    // Add icon to Capabilities header
    const capabilitiesHeader = document.getElementById('capabilities-header');
    if (capabilitiesHeader) {
        capabilitiesHeader.insertAdjacentHTML('afterbegin', utils.createIcon('chart-bar', 'w-5 h-5 text-yellow-600'));
    }
    
    // Add icon to Skills header
    const skillsHeader = document.getElementById('skills-header');
    if (skillsHeader) {
        skillsHeader.insertAdjacentHTML('afterbegin', utils.createIcon('computer-desktop', 'w-5 h-5 text-yellow-600'));
    }
    
    // Add icon to Identity header
    const identityHeader = document.getElementById('identity-header');
    if (identityHeader) {
        identityHeader.insertAdjacentHTML('afterbegin', utils.createIcon('shield-check', 'w-5 h-5 text-yellow-600'));
    }
    
    // Add icon to Extensions header
    const extensionsHeader = document.getElementById('extensions-header');
    if (extensionsHeader) {
        extensionsHeader.insertAdjacentHTML('afterbegin', utils.createIcon('puzzle-piece', 'w-5 h-5 text-yellow-600'));
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSectionIcons();
    loadAndDisplayAgent();
});
