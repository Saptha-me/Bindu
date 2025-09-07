// Common Layout Component Loader
class LayoutManager {
    constructor() {
        this.components = {
            header: '/components/header.html',
            footer: '/components/footer.html'
        };
    }

    async loadComponent(name) {
        try {
            const response = await fetch(this.components[name]);
            if (!response.ok) {
                throw new Error(`Failed to load ${name}: ${response.statusText}`);
            }
            return await response.text();
        } catch (error) {
            console.error(`Error loading ${name} component:`, error);
            return '';
        }
    }

    async loadHeader() {
        const headerHTML = await this.loadComponent('header');
        const headerContainer = document.getElementById('header-container');
        if (headerContainer) {
            headerContainer.innerHTML = headerHTML;
            this.initializeNavigation();
        }
    }

    async loadFooter() {
        const footerHTML = await this.loadComponent('footer');
        const footerContainer = document.getElementById('footer-container');
        if (footerContainer) {
            footerContainer.innerHTML = footerHTML;
        }
    }

    initializeNavigation() {
        // Set active navigation based on current page
        const currentPage = window.location.pathname.split('/').pop().replace('.html', '') || 'agent';
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const page = link.getAttribute('data-page');
            if (page === currentPage) {
                link.classList.add('border-blue-500', 'text-blue-600', 'dark:text-blue-400');
                link.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');
            } else {
                link.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400', 'hover:text-gray-700', 'dark:hover:text-gray-300', 'hover:border-gray-300', 'dark:hover:border-gray-600');
                link.classList.remove('border-blue-500', 'text-blue-600', 'dark:text-blue-400');
            }
        });

        // Set page subtitle
        const pageSubtitle = document.getElementById('page-subtitle');
        if (pageSubtitle) {
            const subtitles = {
                'agent': 'Agent Information & Capabilities',
                'chat': 'Interactive Chat Interface',
                'storage': 'Task History & Storage Management',
                'docs': 'API Documentation & Examples'
            };
            pageSubtitle.textContent = subtitles[currentPage] || '';
        }
    }

    async initialize() {
        await Promise.all([
            this.loadHeader(),
            this.loadFooter()
        ]);
    }
}

// Initialize layout when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    const layoutManager = new LayoutManager();
    await layoutManager.initialize();
});

// Export for use in other scripts
window.LayoutManager = LayoutManager;
