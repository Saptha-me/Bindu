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
 * DOM element cache for performance
 * @type {Object}
 */
const elements = {};

/**
 * Element ID constants
 * @const
 */
const ELEMENT_IDS = {
    HEADER_NAME: 'header-agent-name',
    HEADER_SUBTITLE: 'header-agent-subtitle',
    AGENT_STATS: 'agent-stats',
    AGENT_SETTINGS: 'agent-settings',
    TECHNICAL_DETAILS: 'technical-details',
    CAPABILITIES_SECTION: 'capabilities-section',
    CAPABILITIES_LIST: 'capabilities-list',
    SKILLS_LIST: 'skills-list',
    IDENTITY_TRUST_LIST: 'identity-trust-list',
    EXTENSIONS_LIST: 'extensions-list'
};

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
 * Load and display all agent information
 * Main entry point for rendering the agent page
 * @async
 */
async function loadAndDisplayAgent() {
    try {
        agentCard = await api.loadAgentCard();
        
        if (!agentCard) {
            throw new Error('Agent card data is empty');
        }
        
        // Execute all display functions with individual error handling
        const displayFunctions = [
            { fn: displayAgentCard, name: 'Agent Card' },
            { fn: displayCapabilities, name: 'Capabilities' },
            { fn: displaySkills, name: 'Skills' },
            { fn: displayTechnicalDetails, name: 'Technical Details' },
            { fn: displayIdentityTrust, name: 'Identity & Trust' },
            { fn: displayExtensions, name: 'Extensions' }
        ];
        
        displayFunctions.forEach(({ fn, name }) => {
            try {
                fn();
            } catch (err) {
                console.error(`Error displaying ${name}:`, err);
            }
        });
    } catch (error) {
        console.error('Error loading agent card:', error);
        getElement(ELEMENT_IDS.HEADER_NAME).textContent = 'Unknown Agent';
        getElement(ELEMENT_IDS.HEADER_SUBTITLE).textContent = 'Unable to load agent information';
        utils.showToast('Failed to load agent information: ' + error.message, 'error');
    }
}

/**
 * Display main agent card information in the header and stats sections
 */
function displayAgentCard() {
    // Update header
    getElement(ELEMENT_IDS.HEADER_NAME).textContent = agentCard.name;
    getElement(ELEMENT_IDS.HEADER_SUBTITLE).textContent = agentCard.description || 'AI Agent';

    // Display stats
    const statsHtml = [
        utils.createStatCard('tag', 'Version', agentCard.version),
        utils.createStatCard('globe-alt', 'Protocol', `v${agentCard.protocolVersion}`),
        utils.createStatCard('chart-bar', 'Kind', agentCard.kind || 'Agent'),
        utils.createStatCard('clock', 'Sessions', agentCard.numHistorySessions || 0)
    ].join('');
    getElement(ELEMENT_IDS.AGENT_STATS).innerHTML = statsHtml;

    // Display settings
    const settingsHtml = createSettingsSection();
    getElement(ELEMENT_IDS.AGENT_SETTINGS).innerHTML = settingsHtml;
}

/**
 * Create settings section HTML
 * @returns {string} HTML for settings section
 */
function createSettingsSection() {
    const debugValue = agentCard.debugMode ? `Level ${agentCard.debugLevel}` : 'Disabled';
    const monitoringValue = agentCard.monitoring ? 'Enabled' : 'Disabled';
    const telemetryValue = agentCard.telemetry ? 'Enabled' : 'Disabled';
    
    return `
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
    const technicalHtml = `
        ${utils.createTechnicalDetail('URL', agentCard.url, true)}
        ${utils.createTechnicalDetail('DID', agentCard.identity?.did || 'did:pebble:c94a3e7aa41540a5b25ee342f0908ad')}
    `;
    getElement(ELEMENT_IDS.TECHNICAL_DETAILS).innerHTML = technicalHtml;
}

/**
 * Display agent capabilities (streaming, push notifications, etc.)
 */
function displayCapabilities() {
    const capabilities = agentCard.capabilities;
    
    if (!capabilities || Object.keys(capabilities).length === 0) {
        getElement(ELEMENT_IDS.CAPABILITIES_SECTION).style.display = 'none';
        return;
    }

    getElement(ELEMENT_IDS.CAPABILITIES_SECTION).style.display = 'block';
    
    const capabilitiesHtml = [
        utils.createSettingRow('Streaming', utils.yesNo(capabilities.streaming), capabilities.streaming),
        utils.createSettingRow('Push Notifications', utils.yesNo(capabilities.pushNotifications), capabilities.pushNotifications),
        utils.createSettingRow('State History', utils.yesNo(capabilities.stateTransitionHistory), capabilities.stateTransitionHistory)
    ].join('');
    
    getElement(ELEMENT_IDS.CAPABILITIES_LIST).innerHTML = capabilitiesHtml;
}

/**
 * Display agent skills
 */
function displaySkills() {
    const skills = agentCard.skills;
    const skillsElement = getElement(ELEMENT_IDS.SKILLS_LIST);
    
    if (!skills || skills.length === 0) {
        skillsElement.innerHTML = utils.createEmptyState('No skills defined', 'puzzle-piece', 'w-8 h-8');
        return;
    }

    skillsElement.innerHTML = skills.map(skill => utils.createSkillCard(skill)).join('');
}

/**
 * Display identity and trust information
 */
function displayIdentityTrust() {
    const identityTrustElement = getElement(ELEMENT_IDS.IDENTITY_TRUST_LIST);
    const identity = agentCard.identity;
    
    if (!identity) {
        identityTrustElement.innerHTML = utils.createEmptyState('No identity information available', 'shield-check', 'w-8 h-8');
        return;
    }

    const identityHtml = createIdentitySection(identity);
    identityTrustElement.innerHTML = identityHtml;
}

/**
 * Create identity section HTML
 * @param {Object} identity - Identity object from agent card
 * @returns {string} HTML for identity section
 */
function createIdentitySection(identity) {
    const agentTrust = agentCard.agentTrust || 'unknown';
    const publicKeyPem = extractPublicKey(identity);
    const publicKeyContent = createPublicKeyContent(publicKeyPem);
    const csrContent = createCsrContent(identity.csr);
    const trustBadge = createTrustBadge(agentTrust);
    
    return `
        <div class="space-y-3">
            ${utils.createDropdown('public-key-dropdown', 'Public Key', !!publicKeyPem, publicKeyContent)}
            ${utils.createDropdown('csr-dropdown', 'CSR Path', !!identity.csr, csrContent)}
            ${trustBadge}
            ${createDidDocumentInfo(identity)}
        </div>
    `;
}

/**
 * Extract public key from DID document
 * @param {Object} identity - Identity object
 * @returns {string|null} Public key PEM or null
 */
function extractPublicKey(identity) {
    return identity.didDocument?.verificationMethod?.[0]?.publicKeyPem || null;
}

/**
 * Create public key dropdown content
 * @param {string|null} publicKeyPem - Public key PEM
 * @returns {string} HTML content
 */
function createPublicKeyContent(publicKeyPem) {
    if (!publicKeyPem) {
        return '<div class="text-sm text-gray-500">No public key available</div>';
    }
    
    return `
        <div class="space-y-2">
            <div class="text-xs text-gray-500 font-medium">Full Public Key:</div>
            <div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div class="font-mono text-xs break-all text-gray-600 leading-relaxed">
                    ${publicKeyPem}
                </div>
            </div>
        </div>
    `;
}

/**
 * Create CSR dropdown content
 * @param {string|null} csr - CSR path
 * @returns {string} HTML content
 */
function createCsrContent(csr) {
    if (!csr) {
        return '<div class="text-sm text-gray-500">No CSR path available</div>';
    }
    
    return `
        <div class="space-y-2">
            <div class="text-xs text-gray-500 font-medium">Certificate Signing Request Path:</div>
            <div class="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div class="font-mono text-sm text-gray-600 break-all">
                    ${csr}
                </div>
            </div>
        </div>
    `;
}

/**
 * Create trust level badge HTML
 * @param {string} agentTrust - Trust level
 * @returns {string} HTML for trust badge
 */
function createTrustBadge(agentTrust) {
    const trustBadgeType = utils.getTrustBadgeType(agentTrust);
    const trustBadgeClass = utils.getBadgeClass(trustBadgeType);
    const trustLabel = utils.getTrustLabel(agentTrust);
    
    return `
        <div class="p-3 border border-gray-200 rounded-lg">
            <div class="text-sm font-medium text-gray-500 mb-1">Trust Level</div>
            <div class="flex items-center justify-between">
                <span class="text-gray-600 capitalize">${agentTrust}</span>
                <div class="px-2 py-1 ${trustBadgeClass} border rounded text-xs">
                    ${trustLabel}
                </div>
            </div>
        </div>
    `;
}

/**
 * Create DID document info HTML
 * @param {Object} identity - Identity object
 * @returns {string} HTML for DID document info
 */
function createDidDocumentInfo(identity) {
    const methodCount = identity.didDocument?.verificationMethod?.length || 0;
    
    return `
        <div class="p-3 border border-gray-200 rounded-lg">
            <div class="text-sm font-medium text-gray-500 mb-1">DID Document</div>
            <div class="text-xs text-gray-600">Present (${methodCount} methods)</div>
        </div>
    `;
}

/**
 * Display agent extensions
 */
function displayExtensions() {
    getElement(ELEMENT_IDS.EXTENSIONS_LIST).innerHTML = utils.createEmptyState('No extensions available');
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
