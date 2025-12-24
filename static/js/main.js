// main.js - Keep only unique utility functions

// Format date utility
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// CSRF token utility (if not in gallery.html)
async function ensureCSRFToken() {
    function getCSRFToken() {
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
                    return token;
                }
            }
        }
        return null;
    }
    
    async function fetchCSRFToken() {
        try {
            const response = await fetch('/api/test-csrf');
            const data = await response.json();
            if (data.csrf_token) {
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
    
    let token = getCSRFToken();
    if (!token) {
        token = await fetchCSRFToken();
    }
    return token;
}

// Notification utility (if not in gallery.html)
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
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : '#2196F3'};
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

// Add CSS for animations if not already added
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
    `;
    document.head.appendChild(style);
}

// Photo upload preview
document.addEventListener('DOMContentLoaded', function() {
    const photoUpload = document.getElementById('photoUpload');
    if (photoUpload) {
        photoUpload.addEventListener('change', function(e) {
            const file = e.target.files[0];
            const preview = document.getElementById('photoPreview');
            
            if (file && preview) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Auto-remove flash messages
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });
});