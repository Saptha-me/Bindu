// Layout component loader
document.addEventListener('DOMContentLoaded', async () => {
    // Load header
    const headerContainer = document.getElementById('header-container');
    if (headerContainer) {
        try {
            const response = await fetch('/components/header.html');
            const html = await response.text();
            headerContainer.innerHTML = html;
        } catch (error) {
            console.error('Failed to load header:', error);
        }
    }

    // Load footer
    const footerContainer = document.getElementById('footer-container');
    if (footerContainer) {
        try {
            const response = await fetch('/components/footer.html');
            const html = await response.text();
            footerContainer.innerHTML = html;
        } catch (error) {
            console.error('Failed to load footer:', error);
        }
    }
});
