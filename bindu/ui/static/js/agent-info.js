/**
 * Agent Info Module
 * Handles loading and displaying agent information and skills
 */

import { state, BASE_URL } from './state.js';

export async function loadAgentInfo() {
    try {
        const manifestResponse = await fetch(`${BASE_URL}/.well-known/agent.json`);
        const manifest = manifestResponse.ok ? await manifestResponse.json() : {};

        const skillsResponse = await fetch(`${BASE_URL}/agent/skills`);
        const skillsData = skillsResponse.ok ? await skillsResponse.json() : { skills: [] };

        state.agentInfo = { manifest, skills: skillsData.skills || [] };
        displayAgentInfo();
        displaySkills();
    } catch (error) {
        console.error('Error loading agent info:', error);
        document.getElementById('agent-info-content').innerHTML =
            '<div class="error" style="display:block;">Failed to load agent information</div>';
    }
}

export function displayAgentInfo() {
    if (!state.agentInfo) return;

    const { manifest } = state.agentInfo;
    const container = document.getElementById('agent-info-content');
    
    // Format JSON with syntax highlighting
    const jsonString = JSON.stringify(manifest, null, 4);
    
    let html = `
        <div class="info-section">
            <h3>${manifest.name || 'Unknown Agent'}</h3>
            <p style="color: #666; font-size: 11px; margin-top: 8px;">${manifest.description || 'No description available'}</p>
        </div>
        
        <div class="info-section">
            <h3>Details</h3>
            <div class="info-grid">
                <div class="info-label">Author:</div>
                <div class="info-value">${manifest.capabilities?.extensions?.[0]?.params?.author || 'Unknown'}</div>
                
                <div class="info-label">Version:</div>
                <div class="info-value">${manifest.version || 'N/A'}</div>
                
                ${manifest.url ? `
                    <div class="info-label">URL:</div>
                    <div class="info-value">${manifest.url}</div>
                ` : ''}
            </div>
        </div>
        
        <div class="info-section">
            <h3>Complete Agent Card (JSON)</h3>
            <div class="json-viewer">
                <button class="copy-json-btn" onclick="window.copyAgentCardJSON()">📋 Copy JSON</button>
                <pre><code>${escapeHtml(jsonString)}</code></pre>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

export function displaySkills() {
    if (!state.agentInfo || !state.agentInfo.skills) return;

    const container = document.getElementById('skills-content');
    const { skills } = state.agentInfo;

    if (skills.length === 0) {
        container.innerHTML = '<div class="loading">No skills available</div>';
        return;
    }

    let html = skills.map(skill => `
        <div class="skill-item">
            <div class="skill-name">${skill.name || skill.id || 'Unknown Skill'}</div>
            ${skill.description ? `<div class="skill-description">${skill.description}</div>` : ''}
        </div>
    `).join('');

    container.innerHTML = html;
}

export function copyAgentCardJSON() {
    if (!state.agentInfo || !state.agentInfo.manifest) return;
    
    const jsonString = JSON.stringify(state.agentInfo.manifest, null, 4);
    navigator.clipboard.writeText(jsonString).then(() => {
        const btn = document.querySelector('.copy-json-btn');
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
