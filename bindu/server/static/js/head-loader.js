// Synchronously inject common head content
// This must run before page renders to avoid FOUC

(function() {
    // Add meta tags
    const meta = document.createElement('meta');
    meta.charset = 'UTF-8';
    document.head.appendChild(meta);
    
    const viewport = document.createElement('meta');
    viewport.name = 'viewport';
    viewport.content = 'width=device-width, initial-scale=1.0';
    document.head.appendChild(viewport);
    
    // Add Tailwind CSS CDN
    const tailwindScript = document.createElement('script');
    tailwindScript.src = 'https://cdn.tailwindcss.com';
    document.head.appendChild(tailwindScript);
    
    // Add Tailwind config
    const configScript = document.createElement('script');
    configScript.textContent = `
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        'primary-yellow': '#f9dc5c',
                    },
                    fontFamily: {
                        'geist': ['Geist', 'sans-serif'],
                        'geist-mono': ['Geist Mono', 'monospace'],
                    }
                }
            }
        }
    `;
    document.head.appendChild(configScript);
    
    // Add Iconify
    const iconifyScript = document.createElement('script');
    iconifyScript.src = 'https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js';
    document.head.appendChild(iconifyScript);
    
    // Add custom CSS
    const customCSS = document.createElement('link');
    customCSS.rel = 'stylesheet';
    customCSS.href = 'css/custom.css';
    document.head.appendChild(customCSS);
})();
