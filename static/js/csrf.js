// csrf.js - CSRF Token Helper Functions
function getCSRFToken() {
    // Try multiple ways to get CSRF token
    const tokenSelectors = [
        'meta[name="csrf-token"]',
        'input[name="csrf_token"]',
        'input[name="csrf-token"]'
    ];
    
    for (const selector of tokenSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            const token = element.getAttribute('content') || element.value;
            if (token && token !== 'None' && token !== '') {
                console.log('CSRF token found:', token.substring(0, 10) + '...');
                return token;
            }
        }
    }
    
    console.warn('CSRF token not found. Trying to fetch from API...');
    return null;
}

async function fetchCSRFToken() {
    try {
        const response = await fetch('/api/test-csrf');
        const data = await response.json();
        if (data.csrf_token) {
            // Store it in a meta tag for future use
            let metaTag = document.querySelector('meta[name="csrf-token"]');
            if (!metaTag) {
                metaTag = document.createElement('meta');
                metaTag.name = 'csrf-token';
                document.head.appendChild(metaTag);
            }
            metaTag.setAttribute('content', data.csrf_token);
            return data.csrf_token;
        }
    } catch (error) {
        console.error('Failed to fetch CSRF token:', error);
    }
    return null;
}

async function ensureCSRFToken() {
    let token = getCSRFToken();
    if (!token) {
        token = await fetchCSRFToken();
    }
    return token;
}

// Global notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    document.querySelectorAll('.custom-notification').forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `custom-notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : type === 'warning' ? '#FF9800' : '#2196F3'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        font-family: inherit;
        font-size: 14px;
        max-width: 300px;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Add CSS for animations
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .custom-notification {
            position: fixed !important;
            top: 20px !important;
            right: 20px !important;
            z-index: 10000 !important;
        }
    `;
    document.head.appendChild(style);
}