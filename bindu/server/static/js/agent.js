/**
 * Agent page logic
 * Handles displaying agent information and capabilities
 * @module agent
 */

/**
 * Cached agent card data
 * @type {Object|null}
 */
let agentCard = null;

/**
 * Load and display all agent information
 * Main entry point for rendering the agent page
 * @async
 */
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

/**
 * Display main agent card information in the header and stats sections
 */
function displayAgentCard() {
    if (!agentCard) return;

    // Update header
    document.getElementById('header-agent-name').textContent = agentCard.name;
    document.getElementById('header-agent-subtitle').textContent = agentCard.description || 'AI Agent';

    // Display stats
    const statsDiv = document.getElementById('agent-stats');
    statsDiv.innerHTML = [
        utils.createStatCard('tag', 'Version', agentCard.version),
        utils.createStatCard('globe-alt', 'Protocol', `v${agentCard.protocolVersion}`),
        utils.createStatCard('chart-bar', 'Kind', agentCard.kind || 'Agent'),
        utils.createStatCard('clock', 'Sessions', agentCard.numHistorySessions || 0)
    ].join('');

    // Display settings
    const settingsDiv = document.getElementById('agent-settings');
    const debugValue = agentCard.debugMode ? `Level ${agentCard.debugLevel}` : 'Disabled';
    const monitoringValue = agentCard.monitoring ? 'Enabled' : 'Disabled';
    const telemetryValue = agentCard.telemetry ? 'Enabled' : 'Disabled';
    
    settingsDiv.innerHTML = `
        <div class="space-y-3">
            ${utils.createSettingRow('Debug', debugValue)}
            ${utils.createSettingRow('Monitoring', monitoringValue, agentCard.monitoring)}
            ${utils.createSettingRow('Telemetry', telemetryValue, agentCard.telemetry)}
        </div>
        <div class="space-y-3">
            ${utils.createSettingRow('Trust Level', `<span class="capitalize">${agentCard.agentTrust || 'Unknown'}</span>`)}
            ${utils.createSettingRow('Identity Provider', 'Pebble Protocol')}
            ${utils.createSettingRow('Agent ID', `<span class="font-mono text-xs">${agentCard.id || 'Unknown'}</span>`)}
        </div>
    `;
}

/**
 * Display technical details (URL and DID)
 */
function displayTechnicalDetails() {
    if (!agentCard) return;

    const technicalDiv = document.getElementById('technical-details');
    technicalDiv.innerHTML = `
        ${utils.createTechnicalDetail('URL', agentCard.url, true)}
        ${utils.createTechnicalDetail('DID', agentCard.identity?.did || 'did:pebble:c94a3e7aa41540a5b25ee342f0908ad')}
    `;
}

/**
 * Display agent capabilities (streaming, push notifications, etc.)
 */
function displayCapabilities() {
    if (!agentCard || !agentCard.capabilities || Object.keys(agentCard.capabilities).length === 0) {
        document.getElementById('capabilities-section').style.display = 'none';
        return;
    }

    document.getElementById('capabilities-section').style.display = 'block';
    const capabilities = agentCard.capabilities;
    const capabilitiesDiv = document.getElementById('capabilities-list');

    capabilitiesDiv.innerHTML = [
        utils.createSettingRow('Streaming', utils.yesNo(capabilities.streaming), capabilities.streaming),
        utils.createSettingRow('Push Notifications', utils.yesNo(capabilities.pushNotifications), capabilities.pushNotifications),
        utils.createSettingRow('State History', utils.yesNo(capabilities.stateTransitionHistory), capabilities.stateTransitionHistory)
    ].join('');
}

/**
 * Display agent skills
 */
function displaySkills() {
    if (!agentCard || !agentCard.skills || agentCard.skills.length === 0) {
        document.getElementById('skills-list').innerHTML = utils.createEmptyState('No skills defined', 'puzzle-piece', 'w-8 h-8');
        return;
    }

    const skillsDiv = document.getElementById('skills-list');
    skillsDiv.innerHTML = agentCard.skills.map(skill => utils.createSkillCard(skill)).join('');
}

/**
 * Display identity and trust information
 */
function displayIdentityTrust() {
    const identityTrustDiv = document.getElementById('identity-trust-list');
    
    if (!agentCard || !agentCard.identity) {
        identityTrustDiv.innerHTML = utils.createEmptyState('No identity information available', 'shield-check', 'w-8 h-8');
        return;
    }

    const identity = agentCard.identity;
    const agentTrust = agentCard.agentTrust || 'unknown';
    
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

    // Trust level badge using common utilities
    const trustBadgeType = utils.getTrustBadgeType(agentTrust);
    const trustBadgeClass = utils.getBadgeClass(trustBadgeType);
    const trustLabel = utils.getTrustLabel(agentTrust);

    identityTrustDiv.innerHTML = `
        <div class="space-y-3">
            ${utils.createDropdown('public-key-dropdown', 'Public Key', !!publicKeyPem, publicKeyContent)}
            ${utils.createDropdown('csr-dropdown', 'CSR Path', !!identity.csr, csrContent)}
            
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

/**
 * Display agent extensions
 */
function displayExtensions() {
    const extensionsDiv = document.getElementById('extensions-list');
    extensionsDiv.innerHTML = utils.createEmptyState('No extensions available');
}

/**
 * Initialize section header icons
 * Adds visual icons to each section header
 */
function initializeSectionIcons() {
    const sections = [
        { id: 'capabilities-header', icon: 'chart-bar' },
        { id: 'skills-header', icon: 'computer-desktop' },
        { id: 'identity-header', icon: 'shield-check' },
        { id: 'extensions-header', icon: 'puzzle-piece' }
    ];
    
    sections.forEach(({ id, icon }) => {
        const header = document.getElementById(id);
        if (header) {
            header.insertAdjacentHTML('afterbegin', utils.createIcon(icon, 'w-5 h-5 text-yellow-600'));
        }
    });
}

/**
 * Initialize the agent page on DOM ready
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeSectionIcons();
    loadAndDisplayAgent();
});
